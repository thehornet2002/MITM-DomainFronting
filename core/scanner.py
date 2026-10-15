import socket
import ssl
import time
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

def test_tcp_ping(host, port=443, timeout=2.0):
    start = time.perf_counter()
    sock = None
    try:
        # Detect if IPv6
        is_ipv6 = ":" in host
        family = socket.AF_INET6 if is_ipv6 else socket.AF_INET
        sock = socket.socket(family, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        latency = (time.perf_counter() - start) * 1000.0
        return True, round(latency, 1), "OK"
    except socket.timeout:
        return False, None, "Timeout"
    except ConnectionRefusedError:
        return False, None, "Refused"
    except Exception as e:
        return False, None, str(e)[:25]
    finally:
        if sock:
            try:
                sock.close()
            except Exception:
                pass


def test_icmp_ping(host, timeout=2.0):
    start = time.perf_counter()
    try:
        timeout_ms = int(timeout * 1000)
        # Windows ping command
        cmd = ["ping", "-n", "1", "-w", str(timeout_ms), host]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout + 1)
        latency = (time.perf_counter() - start) * 1000.0
        if proc.returncode == 0 and ("TTL=" in proc.stdout or "ttl=" in proc.stdout):
            # Parse time from stdout if possible
            for line in proc.stdout.splitlines():
                if "time=" in line.lower() or "time<" in line.lower():
                    try:
                        part = line.lower().split("time")[1].split("ms")[0].replace("=", "").replace("<", "").strip()
                        return True, float(part), "OK"
                    except Exception:
                        pass
            return True, round(latency, 1), "OK"
        return False, None, "Loss"
    except subprocess.TimeoutExpired:
        return False, None, "Timeout"
    except Exception as e:
        return False, None, str(e)[:25]


def test_udp_ping(host, port=443, timeout=2.0):
    start = time.perf_counter()
    sock = None
    try:
        is_ipv6 = ":" in host
        family = socket.AF_INET6 if is_ipv6 else socket.AF_INET
        sock = socket.socket(family, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        # Send a dummy QUIC / DNS ping probe
        probe_packet = b"\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x03www\x06google\x03com\x00\x00\x01\x00\x01" if port == 53 else b"\x80" + b"\x00" * 31
        sock.sendto(probe_packet, (host, port))
        try:
            data, _ = sock.recvfrom(512)
            latency = (time.perf_counter() - start) * 1000.0
            return True, round(latency, 1), f"Received ({len(data)}B)"
        except socket.timeout:
            # UDP is connectionless; lack of ICMP Port Unreachable within timeout indicates port might be open
            latency = (time.perf_counter() - start) * 1000.0
            return True, round(latency, 1), "Open/Filtered"
    except Exception as e:
        return False, None, str(e)[:25]
    finally:
        if sock:
            try:
                sock.close()
            except Exception:
                pass


def test_tls_handshake(host, port=443, sni="www.google.com", timeout=3.0):
    start = time.perf_counter()
    sock = None
    ssock = None
    try:
        is_ipv6 = ":" in host
        family = socket.AF_INET6 if is_ipv6 else socket.AF_INET
        sock = socket.socket(family, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ssock = ctx.wrap_socket(sock, server_hostname=sni)
        latency = (time.perf_counter() - start) * 1000.0
        cipher = ssock.cipher()
        cipher_name = cipher[0] if cipher else "TLS"
        return True, round(latency, 1), cipher_name
    except socket.timeout:
        return False, None, "TLS Timeout"
    except ConnectionResetError:
        return False, None, "DPI Reset"
    except Exception as e:
        return False, None, f"TLS Err: {str(e)[:20]}"
    finally:
        if ssock:
            try:
                ssock.close()
            except Exception:
                pass
        elif sock:
            try:
                sock.close()
            except Exception:
                pass


class IPScanner:
    def __init__(self, max_threads=20):
        self.max_threads = max_threads
        self._is_running = False
        self._stop_event = threading.Event()

    def stop(self):
        self._is_running = False
        self._stop_event.set()

    def scan(self, ip_list, test_type="tcp", port=443, sni="www.google.com", timeout=2.0, callback=None):
        self._is_running = True
        self._stop_event.clear()
        results = []

        def worker(ip):
            if self._stop_event.is_set():
                return None
            
            res_item = {
                "ip": ip,
                "port": port,
                "type": test_type,
                "success": False,
                "latency": None,
                "message": ""
            }

            if test_type == "tcp":
                ok, lat, msg = test_tcp_ping(ip, port, timeout)
            elif test_type == "icmp":
                ok, lat, msg = test_icmp_ping(ip, timeout)
            elif test_type == "udp":
                ok, lat, msg = test_udp_ping(ip, port, timeout)
            elif test_type == "tls":
                ok, lat, msg = test_tls_handshake(ip, port, sni, timeout)
            else:
                ok, lat, msg = test_tcp_ping(ip, port, timeout)

            res_item["success"] = ok
            res_item["latency"] = lat
            res_item["message"] = msg

            if callback and not self._stop_event.is_set():
                callback(res_item)

            return res_item

        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            future_to_ip = {executor.submit(worker, ip): ip for ip in ip_list}
            for future in as_completed(future_to_ip):
                if self._stop_event.is_set():
                    break
                try:
                    res = future.result()
                    if res:
                        results.append(res)
                except Exception:
                    pass

        self._is_running = False
        return sorted([r for r in results if r["success"]], key=lambda x: x["latency"] or 9999)
