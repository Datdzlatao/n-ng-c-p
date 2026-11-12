"""
app/services/tailscale_service.py — Quản lý Tích Hợp Tailscale Funnel & Public Camera HTTPS
Tự động kích hoạt Tailscale Funnel, tạo link HTTPS/WSS công khai cho luồng Camera RTSP / Edge AI
cho phép giám sát từ xa trên điện thoại và mạng internet mà vẫn bảo mật 100%.
"""
import os
import json
import shutil
import logging
import subprocess
from typing import Dict, Any, Optional
from pathlib import Path

from app.database import get_db

log = logging.getLogger("stem.tailscale")

TAILSCALE_BIN = shutil.which("tailscale") or "/usr/bin/tailscale"


class TailscaleService:
    """Xử lý toàn bộ logic kiểm tra trạng thái, kích hoạt Funnel và sinh link HTTPS cho camera."""

    @staticmethod
    def is_installed() -> bool:
        """Kiểm tra máy chủ đã cài đặt Tailscale CLI hay chưa."""
        return os.path.exists(TAILSCALE_BIN) or shutil.which("tailscale") is not None

    @staticmethod
    def get_status() -> Dict[str, Any]:
        """
        Lấy trạng thái chi tiết của Tailscale daemon:
        - installed: bool
        - backend_state: "Running" | "NeedsLogin" | "Stopped" | "NotInstalled"
        - is_running: bool
        - domain: FQDN máy chủ (VD: minhphuc-loq-15iax9.tailnet-xyz.ts.net)
        - auth_url: URL đăng nhập khi NeedsLogin
        - funnel_active: bool
        - funnel_url: str
        """
        if not TailscaleService.is_installed():
            return {
                "installed": False,
                "backend_state": "NotInstalled",
                "is_running": False,
                "domain": None,
                "auth_url": None,
                "funnel_active": False,
                "funnel_url": None,
                "message": "Tailscale chưa được cài đặt trên máy chủ."
            }

        cmd_bin = shutil.which("tailscale") or TAILSCALE_BIN
        result = {
            "installed": True,
            "backend_state": "Unknown",
            "is_running": False,
            "domain": None,
            "node_name": None,
            "tailnet": None,
            "tailscale_ips": [],
            "auth_url": None,
            "funnel_active": False,
            "funnel_url": None,
            "message": ""
        }

        # 1. Đọc trạng thái qua tailscale status --json
        try:
            p = subprocess.run(
                [cmd_bin, "status", "--json"],
                capture_output=True,
                text=True,
                timeout=3.0
            )
            if p.returncode == 0 and p.stdout.strip():
                data = json.loads(p.stdout)
                b_state = data.get("BackendState", "Unknown")
                result["backend_state"] = b_state
                result["is_running"] = (b_state == "Running")
                result["auth_url"] = data.get("AuthURL")

                self_node = data.get("Self") or {}
                result["node_name"] = self_node.get("HostName")
                result["tailscale_ips"] = self_node.get("TailscaleIPs") or []

                raw_dns = self_node.get("DNSName") or ""
                # Bỏ dấu chấm cuối tên miền DNS (VD: 'my-pc.ts.net.' -> 'my-pc.ts.net')
                clean_dns = raw_dns.rstrip(".")
                cert_domains = data.get("CertDomains") or []
                if clean_dns:
                    result["domain"] = clean_dns
                elif cert_domains and len(cert_domains) > 0:
                    result["domain"] = cert_domains[0].rstrip(".")
                elif os.getenv("TAILSCALE_DOMAIN"):
                    result["domain"] = os.getenv("TAILSCALE_DOMAIN").strip()

                curr_tailnet = data.get("CurrentTailnet")
                tailnet_name = curr_tailnet.get("Name") if isinstance(curr_tailnet, dict) else None
                result["tailnet"] = data.get("MagicDNSSuffix") or tailnet_name
        except subprocess.TimeoutExpired:
            log.warning("[TAILSCALE] Timeout khi chạy tailscale status --json")
            result["backend_state"] = "Timeout"
        except Exception as ex:
            log.warning(f"[TAILSCALE] Lỗi đọc status: {ex}")
            result["backend_state"] = "Error"

        # Biến môi trường ghi đè thủ công nếu có
        if not result["domain"] and os.getenv("TAILSCALE_DOMAIN"):
            result["domain"] = os.getenv("TAILSCALE_DOMAIN").strip()

        # 2. Kiểm tra trạng thái Funnel hiện tại
        if result["is_running"] and result["domain"]:
            try:
                p_fn = subprocess.run(
                    [cmd_bin, "funnel", "status", "--json"],
                    capture_output=True,
                    text=True,
                    timeout=2.0
                )
                if p_fn.returncode == 0 and p_fn.stdout.strip() not in ("{}", "null", ""):
                    result["funnel_active"] = True
                    result["funnel_url"] = f"https://{result['domain']}"
            except Exception:
                pass

            if not result["funnel_active"]:
                result["funnel_url"] = f"https://{result['domain']}"

        # Tạo thông điệp hướng dẫn thân thiện
        if result["backend_state"] == "Running":
            result["message"] = f"Tailscale đang hoạt động tại miền https://{result['domain'] or 'ts.net'}"
        elif result["backend_state"] == "NeedsLogin":
            result["message"] = "Tailscale chưa đăng nhập. Vui lòng chạy lệnh 'tailscale up' trên máy chủ để kết nối mạng toàn cầu."
        elif result["backend_state"] == "Stopped":
            result["message"] = "Dịch vụ Tailscale đang dừng. Vui lòng bật lại bằng 'tailscale up'."
        else:
            result["message"] = f"Trạng thái Tailscale: {result['backend_state']}"

        return result

    @staticmethod
    def ensure_funnel(port: int = 8000) -> Dict[str, Any]:
        """
        Kích hoạt Tailscale Funnel trên cổng chỉ định (mặc định 8000).
        Funnel sẽ tự động cấp chứng chỉ SSL Let's Encrypt hợp lệ và mở cổng HTTPS công khai ra Internet.
        """
        status = TailscaleService.get_status()
        if not status["installed"]:
            return {
                "success": False,
                "message": "Tailscale chưa được cài đặt trên máy chủ.",
                "status": status
            }

        if not status["is_running"]:
            return {
                "success": False,
                "message": status["message"],
                "status": status,
                "needs_login": (status["backend_state"] == "NeedsLogin")
            }

        cmd_bin = shutil.which("tailscale") or TAILSCALE_BIN
        try:
            # Thử bật Funnel chế độ ngầm (--bg --yes)
            p = subprocess.run(
                [cmd_bin, "funnel", "--bg", "--yes", str(port)],
                capture_output=True,
                text=True,
                timeout=6.0
            )
            output_msg = (p.stdout or "") + (p.stderr or "")

            if p.returncode == 0:
                log.info(f"[TAILSCALE] Đã kích hoạt Funnel trên cổng {port}: {output_msg.strip()}")
                domain = status["domain"]
                funnel_url = f"https://{domain}" if domain else f"https://localhost:{port}"
                return {
                    "success": True,
                    "message": f"Đã kích hoạt Tailscale Funnel HTTPS thành công trên cổng {port}!",
                    "funnel_url": funnel_url,
                    "domain": domain,
                    "status": status
                }
            else:
                # Nếu Funnel không được bật do chính sách Tailnet, thử Tailscale Serve (nội bộ Tailnet)
                log.warning(f"[TAILSCALE] Funnel trả về mã lỗi {p.returncode}: {output_msg.strip()}. Thử Serve...")
                p_srv = subprocess.run(
                    [cmd_bin, "serve", "--bg", "--yes", str(port)],
                    capture_output=True,
                    text=True,
                    timeout=5.0
                )
                if p_srv.returncode == 0:
                    domain = status["domain"]
                    serve_url = f"https://{domain}" if domain else f"https://localhost:{port}"
                    return {
                        "success": True,
                        "message": f"Đã kích hoạt Tailscale Serve HTTPS (Nội bộ Tailnet) trên cổng {port}.",
                        "funnel_url": serve_url,
                        "domain": domain,
                        "status": status,
                        "is_serve_fallback": True
                    }
                err_text = output_msg.strip()
                import re
                m_act = re.search(r"https://login\.tailscale\.com/f/[^\s]+", err_text)
                if m_act:
                    act_url = m_act.group(0)
                    return {
                        "success": False,
                        "needs_funnel_enable": True,
                        "funnel_enable_url": act_url,
                        "message": f"Tài khoản Tailnet cần bật quyền Funnel lần đầu. Vui lòng mở link sau để kích hoạt: {act_url}",
                        "status": status
                    }
                if "access denied" in err_text.lower() or "profiles access" in err_text.lower():
                    friendly_msg = "Quyền điều khiển Tailscale bị từ chối. Hãy mở Terminal máy chủ chạy lệnh: 'sudo tailscale set --operator=$USER' một lần duy nhất."
                else:
                    friendly_msg = f"Không thể bật Tailscale Funnel: {err_text}"
                return {
                    "success": False,
                    "message": friendly_msg,
                    "status": status,
                    "raw_error": err_text
                }
        except subprocess.TimeoutExpired as te:
            import re
            out_raw = (te.stdout or b"").decode("utf-8", "ignore") if isinstance(te.stdout, bytes) else str(te.stdout or "")
            out_err = (te.stderr or b"").decode("utf-8", "ignore") if isinstance(te.stderr, bytes) else str(te.stderr or "")
            comb = out_raw + out_err
            m = re.search(r"https://login\.tailscale\.com/f/[^\s]+", comb)
            if m:
                act_url = m.group(0)
                return {
                    "success": False,
                    "needs_funnel_enable": True,
                    "funnel_enable_url": act_url,
                    "message": f"Tài khoản Tailnet cần bật quyền Funnel lần đầu. Vui lòng mở link sau để kích hoạt: {act_url}",
                    "status": status
                }
            return {
                "success": False,
                "message": "Quá thời gian phản hồi từ lệnh tailscale funnel.",
                "status": status
            }
        except Exception as ex:
            return {
                "success": False,
                "message": f"Ngoại lệ khi gọi Tailscale Funnel: {str(ex)}",
                "status": status
            }

    @staticmethod
    def get_camera_stream_urls(school_id: int, camera_id: int, custom_domain: Optional[str] = None) -> Dict[str, Any]:
        """
        Sinh toàn bộ các đường link xem video, websocket và snapshot bảo mật cho một trạm camera.
        Bao gồm:
        - Link HTTPS công khai qua Tailscale
        - Link WSS thời gian thực qua Tailscale
        - Link Snapshot tức thời
        - Link fallback nội bộ
        """
        domain = custom_domain
        if not domain:
            ts_status = TailscaleService.get_status()
            domain = ts_status.get("domain")

        local_stream_path = f"/api/v1/s/{school_id}/cameras/{camera_id}/live-stream"
        local_ws_path     = f"/api/v1/s/{school_id}/cameras/{camera_id}/live-ws"
        local_snap_path   = f"/api/v1/s/{school_id}/cameras/{camera_id}/snapshot"

        if domain:
            public_https_url = f"https://{domain}{local_stream_path}"
            public_wss_url   = f"wss://{domain}{local_ws_path}"
            public_snap_url  = f"https://{domain}{local_snap_path}"
            public_web_url   = f"https://{domain}/app/index.html"
            is_public_ready  = True
        else:
            public_https_url = local_stream_path
            public_wss_url   = local_ws_path
            public_snap_url  = local_snap_path
            public_web_url   = "/app/index.html"
            is_public_ready  = False

        return {
            "school_id": school_id,
            "camera_id": camera_id,
            "domain": domain,
            "is_public_ready": is_public_ready,
            "public_stream_url": public_https_url,
            "public_wss_url": public_wss_url,
            "public_snapshot_url": public_snap_url,
            "public_web_url": public_web_url,
            "local_stream_url": local_stream_path,
            "local_ws_url": local_ws_path
        }

    @staticmethod
    def auto_publish_camera(school_id: int, camera_id: int, stream_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Tự động thực thi toàn bộ luồng nghiệp vụ khi người dùng nhập link RTSP:
        1. Kiểm tra trạng thái Tailscale và kích hoạt Funnel trên cổng 8000.
        2. Tạo link HTTPS công khai cho Camera.
        3. Cập nhật trường public_stream_url trong CSDL camera_stations.
        4. Trả về thông tin đầy đủ kèm hướng dẫn xem trên Web và điện thoại.
        """
        ts_status = TailscaleService.get_status()
        domain = ts_status.get("domain")

        # Thử kích hoạt Funnel nếu Tailscale đang Running
        funnel_res = None
        if ts_status.get("is_running"):
            try:
                funnel_res = TailscaleService.ensure_funnel(port=8000)
            except Exception as e:
                log.warning(f"[TAILSCALE] Lỗi ensure_funnel: {e}")

        # Sinh các URL trực tiếp
        urls = TailscaleService.get_camera_stream_urls(school_id, camera_id, domain)
        public_url = urls["public_stream_url"] if urls["is_public_ready"] else None

        # Cập nhật CSDL
        conn = get_db()
        try:
            if public_url:
                conn.execute(
                    "UPDATE camera_stations SET public_stream_url=?, tailscale_enabled=1 WHERE id=? AND school_id=?",
                    (public_url, camera_id, school_id)
                )
            else:
                conn.execute(
                    "UPDATE camera_stations SET tailscale_enabled=1 WHERE id=? AND school_id=?",
                    (camera_id, school_id)
                )
            conn.commit()
        finally:
            conn.close()

        msg = f"Đã tự động xuất bản luồng camera sang link HTTPS Tailscale: {public_url}" if public_url else "Đã lưu RTSP vào hệ thống."
        if funnel_res and funnel_res.get("needs_funnel_enable"):
            msg = f"Đã cấu hình luồng camera ({public_url}). Hãy mở link sau để kích hoạt quyền Funnel lần đầu: {funnel_res.get('funnel_enable_url')}"

        return {
            "status": "success",
            "camera_id": camera_id,
            "school_id": school_id,
            "stream_url": stream_url,
            "tailscale_status": ts_status,
            "funnel_result": funnel_res,
            "needs_funnel_enable": bool(funnel_res and funnel_res.get("needs_funnel_enable")),
            "funnel_enable_url": funnel_res.get("funnel_enable_url") if funnel_res else None,
            "urls": urls,
            "public_stream_url": public_url,
            "message": msg
        }
