import json, sys
from pathlib import Path
from config import CREDENTIALS_FILE

cred_file = Path(CREDENTIALS_FILE)
print("=== KIEM TRA CREDENTIALS FILE ===")
if not cred_file.exists():
    print("[MISS] File KHONG TON TAI:", cred_file)
    sys.exit(1)

data = json.loads(cred_file.read_text())
print("[OK ] File ton tai")
print(f"      type          : {data.get('type', '?')}")
print(f"      project_id    : {data.get('project_id', '?')}")
print(f"      client_email  : {data.get('client_email', '?')}")
pk = data.get("private_key", "")
print(f"      private_key   : {len(pk)} chars")
if "-----BEGIN RSA PRIVATE KEY-----" in pk or "-----BEGIN PRIVATE KEY-----" in pk:
    print("      key format    : [OK] Dung dinh dang PEM")
else:
    print("      key format    : [LOI] Sai dinh dang!")
kid = data.get("private_key_id", "?")
print(f"      key_id        : {kid[:8]}...{kid[-4:]}")
