#!/usr/bin/env python3
# =============================================================================
#  NET_DISCOVERY.PY — TỰ ĐỘNG DÒ TÌM & CHẨN ĐOÁN CAMERA IP TRONG MẠNG LAN
#  Hỗ trợ phát hiện IP Camera Hikvision / Dahua / ONVIF khi đổi mạng WiFi/Router
# =============================================================================
import os
import re
import socket
import subprocess
import concurrent.futures
import time
from typing import List, Dict, Optional, Tuple

# Known Camera MAC OUI prefixes (Chữ cái đầu địa chỉ MAC của hãng camera)
CAMERA_OUI_MAP = {
    "64:24:4D": "Hikvision",
    "BC:5E:CD": "Hikvision",
    "C0:56:E3": "Hikvision",
    "AC:CC:8E": "Hikvision",
    "10:DA:43": "Hikvision",
    "EC:A8:6B": "Hikvision",
    "48:EA:63": "Dahua",
    "3C:EF:8C": "Dahua",
    "E0:50:8B": "Dahua",
    "9C:14:63": "Dahua",
    "A4:14:37": "Dahua",
    "00:12:12": "Imou/Dahua",
    "00:1A:79": "Ezviz/Hikvision",
    "00:0F:7D": "Ezviz/Hikvision",
    "B0:F9:63": "Uniview",
    "00:0B:82": "Grandstream",
}


def get_local_ip() -> str:
    """Lấy địa chỉ IP cục bộ chính xác của máy chủ (bỏ qua localhost 127.0.0.1)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Không cần kết nối internet thật, chỉ để OS chọn interface ra ngoài
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def get_local_network_info() -> Dict:
    """Lấy thông tin mạng hiện tại của máy chủ: IP, dải mạng subnet."""
    local_ip = get_local_ip()
    parts = local_ip.split(".")
    if len(parts) == 4 and parts[0] != "127":
        subnet_prefix = f"{parts[0]}.{parts[1]}.{parts[2]}"
    else:
        subnet_prefix = "192.168.1"
    return {
        "local_ip": local_ip,
        "subnet_prefix": subnet_prefix,
        "is_loopback": (local_ip == "127.0.0.1")
    }


def parse_rtsp_url(url: str) -> Dict:
    """Phân tích cú pháp RTSP URL: username, password, host, port, path."""
    clean_url = str(url).strip().strip('"\'')
    if not clean_url.startswith("rtsp://"):
        return {"valid": False, "raw": clean_url}

    pattern = r"rtsp://(?:(?P<user>[^:@]+)(?::(?P<pass>[^@]+))?@)?(?P<host>[^:/]+)(?::(?P<port>\d+))?(?P<path>/.*)?"
    m = re.match(pattern, clean_url)
    if not m:
        return {"valid": False, "raw": clean_url}

    d = m.groupdict()
    return {
        "valid": True,
        "raw": clean_url,
        "user": d.get("user") or "",
        "password": d.get("pass") or "",
        "host": d.get("host") or "",
        "port": int(d.get("port") or 554),
        "path": d.get("path") or "/",
    }


def get_arp_table() -> List[Dict]:
    """Đọc bảng ARP cục bộ để lấy danh sách thiết bị đang hoạt động (cực nhanh < 5ms)."""
    devices = []
    # 1. Thử đọc trực tiếp /proc/net/arp trên Linux
    arp_file = "/proc/net/arp"
    if os.path.isfile(arp_file):
        try:
            with open(arp_file, "r") as f:
                lines = f.readlines()[1:]
            for line in lines:
                parts = line.split()
                if len(parts) >= 4:
                    ip = parts[0]
                    flags = parts[2]
                    mac = parts[3].upper()
                    if flags != "0x0" and mac != "00:00:00:00:00:00":
                        devices.append({"ip": ip, "mac": mac})
            if devices:
                return devices
        except Exception:
            pass

    # 2. Fallback qua lệnh `arp -n` hoặc `arp -a`
    try:
        cmd = ["arp", "-n"] if os.name != "nt" else ["arp", "-a"]
        out = subprocess.check_output(cmd, timeout=1.5, stderr=subprocess.DEVNULL).decode("utf-8", errors="ignore")
        for line in out.splitlines():
            ip_m = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
            mac_m = re.search(r"([0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2})", line)
            if ip_m and mac_m:
                devices.append({
                    "ip": ip_m.group(1),
                    "mac": mac_m.group(1).replace("-", ":").upper()
                })
    except Exception:
        pass

    return devices


def identify_brand_by_mac(mac: str) -> str:
    """Nhận diện hãng sản xuất camera dựa vào 3 byte đầu địa chỉ MAC (OUI)."""
    if not mac:
        return "Camera IP"
    mac_prefix = mac[:8].upper()
    return CAMERA_OUI_MAP.get(mac_prefix, "Camera IP (RTSP/ONVIF)")


def probe_rtsp_port(ip: str, port: int = 554, timeout: float = 0.8) -> Tuple[bool, float, str]:
    """Kiểm tra cổng RTSP có mở không và đo độ trễ mạng."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    t0 = time.perf_counter()
    try:
        err = s.connect_ex((ip, port))
        latency = (time.perf_counter() - t0) * 1000
        if err == 0:
            # Thử gửi gói OPTIONS RTSP
            try:
                req = f"OPTIONS rtsp://{ip}:{port}/ RTSP/1.0\r\nCSeq: 1\r\nUser-Agent: EduSAMS-Discovery\r\n\r\n"
                s.send(req.encode())
                s.settimeout(0.6)
                resp = s.recv(1024).decode("latin-1", errors="ignore")
                server_name = "Camera RTSP"
                for line in resp.splitlines():
                    if line.lower().startswith("server:"):
                        server_name = line.split(":", 1)[1].strip()
                        break
                s.close()
                return True, latency, server_name
            except Exception:
                s.close()
                return True, latency, "Camera RTSP"
        s.close()
        return False, latency, ""
    except Exception:
        try:
            s.close()
        except Exception:
            pass
        return False, 0.0, ""


def check_camera_connection(rtsp_url: str) -> Dict:
    """
    Chẩn đoán chi tiết tình trạng kết nối tới Camera RTSP:
    - Kiểm tra dải mạng subnet (có bị lệch mạng không)
    - Kiểm tra thông mạng & mở cổng 554
    - Đưa ra khuyến nghị khắc phục bằng tiếng Việt rõ ràng.
    """
    parsed = parse_rtsp_url(rtsp_url)
    if not parsed["valid"]:
        return {
            "status": "error",
            "message": "Đường dẫn RTSP không đúng định dạng (phải bắt đầu bằng rtsp://).",
            "suggestion": "Ví dụ chuẩn: rtsp://admin:matkhau@192.168.1.2:554/Streaming/Channels/101"
        }

    net_info = get_local_network_info()
    cam_ip = parsed["host"]
    cam_port = parsed["port"]
    local_ip = net_info["local_ip"]
    local_prefix = net_info["subnet_prefix"]

    # 1. Kiểm tra lệch dải mạng (Subnet mismatch)
    cam_parts = cam_ip.split(".")
    cam_prefix = f"{cam_parts[0]}.{cam_parts[1]}.{cam_parts[2]}" if len(cam_parts) == 4 else ""

    subnet_match = (cam_prefix == local_prefix) if cam_prefix else False

    # 2. Kiểm tra bắt tay TCP cổng 554
    is_open, latency_ms, server_info = probe_rtsp_port(cam_ip, cam_port, timeout=1.5)

    if is_open:
        return {
            "status": "success",
            "cam_ip": cam_ip,
            "cam_port": cam_port,
            "latency_ms": round(latency_ms, 1),
            "local_ip": local_ip,
            "server_info": server_info,
            "message": f"✅ Kết nối camera thành công! (Phản hồi: {latency_ms:.1f}ms - {server_info})",
            "suggestion": "Trạm camera đã sẵn sàng nhận diện và phát luồng trực tiếp."
        }

    # Không kết nối được cổng 554
    if not subnet_match and cam_prefix:
        return {
            "status": "error",
            "cam_ip": cam_ip,
            "cam_port": cam_port,
            "local_ip": local_ip,
            "error_type": "SUBNET_MISMATCH",
            "message": f"⚠️ Lệch dải mạng! Máy chủ đang ở mạng '{local_prefix}.x' (IP: {local_ip}), nhưng Camera đang ở '{cam_prefix}.x' (IP: {cam_ip}).",
            "suggestion": "Bạn vừa đổi WiFi hoặc đổi router cho máy chủ. Hãy bấm nút '🔍 Quét tìm Camera' bên dưới để hệ thống tự động tìm IP mới của camera trong mạng hiện tại!"
        }

    return {
        "status": "error",
        "cam_ip": cam_ip,
        "cam_port": cam_port,
        "local_ip": local_ip,
        "error_type": "PORT_CLOSED_OR_OFFLINE",
        "message": f"⚠️ Không thể kết nối tới IP {cam_ip}:{cam_port} (Không có phản hồi).",
        "suggestion": "Kiểm tra: 1) Camera có cắm nguồn chưa? 2) Camera đã kết nối vào cùng WiFi với máy chủ chưa? 3) Thử bấm 'Quét tìm Camera' để cập nhật lại IP."
    }


def discover_cameras(timeout_per_ip: float = 1.0) -> List[Dict]:
    """
    Quét tự động toàn bộ mạng LAN cục bộ để tìm tất cả Camera RTSP đang hoạt động:
    1. Ưu tiên kiểm tra các IP trong bảng ARP (nhanh < 100ms).
    2. Quét song song 32 luồng trên dải /24 của máy chủ để không bỏ sót thiết bị mới.
    """
    net_info = get_local_network_info()
    subnet_prefix = net_info["subnet_prefix"]
    local_ip = net_info["local_ip"]

    found_cams = {}

    # Bước 1: Quét nhanh danh sách ARP
    arp_entries = get_arp_table()
    arp_map = {item["ip"]: item["mac"] for item in arp_entries}

    def _test_target(ip: str):
        if ip == local_ip:
            return None
        is_open, lat, srv = probe_rtsp_port(ip, 554, timeout=timeout_per_ip)
        if is_open:
            mac = arp_map.get(ip, "")
            brand = identify_brand_by_mac(mac) if mac else (srv if srv != "Camera RTSP" else "Camera IP")
            return {
                "ip": ip,
                "port": 554,
                "mac": mac,
                "brand": brand,
                "latency_ms": round(lat, 1),
                "channels": [
                    {"channel": 101, "name": "Kênh chính 1080p Full HD", "path": "/Streaming/Channels/101"},
                    {"channel": 102, "name": "Kênh phụ Sub-stream siêu mượt", "path": "/Streaming/Channels/102"}
                ]
            }
        return None

    # Quét ưu tiên các IP trong ARP trước (những máy thực sự đang truyền gói tin)
    for ip in arp_map.keys():
        if ip.startswith(subnet_prefix):
            res = _test_target(ip)
            if res:
                found_cams[ip] = res

    # Nếu chưa thấy camera nào hoặc muốn quét kỹ toàn dải /24
    if not found_cams:
        all_ips = [f"{subnet_prefix}.{i}" for i in range(1, 255) if f"{subnet_prefix}.{i}" != local_ip]
        with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
            futures = {executor.submit(_test_target, ip): ip for ip in all_ips}
            for fut in concurrent.futures.as_completed(futures):
                try:
                    res = fut.result()
                    if res:
                        found_cams[res["ip"]] = res
                except Exception:
                    pass

    return list(found_cams.values())


# Aliases for convenience & compatibility
discover_rtsp_cameras = discover_cameras
test_camera_connection = check_camera_connection



if __name__ == "__main__":
    print("=" * 60)
    print("  NET_DISCOVERY — KIỂM TRA & TỰ ĐỘNG QUÉT CAMERA IP")
    print("=" * 60)
    net = get_local_network_info()
    print(f"  IP Máy chủ   : {net['local_ip']}")
    print(f"  Dải mạng LAN : {net['subnet_prefix']}.0/24")
    print("  Đang quét tìm camera RTSP trong mạng...")
    cams = discover_cameras()
    if cams:
        print(f"\n  ✅ ĐÃ TÌM THẤY {len(cams)} CAMERA TRONG MẠNG:")
        for c in cams:
            print(f"    - IP: {c['ip']}:{c['port']} | Hãng: {c['brand']} | MAC: {c['mac']} | Ping: {c['latency_ms']}ms")
            print(f"      Gợi ý URL: rtsp://admin:matkhau@{c['ip']}:554/Streaming/Channels/101")
    else:
        print("\n  ⚠️ Không tìm thấy camera RTSP nào trên dải mạng này.")
        print("     Hãy kiểm tra nguồn camera hoặc kết nối WiFi.")
    print("=" * 60)
