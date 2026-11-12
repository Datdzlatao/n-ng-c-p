# -*- coding: utf-8 -*-
"""
HOG PERSON DETECTOR — PHÁT HIỆN NGƯỜI & PHÂN VÙNG THÂN
person_detector.py
"""
import cv2
import numpy as np
from typing import Optional, List, Dict, Tuple

HOG_WIN_STRIDE   = (8, 8)
HOG_PADDING      = (4, 4)
HOG_SCALE        = 1.06
HOG_FINAL_THRESH = 0.1
DETECT_SCALE     = 0.65
NMS_OVERLAP_THRESH = 0.60

SHIRT_ZONE_TOP    = 0.12
SHIRT_ZONE_BOTTOM = 0.52
PANTS_ZONE_TOP    = 0.52
PANTS_ZONE_BOTTOM = 0.90


def non_max_suppression_fast(boxes: np.ndarray, overlap_thresh: float) -> list:
    if len(boxes) == 0:
        return []
    if boxes.dtype.kind == "i":
        boxes = boxes.astype("float")

    pick = []
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 0] + boxes[:, 2]
    y2 = boxes[:, 1] + boxes[:, 3]
    area = (x2 - x1) * (y2 - y1)
    idxs = np.argsort(y2)

    while len(idxs) > 0:
        last = len(idxs) - 1
        i = idxs[last]
        pick.append(i)

        xx1 = np.maximum(x1[i], x1[idxs[:last]])
        yy1 = np.maximum(y1[i], y1[idxs[:last]])
        xx2 = np.minimum(x2[i], x2[idxs[:last]])
        yy2 = np.minimum(y2[i], y2[idxs[:last]])

        w = np.maximum(0, xx2 - xx1)
        h = np.maximum(0, yy2 - yy1)
        overlap = (w * h) / area[idxs[:last]]

        idxs = np.delete(idxs, np.concatenate(([last], np.where(overlap > overlap_thresh)[0])))
    return boxes[pick].astype("int").tolist()


class PersonDetector:
    def __init__(self, use_face_fallback: bool = True):
        self.use_face_fallback = use_face_fallback
        if hasattr(cv2, "HOGDescriptor") and hasattr(cv2, "HOGDescriptor_getDefaultPeopleDetector"):
            self.hog = cv2.HOGDescriptor()
            self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        else:
            self.hog = None

    def detect(self, frame: np.ndarray, face_locations: Optional[List[Tuple[int, int, int, int]]] = None) -> List[Dict]:
        h, w = frame.shape[:2]
        boxes_raw = []

        if self.hog is not None:
            small = cv2.resize(frame, (0, 0), fx=DETECT_SCALE, fy=DETECT_SCALE)
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            boxes_raw, weights = self.hog.detectMultiScale(
                gray,
                winStride=HOG_WIN_STRIDE,
                padding=HOG_PADDING,
                scale=HOG_SCALE,
                finalThreshold=HOG_FINAL_THRESH,
                useMeanshiftGrouping=False
            )

        detections = []
        if len(boxes_raw) > 0:
            scale_inv = 1.0 / DETECT_SCALE
            boxes_scaled = []
            for b in boxes_raw:
                bx, by, bw, bh = b
                boxes_scaled.append([
                    int(bx * scale_inv),
                    int(by * scale_inv),
                    int(bw * scale_inv),
                    int(bh * scale_inv)
                ])

            boxes_filtered = non_max_suppression_fast(np.array(boxes_scaled), NMS_OVERLAP_THRESH)
            for box in boxes_filtered:
                bx, by, bw, bh = box
                # Clamp boundaries
                bx = max(0, min(bx, w - 1))
                by = max(0, min(by, h - 1))
                bw = max(1, min(bw, w - bx))
                bh = max(1, min(bh, h - by))

                # Aspect ratio filter for humans: height typically > 1.4x width
                if bh < bw * 1.1 or bh < 60:
                    continue

                detections.append({
                    "body_box": (bx, by, bw, bh),
                    "shirt_box": (bx, by + int(bh * SHIRT_ZONE_TOP), bw, int(bh * (SHIRT_ZONE_BOTTOM - SHIRT_ZONE_TOP))),
                    "pants_box": (bx, by + int(bh * PANTS_ZONE_TOP), bw, int(bh * (PANTS_ZONE_BOTTOM - PANTS_ZONE_TOP))),
                    "source": "hog"
                })

        # Fallback from face locations if HOG missed
        if not detections and self.use_face_fallback and face_locations:
            for loc in face_locations:
                top, right, bottom, left = loc
                fw = right - left
                fh = bottom - top

                # Estimate body from face
                bw = int(fw * 2.8)
                bh = int(fh * 6.5)
                bx = max(0, int(left - (bw - fw) / 2))
                by = max(0, top)
                bw = min(bw, w - bx)
                bh = min(bh, h - by)

                if bw > 20 and bh > 40:
                    detections.append({
                        "body_box": (bx, by, bw, bh),
                        "shirt_box": (bx, by + int(bh * SHIRT_ZONE_TOP), bw, int(bh * (SHIRT_ZONE_BOTTOM - SHIRT_ZONE_TOP))),
                        "pants_box": (bx, by + int(bh * PANTS_ZONE_TOP), bw, int(bh * (PANTS_ZONE_BOTTOM - PANTS_ZONE_TOP))),
                        "source": "face"
                    })

        # Fallback 3: Center-frame person estimation (when HOG is unavailable in OpenCV 5.x and face is masked/occluded)
        if not detections and (self.hog is None or len(boxes_raw) == 0):
            bx = int(w * 0.15)
            by = int(h * 0.05)
            bw = int(w * 0.70)
            bh = int(h * 0.90)
            detections.append({
                "body_box": (bx, by, bw, bh),
                "shirt_box": (bx, by + int(bh * SHIRT_ZONE_TOP), bw, int(bh * (SHIRT_ZONE_BOTTOM - SHIRT_ZONE_TOP))),
                "pants_box": (bx, by + int(bh * PANTS_ZONE_TOP), bw, int(bh * (PANTS_ZONE_BOTTOM - PANTS_ZONE_TOP))),
                "source": "frame_center"
            })

        return detections
