import json
import os
import ipaddress
import urllib.request
import urllib.error

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
CATALOG_PATH = os.path.join(DATA_DIR, "asn_catalog.json")
CACHE_PATH = os.path.join(DATA_DIR, "asn_cache.json")


def load_catalog():
    if os.path.exists(CATALOG_PATH):
        try:
            with open(CATALOG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"categories": {}}


def load_cache():
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_cache(cache_data):
    try:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def get_all_catalog_asns():
    catalog = load_catalog()
    asns = []
    for cat_key, cat_data in catalog.get("categories", {}).items():
        cat_name = cat_data.get("name_fa", cat_key)
        for item in cat_data.get("asns", []):
            item_copy = dict(item)
            item_copy["category"] = cat_name
            item_copy["category_key"] = cat_key
            asns.append(item_copy)
    return asns


def fetch_live_asn(asn_number):
    asn_str = str(asn_number).upper().replace("AS", "")
    asn_key = f"AS{asn_str}"

    cache = load_cache()
    if asn_key in cache:
        return cache[asn_key]

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    # 1. Fetch ASN name & holder
    holder = f"ASN {asn_str}"
    country = "Unknown"
    try:
        overview_url = f"https://stat.ripe.net/data/as-overview/data.json?resource=AS{asn_str}"
        req = urllib.request.Request(overview_url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as res:
            ov_data = json.loads(res.read().decode("utf-8"))
            holder = ov_data.get("data", {}).get("holder", holder)
    except Exception:
        pass

    # 2. Fetch Announced Prefixes
    cidrs_v4 = []
    cidrs_v6 = []
    try:
        prefixes_url = f"https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS{asn_str}"
        req = urllib.request.Request(prefixes_url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as res:
            pref_data = json.loads(res.read().decode("utf-8"))
            for item in pref_data.get("data", {}).get("prefixes", []):
                p = item.get("prefix")
                if not p:
                    continue
                if ":" in p:
                    cidrs_v6.append(p)
                else:
                    cidrs_v4.append(p)
    except Exception as e:
        return {"error": f"Failed to fetch prefixes: {str(e)}"}

    result = {
        "asn": int(asn_str) if asn_str.isdigit() else asn_str,
        "name": holder,
        "country": country,
        "cidrs_v4": cidrs_v4,
        "cidrs_v6": cidrs_v6,
        "source": "RIPEstat",
        "category": "استخراج زنده ASN"
    }

    cache[asn_key] = result
    save_cache(cache)
    return result


def sample_ips_from_cidrs(cidr_list, max_ips=100, step=None):
    sampled = []
    for cidr in cidr_list:
        if len(sampled) >= max_ips:
            break
        try:
            net = ipaddress.ip_network(cidr, strict=False)
            if net.version == 4:
                num_hosts = net.num_addresses
                if num_hosts <= 2:
                    for ip in net:
                        sampled.append(str(ip))
                        if len(sampled) >= max_ips:
                            break
                elif num_hosts <= 256:
                    offsets = [1, int(num_hosts * 0.25), int(num_hosts * 0.5), int(num_hosts * 0.75), num_hosts - 2]
                    for off in sorted(set(offsets)):
                        if 0 <= off < num_hosts:
                            sampled.append(str(net.network_address + off))
                            if len(sampled) >= max_ips:
                                break
                else:
                    needed = max_ips - len(sampled)
                    samples_for_this = min(needed, 10)
                    chunk_step = max(1, (num_hosts - 2) // samples_for_this)
                    for idx in range(samples_for_this):
                        off = 1 + idx * chunk_step
                        if off < num_hosts - 1:
                            sampled.append(str(net.network_address + off))
                            if len(sampled) >= max_ips:
                                break
            elif net.version == 6:
                sampled.append(str(net.network_address + 1))
        except Exception:
            continue
    return sampled[:max_ips]
