# MITM-DomainFronting & Serverless Studio

[![CI](https://github.com/patterniha/MITM-DomainFronting/actions/workflows/ci.yml/badge.svg)](https://github.com/patterniha/MITM-DomainFronting/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/patterniha/MITM-DomainFronting?include_prereleases&color=blue)](https://github.com/patterniha/MITM-DomainFronting/releases)
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11-brightgreen.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Xray-core](https://img.shields.io/badge/Xray--core-v26.6.27%2B-blueviolet)](https://github.com/XTLS/Xray-core)

<div dir="rtl">

استودیوی یکپارچه و بهینه‌سازی‌شده برای دورزدن فیلترینگ بدون نیاز به سرور یا ورکر شخصی، با تلفیق دو متد پیشرفته **MITM-DomainFronting** و **Serverless-for-Iran** همراه با رابط گرافیکی (GUI)، اسکنر اختصاصی IP تمیز، بانک داده‌ی رنج‌های ASN جهانی و ایران، و پایپ‌لاین انتشار CI/CD در گیت‌هاب.

---

## فهرست مطالب
1. [ویژگی‌های اصلی](#ویژگیهای-اصلی)
2. [معماری سیستم](#معماری-سیستم)
3. [پایگاه داده ASN و رنج‌های IP](#پایگاه-داده-asn-و-رنجهای-ip)
4. [حالت‌های اتصال](#حالتهای-اتصال)
5. [راهنمای نصب و راه‌اندازی سریع](#راهنمای-نصب-و-راهاندازی-سریع)
6. [نحوه کارکرد اسکنر IP](#نحوه-کارکرد-اسکنر-ip)
7. [تست و مشارکت در پروژه](#تست-و-مشارکت-در-پروژه)

---

## ویژگی‌های اصلی

- **رابط کاربری مستقل (GUI):** بدون نیاز به نصب v2rayN؛ مدیریت و مانیتورینگ مستقیم هسته Xray، مشاهده لاگ زنده و راه‌اندازی تک‌کلیکی.
- **دانلود و راه‌اندازی خودکار هسته Xray:** بررسی خودکار و دانلود آخرین نگارش پایدار Xray-core برای ویندوز در صورت عدم وجود.
- **تغییر خودکار پراکسی ویندوز:** فعال و غیرفعال‌سازی آنی تنظیمات Proxy سیستم‌عامل (WinINet) با یک کلیک.
- **تولید و ثبت آسان گواهی CA:** ساخت کلید و گواهی اختصاصی و نصب مستقیم در مخزن معتمد سیستم (Trusted Root).
- **پشتیبانی از Clean IP اختصاصی برای هر CDN:** امکان وارد کردن آدرس IP تمیز برای هر یک از شبکه‌های Cloudflare، Fastly، Google/YouTube، Meta، GCore و CloudFront جهت برقراری اتصال مستقیم و جلوگیری از خطای مسدودی IP.
- **اسکنر اختصاصی چندنخی (Multi-threaded Scanner):**
  - تست پینگ TCP (Port 443 / سفارشی)
  - تست هندشیک TLS (تشخیص سلامت عبور از DPI)
  - تست پینگ ICMP و UDP
  - مرتب‌سازی خودکار بر اساس کمترین میلی‌ثانیه و دکمه اعمال مستقیم به عنوان Clean IP.
- **لایه ضد تحریم 403 (Serverless WARP):** هدایت ترافیک سرویس‌های تحریم‌کننده کاربران ایرانی (OpenAI، Claude، Spotify) از مسیر سرورلس کلودفلر WARP.

---

## معماری سیستم

```
                   +---------------------------------------------+
                   |           MITM & Serverless Studio          |
                   |               Desktop GUI                   |
                   +----------------------+----------------------+
                                          |
                      +-------------------+-------------------+
                      |                                       |
           [ترافیک مستقیم عمومی]                   [سرویس‌های فیلترشده CDN]
        (Websites, APIs, Telegram)               (YouTube, Instagram, Reddit)
                      |                                       |
             +--------v--------+                     +--------v--------+
             | Serverless Frag |                     |  MITM Decrypt   |
             | TCP Split/Noise |                     | (Local CA Cert) |
             +--------+--------+                     +--------+--------+
                      |                                       |
                      |                               +-------v-------+
                      |                               | SNI Repack    |
                      |                               | Clean IP CDN  |
                      |                               +-------+-------+
                      |                                       |
                      +-------------------+-------------------+
                                          |
                               +----------v----------+
                               |   اینترنت مستقیم    |
                               |  بدون نیاز به سرور  |
                               +---------------------+
```

---

## پایگاه داده ASN و رنج‌های IP

پروژه شامل بیش از **۶۶,۰۰۰ پیشوند شبکه (CIDR)** در قالب فایل استاندارد `data/asn_catalog.json` برای **۶۲ کمپانی و اپراتور بزرگ** است:

1. **CDNها و ابرهای جهانی:**
   Cloudflare (AS13335), Fastly (AS54113), Google/YouTube (AS15169, AS36040), Amazon CloudFront (AS16509, AS14618), Meta/Instagram (AS32934), Microsoft Azure (AS8075), GCore (AS199524), Akamai (AS20940, AS16625), Edgecast (AS15133), Apple (AS714), ByteDance/TikTok (AS138699), Bunny CDN (AS200325), CDN77 (AS60068), StackPath (AS33438), Imperva (AS19551), Edgio (AS22822), CacheFly (AS30081), Oracle Cloud (AS31898), Alibaba Cloud (AS45102), Tencent (AS132203).

2. **دیتاسنترها و هاستینگ‌های جهانی:**
   Hetzner (AS24940), OVHcloud (AS16276), DigitalOcean (AS14061), Linode (AS63949), Vultr (AS20473), Scaleway (AS12876), Leaseweb (AS60781), IBM Cloud (AS36351).

3. **پلتفرم‌ها و DNSهای جهانی:**
   Telegram (AS62041, AS62014, AS44907, AS59930), Twitter/X (AS13414), Valve Steam (AS32590), GitHub (AS36459), OpenDNS (AS36692), Quad9 (AS19281).

4. **اپراتورها و دیتاسنترهای ایران:**
   همراه اول (AS197207), ایرانسل (AS44244), مخابرات ایران (AS58224, AS12880), رایتل (AS57218), شاتل (AS56402), آسیاتک (AS43754), مبین‌نت (AS50810), های‌وب (AS49666, AS56534), زی‌تل (AS60798), صبانت (AS41881), پیشگامان (AS48159), فن‌آوا (AS41689), داتک (AS25182), ابر آروان (AS208004), دراک (AS204620), افرانت (AS25184), پارس آنلاین (AS16322), رسپینا (AS42337), فناپ (AS57534), تبیان (AS39501).

> **به‌روزرسانی خودکار:** اکشن گیت‌هاب هفتگی به‌طور خودکار رنج‌ها را مستقیماً از دیتابیس BGP RIPEstat همگام و تجدید می‌کند.

---

## حالت‌های اتصال

| حالت | شرح عملکرد | نیاز به گواهی |
| :--- | :--- | :---: |
| **ترکیبی هوشمند (Hybrid)** | فرگمنت پکت‌های TLS برای وب عمومی + هدایت خودکار سرویس‌های CDN به لایه MITM Fronting با IP تمیز. | بله |
| **فقط MITM-DomainFronting** | رمزگشایی محلی با گواهی اختصاصی و اتصال به دامنه‌های فرانتینگ یا Clean IPهای مشخص‌شده. | بله |
| **سرورلس نوع A (Serverless FragA)** | خرد کردن هندشیک TLS با تنظیمات پکت تایپ A بدون نیاز به دستکاری گواهی. | خیر |
| **سرورلس نوع B (Serverless FragB)** | قطعه‌بندی ترافیک با تنظیمات پکت تایپ B بدون نیاز به گواهی. | خیر |

---

## راهنمای نصب و راه‌اندازی سریع

### روش ۱: استفاده از نسخه آماده (Releases)
از بخش [Releases گیت‌هاب](https://github.com/patterniha/MITM-DomainFronting/releases) فایل فشرده `MITM-DomainFronting-Serverless-Windows.zip` را دریافت و اکسترکت کنید، سپس `run.bat` را اجرا نمایید.

### روش ۲: اجرا از طریق سورس کد
1. پایتون ۳.۱۰ یا ۳.۱۱ را نصب کنید.
2. مخزن را کلون کنید:
   ```bash
   git clone https://github.com/patterniha/MITM-DomainFronting.git
   cd MITM-DomainFronting
   ```
3. برنامه را اجرا کنید:
   ```bash
   python main.py
   ```
4. در تب اول، روی دکمه **«نصب و فعال‌سازی خودکار گواهی در ویندوز»** کلیک کنید.
5. دکمه **«شروع هسته Xray»** و سپس **«تغییر وضعیت پراکسی سیستم»** را بزنید.

---

## نحوه کارکرد اسکنر IP
1. وارد تب **«اسکنر پیشرفته IP»** شوید.
2. هدف اسکن را انتخاب کنید (مثلاً *Cloudflare* یا *Fastly* یا *ورود رنج دستی از تب ASN*).
3. نوع تست (TCP 443 یا TLS Handshake) را تعیین کرده و **«شروع اسکن»** را بزنید.
4. روی سریع‌ترین IP کلیک کرده و با دکمه **«اعمال IP انتخاب شده»** آن را مستقیماً برای CDN هدف ذخیره کنید.

---

## تست و مشارکت در پروژه

اجرای تست‌های واحد:
```bash
python -m unittest discover tests
```

ساخت بسته نصبی Release محلی:
```bash
python scripts/package_release.py
```

به‌روزرسانی رنج‌های ASN:
```bash
python scripts/build_asn_database.py
```

</div>

---

<div dir="ltr">

## English Summary

**MITM-DomainFronting & Serverless Studio** is an all-in-one desktop application to bypass censorship in restricted network environments without requiring personal remote VPS proxies or workers.

### Highlights:
- Standalone Modern GUI managing `Xray-core` directly (no v2rayN needed).
- Custom Clean IP assignment per CDN (Cloudflare, Fastly, Google, Meta, GCore, CloudFront).
- Multi-threaded IP Scanner supporting TCP 443, TLS Handshake, ICMP, and UDP tests.
- Offline ASN Database holding **over 66,000 IPv4 & IPv6 CIDRs** across 62 global and Iranian providers.
- Automated GitHub Actions CI/CD workflows for testing, release packaging, and weekly ASN updates.

</div>
