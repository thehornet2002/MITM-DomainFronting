import json
import os
import sys
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_PATH = os.path.join(DATA_DIR, "asn_catalog.json")

TARGET_ENTITIES = [
    # Global CDNs & Cloud Providers
    {"asn": 13335, "name": "Cloudflare", "country": "US", "website": "cloudflare.com", "cat": "cdn_global"},
    {"asn": 54113, "name": "Fastly", "country": "US", "website": "fastly.com", "cat": "cdn_global"},
    {"asn": 15169, "name": "Google LLC (YouTube, GCP)", "country": "US", "website": "google.com", "cat": "cdn_global"},
    {"asn": 36040, "name": "Google Cloud Platform (GCP)", "country": "US", "website": "cloud.google.com", "cat": "cdn_global"},
    {"asn": 16509, "name": "Amazon AWS (CloudFront)", "country": "US", "website": "aws.amazon.com", "cat": "cdn_global"},
    {"asn": 14618, "name": "Amazon.com (AWS Global)", "country": "US", "website": "amazon.com", "cat": "cdn_global"},
    {"asn": 32934, "name": "Meta (Facebook, Instagram, WhatsApp)", "country": "US", "website": "meta.com", "cat": "cdn_global"},
    {"asn": 8075, "name": "Microsoft Corporation (Azure, M365)", "country": "US", "website": "microsoft.com", "cat": "cdn_global"},
    {"asn": 199524, "name": "GCore", "country": "LU", "website": "gcore.com", "cat": "cdn_global"},
    {"asn": 20940, "name": "Akamai Technologies", "country": "US", "website": "akamai.com", "cat": "cdn_global"},
    {"asn": 16625, "name": "Akamai International", "country": "NL", "website": "akamai.com", "cat": "cdn_global"},
    {"asn": 15133, "name": "Edgecast / Yahoo (Verizon CDN)", "country": "US", "website": "edgecast.com", "cat": "cdn_global"},
    {"asn": 714, "name": "Apple Inc.", "country": "US", "website": "apple.com", "cat": "cdn_global"},
    {"asn": 138699, "name": "ByteDance / TikTok", "country": "SG", "website": "bytedance.com", "cat": "cdn_global"},
    {"asn": 200325, "name": "Bunny CDN (BunnyWay)", "country": "SI", "website": "bunny.net", "cat": "cdn_global"},
    {"asn": 60068, "name": "CDN77 / DataCamp", "country": "GB", "website": "cdn77.com", "cat": "cdn_global"},
    {"asn": 33438, "name": "StackPath / Highwinds", "country": "US", "website": "stackpath.com", "cat": "cdn_global"},
    {"asn": 19551, "name": "Imperva Incapsula", "country": "US", "website": "imperva.com", "cat": "cdn_global"},
    {"asn": 22822, "name": "Edgio / Limelight Networks", "country": "US", "website": "edg.io", "cat": "cdn_global"},
    {"asn": 30081, "name": "CacheFly", "country": "US", "website": "cachefly.com", "cat": "cdn_global"},
    {"asn": 31898, "name": "Oracle Cloud Infrastructure", "country": "US", "website": "oracle.com", "cat": "cdn_global"},
    {"asn": 45102, "name": "Alibaba Cloud (Aliyun)", "country": "CN", "website": "alibabacloud.com", "cat": "cdn_global"},
    {"asn": 132203, "name": "Tencent Cloud", "country": "CN", "website": "tencentcloud.com", "cat": "cdn_global"},

    # Global Hosting, VPS & Cloud Infrastructure
    {"asn": 24940, "name": "Hetzner Online GmbH", "country": "DE", "website": "hetzner.com", "cat": "hosting_global"},
    {"asn": 16276, "name": "OVHcloud", "country": "FR", "website": "ovhcloud.com", "cat": "hosting_global"},
    {"asn": 14061, "name": "DigitalOcean, LLC", "country": "US", "website": "digitalocean.com", "cat": "hosting_global"},
    {"asn": 63949, "name": "Linode (Akamai Cloud)", "country": "US", "website": "linode.com", "cat": "hosting_global"},
    {"asn": 20473, "name": "The Constant Company (Vultr / Choopa)", "country": "US", "website": "vultr.com", "cat": "hosting_global"},
    {"asn": 12876, "name": "Scaleway S.A.S.", "country": "FR", "website": "scaleway.com", "cat": "hosting_global"},
    {"asn": 60781, "name": "Leaseweb Global B.V.", "country": "NL", "website": "leaseweb.com", "cat": "hosting_global"},
    {"asn": 36351, "name": "IBM Cloud (SoftLayer)", "country": "US", "website": "ibm.com/cloud", "cat": "hosting_global"},

    # Social Media, Platforms & DNS
    {"asn": 62041, "name": "Telegram Messenger Inc. (UK/EU)", "country": "GB", "website": "telegram.org", "cat": "platforms_global"},
    {"asn": 62014, "name": "Telegram Messenger Network", "country": "AE", "website": "telegram.org", "cat": "platforms_global"},
    {"asn": 44907, "name": "Telegram Messenger Network (NL)", "country": "NL", "website": "telegram.org", "cat": "platforms_global"},
    {"asn": 59930, "name": "Telegram Messenger Network (SG)", "country": "SG", "website": "telegram.org", "cat": "platforms_global"},
    {"asn": 13414, "name": "Twitter / X Corp", "country": "US", "website": "x.com", "cat": "platforms_global"},
    {"asn": 32590, "name": "Valve Corporation (Steam)", "country": "US", "website": "steampowered.com", "cat": "platforms_global"},
    {"asn": 36459, "name": "GitHub Inc.", "country": "US", "website": "github.com", "cat": "platforms_global"},
    {"asn": 36692, "name": "Cisco OpenDNS", "country": "US", "website": "opendns.com", "cat": "platforms_global"},
    {"asn": 19281, "name": "Quad9 Anycast DNS", "country": "CH", "website": "quad9.net", "cat": "platforms_global"},

    # Iranian Mobile Operators & Fixed ISPs
    {"asn": 197207, "name": "Mobile Telecommunication Company of Iran (MCI / همراه اول)", "country": "IR", "website": "mci.ir", "cat": "iran_telecom"},
    {"asn": 44244, "name": "MTN Irancell (ایرانسل)", "country": "IR", "website": "irancell.ir", "cat": "iran_telecom"},
    {"asn": 58224, "name": "Telecommunication Company of Iran (TCI / مخابرات ایران)", "country": "IR", "website": "tci.ir", "cat": "iran_telecom"},
    {"asn": 12880, "name": "Information Technology Company (TIC / زیرساخت)", "country": "IR", "website": "tic.ir", "cat": "iran_telecom"},
    {"asn": 57218, "name": "Rightel (رایتل)", "country": "IR", "website": "rightel.ir", "cat": "iran_telecom"},
    {"asn": 56402, "name": "Shatel (شاتل)", "country": "IR", "website": "shatel.ir", "cat": "iran_telecom"},
    {"asn": 43754, "name": "Asiatech (آسیاتک)", "country": "IR", "website": "asiatech.ir", "cat": "iran_telecom"},
    {"asn": 50810, "name": "Mobinnet (مبین‌نت)", "country": "IR", "website": "mobinnet.ir", "cat": "iran_telecom"},
    {"asn": 49666, "name": "HiWEB / Dadeh Gostar Asr (های‌وب)", "country": "IR", "website": "hiweb.ir", "cat": "iran_telecom"},
    {"asn": 56534, "name": "Parsian HiWeb", "country": "IR", "website": "hiweb.ir", "cat": "iran_telecom"},
    {"asn": 60798, "name": "Helma Gostar / Zitel (زی‌تل)", "country": "IR", "website": "zitel.ir", "cat": "iran_telecom"},
    {"asn": 41881, "name": "Sabanet (صبانت)", "country": "IR", "website": "sabanet.ir", "cat": "iran_telecom"},
    {"asn": 48159, "name": "Pishgaman Kavir Yazd (پیشگامان)", "country": "IR", "website": "pishgaman.net", "cat": "iran_telecom"},
    {"asn": 41689, "name": "Fanava (فن‌آوا)", "country": "IR", "website": "fanava.com", "cat": "iran_telecom"},
    {"asn": 25182, "name": "Datak Telecom (داتک)", "country": "IR", "website": "datak.ir", "cat": "iran_telecom"},

    # Iranian Datacenters, Cloud & Enterprise
    {"asn": 208004, "name": "ArvanCloud / Asre Novin (ابر آروان)", "country": "IR", "website": "arvancloud.ir", "cat": "iran_datacenter"},
    {"asn": 204620, "name": "Derak Cloud (دراک)", "country": "IR", "website": "derak.cloud", "cat": "iran_datacenter"},
    {"asn": 25184, "name": "Afranet (افرانت)", "country": "IR", "website": "afranet.com", "cat": "iran_datacenter"},
    {"asn": 16322, "name": "Pars Online (پارس آنلاین)", "country": "IR", "website": "parsonline.com", "cat": "iran_datacenter"},
    {"asn": 42337, "name": "Respina Networks (رسپینا)", "country": "IR", "website": "respina.net", "cat": "iran_datacenter"},
    {"asn": 57534, "name": "Fanap Telecom (فناپ)", "country": "IR", "website": "fanap.ir", "cat": "iran_datacenter"},
    {"asn": 39501, "name": "Tebyan Cultural Institute (تبیان)", "country": "IR", "website": "tebyan.net", "cat": "iran_datacenter"}
]

CATEGORY_TITLES = {
    "cdn_global": "CDNها و سرویس‌های ابری جهانی (Global CDNs & Cloud)",
    "hosting_global": "دیتاسنترها و هاستینگ‌های برتر جهان (Global Hosting & VPS)",
    "platforms_global": "پلتفرم‌های ارتباطی، گیمینگ و DNS جهانی (Global Platforms & DNS)",
    "iran_telecom": "اپراتورهای موبایل و ثابت ایران (Iranian Mobile & Fixed Telecoms)",
    "iran_datacenter": "دیتاسنترها و کلودهای داخلی ایران (Iranian Datacenters & Cloud)"
}


def fetch_prefixes(asn):
    headers = {"User-Agent": "Mozilla/5.0"}
    url = f"https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS{asn}"
    cidrs_v4 = []
    cidrs_v6 = []
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as res:
            data = json.loads(res.read().decode("utf-8"))
            for p in data.get("data", {}).get("prefixes", []):
                p_str = p.get("prefix")
                if not p_str:
                    continue
                if ":" in p_str:
                    cidrs_v6.append(p_str)
                else:
                    cidrs_v4.append(p_str)
    except Exception as e:
        pass
    return cidrs_v4, cidrs_v6


def main():
    print(f"Building ASN Database for {len(TARGET_ENTITIES)} global and Iranian providers...")
    result_catalog = {"categories": {}}

    for cat_key, cat_title in CATEGORY_TITLES.items():
        result_catalog["categories"][cat_key] = {
            "name_fa": cat_title,
            "asns": []
        }

    def process_entity(entity):
        asn = entity["asn"]
        v4, v6 = fetch_prefixes(asn)
        item = {
            "asn": asn,
            "name": entity["name"],
            "country": entity["country"],
            "website": entity["website"],
            "cidrs_v4": v4,
            "cidrs_v6": v6
        }
        return entity["cat"], item

    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = [executor.submit(process_entity, ent) for ent in TARGET_ENTITIES]
        for f in as_completed(futures):
            cat_key, item = f.result()
            print(f"AS{item['asn']} fetched: {len(item['cidrs_v4'])} v4, {len(item['cidrs_v6'])} v6 prefixes")
            result_catalog["categories"][cat_key]["asns"].append(item)

    for cat_key in result_catalog["categories"]:
        result_catalog["categories"][cat_key]["asns"].sort(key=lambda x: x["asn"])

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result_catalog, f, indent=2, ensure_ascii=False)

    total_asns = sum(len(c["asns"]) for c in result_catalog["categories"].values())
    total_v4 = sum(len(a["cidrs_v4"]) for c in result_catalog["categories"].values() for a in c["asns"])
    total_v6 = sum(len(a["cidrs_v6"]) for c in result_catalog["categories"].values() for a in c["asns"])
    print(f"Done! Saved {total_asns} ASNs with {total_v4} IPv4 and {total_v6} IPv6 prefixes to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
