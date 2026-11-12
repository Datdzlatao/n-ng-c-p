import cv2
import numpy as np
WINDOW_MAIN = "Test Window"
print("Creating namedWindow")
cv2.namedWindow(WINDOW_MAIN)
print("Setting mouse callback")
def _mouse_callback(event, x, y, flags, param): pass
try:
    cv2.setMouseCallback(WINDOW_MAIN, _mouse_callback)
    print("Success without imshow")
except Exception as e:
    print(f"Failed: {e}")

cv2.destroyAllWindows()
