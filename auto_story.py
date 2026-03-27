import time
from datetime import datetime

import cv2
import easyocr
import numpy as np

from tools import (
    find_and_click,
    find_only,
    keyboard,
    pyautogui,
    save_debug_screenshot,
    wake_up_gpu,
)

def log(message):
    """簡單的終端機印出小工具，幫你加上時間戳記"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

def auto_story_mode():
    """全自動刷活動故事關卡與劇情"""
    
    # 1. 初始化設定
    dialog_region = (468, 155, 1012, 597)
    not_found_streak = 0
    
    log("初始化 EasyOCR 模型中... (請稍候)")
    try:
        reader = easyocr.Reader(['ch_tra'], gpu=False)
        log("EasyOCR 初始化完成！")
    except Exception as e:
        log(f"❌ EasyOCR 初始化失敗: {e}")
        return

    log("==================================================")
    log("🚀 開始全自動刷活動故事，按住 'q' 可隨時停止。")
    log("==================================================")

    # 2. 核心大迴圈 (直白寫法)
    while True:
        # 隨時偵測是否按下 q 鍵退出
        if keyboard.is_pressed("q"):
            log("🛑 使用者按下 q 鍵，中止自動腳本。")
            break

        action_taken = False

        try:
            # --------------------------------------------------
            # 階段一：快速圖片辨識 (UI 按鈕優先)
            # --------------------------------------------------
            if find_and_click("next_level_02.png", custom_confidence=0.8):
                log("🚀 點擊下一關")
                time.sleep(1)
                action_taken = True
                
            elif find_only("victory_02.png", custom_confidence=0.7):
                if not find_only("next_level_02.png", 0.6) and not find_only("fight_again.png", 0.6):
                    log("🏆 Victory 動畫中，點中央加速")
                    screen_width, screen_height = pyautogui.size()
                    pyautogui.click(screen_width // 2, screen_height // 2)
                    time.sleep(0.5)
                    action_taken = True
                    
            # 狀態 A：看得到一般快轉，就點擊它 (持續跳過前置劇情)
            elif find_and_click(["fast_forward_03.png", "fast_forward_02.png", "fast_forward_01.png"], custom_confidence=0.9,region=(1536,8,383,172)):
                log("▶️ 點擊一般快轉按鈕")
                time.sleep(0.5) 
                action_taken = True

            # --------------------------------------------------
            # 狀態 B：如果發現快轉被禁用了 (no_fast_forward.png)
            # 代表目前卡在強制劇情或選項，立刻啟動 OCR 辨識點擊！
            # --------------------------------------------------
            elif find_only("no_fast_forward.png", custom_confidence=0.9, region=(1314,0,605,180)):
                screenshot = pyautogui.screenshot(region=dialog_region)
                img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

                result_texts = reader.readtext(img)

                if result_texts:
                    first_result = result_texts[0]
                    bbox = first_result[0]      
                    detected_text = first_result[1] 
                    
                    if detected_text.strip(): 
                        center_x_rel = int((bbox[0][0] + bbox[2][0]) / 2)
                        center_y_rel = int((bbox[0][1] + bbox[2][1]) / 2)
                        
                        click_x = dialog_region[0] + center_x_rel
                        click_y = dialog_region[1] + center_y_rel
                        
                        log(f"💬 強制劇情中: [{detected_text}] -> 點擊 ({click_x}, {click_y})")
                        pyautogui.click(click_x, click_y)
                        
                        time.sleep(0.1) # 點擊後短暫冷卻
                        action_taken = True         
            elif find_only("leave_01.png", custom_confidence=0.8,region=(1681,929,238,150)):
                log("🚪 發現離開按鈕，完成故事劇情，跳出迴圈。")
                break
        # 這裡補上了漏掉的 except 區塊，防止語法崩潰！
        except Exception as e:
            log(f"執行過程中發生錯誤: {e}")

        # --------------------------------------------------
        # 狀態監控與冷卻機制
        # --------------------------------------------------
        if action_taken:
            not_found_streak = 0
            time.sleep(0.05) # 如果有做事，只休息一下下就繼續
            continue

        not_found_streak += 1
        if not_found_streak % 15 == 0:
            log(f"👀 畫面無動靜... 持續監控中 (Streak: {not_found_streak})")
            wake_up_gpu()
            
        if not_found_streak >= 100:
            log("⚠️ 連續 100 次無動作，可能卡住了，保存除錯截圖。")
            save_debug_screenshot("lost_track_long")
            not_found_streak = 0
        
        # 什麼都沒找到時的基礎冷卻時間，避免 CPU 飆高
        time.sleep(0.2)

if __name__ == "__main__":
    auto_story_mode()