import pyautogui
import time

print("OpenClaw 手臂測試中...")
print("請在 3 秒內切換到瀏覽器或空白處，不要遮擋螢幕。")
time.sleep(3)

# 取得螢幕解析度
width, height = pyautogui.size()
print(f"螢幕解析度: {width} x {height}")

# 畫一個正方形測試滑鼠移動
print("開始移動滑鼠...")
pyautogui.moveRel(100, 0, duration=0.5)
pyautogui.moveRel(0, 100, duration=0.5)
pyautogui.moveRel(-100, 0, duration=0.5)
pyautogui.moveRel(0, -100, duration=0.5)

print("測試完成！如果你看到滑鼠動了，代表環境設定成功。")