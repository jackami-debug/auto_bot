import threading
import time
import tkinter as tk
from datetime import datetime
from queue import Empty, Queue
from tkinter import ttk

from tools import (
    find_and_click,
    find_only,
    handle_dialog_windows,
    keyboard,
    pyautogui,
    save_debug_screenshot,
    set_logger,
    wake_up_gpu,
)


class UILogger:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.queue = Queue()
        self._is_running = True

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.queue.put(f"[{timestamp}] {message}")

    def process_queue(self):
        try:
            while True:
                message = self.queue.get_nowait()
                self.text_widget.config(state=tk.NORMAL)
                self.text_widget.insert(tk.END, message + "\n")
                self.text_widget.see(tk.END)
                self.text_widget.config(state=tk.DISABLED)
        except Empty:
            pass

        if self._is_running:
            self.text_widget.after(100, self.process_queue)


class AutoNextLoop:
    def __init__(self, logger):
        self.logger = logger
        self._stop_event = threading.Event()
        self.thread = None

    def _log(self, message):
        print(message)
        self.logger.log(message)

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
        self._log("開始自動下一關監控，按 q 可停止。")

        while not self._stop_event.is_set():
            if keyboard.is_pressed("q"):
                self._log("使用者中止自動下一關。")
                break

            time.sleep(0.3)
            action_taken = False

            if handle_dialog_windows():
                action_taken = True
            elif find_and_click("next_level_02.png", custom_confidence=0.8):
                self._log("🚀 點擊下一關")
                time.sleep(4)
                action_taken = True
            elif find_only("fight_again.png", custom_confidence=0.75):
                if find_and_click("next_level_02.png", custom_confidence=0.6):
                    self._log("🚀 再次挑戰後點擊下一關")
                    time.sleep(4)
                    action_taken = True
            elif find_only("victory_02.png", custom_confidence=0.7):
                if not find_only("next_level_02.png", 0.6) and not find_only("fight_again.png", 0.6):
                    self._log("🏆 Victory 動畫中，點中央加速")
                    screen_width, screen_height = pyautogui.size()
                    pyautogui.click(screen_width // 2, screen_height // 2)
                    time.sleep(0.5)
                    action_taken = True
            elif find_and_click("start.png"):
                self._log("⚔️ 開始戰鬥")
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

            not_found_streak += 1
            if not_found_streak % 15 == 0:
                self._log(f"👀 監控中... (Streak: {not_found_streak})")
                wake_up_gpu()
            if not_found_streak >= 100:
                self._log("⚠️ 連續 100 次無動作，保存除錯截圖後繼續。")
                save_debug_screenshot("lost_track_long")
                not_found_streak = 0


def build_ui():
    root = tk.Tk()
    root.title("Auto Next Level")
    root.geometry("600x500")

    var = tk.BooleanVar(value=False)

    control_frame = ttk.Frame(root)
    control_frame.pack(fill=tk.X, padx=10, pady=10)

    log_frame = ttk.LabelFrame(root, text="Log", padding=5)
    log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    scrollbar = ttk.Scrollbar(log_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    log_text = tk.Text(
        log_frame,
        height=20,
        width=80,
        bg="#1e1e1e",
        fg="#00ff88",
        font=("Courier New", 9),
        yscrollcommand=scrollbar.set,
        state=tk.DISABLED,
    )
    log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=log_text.yview)

    logger = UILogger(log_text)
    set_logger(logger.log)
    loop = AutoNextLoop(logger)

    chk = ttk.Checkbutton(
        control_frame,
        text="Enable Auto Next Level",
        variable=var,
        command=lambda: loop.start() if var.get() else loop.stop(),
    )
    chk.pack(side=tk.LEFT)

    info = ttk.Label(control_frame, text="Use q to stop the running loop.", font=("Arial", 9))
    info.pack(side=tk.LEFT, padx=10)

    logger.log("Auto Next Level UI 已啟動")
    logger.process_queue()

    def on_close():
        var.set(False)
        loop.stop()
        logger._is_running = False
        set_logger(None)
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    return root


def main():
    root = build_ui()
    root.mainloop()


if __name__ == "__main__":
    main()
