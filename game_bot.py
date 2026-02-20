import time
import random
import os
import sys
import subprocess
import datetime

# --- 1. 自動安裝缺失庫 ---
def install_requirements():
    import importlib.util
    required = {
        "pyautogui": "pyautogui",
        "keyboard": "keyboard", 
        "pillow": "PIL",
        "opencv-python": "cv2",
        "numpy": "numpy"
    }
    needs_install = False
    for package_name, import_name in required.items():
        if importlib.util.find_spec(import_name) is None:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
                needs_install = True
            except Exception:
                pass
    if needs_install:
        os.execv(sys.executable, ['python'] + sys.argv)

install_requirements()

# --- 2. 核心庫導入 ---
try:
    import pyautogui
    import keyboard
    import cv2
    import numpy as np
    pyautogui.FAILSAFE = True 
    pyautogui.PAUSE = 0.05 
except ImportError as e:
    sys.exit(1)

# --- 3. 路徑與全域變數 ---
# 修正：將圖片資料夾路徑直接設定為腳本所在的目錄，以實現可攜性
# 這移除了所有硬編碼的路徑，讓程式更容易轉移
IMAGE_FOLDER = os.path.dirname(os.path.abspath(__file__))

# 檢查該路徑是否存在（雖然它應該永遠存在）
if not os.path.isdir(IMAGE_FOLDER):
    input(f"❌ 錯誤：腳本目錄 '{IMAGE_FOLDER}' 不存在或不是一個資料夾，按 Enter 退出...")
    sys.exit(1)

GAME_REGION = None 
LAST_RESOLUTION = pyautogui.size() # 記錄目前的解析度

# --- 4. 核心功能 ---

def save_debug_screenshot(reason):
    """ 保存當前畫面以便除錯 """
    debug_dir = os.path.join(IMAGE_FOLDER, "debug_screenshots")
    if not os.path.exists(debug_dir):
        os.makedirs(debug_dir)
    timestamp = datetime.datetime.now().strftime("%H-%M-%S")
    filename = f"{reason}_{timestamp}.png"
    filepath = os.path.join(debug_dir, filename)
    try:
        pyautogui.screenshot(filepath)
    except:
        pass

def wake_up_gpu():
    """ 
    [V11 新功能] 
    嘗試喚醒 GPU 渲染。
    當螢幕關閉或切換時，微小的輸入有助於讓 Windows 保持渲染活躍。
    """
    # 1. 輕微晃動滑鼠
    x, y = pyautogui.position()
    pyautogui.moveTo(x+1, y+1)
    pyautogui.moveTo(x, y)
    
    # 2. 按一下 Shift (通常不會影響遊戲，但能喚醒系統)
    pyautogui.press('shift')
    # print("   ⚡ 嘗試喚醒 GPU 渲染...")

def check_resolution_change():
    """
    [V11 新功能]
    監控螢幕解析度是否因為 HDMI Dummy 切換而改變。
    如果改變了，強制重置遊戲視窗鎖定。
    """
    global LAST_RESOLUTION, GAME_REGION
    current_res = pyautogui.size()
    if current_res != LAST_RESOLUTION:
        print(f"\n⚠️ 警告：偵測到螢幕解析度改變！")
        print(f"   舊: {LAST_RESOLUTION} -> 新: {current_res}")
        print("   正在重置視窗鎖定，請稍候...")
        LAST_RESOLUTION = current_res
        GAME_REGION = None # 強制重置區域
        detect_game_window() # 重新抓視窗

def read_image_safe(path):
    try:
        img_array = np.fromfile(path, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_UNCHANGED)
        if img.shape[2] == 3:
             return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        return img 
    except Exception:
        return None

def human_click(location, clicks=1):
    if not location: return
    
    original_failsafe_state = pyautogui.FAILSAFE
    try:
        # 暫時禁用防呆，以允許點擊靠近角落的目標
        pyautogui.FAILSAFE = False
        
        x, y = location
        offset_x = x + random.randint(-8, 8)
        offset_y = y + random.randint(-5, 5)
        
        # 確保座標不會超出螢幕範圍 (額外保護)
        screen_width, screen_height = pyautogui.size()
        offset_x = min(screen_width - 1, max(0, offset_x))
        offset_y = min(screen_height - 1, max(0, offset_y))

        pyautogui.moveTo(offset_x, offset_y, duration=random.uniform(0.1, 0.2))
        for i in range(clicks):
            pyautogui.mouseDown()
            time.sleep(random.uniform(0.08, 0.15)) 
            pyautogui.mouseUp()
            if clicks > 1: time.sleep(random.uniform(0.05, 0.1))
    
    except Exception as e:
        # 在發生錯誤時印出資訊
        print(f"   -> ⚠️ human_click 發生錯誤: {e}")
    
    finally:
        # 無論如何都恢復防呆功能
        pyautogui.FAILSAFE = original_failsafe_state

def detect_game_window():
    """
    [V13] 使用多層次信心度偵測遊戲視窗，以適應 HDMI Dummy。
    """
    global GAME_REGION
    GAME_REGION = None # 每次偵測都先重置
    window_img_path = os.path.join(IMAGE_FOLDER, "game_window.png")

    try:
        img_array = np.fromfile(window_img_path, dtype=np.uint8)
        window_needle = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if window_needle is None: return
    except Exception:
        return # Cannot read image, nothing to do

    # 從高到低嘗試不同的信心度
    confidence_levels = [0.8, 0.7, 0.65, 0.6]
    for conf in confidence_levels:
        try:
            box = pyautogui.locateOnScreen(window_needle, confidence=conf, grayscale=True)
            if box:
                GAME_REGION = (int(box.left), int(box.top), 1024, 780)
                print(f"✅ 視窗成功鎖定 (信心度: {conf}): {GAME_REGION}")
                return # 成功找到，退出函式
        except pyautogui.PyAutoGUIException:
            continue # 找不到，繼續用下一個信心度
        except Exception:
            return # 其他錯誤

def get_image_path(image_name):
    possible_names = [image_name, image_name.upper(), image_name.lower()]
    if not image_name.lower().endswith((".png", ".jpg")):
        possible_names.append(image_name + ".png")
    for name in possible_names:
        temp_path = os.path.join(IMAGE_FOLDER, name)
        if os.path.exists(temp_path):
            return temp_path
    return None

def find_only(image_name, custom_confidence=None):
    """
    [V13] 使用多層次信心度來尋找圖片，以應對 HDMI Dummy 造成的渲染差異。
    [V14] 修正了 Unicode 路徑問題，確保圖片能被正確讀取。
    """
    target_path = get_image_path(image_name)
    if not target_path: return None

    # [V14] 修正：先用安全的方式讀取圖片，再傳遞給 pyautogui
    needle_image = read_image_safe(target_path)
    if needle_image is None:
        return None

    # 準備一個信心度列表，從高到低
    base_conf = custom_confidence if custom_confidence else 0.85
    confidence_levels = [base_conf, base_conf - 0.1, 0.7, 0.6] # 逐步降低
    unique_confidences = sorted(list(set(c for c in confidence_levels if c >= 0.6)), reverse=True)

    # 針對每個信心度，都先嘗試區域再嘗試全螢幕
    for conf in unique_confidences:
        try:
            # 1. 優先在鎖定區域找
            if GAME_REGION:
                location = pyautogui.locateCenterOnScreen(needle_image, confidence=conf, grayscale=True, region=GAME_REGION)
                if location:
                    return location
            
            # 2. 如果區域找不到或無區域，則全螢幕尋找
            location = pyautogui.locateCenterOnScreen(needle_image, confidence=conf, grayscale=True)
            if location:
                return location
                
        except pyautogui.PyAutoGUIException:
            continue # 找不到是正常的，換下個 confidence
        except Exception:
            # 其他錯誤就直接返回
            return None
            
    return None

def find_and_click(image_name, custom_confidence=None, clicks=1):
    location = find_only(image_name, custom_confidence)
    if location:
        print(f"🎯 發現: {image_name}")
        human_click(location, clicks=clicks)
        return True
    return False

def launch_game_from_steam():
    """
    從 Steam 啟動遊戲 "Rise of Eros" 的完整流程。
    假設已有 find_and_click() 函式可供使用。
    """
    print("\n🚀 === 開始從 Steam 啟動遊戲 ===")

    # 0. 點擊螢幕最右下角 (顯示桌面)
    print("   -> 正在點擊右下角以顯示桌面...")
    try:
        # 暫時禁用防呆機制，以便點擊螢幕角落
        pyautogui.FAILSAFE = False
        screen_width, screen_height = pyautogui.size()
        pyautogui.click(screen_width - 1, screen_height - 1)
        time.sleep(1) # 等待桌面顯示動畫
    except Exception as e:
        print(f"   -> ⚠️ 點擊右下角時發生錯誤: {e}")
    finally:
        # 無論如何，操作結束後都恢復防呆機制
        pyautogui.FAILSAFE = True

    # 1. 點擊 Steam 圖示 (改為雙擊)
    print("   -> 正在尋找並雙擊 Steam 圖示...")
    if not find_and_click("steam_icon.png", custom_confidence=0.8, clicks=2):
        print("   -> ❌ 錯誤：在桌面或工作列上找不到 'steam_icon.png'。")
        return False
    
    # 2. 等待 Steam 主視窗載入
    print("   -> 等待 Steam 啟動... (10秒)")
    time.sleep(10)

    # 3. 選擇帳號並登入
    print("   -> 正在尋找指定帳號 (loopcraft001 或 e08s93)...")
    account_clicked = find_and_click("loopcraft001.png", custom_confidence=0.85)
    if not account_clicked:
        account_clicked = find_and_click("e08s93.png", custom_confidence=0.85)

    if account_clicked:
        print("   -> 偵測到帳號，已點擊。")
    else:
        # 如果找不到特定帳號，可能是因為已自動登入，所以只顯示提示訊息而不是中止
        print("   -> ℹ️ 未找到特定帳號截圖，假設 Steam 會自動登入。")

    # 4. 等待登入與主介面載入
    print("   -> 等待 Steam 登入與載入主介面... (20秒)")
    time.sleep(20)

    # 5. 關閉彈出廣告
    print("   -> 正在嘗試關閉 Steam 彈出廣告...")
    if find_and_click("steam_close_ad.png", custom_confidence=0.85):
        print("   -> 已關閉廣告視窗。")
        time.sleep(2) # 等待視窗關閉動畫
    else:
        print("   -> 未發現廣告視窗。")

    # 6. 點擊「收藏庫」
    print("   -> 正在點擊「收藏庫」...")
    if not find_and_click("steam_library.png", custom_confidence=0.8):
        print("   -> ❌ 錯誤：找不到「收藏庫」按鈕 'steam_library.png'。")
        return False
    time.sleep(3)

    # 7. 在左側列表中選擇遊戲
    print("   -> 正在從收藏庫選擇 'Rise of Eros'...")
    if not find_and_click("rise_of_eros_list.png", custom_confidence=0.9):
         print("   -> ❌ 錯誤：在收藏庫中找不到遊戲 'rise_of_eros_list.png'。")
         return False
    time.sleep(3)

    # 8. 點擊「開始遊戲」
    print("   -> 正在點擊「開始遊戲」按鈕...")
    if not find_and_click("steam_play_btn.png", custom_confidence=0.8):
        print("   -> ❌ 錯誤：找不到「開始遊戲」按鈕 'steam_play_btn.png'。")
        return False
    
    print("✅ === 遊戲啟動指令已發送！ ===")
    return True

# --- 5. 主程式 ---

def main():
    global GAME_REGION
    print("\n=== OpenClaw V15 (Portable Paths) ===")
    print("特色：可攜式路徑、持續視窗搜尋、解析度監控、防休眠")
    print(f"初始解析度: {LAST_RESOLUTION}")
    detect_game_window()
    
    last_log_time = time.time()
    not_found_streak = 0
    
     # 首先啟動遊戲
    if not launch_game_from_steam():
        print("🛑 遊戲啟動失敗，程式結束。")
        return # 或 sys.exit()


    while True:
        if keyboard.is_pressed('q'):
            print("🛑 程式停止。")
            break
        
        # --- 1. 檢查與維持環境 ---
        check_resolution_change() # 可能會重置 GAME_REGION

        # --- 2. 核心：視窗搜尋模式 ---
        if GAME_REGION is None:
            print("❓ 遊戲視窗遺失，進入持續搜尋模式...")
            
            # 嘗試點擊圖示來啟動或喚醒遊戲
            if find_and_click("game_sign.png", custom_confidence=0.8):
                print("   -> 點擊了啟動圖示，等待 3 秒讓視窗反應...")
                time.sleep(3)
            else:
                # 如果連圖示都找不到，可能視窗已開啟但未被偵測，或被遮擋
                print("   -> 未找到啟動圖示，5 秒後重試...")
                time.sleep(5)

            # 無論如何都重新偵測一次
            detect_game_window()
            # 立即重新開始迴圈，檢查 GAME_REGION 是否已找到
            # 如果找到了，下一個迴圈就會進入遊戲邏輯；如果沒找到，會再次進入此模式
            continue

        # --- 3. 遊戲內決策流程 (僅在 GAME_REGION 有效時執行) ---
        time.sleep(0.3) # 在活躍狀態下降低CPU使用率
        action_taken = False

        if find_and_click("warn.png"):
             time.sleep(1)
             find_and_click("yes.png", clicks=2)
             action_taken = True
        elif find_and_click("next_level.png", custom_confidence=0.75):
            print("🚀 點擊：下一關")
            time.sleep(4)
            action_taken = True
        elif find_only("fight_again.png", custom_confidence=0.75):
            if find_and_click("next_level.png", custom_confidence=0.6):
                print("🚀 (再次挑戰觸發) 下一關")
                time.sleep(4)
                action_taken = True
        elif find_only("victory.png", custom_confidence=0.7):
            if not find_only("next_level.png", 0.6) and not find_only("fight_again.png", 0.6):
                 print("🏆 Victory 動畫... 加速")
                 if GAME_REGION: # Should always be true here
                     cx = GAME_REGION[0] + 512
                     cy = GAME_REGION[1] + 384
                     pyautogui.click(cx, cy)
                 else:
                     pyautogui.click(960, 540)
                 time.sleep(0.5)
                 action_taken = True
        elif find_and_click("start.png"):
            print("⚔️ 開始戰鬥")
            time.sleep(5)
            action_taken = True
        elif find_and_click("auto.png"):
            time.sleep(1)
            action_taken = True
        elif find_and_click("fast_forward.png") or find_and_click("skip.png"):
            action_taken = True
        elif find_and_click("confirm.png"):
            action_taken = True

        # --- 4. 狀態管理與日誌 ---
        if action_taken:
            not_found_streak = 0
            continue # 如果有動作，直接進入下一輪
        else:
            not_found_streak += 1
            if not_found_streak % 15 == 0: # 每隔約4.5秒
                print(f"👀 監控中... (Streak: {not_found_streak})")
                wake_up_gpu()
            
            # 如果連續非常多次都找不到，可能視窗真的卡死了，強制重新偵測
            if not_found_streak >= 100:
                print("❓ 連續100次無動作，強制重新鎖定視窗...")
                save_debug_screenshot("lost_track_long")
                GAME_REGION = None # 這會讓下一個迴圈進入搜尋模式
                not_found_streak = 0 # 重置計數器

if __name__ == "__main__":
    main()