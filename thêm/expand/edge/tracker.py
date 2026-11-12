# -*- coding: utf-8 -*-
"""
=============================================================
  BUOC 2: MULTI-OBJECT TRACKING (MOT) & SPATIAL FUSION
  tracker.py

  Muc tieu: Cho phep he thong nhan dien CUNG LUC nhieu nguoi
  (3-8 nguoi) trong khung hinh ma khong bi nham lan du lieu
  giua QR / khuon mat / trang phuc cua tung nguoi.

  Thanh phan chinh:
    1. MultiObjectTracker — thuat toan theo doi nhe, ket hop:
         - IoU Tracker (uu tien, chinh xac khi cac box gan nhau)
         - Centroid Tracker (fallback khi IoU=0, di chuyen nhanh)
       Moi nguoi xuat hien duoc cap 1 `track_id` duy nhat, duy
       tri xuyen suot cac frame ke ca khi tam thoi bi che khuat.

    2. TrackState — trang thai DOC LAP cho moi track_id:
         {id, student_id, name, qr_scanned, face_matched,
          uniform_status, is_stranger, is_spoof, spoof_status,
          status_time}

    3. Spatial Fusion helpers — gan QR / khuon mat / ket qua
       trang phuc vao dung track_id dua theo toa do bounding box
       (khong dua vao "nguoi nhan dien gan nhat" nhu truoc day,
       von de bi nham khi nhieu hoc sinh dung gan nhau).

  Dung:
    from tracker import MultiObjectTracker

    mot = MultiObjectTracker()
    mot.update(list_of_body_boxes)                  # (x, y, w, h)
    trk = mot.find_track_for_face(face_location)     # (top,right,bottom,left)
    trk = mot.find_track_for_qr(qr_rect)             # pyzbar Rect hoac (x,y,w,h)
    mot.link_face(trk, student_id, name, location)
    mot.link_qr(trk, student_id, name)
    mot.link_uniform(trk, status)
    if mot.ready_for_attendance(trk): ...
=============================================================
"""

import time
from typing import Dict, List, Optional, Tuple

BoxType = Tuple[int, int, int, int]   # (x, y, w, h)


# =============================================================================
# HAM HINH HOC DUNG CHUNG
# =============================================================================
def _iou(box_a: BoxType, box_b: BoxType) -> float:
    """Intersection-over-Union giua 2 box dang (x, y, w, h)."""
    ax1, ay1, aw, ah = box_a
    ax2, ay2 = ax1 + aw, ay1 + ah
    bx1, by1, bw, bh = box_b
    bx2, by2 = bx1 + bw, by1 + bh

    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0

    area_a = max(0, aw) * max(0, ah)
    area_b = max(0, bw) * max(0, bh)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _centroid(box: BoxType) -> Tuple[float, float]:
    x, y, w, h = box
    return (x + w / 2.0, y + h / 2.0)


def _dist(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5


def _point_in_box(point: Tuple[float, float], box: Optional[BoxType],
                   margin_ratio: float = 0.35) -> bool:
    """Kiem tra 1 diem co nam trong box hay khong (co bien do de bu
    sai so uoc luong cua HOG / fallback face->body)."""
    if box is None:
        return False
    px, py = point
    x, y, w, h = box
    mx, my = w * margin_ratio, h * margin_ratio
    return (x - mx) <= px <= (x + w + mx) and (y - my) <= py <= (y + h + my)


# =============================================================================
# TRANG THAI DOC LAP CHO MOI TRACK_ID
# =============================================================================
class TrackState:
    """
    Trang thai theo doi doc lap cho 1 nguoi (1 track_id) dang xuat hien
    trong camera. Duoc cap nhat lien tuc qua Spatial Fusion khi he thong
    phat hien QR / khuon mat / trang phuc trung voi vi tri cua track nay.
    """

    __slots__ = (
        "id", "body_box", "centroid",
        "student_id", "name",
        "qr_scanned", "face_matched",
        "uniform_status", "uniform_message", "uniform_label", "uniform_conf",
        "uniform_history",
        "is_stranger",
        "is_spoof", "spoof_status", "last_uniform_check_frame",
        "captured_violations",
        "status_time", "last_seen", "hits",
        "face_location", "attendance_done",
        "_last_uniform_body_area",
    )

    def __init__(self, track_id: int, body_box: BoxType):
        self.id = track_id
        self.body_box = body_box
        self.centroid = _centroid(body_box)

        # ── Danh tinh & trang thai diem danh (Spatial Fusion) ──
        self.student_id: Optional[str] = None
        self.name: Optional[str] = None
        self.qr_scanned: bool = False
        self.face_matched: bool = False
        self.uniform_status: Optional[str] = None   # OK/FAIL/UNCLEAR/SKIP
        self.uniform_message: str = ""
        self.uniform_label: str = ""
        self.uniform_conf: float = 0.0
        self.uniform_history: list = []
        self.is_stranger: bool = False
        self.is_spoof: bool = False
        self.spoof_status: Optional[str] = None
        self.last_uniform_check_frame: int = 0
        self.captured_violations: set = set()
        self.status_time: float = time.time()
        self._last_uniform_body_area: int = 0

        # ── Trang thai noi bo cua tracker ──
        self.last_seen: float = time.time()
        self.hits: int = 1
        self.face_location = None   # (top, right, bottom, left)
        self.attendance_done: bool = False  # da diem danh (tranh commit lap)

    # -------------------------------------------------------------------
    def to_dict(self) -> dict:
        """Xuat trang thai theo dung cau truc yeu cau:
        {id, student_id, name, qr_scanned, face_matched,
         uniform_status, is_stranger, is_spoof, spoof_status, status_time}"""
        return {
            "id":              self.id,
            "student_id":      self.student_id,
            "name":            self.name,
            "qr_scanned":      self.qr_scanned,
            "face_matched":    self.face_matched,
            "uniform_status":  self.uniform_status,
            "is_stranger":     self.is_stranger,
            "is_spoof":        self.is_spoof,
            "spoof_status":    self.spoof_status,
            "status_time":     self.status_time,
        }

    def reset_identity(self):
        """Goi sau khi da diem danh xong hoac track qua cu -> lam sach
        de tranh mang trang thai cua nguoi cu sang nguoi dung vao vi tri do."""
        self.student_id = None
        self.name = None
        self.qr_scanned = False
        self.face_matched = False
        self.uniform_status = None
        self.uniform_message = ""
        self.uniform_label = ""
        self.uniform_conf = 0.0
        self.is_stranger = False
        self.is_spoof = False
        self.spoof_status = None
        self.last_uniform_check_frame = 0
        self.captured_violations.clear()
        self.status_time = time.time()
        self.attendance_done = False


# =============================================================================
# MULTI-OBJECT TRACKER (IoU + Centroid, nhe, khong can GPU)
# =============================================================================
class MultiObjectTracker:
    """
    Bo theo doi da doi tuong nhe cho 3-8 nguoi dung truoc camera cung luc.

    Thuat toan (moi frame):
      1. Khop moi body_box moi phat hien voi cac track dang co bang IoU
         (uu tien - chinh xac khi nguoi dung gan/giao nhau).
      2. Voi cac track/box CHUA khop, thu khop tiep bang khoang cach
         centroid (fallback - xu ly truong hop di chuyen nhanh khien
         IoU = 0 giua 2 frame lien tiep).
      3. Track khop -> cap nhat vi tri, giu nguyen track_id (va toan bo
         trang thai QR/mat/trang phuc da gan truoc do).
      4. Track khong khop qua `max_disappeared` frame lien tiep -> xoa.
      5. Box moi khong khop track nao -> dang ky track_id moi.
    """

    def __init__(self,
                 max_disappeared: int = 15,
                 iou_threshold: float = 0.25,
                 max_centroid_dist: float = 140.0,
                 max_tracks: int = 8):
        self.next_id: int = 1
        self.tracks: Dict[int, TrackState] = {}
        self.disappeared: Dict[int, int] = {}

        self.max_disappeared = max_disappeared
        self.iou_threshold = iou_threshold
        self.max_centroid_dist = max_centroid_dist
        self.max_tracks = max_tracks   # gioi han 3-8 nguoi theo yeu cau

    # -------------------------------------------------------------------
    # CAP NHAT TRACKER VOI DETECTION MOI CUA FRAME HIEN TAI
    # -------------------------------------------------------------------
    def update(self, body_boxes: List[BoxType]) -> Dict[int, TrackState]:
        """
        Args:
            body_boxes: Danh sach (x, y, w, h) tu PersonDetector.detect()
                        cua frame hien tai.
        Returns:
            Dict {track_id: TrackState} cho cac track dang active.
        """
        body_boxes = list(body_boxes)[: self.max_tracks] if body_boxes else []
        now = time.time()

        # --- Khong phat hien ai trong frame nay ---
        if not body_boxes:
            for tid in list(self.disappeared.keys()):
                self.disappeared[tid] += 1
                if self.disappeared[tid] > self.max_disappeared:
                    self.tracks.pop(tid, None)
                    self.disappeared.pop(tid, None)
            return self.tracks

        # --- Chua co track nao -> dang ky tat ca ---
        if not self.tracks:
            for box in body_boxes:
                self._register(box)
            return self.tracks

        track_ids = list(self.tracks.keys())
        unmatched_tracks = set(track_ids)
        unmatched_boxes = set(range(len(body_boxes)))
        matches: List[Tuple[int, int]] = []

        # ── Buoc 1: Khop theo IoU (uu tien, chinh xac) ──
        iou_candidates = []
        for tid in track_ids:
            for bi, box in enumerate(body_boxes):
                score = _iou(self.tracks[tid].body_box, box)
                if score >= self.iou_threshold:
                    iou_candidates.append((score, tid, bi))
        iou_candidates.sort(key=lambda t: t[0], reverse=True)

        for score, tid, bi in iou_candidates:
            if tid in unmatched_tracks and bi in unmatched_boxes:
                matches.append((tid, bi))
                unmatched_tracks.discard(tid)
                unmatched_boxes.discard(bi)

        # ── Buoc 2: Fallback khop theo khoang cach centroid ──
        if unmatched_tracks and unmatched_boxes:
            dist_candidates = []
            for tid in unmatched_tracks:
                c1 = self.tracks[tid].centroid
                for bi in unmatched_boxes:
                    d = _dist(c1, _centroid(body_boxes[bi]))
                    if d <= self.max_centroid_dist:
                        dist_candidates.append((d, tid, bi))
            dist_candidates.sort(key=lambda t: t[0])

            for d, tid, bi in dist_candidates:
                if tid in unmatched_tracks and bi in unmatched_boxes:
                    matches.append((tid, bi))
                    unmatched_tracks.discard(tid)
                    unmatched_boxes.discard(bi)

        # ── Cap nhat cac track da khop (giu nguyen track_id + state) ──
        for tid, bi in matches:
            trk = self.tracks[tid]
            trk.body_box = body_boxes[bi]
            trk.centroid = _centroid(body_boxes[bi])
            trk.last_seen = now
            trk.hits += 1
            self.disappeared[tid] = 0

        # ── Track khong xuat hien frame nay -> tang bo dem mat dau ──
        for tid in unmatched_tracks:
            trk = self.tracks.get(tid)
            if trk is not None:
                # [FIX BOUNDER BOX] Khong con thay trong frame -> xoa ngay face_location cu
                trk.face_location = None
            self.disappeared[tid] = self.disappeared.get(tid, 0) + 1
            limit = 6 if (trk and trk.attendance_done) else self.max_disappeared
            if self.disappeared[tid] > limit:
                self.tracks.pop(tid, None)
                self.disappeared.pop(tid, None)

        # ── Box moi (nguoi moi buoc vao khung hinh) -> track_id moi ──
        if len(self.tracks) < self.max_tracks:
            for bi in unmatched_boxes:
                if len(self.tracks) >= self.max_tracks:
                    break
                self._register(body_boxes[bi])

        return self.tracks

    def _register(self, box: BoxType) -> int:
        tid = self.next_id
        self.next_id += 1
        self.tracks[tid] = TrackState(tid, box)
        self.disappeared[tid] = 0
        return tid

    # -------------------------------------------------------------------
    # SPATIAL FUSION — GAN QR / KHUON MAT / TRANG PHUC VAO DUNG TRACK_ID
    # -------------------------------------------------------------------
    def find_track_for_point(self, point: Tuple[float, float]) -> Optional[TrackState]:
        """Tra ve track co body_box chua diem cho truoc va co centroid
        gan diem do nhat (xu ly truong hop nhieu box giao nhau)."""
        best, best_d = None, float("inf")
        for trk in self.tracks.values():
            if _point_in_box(point, trk.body_box):
                d = _dist(point, trk.centroid)
                if d < best_d:
                    best, best_d = trk, d
        return best

    def update_from_faces(self, face_locations: List[Tuple[int, int, int, int]],
                          frame_w: int, frame_h: int) -> Dict[int, TrackState]:
        """
        [NANG CAP DUAL-SCAN] Dong bo tracker tuc thi tu danh sach khuon mat.
        Moi khuon mat phat hien lap tuc tao hoac cap nhat Body Box (than nguoi / vung ao)
        giup kiem tra trang phuc va nhan dien mat chay dong thoi 100% tu frame dau tien.
        """
        if not face_locations:
            return self.tracks

        now = time.time()
        for loc in face_locations:
            top, right, bottom, left = loc
            fw = max(1, right - left)
            fh = max(1, bottom - top)

            # Uoc tinh than nguoi dua tren nhan trac hoc (vai rong ~2.6 mat, than cao ~6.0 mat)
            body_w = int(fw * 2.6)
            body_h = int(fh * 6.0)
            body_x = max(0, left + fw // 2 - body_w // 2)
            body_y = max(0, top - int(fh * 0.2))
            body_w = min(body_w, frame_w - body_x)
            body_h = min(body_h, frame_h - body_y)
            body_box = (body_x, body_y, body_w, body_h)

            trk = self.find_track_for_face(loc)
            if trk is not None:
                trk.face_location = loc
                trk.body_box = body_box
                trk.centroid = _centroid(body_box)
                trk.last_seen = now
                trk.hits += 1
                self.disappeared[trk.id] = 0
            else:
                if len(self.tracks) < self.max_tracks:
                    tid = self._register(body_box)
                    t = self.tracks[tid]
                    t.face_location = loc

        return self.tracks

    def find_track_for_face(self, face_location) -> Optional[TrackState]:
        """
        face_location: (top, right, bottom, left) — dung dinh dang tra ve
        boi face_engine.FaceEngine.detect_locations()/recognize().

        Gan khuon mat vao dung track_id dua theo toa do tam khuon mat co
        nam trong body_box cua track hay khong (thay vi 'nguoi nhan dien
        gan nhat' — cach cu de gan nham khi 2 hoc sinh dung sat nhau).
        """
        top, right, bottom, left = face_location
        cx, cy = (left + right) / 2.0, (top + bottom) / 2.0

        # 1. Kiem tra theo diem tam nam trong body_box
        trk = self.find_track_for_point((cx, cy))
        if trk is not None:
            return trk

        # 2. Fallback: Kiem tra khoang cach toi face_location truoc do cua track
        best, best_d = None, 120.0
        for t in self.tracks.values():
            if t.face_location is not None:
                ft, fr, fb, fl = t.face_location
                fcx, fcy = (fl + fr) / 2.0, (ft + fb) / 2.0
                d = _dist((cx, cy), (fcx, fcy))
                if d < best_d:
                    best, best_d = t, d
        return best

    def find_track_for_qr(self, qr_rect) -> Optional[TrackState]:
        """
        qr_rect: pyzbar `Rect(left, top, width, height)` hoac tuple
        (x, y, w, h).

        Gan ma QR vua quet duoc vao track_id GAN NHAT theo khong gian:
        uu tien track co body_box chua tam ma QR; neu khong co track nao
        chua tam QR (VD hoc sinh gio the ra xa than nguoi / goc camera
        lech), fallback sang track co centroid gan tam QR nhat.
        """
        try:
            x, y, w, h = qr_rect.left, qr_rect.top, qr_rect.width, qr_rect.height
        except AttributeError:
            x, y, w, h = qr_rect
        cx, cy = x + w / 2.0, y + h / 2.0

        trk = self.find_track_for_point((cx, cy))
        if trk is not None:
            return trk

        best, best_d = None, float("inf")
        for t in self.tracks.values():
            d = _dist((cx, cy), t.centroid)
            if d < best_d:
                best, best_d = t, d
        return best

    # -------------------------------------------------------------------
    # CAP NHAT TRANG THAI DOC LAP CUA 1 TRACK
    # -------------------------------------------------------------------
    @staticmethod
    def link_face(track: TrackState, student_id: Optional[str],
                  name: Optional[str], location) -> None:
        """Gan ket qua nhan dien khuon mat vao track (theo toa do bbox)."""
        track.face_location = location
        if student_id:
            track.student_id = student_id
            track.name = name
            track.face_matched = True
            track.is_stranger = False
        else:
            # Khong khop ai trong danh sach -> nguoi la, van cap nhat vi tri
            track.face_matched = False
            track.is_stranger = True
        track.status_time = time.time()

    @staticmethod
    def link_qr(track: TrackState, student_id: str, name: str) -> None:
        """Gan ma QR vua quet duoc vao track (theo toa do gan nhat)."""
        track.qr_scanned = True
        # Chi ghi de danh tinh neu track chua co danh tinh tu khuon mat,
        # tranh QR cua nguoi dung canh ben ghi de len danh tinh da xac
        # thuc bang khuon mat cua track nay.
        if not track.face_matched:
            track.student_id = student_id
            track.name = name
        track.status_time = time.time()

    @staticmethod
    def link_uniform(track: TrackState, status: str, message: str = "", label: str = "", conf: float = 0.0) -> None:
        """Gan ket qua kiem tra trang phuc voi co che Temporal Voting 3-frame."""
        if not hasattr(track, "uniform_history") or track.uniform_history is None:
            track.uniform_history = []
        track.uniform_history.append((status, message, label, conf))
        if len(track.uniform_history) > 5:
            track.uniform_history.pop(0)

        # Bầu chọn đa số qua các lần đánh giá gần nhất (Temporal Voting)
        statuses = [item[0] for item in track.uniform_history]
        fail_votes = statuses.count("FAIL")
        ok_votes = statuses.count("OK")
        unclear_votes = statuses.count("UNCLEAR")

        if fail_votes >= 2:
            final_status = "FAIL"
            final_msg = next((item[1] for item in reversed(track.uniform_history) if item[0] == "FAIL"), message)
        elif ok_votes >= 2:
            final_status = "OK"
            final_msg = next((item[1] for item in reversed(track.uniform_history) if item[0] == "OK"), message)
        elif len(statuses) >= 2 and unclear_votes >= 1:
            final_status = "UNCLEAR"
            final_msg = message or "Chua ro trang phuc"
        else:
            final_status = status
            final_msg = message

        track.uniform_status = final_status
        track.uniform_message = final_msg
        track.uniform_label = label
        track.uniform_conf = conf
        track.status_time = time.time()

    @staticmethod
    def link_spoof(track: TrackState, is_spoof: bool, spoof_status: str) -> None:
        """Gan ket qua kiem tra gia mao (Anti-Spoofing) vao track."""
        track.is_spoof = is_spoof
        track.spoof_status = spoof_status
        track.status_time = time.time()

    @staticmethod
    def ready_for_attendance(track: TrackState) -> bool:
        """
        Dieu kien diem danh DOC LAP cho 1 track:
          - Da khop the QR      (qr_scanned)
          - Da khop khuon mat   (face_matched)
          - Danh tinh QR va mat TRUNG NHAU (khong bi gan nham nguoi khac
            do dung gan nhau trong khung hinh)
          - Khong phai gia mao  (not is_spoof)
          - Chua diem danh cho lan nay (attendance_done == False)
          - Khong phat hien gia mao (not is_spoof)
        """
        return bool(
            track.qr_scanned and track.face_matched
            and track.student_id and not track.attendance_done
            and not track.is_spoof
        )

    # -------------------------------------------------------------------
    # TIEN ICH
    # -------------------------------------------------------------------
    def get_active_tracks(self) -> List[TrackState]:
        """Tra ve danh sach track dang hien dien THUC SU trong frame.
        Loai bo track da bien mat hoac da diem danh xong > 1.2s de tranh che man hinh."""
        now = time.time()
        active = []
        for tid, trk in self.tracks.items():
            if self.disappeared.get(tid, 0) > 0:
                continue
            if trk.attendance_done and (now - trk.status_time > 1.2):
                continue
            active.append(trk)
        return active

    def get_track(self, track_id: int) -> Optional[TrackState]:
        return self.tracks.get(track_id)

    def count(self) -> int:
        return len(self.tracks)

    def draw_tracks(self, frame, color: Tuple[int, int, int] = (255, 210, 0)):
        """Ve khung + track_id + danh tinh (neu co) len frame — dung debug/HUD."""
        import cv2
        for trk in self.tracks.values():
            x, y, w, h = trk.body_box
            box_color = color
            if trk.is_spoof:
                box_color = (0, 0, 255)
            elif trk.is_stranger:
                box_color = (30, 30, 220)
            elif trk.face_matched and trk.qr_scanned:
                box_color = (0, 220, 80)

            cv2.rectangle(frame, (x, y), (x + w, y + h), box_color, 1)
            label = f"ID{trk.id}"
            if trk.name:
                label += f" {trk.name}"
            flags = []
            if trk.qr_scanned:
                flags.append("QR")
            if trk.face_matched:
                flags.append("MAT")
            if trk.uniform_status:
                flags.append(trk.uniform_status)
            if trk.spoof_status and trk.is_spoof:
                flags.append(trk.spoof_status)
            if flags:
                label += " [" + "/".join(flags) + "]"
            cv2.putText(frame, label, (x, max(12, y - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, box_color, 1)
        return frame
