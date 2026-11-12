import sys
sys.stdout.reconfigure(encoding='utf-8')
import re
with open(r'c:\Users\ADMIN\Desktop\Diem danh STEM\cloud_server.py', encoding='utf-8') as f:
    content = f.read()
routes = re.findall(r'@app\.(get|post|put|delete|websocket)\(["\']([^"\']+)["\']', content)
for method, path in routes:
    print(method.upper().ljust(10), path)
