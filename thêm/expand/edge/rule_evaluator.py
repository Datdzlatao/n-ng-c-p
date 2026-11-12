"""
edge/rule_evaluator.py — Raspberry Pi Dynamic Rule Evaluator
Downloads school-specific rules from Cloud Server and evaluates camera detections locally.
"""
import os, json, time, logging
from datetime import datetime
from typing import Dict, Any, List, Tuple
try:
    import requests
except ImportError:
    import urllib.request as urllib_req

log = logging.getLogger("edge.rule_evaluator")

CACHE_PATH = os.path.join(os.path.dirname(__file__), "data", "cached_school_rules.json")

class EdgeRuleEvaluator:
    def __init__(self, school_id: int, api_url: str = "http://localhost:8000"):
        self.school_id = school_id
        self.api_url   = api_url.rstrip("/")
        self.rules     = {}
        self.load_cached_rules()

    def load_cached_rules(self):
        """Load rules from local file cache if available."""
        if os.path.exists(CACHE_PATH):
            try:
                with open(CACHE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.rules = data.get("rules", {})
                    log.info(f"[Edge Rules] Loaded cached rules for School #{self.school_id}")
            except Exception as e:
                log.warning(f"[Edge Rules] Failed reading cached rules: {e}")

    def sync_rules_from_cloud(self) -> bool:
        """Fetch latest AI-generated rules from Cloud API."""
        url = f"{self.api_url}/api/v1/schools/{self.school_id}/ai-rules/profile"
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                self.rules = data.get("rules", {})
                os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
                with open(CACHE_PATH, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                log.info(f"[Edge Rules] Successfully synced rules from Cloud for School #{self.school_id}")
                return True
        except Exception as e:
            log.warning(f"[Edge Rules] Cloud rule sync failed ({e}), using offline cache.")
        return False

    def evaluate_attendance(self, timestamp: datetime, attributes: Dict[str, Any]) -> Tuple[str, str, int, List[str]]:
        """
        Evaluate student detection against school rules.
        attributes format example:
        {
          "shirt_type": "WHITE_SHIRT",
          "has_badge": true,
          "pants_color": "BLACK",
          "is_shorts": false,
          "footwear": "SHOES", # "SHOES" | "SLIPPERS" | "SANDALS"
          "has_cap": false,
          "has_dyed_hair": false
        }
        Returns: (status: str, uniform_status: str, deduct_points: int, violation_tags: List[str])
        """
        violations = []
        deduct_points = 0
        
        # 1. Time Check — Hỗ trợ đa ca (Sáng / Chiều / Tối) và tương thích ngược
        time_rules = self.rules.get("time_rules", {}) if isinstance(self.rules.get("time_rules"), dict) else {}
        
        m_on_time = self.rules.get("morning_on_time") or self.rules.get("checkin_on_time_until") or time_rules.get("on_time_deadline", "07:15")
        m_late_cut = self.rules.get("morning_late_until") or self.rules.get("checkin_late_until") or time_rules.get("late_cutoff", "07:30")

        a_from = self.rules.get("afternoon_from", "12:30")
        a_on_time = self.rules.get("afternoon_on_time", "13:15")
        a_late_cut = self.rules.get("afternoon_late_until", "13:30")

        e_from = self.rules.get("evening_from", "18:00")
        e_on_time = self.rules.get("evening_on_time", "18:45")
        e_late_cut = self.rules.get("evening_late_until", "19:15")

        late_pts = self.rules.get("late_deduct_points") or time_rules.get("late_deduct_points", 2)
        cur_time_str = timestamp.strftime("%H:%M")

        # Xác định ca học
        if cur_time_str < a_from:
            s_name = "buổi sáng"
            on_time_str = m_on_time
            late_cut_str = m_late_cut
            shift_uniform_check = self.rules["morning_uniform_check"] if "morning_uniform_check" in self.rules else self.rules.get("uniform_check", True)
            shift_late_pts = self.rules["morning_late_deduct"] if "morning_late_deduct" in self.rules else late_pts
        elif cur_time_str < e_from:
            s_name = "buổi chiều"
            on_time_str = a_on_time
            late_cut_str = a_late_cut
            shift_uniform_check = self.rules["afternoon_uniform_check"] if "afternoon_uniform_check" in self.rules else self.rules.get("uniform_check", True)
            shift_late_pts = self.rules["afternoon_late_deduct"] if "afternoon_late_deduct" in self.rules else late_pts
        else:
            s_name = "buổi tối"
            on_time_str = e_on_time
            late_cut_str = e_late_cut
            shift_uniform_check = self.rules["evening_uniform_check"] if "evening_uniform_check" in self.rules else self.rules.get("uniform_check", True)
            shift_late_pts = self.rules["evening_late_deduct"] if "evening_late_deduct" in self.rules else late_pts
        
        status = "ON_TIME"
        if cur_time_str > on_time_str:
            if cur_time_str <= late_cut_str:
                status = "LATE"
                pts = shift_late_pts
                deduct_points += pts
                violations.append(f"Đi trễ {s_name} ({cur_time_str} > {on_time_str}) -{pts}đ")
            else:
                status = "LATE"
                pts = shift_late_pts + 1
                deduct_points += pts
                violations.append(f"Đi trễ quá giờ {s_name} ({cur_time_str} > {late_cut_str}) -{pts}đ")

        # 2. Uniform Check (chỉ kiểm tra khi ca này có bật quét đồng phục)
        u_rules = self.rules.get("uniform_rules", {})
        uniform_status = "OK"
        if shift_uniform_check:
            # Shirt Check
            shirt_cfg = u_rules.get("shirt", {})
            req_types = shirt_cfg.get("required_types", ["WHITE_SHIRT"])
            detected_shirt = attributes.get("shirt_type", "WHITE_SHIRT")
            if req_types and detected_shirt not in req_types:
                uniform_status = "VIOLATION"
                pts = shirt_cfg.get("violation_deduct_points", 3)
                deduct_points += pts
                violations.append(f"Sai loại áo ({detected_shirt}) -{pts}đ")
                
            if shirt_cfg.get("require_school_badge") and not attributes.get("has_badge", True):
                uniform_status = "VIOLATION"
                violations.append("Thiếu phù hiệu trường")

            # Footwear Check
            foot_cfg = u_rules.get("footwear", {})
            if foot_cfg.get("prohibit_slippers") and attributes.get("footwear") == "SLIPPERS":
                uniform_status = "VIOLATION"
                pts = foot_cfg.get("violation_deduct_points", 2)
                deduct_points += pts
                violations.append(f"Đi dép lê không quai -{pts}đ")

            # Accessory Check (Caps / Hats / Headphones)
            acc_cfg = u_rules.get("accessories_and_appearance", {})
            if acc_cfg.get("prohibit_caps_in_yard") and attributes.get("has_cap", False):
                uniform_status = "VIOLATION"
                pts = acc_cfg.get("violation_deduct_points", 2)
                deduct_points += pts
                violations.append(f"Đội mũ trong sân trường -{pts}đ")
                
            if acc_cfg.get("prohibit_dyed_hair") and attributes.get("has_dyed_hair", False):
                uniform_status = "VIOLATION"
                violations.append("Nhuộm tóc sai quy định")

        return status, uniform_status, deduct_points, violations
