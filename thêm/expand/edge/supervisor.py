#!/usr/bin/env python3
# =============================================================================
#  SUPERVISOR ENGINE — QUẢN TRỊ ĐA TRẠM CAMERA AI ĐIỂM DANH STEM
#  Hỗ trợ chạy song song N camera AI (RTSP / Webcam) đồng thời
#  Tự động nạp cấu hình từ Web Dashboard / Database (Zero-Touch)
#  Tự động hồi phục khi mất mạng (Watchdog & Auto-Reconnect)
# =============================================================================
"""
edge/supervisor.py — Bộ điều phối và giám sát đa camera AI trung tâm.
"""
import os
import sys
import time
import json
import sqlite3
import signal
import argparse
import threading
import subprocess
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONF_JSON = os.path.join(BASE_DIR, "data", "cameras.json")
CONF_INI  = os.path.join(BASE_DIR, "data", "camera.conf")
DB_PATH   = os.path.join(BASE_DIR, "..", "backend", "data", "stem_platform.db")
LOG_DIR   = os.path.join(BASE_DIR, "data", "logs")

os.makedirs(LOG_DIR, exist_ok=True)

# ANSI Color codes for clean terminal outputs
COLORS = [
    "\033[92m",  # Green
    "\033[96m",  # Cyan
    "\033[93m",  # Yellow
    "\033[95m",  # Magenta
    "\033[94m",  # Blue
]
RESET_COLOR = "\033[0m"


class MultiCameraSupervisor:
    def __init__(self, school_id=None, server_url="http://localhost:8000", gui_mode=False):
        self.school_id = school_id
        self.server_url = server_url
        self.gui_mode = gui_mode
        self.workers = {}  # { cam_id: { "process": Popen, "config": dict, "last_restart": float, "color": str } }
        self.running = True
        self.last_conf_mtime = 0
        self.lock = threading.Lock()

        # Register termination signals
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        print(f"\n{RESET_COLOR}[SUPERVISOR] 🛑 Nhận tín hiệu dừng (Signal {signum}). Đang tắt tất cả trạm camera an toàn...")
        self.running = False
        self.stop_all()
        print("[SUPERVISOR] Đã dừng tất cả các trạm thành công. Tạm biệt!\n")
        sys.exit(0)

    def get_school_id(self):
        if self.school_id is not None:
            return self.school_id

        # Thử đọc từ cameras.json
        if os.path.isfile(CONF_JSON):
            try:
                with open(CONF_JSON, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    if d.get("school_id"):
                        self.school_id = int(d["school_id"])
                        return self.school_id
            except Exception:
                pass

        # Thử đọc từ camera.conf
        if os.path.isfile(CONF_INI):
            try:
                import configparser
                cfg = configparser.ConfigParser()
                cfg.read(CONF_INI, encoding="utf-8")
                if "camera" in cfg and "school_id" in cfg["camera"]:
                    self.school_id = int(cfg["camera"]["school_id"])
                    return self.school_id
            except Exception:
                pass

        # Fallback từ SQLite DB
        if os.path.isfile(DB_PATH):
            try:
                conn = sqlite3.connect(DB_PATH)
                row = conn.execute("SELECT school_id FROM camera_stations ORDER BY id DESC LIMIT 1").fetchone()
                conn.close()
                if row and row[0]:
                    self.school_id = int(row[0])
                    return self.school_id
            except Exception:
                pass

        self.school_id = 10
        return self.school_id

    def sync_from_database(self):
        """Đồng bộ danh sách camera từ SQLite vào cameras.json nếu file chưa có hoặc cần cập nhật."""
        sch_id = self.get_school_id()
        if not os.path.isfile(DB_PATH):
            return []

        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT id, school_id, camera_num, name, location, stream_type, stream_url, secret_key, uniform_check, status 
                   FROM camera_stations WHERE school_id=? AND (status != 'DISABLED' OR status IS NULL)
                   ORDER BY camera_num ASC, id ASC""",
                (sch_id,)
            ).fetchall()
            conn.close()

            cameras_list = []
            base_port = 8081
            for idx, r in enumerate(rows):
                c_dict = dict(r)
                c_dict["stream_port"] = base_port + idx
                c_dict["uniform_check"] = bool(c_dict.get("uniform_check", 1))
                cameras_list.append(c_dict)

            # Chỉ ghi file nếu danh sách camera thực sự thay đổi (tránh thay đổi mtime liên tục)
            if os.path.isfile(CONF_JSON):
                try:
                    with open(CONF_JSON, "r", encoding="utf-8") as f_ex:
                        ex_data = json.load(f_ex)
                        if ex_data.get("cameras") == cameras_list and ex_data.get("school_id") == sch_id:
                            return cameras_list
                except Exception:
                    pass

            data = {
                "school_id": sch_id,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "cameras": cameras_list
            }

            os.makedirs(os.path.dirname(CONF_JSON), exist_ok=True)
            with open(CONF_JSON, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return cameras_list
        except Exception as ex:
            print(f"[SUPERVISOR] ⚠️ Lỗi đọc DB cục bộ: {ex}")
            return []

    def load_active_cameras(self):
        """Đọc danh sách camera hoạt động từ cameras.json hoặc fallback."""
        if not os.path.isfile(CONF_JSON):
            return self.sync_from_database()

        try:
            with open(CONF_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
                cams = data.get("cameras", [])
                if cams:
                    return cams
        except Exception as e:
            print(f"[SUPERVISOR] ⚠️ Không thể đọc {CONF_JSON}: {e}")

        return self.sync_from_database()

    def _stream_worker_output(self, cam_id, cam_name, color, process, log_path):
        """Luồng đọc log của camera con và in ra console kèm ghi file log."""
        try:
            with open(log_path, "a", encoding="utf-8") as f_log:
                f_log.write(f"\n--- KHỞI ĐỘNG TRẠM #{cam_id} ({cam_name}) lúc {datetime.now()} ---\n")
                for line in iter(process.stdout.readline, ''):
                    if not line:
                        break
                    line_clean = line.rstrip()
                    f_log.write(line_clean + "\n")
                    f_log.flush()
                    # In ra terminal với tag màu riêng cho từng camera
                    prefix = f"{color}[Trạm #{cam_id} - {cam_name}]{RESET_COLOR} "
                    print(f"{prefix}{line_clean}")
        except Exception:
            pass

    def start_worker(self, cam):
        cam_id = cam["id"]
        cam_name = cam.get("name", f"Camera #{cam_id}")
        stream_url = str(cam.get("stream_url", "0")).strip().strip('"\'')
        stream_port = cam.get("stream_port", 8080 + int(cam.get("camera_num", 1)))
        secret_key = str(cam.get("secret_key", "")).strip()
        school_id = cam.get("school_id", self.get_school_id())

        color = COLORS[(cam_id % len(COLORS))]

        cmd = [
            sys.executable,
            os.path.join(BASE_DIR, "main.py"),
            "--school", str(school_id),
            "--cam-id", str(cam_id),
            "--camera", stream_url,
            "--port", str(stream_port),
            "--server", self.server_url,
            "--auto-reconnect"
        ]
        if secret_key:
            cmd.extend(["--secret", secret_key])
        if not self.gui_mode:
            cmd.append("--headless")
        if bool(cam.get("uniform_check", True)):
            cmd.append("--uniform")
        else:
            cmd.append("--no-uniform")

        if bool(cam.get("occlusion_check", True)):
            cmd.append("--occlusion-check")
        else:
            cmd.append("--no-occlusion-check")

        log_path = os.path.join(LOG_DIR, f"camera_{cam_id}.log")

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=BASE_DIR
            )

            # Khởi chạy thread đọc log
            log_thread = threading.Thread(
                target=self._stream_worker_output,
                args=(cam_id, cam_name, color, proc, log_path),
                daemon=True
            )
            log_thread.start()

            with self.lock:
                self.workers[cam_id] = {
                    "process": proc,
                    "config": dict(cam),
                    "last_restart": time.time(),
                    "color": color,
                    "log_thread": log_thread
                }

            print(f"{color}[SUPERVISOR] 🚀 Khởi chạy Trạm #{cam_id} ({cam_name}) -> Luồng: {stream_url} | Stream: http://localhost:{stream_port}{RESET_COLOR}")
        except Exception as e:
            print(f"[SUPERVISOR] ❌ Không thể khởi chạy Trạm #{cam_id}: {e}")

    def stop_worker(self, cam_id):
        with self.lock:
            worker = self.workers.pop(cam_id, None)

        if not worker:
            return

        proc = worker["process"]
        cam_name = worker["config"].get("name", f"Camera #{cam_id}")
        print(f"[SUPERVISOR] 🛑 Đang dừng Trạm #{cam_id} ({cam_name})...")

        try:
            proc.terminate()
            try:
                proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=1.0)
        except Exception:
            pass

    def stop_all(self):
        with self.lock:
            cids = list(self.workers.keys())
        for cid in cids:
            self.stop_worker(cid)

    def restart_worker(self, cam):
        self.stop_worker(cam["id"])
        time.sleep(0.5)
        self.start_worker(cam)

    def run(self):
        sch_id = self.get_school_id()
        print("=" * 65)
        print("  🎥 HỆ THỐNG QUẢN TRỊ ĐA CAMERA AI STEM (SUPERVISOR v1.0)")
        print(f"  Trường ID: #{sch_id} | Server Backend: {self.server_url}")
        print("  Chế độ: Đa tiến trình song song | Tự động đồng bộ Zero-Touch")
        print("=" * 65)

        # 1. Nạp danh sách ban đầu và khởi chạy
        initial_cams = self.load_active_cameras()
        if not initial_cams:
            print("[SUPERVISOR] ⚠️ Chưa tìm thấy trạm camera nào. Đang chờ cấu hình từ Web Dashboard...")
        else:
            print(f"[SUPERVISOR] 🔍 Đã tìm thấy {len(initial_cams)} trạm camera. Đang khởi động...")
            for cam in initial_cams:
                self.start_worker(cam)

        if os.path.isfile(CONF_JSON):
            self.last_conf_mtime = os.path.getmtime(CONF_JSON)

        # 2. Vòng lặp giám sát liên tục (Watchdog & Hot-Reload)
        last_db_check = time.time()
        while self.running:
            try:
                time.sleep(2.0)
                now = time.time()

                # Kiểm tra định kỳ SQLite DB mỗi 5 giây để tự động đồng bộ ngay khi Admin bấm Lưu trên Web
                if now - last_db_check >= 5.0:
                    last_db_check = now
                    self.sync_from_database()

                # Kiểm tra file cấu hình cameras.json có thay đổi không (Hot-Reload)
                if os.path.isfile(CONF_JSON):
                    current_mtime = os.path.getmtime(CONF_JSON)
                    if current_mtime > self.last_conf_mtime:
                        self.last_conf_mtime = current_mtime
                        print("\n[SUPERVISOR] 🔄 Phát hiện cấu hình camera thay đổi từ Web Dashboard. Đang đồng bộ...")
                        new_cams = self.load_active_cameras()
                        new_cam_map = {c["id"]: c for c in new_cams}

                        with self.lock:
                            current_ids = set(self.workers.keys())
                        target_ids = set(new_cam_map.keys())

                        # Dừng các camera đã bị xóa/tắt
                        for removed_id in (current_ids - target_ids):
                            self.stop_worker(removed_id)

                        # Khởi chạy các camera mới được thêm
                        for added_id in (target_ids - current_ids):
                            self.start_worker(new_cam_map[added_id])

                        # Khởi động lại các camera bị thay đổi cấu hình luồng (stream_url, secret, v.v.)
                        for common_id in (current_ids & target_ids):
                            old_cfg = self.workers[common_id]["config"]
                            new_cfg = new_cam_map[common_id]
                            if (str(old_cfg.get("stream_url")) != str(new_cfg.get("stream_url")) or
                                str(old_cfg.get("secret_key")) != str(new_cfg.get("secret_key")) or
                                bool(old_cfg.get("uniform_check")) != bool(new_cfg.get("uniform_check"))):
                                print(f"[SUPERVISOR] 🔄 Cấu hình Trạm #{common_id} thay đổi. Đang áp dụng luồng mới...")
                                self.restart_worker(new_cfg)

                # Kiểm tra trạng thái sống của các Worker (Watchdog)
                with self.lock:
                    active_items = list(self.workers.items())

                for cam_id, w_info in active_items:
                    proc = w_info["process"]
                    poll_code = proc.poll()
                    if poll_code is not None:
                        # Tiến trình đã dừng (do lỗi camera, rớt mạng hoặc lỗi OpenCV)
                        cam_name = w_info["config"].get("name", f"Camera #{cam_id}")
                        time_since_restart = now - w_info["last_restart"]

                        # Tránh restart dồn dập (Cool down tối thiểu 5s)
                        if time_since_restart >= 5.0:
                            print(f"{w_info['color']}[SUPERVISOR] ⚠️ Trạm #{cam_id} ({cam_name}) đã dừng (Exit code: {poll_code}). Đang tự động hồi phục sau 3s...{RESET_COLOR}")
                            time.sleep(3.0)
                            self.restart_worker(w_info["config"])

            except KeyboardInterrupt:
                break
            except Exception as loop_err:
                print(f"[SUPERVISOR] ⚠️ Ngoại lệ trong vòng lặp giám sát: {loop_err}")
                time.sleep(2.0)

        self.stop_all()


def main():
    parser = argparse.ArgumentParser(description="Multi-Camera AI Supervisor Engine for STEM Attendance")
    parser.add_argument("--school", "-s", type=int, default=None, help="School ID")
    parser.add_argument("--server", type=str, default="http://localhost:8000", help="Backend Server URL")
    parser.add_argument("--gui", action="store_true", help="Hiển thị cửa sổ OpenCV cho từng camera (mặc định headless)")
    args = parser.parse_args()

    supervisor = MultiCameraSupervisor(
        school_id=args.school,
        server_url=args.server,
        gui_mode=args.gui
    )
    supervisor.run()


if __name__ == "__main__":
    main()
