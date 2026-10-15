import json
import os

DEFAULT_SETTINGS = {
    "mode": "hybrid",  # "hybrid", "mitm", "serverless_a", "serverless_b"
    "local_port": 10808,
    "cert_file": "mycert.crt",
    "key_file": "mycert.key",
    "enable_warp": False,
    "enable_udp_noise": True,
    "turbo_happy_eyeballs": True,
    "cdn_ips": {
        "fastly": "",
        "cloudflare": "",
        "google": "",
        "meta": "",
        "gcore": "",
        "cloudfront": ""
    },
    "fragment_params": {
        "packets": "tlshello",
        "lengths": "6,98,1",
        "delays": "0",
        "maxSplit": "0",
        "tcp_packets": "1-1",
        "tcp_lengths": "114,1",
        "tcp_delays": "1",
        "tcp_maxSplit": "11"
    }
}


def build_xray_config(settings=None, base_dir="."):
    cfg = dict(DEFAULT_SETTINGS)
    if settings:
        for k, v in settings.items():
            if k == "cdn_ips" and isinstance(v, dict):
                cfg["cdn_ips"].update(v)
            elif k == "fragment_params" and isinstance(v, dict):
                cfg["fragment_params"].update(v)
            else:
                cfg[k] = v

    mode = cfg.get("mode", "hybrid")
    local_port = int(cfg.get("local_port", 10808))
    cert_path = os.path.abspath(os.path.join(base_dir, cfg.get("cert_file", "mycert.crt"))).replace("\\", "/")
    key_path = os.path.abspath(os.path.join(base_dir, cfg.get("key_file", "mycert.key"))).replace("\\", "/")
    cdn_ips = cfg.get("cdn_ips", {})

    frag_params = cfg.get("fragment_params", {})
    frag_lengths = [x.strip() for x in frag_params.get("lengths", "6,98,1").split(",")]
    frag_delays = [x.strip() for x in frag_params.get("delays", "0").split(",")]
    tcp_lengths = [x.strip() for x in frag_params.get("tcp_lengths", "114,1").split(",")]
    tcp_delays = [x.strip() for x in frag_params.get("tcp_delays", "1").split(",")]

    happy_eyeballs = {
        "tryDelayMs": 200 if cfg.get("turbo_happy_eyeballs") else 300,
        "prioritizeIPv6": True,
        "interleave": 4 if cfg.get("turbo_happy_eyeballs") else 2,
        "maxConcurrentTry": 30 if cfg.get("turbo_happy_eyeballs") else 20
    }

    # Base Skeleton
    config = {
        "log": {"loglevel": "warning", "dnsLog": False, "access": "none"},
        "policy": {
            "levels": {
                "0": {"uplinkOnly": 0, "downlinkOnly": 0},
                "1": {"uplinkOnly": 0, "downlinkOnly": 0, "connIdle": 12}
            }
        },
        "dns": {
            "hosts": {
                "geosite:category-ads-all": "#3",
                "cloudflare-dns.com": "challenges.cloudflare.com"
            },
            "servers": [
                {
                    "address": "fakedns",
                    "domains": ["domain:ir", "geosite:private", "geosite:category-ir", "full:challenges.cloudflare.com"]
                },
                {
                    "tag": "no-filter-dns",
                    "address": "https://cloudflare-dns.com/dns-query",
                    "timeoutMs": 10000,
                    "finalQuery": True
                },
                {
                    "tag": "domestic-dns",
                    "address": "localhost",
                    "domains": ["domain:ir", "geosite:private", "geosite:category-ir"],
                    "timeoutMs": 10000,
                    "finalQuery": True
                }
            ],
            "queryStrategy": "UseSystem",
            "useSystemHosts": True,
            "serveStale": True
        },
        "inbounds": [
            {
                "tag": "mixed-in",
                "port": local_port,
                "protocol": "mixed",
                "sniffing": {
                    "enabled": True,
                    "destOverride": ["fakedns", "tls", "http", "quic"],
                    "routeOnly": False
                },
                "settings": {"udp": True, "ip": "127.0.0.1"},
                "streamSettings": {
                    "sockopt": {"tcpKeepAliveInterval": 1, "tcpKeepAliveIdle": 11}
                }
            }
        ],
        "outbounds": [],
        "routing": {"domainStrategy": "IPOnDemand", "rules": []}
    }

    # Block outbound
    config["outbounds"].append({"tag": "block", "protocol": "block"})
    config["outbounds"].append({"tag": "dns-out", "protocol": "dns", "settings": {"userLevel": 1}})

    # Direct outbound
    config["outbounds"].append({
        "tag": "direct",
        "protocol": "direct",
        "streamSettings": {
            "sockopt": {
                "domainStrategy": "ForceIP",
                "happyEyeballs": happy_eyeballs
            }
        }
    })

    # Fragment outbounds
    config["outbounds"].append({
        "tag": "tcp-fragment",
        "protocol": "direct",
        "streamSettings": {
            "finalmask": {
                "tcp": [
                    {
                        "type": "fragment",
                        "settings": {
                            "packets": frag_params.get("tcp_packets", "1-1"),
                            "lengths": tcp_lengths,
                            "delays": tcp_delays,
                            "maxSplit": str(frag_params.get("tcp_maxSplit", "11"))
                        }
                    }
                ]
            },
            "sockopt": {
                "domainStrategy": "ForceIP",
                "happyEyeballs": happy_eyeballs
            }
        }
    })

    config["outbounds"].append({
        "tag": "tcp-fragment-tls",
        "protocol": "direct",
        "streamSettings": {
            "finalmask": {
                "tcp": [
                    {
                        "type": "fragment",
                        "settings": {
                            "packets": frag_params.get("packets", "tlshello"),
                            "lengths": frag_lengths,
                            "delays": frag_delays,
                            "maxSplit": str(frag_params.get("maxSplit", "0"))
                        }
                    },
                    {
                        "type": "fragment",
                        "settings": {
                            "packets": frag_params.get("tcp_packets", "1-1"),
                            "lengths": tcp_lengths,
                            "delays": tcp_delays,
                            "maxSplit": str(frag_params.get("tcp_maxSplit", "11"))
                        }
                    }
                ]
            },
            "sockopt": {
                "domainStrategy": "ForceIP",
                "happyEyeballs": happy_eyeballs
            }
        }
    })

    # UDP Noise Outbound
    if cfg.get("enable_udp_noise"):
        config["outbounds"].append({
            "tag": "udp-noises",
            "protocol": "direct",
            "streamSettings": {
                "sockopt": {"domainStrategy": "ForceIPv6v4"},
                "finalmask": {
                    "udp": [
                        {
                            "type": "noise",
                            "settings": {
                                "reset": "28",
                                "noise": [{"rand": "1200-1230", "delay": "10"} for _ in range(8)]
                            }
                        }
                    ]
                }
            }
        })
    else:
        config["outbounds"].append({
            "tag": "udp-noises",
            "protocol": "direct",
            "streamSettings": {"sockopt": {"domainStrategy": "ForceIPv6v4"}}
        })

    # MITM Inbounds & Outbounds if mode is 'mitm' or 'hybrid'
    if mode in ("mitm", "hybrid"):
        # Tunnel inbounds for local decryption
        config["inbounds"].append({
            "port": 11666,
            "tag": "tls-decrypt-h11",
            "protocol": "tunnel",
            "settings": {"network": "tcp", "port": 443, "followRedirect": True},
            "streamSettings": {
                "security": "tls",
                "tlsSettings": {
                    "alpn": ["http/1.1"],
                    "certificates": [{"usage": "issue", "certificateFile": cert_path, "keyFile": key_path}]
                }
            }
        })
        config["inbounds"].append({
            "port": 11777,
            "tag": "tls-decrypt-h211",
            "protocol": "tunnel",
            "settings": {"network": "tcp", "port": 443, "followRedirect": True},
            "streamSettings": {
                "security": "tls",
                "tlsSettings": {
                    "alpn": ["h2", "http/1.1"],
                    "certificates": [{"usage": "issue", "certificateFile": cert_path, "keyFile": key_path}]
                }
            }
        })

        # Redirect inbounds to local tunnels
        config["outbounds"].append({
            "tag": "redirect-out-h11",
            "protocol": "direct",
            "settings": {"redirect": "127.0.0.1:11666"}
        })
        config["outbounds"].append({
            "tag": "redirect-out-h211",
            "protocol": "direct",
            "settings": {"redirect": "127.0.0.1:11777"}
        })

        # --- Dynamic Clean IP Outbounds for each CDN ---
        # 1. Fastly
        fastly_redirect = f"{cdn_ips['fastly']}:443" if cdn_ips.get("fastly") else "github.githubassets.com:443"
        config["outbounds"].append({
            "tag": "tls-repack-fastly",
            "protocol": "direct",
            "settings": {"redirect": fastly_redirect},
            "streamSettings": {
                "security": "tls",
                "tlsSettings": {
                    "serverName": "github.githubassets.com",
                    "verifyPeerCertByName": "fromMitM,www.python.org,pypi.org,fastly.com,www.fastly.com,developer.fastly.com,reddit.com,githubassets.com,github.com,github.io,githubusercontent.com,github.githubassets.com",
                    "alpn": ["fromMitM"],
                    "fingerprint": "chrome"
                },
                "sockopt": {"domainStrategy": "ForceIP", "happyEyeballs": happy_eyeballs}
            }
        })

        # 2. Google / YouTube
        google_redirect = f"{cdn_ips['google']}:443" if cdn_ips.get("google") else None
        google_outbound = {
            "tag": "tls-repack-google",
            "protocol": "direct",
            "streamSettings": {
                "security": "tls",
                "tlsSettings": {
                    "serverName": "www.google.com",
                    "verifyPeerCertByName": "fromMitM,www.google.com,dns.google,www.googlevideo.com,www.youtube.com",
                    "alpn": ["fromMitM"],
                    "fingerprint": "chrome"
                },
                "sockopt": {"domainStrategy": "ForceIP", "happyEyeballs": happy_eyeballs}
            }
        }
        if google_redirect:
            google_outbound["settings"] = {"redirect": google_redirect}
        config["outbounds"].append(google_outbound)

        # 3. Meta (Instagram / WhatsApp)
        meta_redirect = f"{cdn_ips['meta']}:443" if cdn_ips.get("meta") else None
        meta_outbound = {
            "tag": "tls-repack-meta",
            "protocol": "direct",
            "streamSettings": {
                "security": "tls",
                "tlsSettings": {
                    "serverName": "www.microsoft.com",
                    "verifyPeerCertByName": "fromMitM,www.google.com,www.microsoft.com,www.whatsapp.com,www.facebook.com,www.fb.com,www.instagram.com,www.meta.com",
                    "alpn": ["fromMitM"],
                    "fingerprint": "chrome"
                },
                "sockopt": {"domainStrategy": "ForceIP", "happyEyeballs": happy_eyeballs}
            }
        }
        if meta_redirect:
            meta_outbound["settings"] = {"redirect": meta_redirect}
        config["outbounds"].append(meta_outbound)

        # 4. Cloudflare
        cf_redirect = f"{cdn_ips['cloudflare']}:443" if cdn_ips.get("cloudflare") else None
        cf_outbound = {
            "tag": "tls-repack-cloudflare",
            "protocol": "direct",
            "streamSettings": {
                "security": "tls",
                "tlsSettings": {
                    "serverName": "challenges.cloudflare.com",
                    "verifyPeerCertByName": "fromMitM,cloudflare.com,challenges.cloudflare.com,one.one.one.one",
                    "alpn": ["fromMitM"],
                    "fingerprint": "chrome"
                },
                "sockopt": {"domainStrategy": "ForceIP", "happyEyeballs": happy_eyeballs}
            }
        }
        if cf_redirect:
            cf_outbound["settings"] = {"redirect": cf_redirect}
        config["outbounds"].append(cf_outbound)

        # 5. GCore
        gcore_redirect = f"{cdn_ips['gcore']}:443" if cdn_ips.get("gcore") else None
        gcore_outbound = {
            "tag": "tls-repack-gcore",
            "protocol": "direct",
            "streamSettings": {
                "security": "tls",
                "tlsSettings": {
                    "serverName": "gcore.com",
                    "verifyPeerCertByName": "fromMitM,gcore.com,cdn.gcore.com",
                    "alpn": ["fromMitM"],
                    "fingerprint": "chrome"
                },
                "sockopt": {"domainStrategy": "ForceIP", "happyEyeballs": happy_eyeballs}
            }
        }
        if gcore_redirect:
            gcore_outbound["settings"] = {"redirect": gcore_redirect}
        config["outbounds"].append(gcore_outbound)

    # Optional WARP WireGuard outbound for Anti-Sanction (403 bypass)
    if cfg.get("enable_warp"):
        config["outbounds"].append({
            "tag": "warp-out",
            "protocol": "wireguard",
            "settings": {
                "secretKey": "",  # Auto-generated or user provided
                "address": ["172.16.0.2/32", "2606:4700:110:8751::/128"],
                "peers": [
                    {
                        "publicKey": "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=",
                        "endpoint": "engage.cloudflareclient.com:2408"
                    }
                ]
            }
        })

    # --- Routing Rules ---
    rules = []
    # Block Ads
    rules.append({"outboundTag": "block", "domain": ["geosite:category-ads-all"]})
    # Domestic & Private
    rules.append({"outboundTag": "direct", "domain": ["domain:ir", "geosite:private", "geosite:category-ir"]})
    rules.append({"outboundTag": "direct", "ip": ["geoip:private", "geoip:ir"]})

    # DNS routing
    rules.append({"outboundTag": "dns-out", "port": 53})

    if cfg.get("enable_warp"):
        # Route sanctioned domains through WARP
        rules.append({
            "outboundTag": "warp-out",
            "domain": [
                "geosite:openai", "geosite:anthropic", "domain:claude.ai",
                "geosite:spotify", "domain:deepseek.com"
            ]
        })

    if mode in ("mitm", "hybrid"):
        # Redirect decrypted MITM sessions to appropriate CDN repacks
        rules.append({"outboundTag": "tls-repack-google", "domain": ["domain:googlevideo.com"], "inboundTag": ["tls-decrypt-h11"]})
        rules.append({"outboundTag": "tls-repack-google", "domain": ["geosite:google"], "inboundTag": ["tls-decrypt-h211"]})
        rules.append({"outboundTag": "tls-repack-fastly", "domain": ["geosite:fastly", "geosite:reddit", "geosite:cnn", "domain:buzzfeed.com"], "inboundTag": ["tls-decrypt-h211"]})
        rules.append({"outboundTag": "tls-repack-meta", "domain": ["geosite:meta"], "inboundTag": ["tls-decrypt-h211"]})
        rules.append({"outboundTag": "tls-repack-cloudflare", "domain": ["geosite:cloudflare"], "inboundTag": ["tls-decrypt-h211"]})
        rules.append({"outboundTag": "tls-repack-gcore", "domain": ["geosite:gcore"], "inboundTag": ["tls-decrypt-h211"]})
        rules.append({"outboundTag": "block", "inboundTag": ["tls-decrypt-h11", "tls-decrypt-h211"]})

        # Intercept port 443 TCP connections for targeted CDN domains
        rules.append({"outboundTag": "redirect-out-h11", "network": "tcp", "port": 443, "domain": ["domain:googlevideo.com"]})
        rules.append({
            "outboundTag": "redirect-out-h211",
            "network": "tcp",
            "port": 443,
            "domain": [
                "geosite:google", "geosite:meta", "geosite:fastly",
                "geosite:reddit", "geosite:cnn", "domain:buzzfeed.com", "geosite:gcore"
            ]
        })

    # Base internet routing
    if mode in ("serverless_a", "serverless_b", "hybrid"):
        rules.append({"outboundTag": "tcp-fragment-tls", "network": "tcp", "port": 443})
        rules.append({"outboundTag": "tcp-fragment", "network": "tcp"})
        rules.append({"outboundTag": "udp-noises", "network": "udp"})
    else:
        rules.append({"outboundTag": "direct", "network": "tcp,udp"})

    config["routing"]["rules"] = rules
    return config
