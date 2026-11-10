import os
import glob
import cv2
import numpy as np
import pyautogui
import time

def analyze_template_matching(image_dir="./pictures", confidence_threshold=0.85):
    time.sleep(3)  # 等待一秒，確保螢幕畫面穩定
    # 1. 抓取當前螢幕畫面
    screenshot = pyautogui.screenshot()
    screen_bgr = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    screen_gray = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)
    
    debug_canvas = screen_bgr.copy()
    
    img_files = glob.glob(os.path.join(image_dir, "*.png"))
    img_files = [f for f in img_files if not f.endswith("debug_output.png")]
    
    if not img_files:
        print(f"❌ 未在 {image_dir} 目錄中找到任何 .png 圖片檔！")
        return

    print("=" * 65)
    print(f"{'圖片檔名':<25} | {'最高相似度':<12} | {'辨識狀態':<10}")
    print("=" * 65)

    for img_path in img_files:
        file_name = os.path.basename(img_path)
        template_bgr = cv2.imread(img_path)
        
        if template_bgr is None:
            continue
            
        template_gray = cv2.cvtColor(template_bgr, cv2.COLOR_BGR2GRAY)
        h, w = template_gray.shape[:2]

        res = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

        top_left = max_loc
        bottom_right = (top_left[0] + w, top_left[1] + h)

        # 2. 判定畫框與輸出條件
        if max_val >= confidence_threshold:
            # 大於 0.85：成功，畫綠框
            status = "✅ 成功"
            box_color = (0, 255, 0)
            draw = True
        elif max_val >= 0.60:
            # 介於 0.60 ~ 0.84：有抓到類似的東西但未達標，畫紅框
            status = "❌ 失敗"
            box_color = (0, 0, 255)
            draw = True
        else:
            # 低於 0.60：根本不在畫面上，無視且不畫框
            draw = False

        # 只處理畫面上真正有出現（或極度相似）的圖片
        if draw:
            print(f"{file_name:<25} | {max_val*100:6.2f}% ({max_val:.3f}) | {status:<10}")
            
            cv2.rectangle(debug_canvas, top_left, bottom_right, box_color, 2)
            label = f"{file_name} ({max_val:.2f})"
            label_y = max(20, top_left[1] - 8)
            cv2.putText(debug_canvas, label, (top_left[0], label_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2)

    print("=" * 65)
    output_path = "debug_output.png"
    cv2.imwrite(output_path, debug_canvas)
    print(f"\n💡 視覺化除錯圖已儲存至: {output_path}")

    # 3. 簡單粗暴的視窗切換與開圖
    pyautogui.press('win')  # 按下 Win 鍵，通常能讓全螢幕遊戲失去焦點並叫出工作列
    os.system("start debug_output.png")  # 直接讓 Windows 打開這張除錯圖

if __name__ == "__main__":
    analyze_template_matching(image_dir="./pictures", confidence_threshold=0.85)