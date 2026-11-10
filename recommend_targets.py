import cv2
import numpy as np
import pyautogui
import os
import time

def find_best_screenshot_targets():
    time.sleep(3)  # 等待3秒，確保螢幕畫面穩定
    print("📸 正在掃描當前畫面，尋找高辨識度的特徵熱區...")
    
    # 1. 抓取當下螢幕畫面
    screenshot = pyautogui.screenshot()
    img_bgr = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    
    # 2. 邊緣檢測與膨脹處理
    edges = cv2.Canny(img_gray, 50, 150)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (18, 5))
    dilated = cv2.dilate(edges, kernel, iterations=2)
    
    # 3. 尋找輪廓區塊
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    recommendations = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if 40 < w < 350 and 15 < h < 100:
            roi_edges = edges[y:y+h, x:x+w]
            edge_density = np.sum(roi_edges) / 255 / (w * h)
            if edge_density > 0.08: 
                recommendations.append((x, y, w, h, edge_density))
                
    # 4. 排序並取前 25 個
    recommendations = sorted(recommendations, key=lambda x: x[4], reverse=True)[:25]
    
    # 5. 在畫面上繪製「純黃色推薦框」，不加任何文字
    for (x, y, w, h, density) in recommendations:
        cv2.rectangle(img_bgr, (x, y), (x+w, y+h), (0, 255, 255), 2)

    # 儲存並自動彈出圖片
    output_name = "recommend_targets.png"
    cv2.imwrite(output_name, img_bgr)
    
    print(f"✅ 分析完成！已標出全螢幕前 {len(recommendations)} 個最佳辨識區域 (純淨版)。")
    print("🎯 截圖秘訣：請直接沿著「黃色框線內部」進行截圖，盡量不要截到框外的背景！")
    
    pyautogui.press('win')
    os.system(f"start {output_name}")

if __name__ == "__main__":
    find_best_screenshot_targets()