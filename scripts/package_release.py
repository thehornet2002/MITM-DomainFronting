import os
import sys
import zipfile
import hashlib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.join(BASE_DIR, "dist")

INCLUDE_PATTERNS = [
    "core",
    "gui",
    "data",
    "Xray-config",
    "Serverless-config",
    "main.py",
    "run.bat",
    "README.md",
    "LICENSE"
]

EXCLUDE_PATTERNS = [
    "__pycache__",
    ".git",
    ".github",
    ".venv",
    "active_config.json",
    "settings.json",
    "dist"
]


def sha256sum(filename):
    h = hashlib.sha256()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def package():
    os.makedirs(DIST_DIR, exist_ok=True)
    zip_name = "MITM-DomainFronting-Serverless-Windows.zip"
    zip_path = os.path.join(DIST_DIR, zip_name)

    print(f"Creating release package: {zip_path}...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for item in INCLUDE_PATTERNS:
            item_path = os.path.join(BASE_DIR, item)
            if not os.path.exists(item_path):
                continue
            if os.path.isfile(item_path):
                zip_file.write(item_path, arcname=item)
                print(f"  Added file: {item}")
            elif os.path.isdir(item_path):
                for root, dirs, files in os.walk(item_path):
                    dirs[:] = [d for d in dirs if d not in EXCLUDE_PATTERNS]
                    for f in files:
                        if any(ex in f for ex in [".pyc", ".DS_Store"]):
                            continue
                        full_f = os.path.join(root, f)
                        rel_f = os.path.relpath(full_f, BASE_DIR)
                        zip_file.write(full_f, arcname=rel_f)
                print(f"  Added directory: {item}/")

    checksum = sha256sum(zip_path)
    sha_file = zip_path + ".sha256"
    with open(sha_file, "w", encoding="utf-8") as f:
        f.write(f"{checksum}  {zip_name}\n")

    print(f"Package created successfully!")
    print(f"Archive: {zip_path}")
    print(f"SHA-256: {checksum}")


if __name__ == "__main__":
    package()
