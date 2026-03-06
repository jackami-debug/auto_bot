import threading
import time
import random
import os
import sys
import tkinter as tk
from tkinter import ttk
from datetime import datetime
from queue import Queue

try:
    import pyautogui
    import keyboard
except Exception as e:
    print("Missing dependencies: please install pyautogui and keyboard")
    raise

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

IMAGE_FOLDER = os.path.dirname(os.path.abspath(__file__))


class UILogger:
    """Thread-safe logger that writes to Tkinter Text widget"""
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.queue = Queue()
        self._is_running = True
    
    def log(self, message):
        """Queue a message to be written to the text widget"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.queue.put(f"[{timestamp}] {message}")
    
    def process_queue(self):
        """Process queued messages and update the text widget (call from main thread)"""
        try:
            while True:
                message = self.queue.get_nowait()
                self.text_widget.config(state=tk.NORMAL)
                self.text_widget.insert(tk.END, message + "\n")
                self.text_widget.see(tk.END)
                self.text_widget.config(state=tk.DISABLED)
        except:
            pass
        if self._is_running:
            self.text_widget.after(100, self.process_queue)


# Global logger instance
_logger = None


def set_logger(logger):
    """Set the global logger instance"""
    global _logger
    _logger = logger


def get_image_path(image_name):
    if not image_name.lower().endswith((".png", ".jpg")):
        image_name = image_name + ".png"
    path = os.path.join(IMAGE_FOLDER, image_name)
    return path if os.path.exists(path) else None


def find_only(image_name, custom_confidence=0.85, region=None):
    path = get_image_path(image_name)
    if not path:
        return None
    confidences = [custom_confidence, max(0.6, custom_confidence - 0.1), 0.7, 0.6]
    tried = set()
    for c in confidences:
        if c in tried:
            continue
        tried.add(c)
        try:
            loc = pyautogui.locateCenterOnScreen(path, confidence=c, region=region)
            if loc:
                return loc
        except Exception:
            continue
    return None


def human_click(location, clicks=1):
    """Move the mouse and click at the given location.

    Returns True if the sequence was attempted, False otherwise.  The
    caller should not assume the click succeeded in the target application
    (that depends on window focus etc.), but this helper will always log
    what it tried and convert coordinates to plain ints so PyAutoGUI
    receives valid arguments.
    """
    if not location:
        return False

    # make sure we are working with plain Python ints; the Point returned by
    # `locateCenterOnScreen` may contain numpy.int64 values which sometimes
    # confuse downstream math or PyAutoGUI itself.
    try:
        x, y = int(location[0]), int(location[1])
    except Exception:
        # fallback in case the passed object is already a tuple-like
        x, y = location
        x, y = int(x), int(y)

    # log coordinates for debugging
    msg = f"🔍 human_click trying at {(x, y)}"
    print(msg)
    if _logger:
        _logger.log(msg)

    original = pyautogui.FAILSAFE
    try:
        pyautogui.FAILSAFE = False
        # small random offset can help avoid detection by some anti‑bot
        # systems, but during debugging it may move the cursor off the
        # target.  remove or reduce these values as needed.
        x += random.randint(-8, 8)
        y += random.randint(-5, 5)
        screen_w, screen_h = pyautogui.size()
        x = min(max(0, x), screen_w - 1)
        y = min(max(0, y), screen_h - 1)

        pyautogui.moveTo(x, y, duration=random.uniform(0.1, 0.25))
        for i in range(clicks):
            # specify coords explicitly so the click happens even if the
            # move takes a tick and the cursor drifts.
            # pyautogui.click(x, y)
            pyautogui.mouseDown(x, y)
            time.sleep(random.uniform(0.05, 0.15))
            pyautogui.mouseUp(x, y)
            if clicks > 1:
                time.sleep(random.uniform(0.05, 0.12))
        return True
    except Exception as e:
        err = f"❌ human_click failed: {e}"
        print(err)
        if _logger:
            _logger.log(err)
        return False
    finally:
        pyautogui.FAILSAFE = original


def find_and_click(image_name, custom_confidence=0.85, clicks=1, region=None):
    loc = find_only(image_name, custom_confidence=custom_confidence, region=region)
    if loc:
        msg = f"🎯 發現: {image_name} @ {loc}"
        print(msg)
        if _logger:
            _logger.log(msg)
        # propagate whether the clicking attempt succeeded so callers can
        # tell the difference between "button seen" and "button seen and
        # clicked".
        clicked = human_click((loc.x, loc.y), clicks=clicks)
        if clicked:
            return True
        else:
            # log that we failed to send a click
            err = f"⚠️ 找到 {image_name} 但點擊失敗"
            print(err)
            if _logger:
                _logger.log(err)
            return False
    return False


def wake_up_gpu():
    try:
        x, y = pyautogui.position()
        pyautogui.moveTo(x + 1, y + 1)
        pyautogui.moveTo(x, y)
        pyautogui.press('shift')
    except Exception:
        pass


def save_debug_screenshot(reason):
    debug_dir = os.path.join(IMAGE_FOLDER, "debug_screenshots")
    os.makedirs(debug_dir, exist_ok=True)
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    path = os.path.join(debug_dir, f"{reason}_{timestamp}.png")
    try:
        pyautogui.screenshot(path)
    except Exception:
        pass


def handle_dialog_windows():
    # Lightweight dialog handler: looks for common OK/close buttons
    buttons = ["ok.png", "OK.png", "confirm.png","yes_02.PNG",
                "close_02.png", "OK03.png", "fast_forward_02.png",
                ]
    center_region = (0, 0, 1920, 900)
    for b in buttons:
        if find_and_click(b, custom_confidence=0.86, clicks=1, region=center_region):
            time.sleep(0.3)
            return True
    return False


class AutoNextLoop:
    def __init__(self):
        self._stop_event = threading.Event()
        self.thread = None

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self._stop_event.set()
        if self.thread:
            self.thread.join(timeout=1)

    def _run_loop(self):
        not_found_streak = 0
        msg = "🟢 自動下一關已啟動。按 'q' 或取消勾選停止。"
        print(msg)
        if _logger:
            _logger.log(msg)
        while not self._stop_event.is_set():
            if keyboard.is_pressed('q'):
                msg = "🛑 程式停止 (鍵盤 q)。"
                print(msg)
                if _logger:
                    _logger.log(msg)
                break

            time.sleep(0.3)
            action_taken = False

            if handle_dialog_windows():
                action_taken = True
            elif find_and_click("next_level_02.png", custom_confidence=0.8):
                msg = "🚀 點擊：下一關"
                print(msg)
                if _logger:
                    _logger.log(msg)
                time.sleep(4)
                action_taken = True
            elif find_only("fight_again.png", custom_confidence=0.75):
                if find_and_click("next_level_02.png", custom_confidence=0.6):
                    msg = "🚀 (再次挑戰觸發) 下一關"
                    print(msg)
                    if _logger:
                        _logger.log(msg)
                    time.sleep(4)
                    action_taken = True
            elif find_only("victory_02.png", custom_confidence=0.7):
                if not find_only("next_level_02.png", 0.6) and not find_only("fight_again.png", 0.6):
                    msg = "🏆 Victory 動畫... 加速"
                    print(msg)
                    if _logger:
                        _logger.log(msg)
                    sw, sh = pyautogui.size()
                    pyautogui.click(sw // 2, sh // 2)
                    time.sleep(0.5)
                    action_taken = True
            elif find_and_click("start.png"):
                msg = "⚔️ 開始戰鬥"
                print(msg)
                if _logger:
                    _logger.log(msg)
                time.sleep(5)
                action_taken = True
            elif find_and_click("auto.png"):
                time.sleep(1)
                action_taken = True
            elif find_and_click("fast_forward_02.png"):
                action_taken = True

            if action_taken:
                not_found_streak = 0
                continue
            else:
                not_found_streak += 1
                if not_found_streak % 15 == 0:
                    msg = f"👀 監控中... (Streak: {not_found_streak})"
                    print(msg)
                    if _logger:
                        _logger.log(msg)
                    wake_up_gpu()
                if not_found_streak >= 100:
                    msg = "❓ 連續100次無動作，保存截圖後持續監控..."
                    print(msg)
                    if _logger:
                        _logger.log(msg)
                    save_debug_screenshot("lost_track_long")
                    not_found_streak = 0


def build_ui():
    root = tk.Tk()
    root.title("Auto Next Level")
    root.geometry("600x500")

    loop = AutoNextLoop()

    var = tk.BooleanVar(value=False)

    # Create frame for controls
    control_frame = ttk.Frame(root)
    control_frame.pack(fill=tk.X, padx=10, pady=10)

    chk = ttk.Checkbutton(control_frame, text="Enable Auto Next Level", variable=var, command=lambda: loop.start() if var.get() else loop.stop())
    chk.pack(side=tk.LEFT)

    info = ttk.Label(control_frame, text="勾選後程式會在背景偵測並自動點下一關", font=("Arial", 9))
    info.pack(side=tk.LEFT, padx=10)

    # Create log frame with title
    log_frame = ttk.LabelFrame(root, text="執行日誌 (Log)", padding=5)
    log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    # Create text widget with scrollbar
    scrollbar = ttk.Scrollbar(log_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    log_text = tk.Text(
        log_frame,
        height=20,
        width=80,
        bg="#1e1e1e",
        fg="#00ff00",
        font=("Courier New", 9),
        yscrollcommand=scrollbar.set,
        state=tk.DISABLED
    )
    log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=log_text.yview)

    # Initialize logger
    logger = UILogger(log_text)
    set_logger(logger)
    logger.log("🟡 Auto Next Level UI 已啟動")

    # Start the queue processing
    logger.process_queue()

    def on_close():
        var.set(False)
        loop.stop()
        logger._is_running = False
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    return root


def main():
    root = build_ui()
    root.mainloop()

if __name__ == "__main__":
    main()