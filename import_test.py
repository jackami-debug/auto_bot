import sys
print(f"Python Executable: {sys.executable}")
try:
    import pyautogui
    print("pyautogui: SUCCESS")
except ImportError as e:
    print(f"pyautogui: FAILED ({e})")

try:
    import cv2
    print("cv2: SUCCESS")
except ImportError as e:
    print(f"cv2: FAILED ({e})")

try:
    import keyboard
    print("keyboard: SUCCESS")
except ImportError as e:
    print(f"keyboard: FAILED ({e})")

try:
    import PIL
    print("PIL: SUCCESS")
except ImportError as e:
    print(f"PIL: FAILED ({e})")
