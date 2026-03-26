import threading
import time
import tkinter as tk
from datetime import datetime
from queue import Empty, Queue
from tkinter import ttk

import cv2
import easyocr
import numpy as np

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


# ---------------------------------------------------------
# 原本的圖片辨識自動下一關迴圈
# ---------------------------------------------------------
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
        self._log("開始自動下一關監控 (圖片)，按 q 可停止。")

        while not self._stop_event.is_set():
            if keyboard.is_pressed("q"):
                self._log("使用者中止自動下一關。")
                break

            time.sleep(0.3)
            action_taken = False

            if handle_dialog_windows():
                action_taken = True
            if find_and_click("next_level_02.png", custom_confidence=0.8):
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
            elif find_and_click(["fast_forward_03.png", "fast_forward_01.png"]):
                action_taken = True
            if find_and_click(["arrow_01.png", "arrow_02.png", "arrow_03.png","arrow_04.png","arrow_05.png"], custom_confidence=0.7,region=(415,135,558,667)):
                action_taken = True

            if action_taken:
                not_found_streak = 0
                continue

            not_found_streak += 1
            if not_found_streak % 15 == 0:
                self._log(f"👀 圖片監控中... (Streak: {not_found_streak})")
                wake_up_gpu()
            if not_found_streak >= 100:
                self._log("⚠️ 連續 100 次無動作，保存除錯截圖後繼續。")
                save_debug_screenshot("lost_track_long")
                not_found_streak = 0


# ---------------------------------------------------------
# 新增的 OCR 文字辨識自動對話迴圈
# ---------------------------------------------------------
class AutoDialogLoop:
    def __init__(self, logger):
        self.logger = logger
        self._stop_event = threading.Event()
        self.thread = None
        self.reader = None
        self.region = (468, 155, 1012, 597) # 你指定的掃描區域

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
        if self.reader is None:
            self._log("初始化 EasyOCR 模型中... (首次啟動需等待幾秒)")
            try:
                self.reader = easyocr.Reader(['ch_tra'], gpu=False)
                self._log("EasyOCR 初始化完成！")
            except Exception as e:
                self._log(f"EasyOCR 初始化失敗: {e}")
                return

        self._log(f"開始自動對話偵測 (區域: {self.region})，按 q 可停止。")

        while not self._stop_event.is_set():
            if keyboard.is_pressed("q"):
                self._log("使用者中止 OCR 對話偵測。")
                break

            try:
                screenshot = pyautogui.screenshot(region=self.region)
                img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

                # 把 detail=0 拿掉，這樣 EasyOCR 就會回傳文字的座標！
                # 回傳格式會變成: [([[左上x, 左上y], [右上x, 右上y], [右下x, 右下y], [左下x, 左下y]], '文字內容', 信心度), ...]
                result_texts = self.reader.readtext(img)

                if result_texts:
                    # 我們抓取畫面上偵測到的「第一組」文字來當作點擊目標
                    first_result = result_texts[0]
                    bbox = first_result[0]      # 取得文字的四個角落座標
                    detected_text = first_result[1] # 取得文字內容
                    
                    if detected_text.strip(): 
                        # 1. 計算這段文字在「截圖小區域」裡面的中心點
                        # bbox[0] 是左上角 [x, y], bbox[2] 是右下角 [x, y]
                        center_x_rel = int((bbox[0][0] + bbox[2][0]) / 2)
                        center_y_rel = int((bbox[0][1] + bbox[2][1]) / 2)
                        
                        # 2. 轉換為「全螢幕」的絕對座標
                        # 必須加上原本 region 的左上角座標 self.region[0] 和 self.region[1]
                        click_x = self.region[0] + center_x_rel
                        click_y = self.region[1] + center_y_rel
                        
                        self._log(f"💬 發現文字: [{detected_text}] -> 點擊座標 ({click_x}, {click_y})")
                        
                        # 3. 執行精準點擊！
                        pyautogui.click(click_x, click_y)
                        
                        # 點擊後休息 1 秒，等待下一句對話的動畫跑完
                        time.sleep(0.1) 
            except Exception as e:
                self._log(f"OCR 執行過程中發生錯誤: {e}")

            time.sleep(0.3)


# ---------------------------------------------------------
# UI 介面建置
# ---------------------------------------------------------
def build_ui():
    root = tk.Tk()
    root.title("Auto Next Level & Dialog")
    root.geometry("650x500")

    next_level_var = tk.BooleanVar(value=False)
    dialog_var = tk.BooleanVar(value=False)

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
    
    next_level_loop = AutoNextLoop(logger)
    dialog_loop = AutoDialogLoop(logger)

    chk_next_level = ttk.Checkbutton(
        control_frame,
        text="Enable Auto Next Level (Image)",
        variable=next_level_var,
        command=lambda: next_level_loop.start() if next_level_var.get() else next_level_loop.stop(),
    )
    chk_next_level.pack(side=tk.LEFT, padx=(0, 10))

    chk_dialog = ttk.Checkbutton(
        control_frame,
        text="Enable Auto Dialog (OCR)",
        variable=dialog_var,
        command=lambda: dialog_loop.start() if dialog_var.get() else dialog_loop.stop(),
    )
    chk_dialog.pack(side=tk.LEFT)

    info = ttk.Label(control_frame, text="(Use 'q' to stop loops)", font=("Arial", 9))
    info.pack(side=tk.LEFT, padx=15)

    logger.log("Auto Next Level & Dialog UI 已啟動")
    logger.process_queue()

    def on_close():
        next_level_var.set(False)
        dialog_var.set(False)
        next_level_loop.stop()
        dialog_loop.stop()
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