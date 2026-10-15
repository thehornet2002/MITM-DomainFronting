import os
import sys
import json
import zipfile
import winreg
import ctypes
import shutil
import subprocess
import threading
import urllib.request

INTERNET_OPTION_SETTINGS_CHANGED = 39
INTERNET_OPTION_REFRESH = 37

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN_DIR = os.path.join(BASE_DIR, "bin")


def get_xray_path():
    candidates = [
        os.path.join(BIN_DIR, "xray.exe"),
        os.path.join(BASE_DIR, "xray.exe"),
        os.path.join(BASE_DIR, "xray", "xray.exe")
    ]
    for c in candidates:
        if os.path.isfile(c):
            return os.path.abspath(c)
    # Check PATH
    which_xray = shutil.which("xray.exe")
    if which_xray:
        return os.path.abspath(which_xray)
    return None


def download_xray_core(progress_cb=None):
    os.makedirs(BIN_DIR, exist_ok=True)
    target_zip = os.path.join(BIN_DIR, "xray.zip")
    
    # Official GitHub release URL
    url = "https://github.com/XTLS/Xray-core/releases/latest/download/Xray-windows-64.zip"
    if progress_cb:
        progress_cb(0, "شروع دانلود هسته Xray...")

    headers = {"User-Agent": "Mozilla/5.0"}
    req = urllib.request.Request(url, headers=headers)
    
    with urllib.request.urlopen(req, timeout=30) as resp, open(target_zip, "wb") as out_file:
        total_size = resp.getheader("Content-Length")
        total_size = int(total_size) if total_size else 0
        downloaded = 0
        chunk_size = 64 * 1024

        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            out_file.write(chunk)
            downloaded += len(chunk)
            if total_size and progress_cb:
                pct = int((downloaded / total_size) * 100)
                progress_cb(pct, f"دانلود Xray-core ({pct}%)...")

    if progress_cb:
        progress_cb(95, "استخراج فایل‌های هسته...")

    with zipfile.ZipFile(target_zip, "r") as zip_ref:
        zip_ref.extractall(BIN_DIR)

    try:
        os.remove(target_zip)
    except Exception:
        pass

    if progress_cb:
        progress_cb(100, "هسته Xray با موفقیت نصب شد.")

    return get_xray_path()


class ProcessManager:
    def __init__(self):
        self.process = None
        self.log_lines = []
        self._max_logs = 500
        self._log_lock = threading.Lock()
        self._reader_thread = None

    def is_running(self):
        if self.process is None:
            return False
        return self.process.poll() is None

    def start(self, config_dict, config_path=None):
        if self.is_running():
            self.stop()

        xray_exe = get_xray_path()
        if not xray_exe:
            raise FileNotFoundError("xray.exe یافت نشد. لطفاً ابتدا هسته را دانلود یا در پوشه bin قرار دهید.")

        if not config_path:
            config_path = os.path.join(BASE_DIR, "active_config.json")

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)

        # Clear logs
        with self._log_lock:
            self.log_lines = [f"[INFO] اجرای هسته: {xray_exe} با فایل کانفیگ {config_path}"]

        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = subprocess.CREATE_NO_WINDOW

        self.process = subprocess.Popen(
            [xray_exe, "run", "-c", config_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=BASE_DIR,
            creationflags=creation_flags
        )

        def _log_reader():
            while self.process and self.process.poll() is None:
                line = self.process.stdout.readline()
                if not line:
                    break
                line_str = line.strip()
                if line_str:
                    with self._log_lock:
                        self.log_lines.append(line_str)
                        if len(self.log_lines) > self._max_logs:
                            self.log_lines.pop(0)

        self._reader_thread = threading.Thread(target=_log_reader, daemon=True)
        self._reader_thread.start()
        return True

    def stop(self):
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None
        with self._log_lock:
            self.log_lines.append("[INFO] هسته Xray متوقف شد.")

    def get_logs(self):
        with self._log_lock:
            return list(self.log_lines)


def set_system_proxy(port=10808):
    try:
        reg_key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
            0,
            winreg.KEY_SET_VALUE
        )
        proxy_server = f"127.0.0.1:{port}"
        winreg.SetValueEx(reg_key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(reg_key, "ProxyServer", 0, winreg.REG_SZ, proxy_server)
        winreg.SetValueEx(reg_key, "ProxyOverride", 0, winreg.REG_SZ, "<local>;localhost;127.*;10.*;192.168.*")
        winreg.CloseKey(reg_key)

        # Notify system & browsers
        ctypes.windll.wininet.InternetSetOptionW(0, INTERNET_OPTION_SETTINGS_CHANGED, 0, 0)
        ctypes.windll.wininet.InternetSetOptionW(0, INTERNET_OPTION_REFRESH, 0, 0)
        return True, "پراکسی سیستم با موفقیت تنظیم شد."
    except Exception as e:
        return False, f"خطا در تنظیم پراکسی: {str(e)}"


def clear_system_proxy():
    try:
        reg_key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
            0,
            winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(reg_key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
        winreg.CloseKey(reg_key)

        ctypes.windll.wininet.InternetSetOptionW(0, INTERNET_OPTION_SETTINGS_CHANGED, 0, 0)
        ctypes.windll.wininet.InternetSetOptionW(0, INTERNET_OPTION_REFRESH, 0, 0)
        return True, "پراکسی سیستم غیرفعال شد."
    except Exception as e:
        return False, f"خطا در غیرفعال‌سازی پراکسی: {str(e)}"


def is_system_proxy_enabled():
    try:
        reg_key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
            0,
            winreg.KEY_READ
        )
        val, _ = winreg.QueryValueEx(reg_key, "ProxyEnable")
        winreg.CloseKey(reg_key)
        return bool(val)
    except Exception:
        return False


def generate_ca_certificate():
    cert_path = os.path.join(BASE_DIR, "mycert.crt")
    key_path = os.path.join(BASE_DIR, "mycert.key")

    xray_exe = get_xray_path()
    if xray_exe:
        cmd = [xray_exe, "tls", "cert", "-ca", "-expire=1000000h", "-file=mycert"]
        creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        proc = subprocess.run(cmd, cwd=BASE_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=creation_flags)
        if os.path.exists(cert_path) and os.path.exists(key_path):
            return True, "گواهی اختصاصی CA با موفقیت از طریق Xray ایجاد شد."

    # Fallback to PowerShell New-SelfSignedCertificate
    ps_cmd = (
        "$cert = New-SelfSignedCertificate -Type Custom -KeySpec Signature "
        "-Subject 'CN=MITM DomainFronting Root CA' -KeyExportPolicy Exportable "
        "-HashAlgorithm sha256 -KeyLength 2048 -CertStoreLocation 'Cert:\\CurrentUser\\My' "
        "-KeyUsage CertSign, CRLSign -TextExtension @('2.5.29.19={text}ca=1&pathlength=1'); "
        f"[System.IO.File]::WriteAllBytes('{cert_path}', $cert.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert))"
    )
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        if os.path.exists(cert_path):
            return True, "گواهی اختصاصی CA با PowerShell ساخته شد."
    except Exception as e:
        return False, f"خطا در ساخت گواهی CA: {str(e)}"

    return False, "فایل‌های گواهی ایجاد نشدند."


def install_ca_to_windows_store():
    cert_path = os.path.join(BASE_DIR, "mycert.crt")
    if not os.path.exists(cert_path):
        ok, msg = generate_ca_certificate()
        if not ok:
            return False, msg

    try:
        # certutil -addstore -f "Root" mycert.crt
        cmd = ["certutil", "-addstore", "-f", "Root", cert_path]
        creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=creation_flags)
        if proc.returncode == 0:
            return True, "گواهی امنیتی با موفقیت در مخزن سیستم (Trusted Root) نصب شد."
        return False, f"خطای certutil: {proc.stderr or proc.stdout}"
    except Exception as e:
        return False, f"خطا در نصب گواهی: {str(e)}"


def check_ca_installed():
    cert_path = os.path.join(BASE_DIR, "mycert.crt")
    if not os.path.exists(cert_path):
        return False
    return True
