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

def get_image_path(image_name):
    possible_names = [image_name, image_name.upper(), image_name.lower()]
    if not image_name.lower().endswith((".png", ".jpg")):
        possible_names.append(image_name + ".png")
    for name in possible_names:
        temp_path = os.path.join(IMAGE_FOLDER, name)
        if os.path.exists(temp_path):
            return temp_path
    return None

def find_only(image_name, custom_confidence=None, region=None):
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

    # 針對每個信心度嘗試全螢幕搜尋
    for conf in unique_confidences:
        try:
            if region:
                location = pyautogui.locateCenterOnScreen(
                    needle_image, confidence=conf, grayscale=True, region=region
                )
            else:
                location = pyautogui.locateCenterOnScreen(needle_image, confidence=conf, grayscale=True)
            if location:
                return location
                
        except pyautogui.PyAutoGUIException:
            continue # 找不到是正常的，換下個 confidence
        except Exception:
            # 其他錯誤就直接返回
            return None
            
    return None

def find_only_strict(image_name, confidence=0.97, region=None, grayscale=False):
    """
    嚴格比對模式：不自動降低 confidence，避免誤判。
    適合帳號名稱、文字等高精度辨識場景。
    """
    target_path = get_image_path(image_name)
    if not target_path:
        return None

    needle_image = read_image_safe(target_path)
    if needle_image is None:
        return None

    try:
        if region:
            return pyautogui.locateCenterOnScreen(
                needle_image, confidence=confidence, grayscale=grayscale, region=region
            )
        return pyautogui.locateCenterOnScreen(
            needle_image, confidence=confidence, grayscale=grayscale
        )
    except pyautogui.PyAutoGUIException:
        return None
    except Exception:
        return None

def find_and_click(image_name, custom_confidence=None, clicks=1, region=None):
    location = find_only(image_name, custom_confidence, region=region)
    if location:
        print(f"🎯 發現: {image_name} @ {location}")
        human_click(location, clicks=clicks)
        return True
    return False

def get_center_region(width_ratio=0.7, height_ratio=0.7):
    """回傳螢幕中央區域，降低全螢幕誤判。"""
    screen_width, screen_height = pyautogui.size()
    region_width = int(screen_width * width_ratio)
    region_height = int(screen_height * height_ratio)
    left = (screen_width - region_width) // 2
    top = (screen_height - region_height) // 2
    return (left, top, region_width, region_height)

def get_region_around_point(x, y, width=900, height=420):
    """以座標為中心產生搜尋區域，並自動限制在螢幕範圍內。"""
    screen_width, screen_height = pyautogui.size()
    left = max(0, int(x - width // 2))
    top = max(0, int(y - height // 2))
    right = min(screen_width, left + width)
    bottom = min(screen_height, top + height)
    return (left, top, right - left, bottom - top)

def wait_seconds_with_abort(seconds, title):
    """可中止的等待。"""
    print(f"\n⏳ {title} ({seconds} 秒)...")
    for remaining in range(seconds, 0, -1):
        if keyboard.is_pressed('q'):
            print("🛑 使用者中止。")
            return False
        if remaining % 5 == 0 or remaining <= 5:
            print(f"   -> 倒數 {remaining} 秒")
        time.sleep(1)
    return True

def click_screen_center():
    """點擊螢幕中央，作為無法辨識按鈕時的備援。"""
    screen_width, screen_height = pyautogui.size()
    human_click((screen_width // 2, screen_height // 2))

def handle_dialog_windows():
    """
    處理可能阻擋流程的詢問視窗。
    回傳 True 代表本輪有實際點擊到任何按鈕。
    """
    center_region = get_center_region(0.82, 0.82)
    full_region = None
    acted = False

    def click_buttons(buttons, region):
        nonlocal acted
        for image_name, conf, clicks in buttons:
            if find_and_click(image_name, custom_confidence=conf, clicks=clicks, region=region):
                print(f"   -> 已處理對話框: {image_name}")
                acted = True
                return True
        return False

    warn_buttons = [("warn.png", 0.88, 1)]
    followup_buttons = [
        ("yes.png", 0.9, 1),
        ("confirm.png", 0.9, 1),
        ("ok.png", 0.92, 1),
        ("OK.png", 0.92, 1),
        ("OK03.png", 0.92, 1),
        ("close.png", 0.92, 1),
        ("close_02.png", 0.92, 1),
    ]
    common_buttons = [
        ("confirm.png", 0.9, 1),
        ("ok.png", 0.92, 1),
        ("OK.png", 0.92, 1),
        ("OK03.png", 0.92, 1),
        ("accept_all.png", 0.9, 1),
        ("close.png", 0.92, 1),
        ("close_02.png", 0.92, 1),
    ]

    # 先檢查 warn，再嘗試關閉後續視窗
    if click_buttons(warn_buttons, center_region):
        time.sleep(0.35)
        followup_clicked = click_buttons(followup_buttons, center_region)
        if not followup_clicked:
            click_buttons(followup_buttons, full_region)
        return True

    # 一般彈窗先找中心，再找全螢幕
    if click_buttons(common_buttons, center_region):
        return True
    if click_buttons(common_buttons, full_region):
        return True
    return False

def wait_for_press_to_start(max_wait_seconds=120, center_click_interval=3.0):
    """
    不做視窗定位，直接全螢幕偵測 press_to_start.png。
    若長時間找不到，會定期點擊螢幕中央嘗試推進流程。
    """
    print("\n⏳ 全螢幕持續偵測 'press_to_start.png'（含中央點擊備援）...")
    start_time = time.time()
    last_center_click_time = 0.0
    last_progress_log_time = 0.0

    while time.time() - start_time < max_wait_seconds:
        if keyboard.is_pressed('q'):
            print("🛑 使用者中止。")
            return False

        # 若已經看到遊戲內元素，視為已進入遊戲
        if find_only_strict("set.png", confidence=0.94, grayscale=True):
            print("✅ 偵測到遊戲內介面元素，視為已成功進入。")
            return True
        if find_only("set_02.png", custom_confidence=0.94):
            print("✅ 偵測到遊戲內介面元素，視為已成功進入。")
            return True

        if find_and_click("press_to_start.png", custom_confidence=0.85):
            print("✅ 已點擊 'Press to Start'，確認是否成功進入...")
            verify_deadline = time.time() + 8
            while time.time() < verify_deadline:
                if find_only_strict("set.png", confidence=0.94):
                    print("✅ 按下後已進入遊戲。")
                    return True
                if handle_dialog_windows():
                    time.sleep(0.6)
                time.sleep(0.3)
            print("   -> 已點擊但尚未進入，繼續偵測...")

        if handle_dialog_windows():
            time.sleep(1.2)
            continue

        now = time.time()
        if now - last_center_click_time >= center_click_interval:
            print("   👉 未找到 'Press to Start'，點擊螢幕中央嘗試喚醒流程...")
            click_screen_center()
            time.sleep(0.8)
            if handle_dialog_windows():
                time.sleep(0.8)
            last_center_click_time = now
            time.sleep(0.8)
            continue            

        if now - last_progress_log_time >= 5:
            remaining = int(max_wait_seconds - (now - start_time))
            print(f"   -> 尚未找到 'Press to Start'，持續偵測中... (剩餘 {remaining} 秒)")
            last_progress_log_time = now
            wake_up_gpu()

        time.sleep(0.4)

    print("❌ 等待 'Press to Start' 超時。")
    save_debug_screenshot("press_to_start_timeout")
    return False

def wait_for_image(image_name, timeout=15.0, custom_confidence=None):
    """
    動態等待直到畫面出現指定的圖片。
    :param image_name: 要等待的圖片名稱
    :param timeout: 最多等幾秒 (預設 15 秒)
    :param custom_confidence: 辨識信心度
    :return: 找到回傳 True，超時回傳 False
    """
    print(f"   ⏳ 等待畫面: {image_name} (最多等 {timeout} 秒)...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        # 呼叫我們之前寫好的 find_only 函式來找圖 (只看不點)
        location = find_only(image_name, custom_confidence)
        
        if location:
            elapsed = time.time() - start_time
            print(f"   ✅ 畫面出現了！(耗時 {elapsed:.1f} 秒)")
            return True
            
        # 每 0.5 秒檢查一次，避免 CPU 跑到 100%
        time.sleep(0.5)
        
    print(f"   ❌ 等待超時 ({timeout} 秒)，沒看到 {image_name}！")
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
    wait_for_image("who.png", timeout=30.0)
    # 3. 選擇帳號並登入 (懸停顯示-點擊機制)
    print("   -> 開始尋找 Steam 帳號...")
    
    account_found_and_clicked = False
    who_buttons_found = False # 用於判斷是否曾找到who.png
    target_account_images = ["e08s93.123.png"]
    
    original_failsafe_state = pyautogui.FAILSAFE
    try:
        # a. 找到 'who.png' 的圖片路徑
        who_image_path = get_image_path('who.png')
        if not who_image_path:
             print("   -> ℹ️ 未在資料夾中找到 'who.png' 圖片，跳過帳號選擇。")
        else:
            # 暫時禁用防呆，因為我們可能會在螢幕角落進行尋找或懸停
            pyautogui.FAILSAFE = False
            
            # a. 找到畫面上所有 'who.png' 的位置
            who_buttons = list(pyautogui.locateAllOnScreen(who_image_path, confidence=0.99, grayscale=True))
            who_buttons_found = len(who_buttons) > 0

            # b. 從左到右排序
            who_buttons.sort(key=lambda box: box.left)
            
            if not who_buttons:
                print("   -> ℹ️ 未在畫面上找到 'who.png' 按鈕，假設 Steam 會自動登入。")
            else:
                print(f"   -> 找到 {len(who_buttons)} 個潛在帳號，開始從左到右檢查...")
                
                # c. 遍歷所有按鈕
                for button_box in who_buttons:
                    button_center = pyautogui.center(button_box)
                    
                    # d. 移動滑鼠到按鈕上以觸發懸停效果
                    pyautogui.moveTo(button_center.x, button_center.y, duration=0.2)
                    time.sleep(0.65) # 等待帳號名稱出現

                    # e. 只在懸停按鈕附近做比對：先嚴格再逐步放寬
                    hover_region = get_region_around_point(button_center.x, button_center.y, width=1200, height=520)
                    match_profiles = [
                        ("strict_color", 0.97, False, 2),
                        ("balanced_color", 0.94, False, 2),
                        ("balanced_gray", 0.92, True, 1),
                    ]
                    account_matched = False

                    for profile_name, profile_conf, profile_gray, required_hits in match_profiles:
                        stable_hits = 0
                        for _ in range(2):
                            matched = False
                            for account_image in target_account_images:
                                if find_only_strict(
                                    account_image,
                                    confidence=profile_conf,
                                    region=hover_region,
                                    grayscale=profile_gray
                                ):
                                    matched = True
                                    break
                            if matched:
                                stable_hits += 1
                            time.sleep(0.12)

                        print(
                            f"   -> 帳號比對 {profile_name}: "
                            f"hits={stable_hits}/2, conf={profile_conf}, gray={profile_gray}"
                        )

                        if stable_hits >= required_hits:
                            account_matched = True
                            break

                    if account_matched:
                        print(f"   -> 找到目標帳號！正在點擊位於 ({button_center.x}, {button_center.y}) 的按鈕...")
                        # human_click 內部已有自己的防呆處理
                        human_click(button_center)
                        account_found_and_clicked = True
                        break # 找到並點擊後，跳出迴圈
    
    except Exception as e:
        print(f"   -> ⚠️ 尋找帳號時發生錯誤: {e}")
    finally:
        # 確保防呆在任何情況下都恢復到原始狀態
        pyautogui.FAILSAFE = original_failsafe_state

    # 根據查找結果決定後續流程
    if not account_found_and_clicked:
        if who_buttons_found:
            # 找到了 who.png 但沒有匹配的帳號
            print("   -> ⚠️ 檢查了所有帳號，但未找到 'loopcraft001.png' 或 'e08s93.png'。請確認截圖。")
        else:
            # 從一開始就沒找到 who.png
            print("   -> ℹ️ 未找到任何帳號按鈕，假設 Steam 會自動登入。")

    # 4. 等待登入與主介面載入
    print("   -> 等待 Steam 登入與載入主介面... (20秒)")
    wait_for_image("steam_library.png", timeout=60.0)

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
    if not find_and_click("steam_play_btn.png", custom_confidence=1): # Use confidence=1 for higher accuracy
        print("   -> ❌ 錯誤：找不到「開始遊戲」按鈕 'steam_play_btn.png'。")
        return False
    time.sleep(3)

    print("✅ === 遊戲啟動指令已發送！ ===")
    return True

def leave_game():
    """
    依序離開遊戲：
    set.png -> quit_game.png -> confirm.png -> steam_sign.png -> quit.png
    """
    print("\n🚪 === 開始執行離開遊戲流程 ===")

    steps = [
        ("set.png", 0.85, 1),
        ("quit_game.png", 0.85, 1),
        ("confirm.png", 0.88, 1),
        ("steam_sign.png", 0.85, 1),
        ("quit.png", 0.85, 0),
    ]

    for image_name, confidence, wait_after_click in steps:
        print(f"   -> 嘗試點擊: {image_name}")
        if not find_and_click(image_name, custom_confidence=confidence):
            print(f"   -> ❌ 錯誤：找不到 '{image_name}'。")
            save_debug_screenshot(f"leave_game_no_{os.path.splitext(image_name)[0]}")
            return False

        if wait_after_click > 0:
            if not wait_seconds_with_abort(wait_after_click, f"等待 {image_name} 操作完成"):
                return False

    print("✅ 離開遊戲流程完成。")
    return True

def consume_energy():
    """
    自動執行消耗體力的流程。
    """
    print("\n💪 === 開始執行消耗體力流程 ===")
    wait_for_image("ongoing_activity.png", timeout=15.0)
    # 1. 點擊 "ongoing_activity"
    if not find_and_click("ongoing_activity.png", custom_confidence=0.8):
        print("   -> ❌ 錯誤：找不到 'ongoing_activity.png'。")
        save_debug_screenshot("no_ongoing_activity")
        return False
    
    # 2. 等待5秒
    if not wait_seconds_with_abort(5, "等待活動頁面載入"):
        return False # 使用者中止

    # 3. 點擊 "activity"
    if not find_and_click("activity.png", custom_confidence=0.8):
        print("   -> ❌ 錯誤：找不到 'activity.png'。")
        save_debug_screenshot("no_activity_button")
        return False
    
    if not wait_seconds_with_abort(2, "等待戰鬥按鈕"):
        return False

    # 4. 點擊 "battle"
    
    if not find_and_click("battle.png", custom_confidence=0.85):
        print("   -> ❌ 錯誤：找不到 'battle.png'。")
        save_debug_screenshot("no_battle_button")
        return False
    

    if not wait_seconds_with_abort(2, "等待關卡選擇畫面"):
        return False

    # 5. 點擊 "battle7" 右方的關卡
    # 策略：以 "battle7" 按鈕位置為基準，向右偏移來點擊關卡
    print("   -> 嘗試點擊 'battle7' 按鈕右方的關卡...")
    battle_location = find_only("battle7.png", custom_confidence=0.9)
    # 假設關卡在右方約 250 像素的位置，Y 軸不變。這是一個估計值。
    target_x = battle_location.x + random.randint(400, 600) # 增加隨機偏移，避免每次點擊完全相同的位置
    target_y = battle_location.y
    print(f"   -> 計算出的關卡座標: ({target_x}, {target_y})")
    human_click((target_x, target_y))
    
    if not wait_seconds_with_abort(3, "等待關卡資訊載入"):
        return False

    # 6. 點擊 "swape" (掃蕩)
    if not find_and_click("swape.png", custom_confidence=0.8):
        print("   -> ⚠️ 警告：找不到 'swape.png'，腳本將繼續。")
        save_debug_screenshot("swape_not_found")
        pass # 即使找不到也嘗試繼續

    if not wait_seconds_with_abort(2, "等待掃蕩視窗"):
        return False

    # 7. 點擊 "max"
    if not find_and_click("max.png", custom_confidence=0.8):
        print("   -> ❌ 錯誤：找不到 'max.png'。")
        save_debug_screenshot("max_not_found")
        return False
    # 8. 點擊 "confirm" (確認)
    if not find_and_click("confirm.png", custom_confidence=0.8):
        print("   -> ❌ 錯誤：找不到 'confirm.png'。")
        save_debug_screenshot("confirm_not_found")
        return False
 # === 新增：8.1 升級/額外彈窗偵測與補掃蕩 ===
    print("   -> ⏳ 正在檢查是否有升級畫面 (等待 2 秒)...")
    # 這裡稍微停久一點，因為升級動畫通常比較慢
    if not wait_seconds_with_abort(2, "等待升級判定"):
        return False

    # 偵測是否有額外的 "confirm" (升級視窗)
    # 如果找到，find_and_click 會直接點擊它，並進入 if 區塊
    if find_and_click("confirm.png", custom_confidence=0.8):
        print("   -> 🆙 偵測到升級視窗！執行「補掃蕩」流程...")
        
        # 步驟 A: 點擊 OK (關閉升級後的獎勵顯示或其他視窗)
        # 這裡假設你的 OK 按鈕是 OK_02.png，如果升級畫面的 OK 長得不一樣，請更換圖片檔名
        wait_seconds_with_abort(2, "等待OK按鈕") 
        if not find_and_click("OK_02.png", custom_confidence=0.8):
            print("   -> ⚠️ 升級後找不到 OK 按鈕，嘗試繼續...")
        
        # 步驟 B: 重新執行掃蕩設定 (Swape -> Max -> Confirm)
        print("   -> 🔄 利用升級體力，重新設定掃蕩...")
        
        wait_seconds_with_abort(2, "等待回到關卡畫面")
        
        # 點擊 Swape
        if find_and_click("swape.png", custom_confidence=0.8):
            wait_seconds_with_abort(1, "等待Max")
            # 點擊 Max
            find_and_click("max.png", custom_confidence=0.8)
            wait_seconds_with_abort(1, "等待確認")
            # 點擊 Confirm
            find_and_click("confirm.png", custom_confidence=0.8)
            print("   -> ✅ 補掃蕩設定完成，等待結算...")
            
            # 這裡需要多等一下，因為重新掃蕩需要時間
            wait_seconds_with_abort(3, "等待補掃蕩結算")
        else:
            print("   -> ❌ 找不到 swape 按鈕，無法執行補掃蕩。")

    else:
        print("   -> 👌 未偵測到升級畫面，繼續正常流程。")
    # ==========================================
    
    
    # 9. 點擊 "OK_02" (OK)
    if not find_and_click("OK_02.png", custom_confidence=0.8):
        print("   -> ❌ 錯誤：找不到 'OK_02.png'。")
        save_debug_screenshot("ok_02_not_found")
        return False
    # 10. 點擊 "main_page" (主畫面)
    if not find_and_click("main_page.png", custom_confidence=0.8):
        print("   -> ❌ 錯誤：找不到 'main_page.png'。")
        save_debug_screenshot("main_page_not_found")
        return False
    return True

# --- 5. 主程式 ---

def main():
    
    print("🔍 正在尋找遊戲畫面...")
    
    print("\n=== OpenClaw V15 (Portable Paths) ===")
    print("特色：可攜式路徑、全螢幕偵測、防休眠")
    print(f"初始解析度: {pyautogui.size()}")
    not_found_streak = 0
    
    # 首先啟動遊戲
    if not launch_game_from_steam():
        print("🛑 遊戲啟動失敗，程式結束。")
        return # 或 sys.exit()

    # 啟動後，直接持續全螢幕找 Press to Start，直到成功
    if not wait_for_press_to_start(max_wait_seconds=120):
        print("🛑 等待 'Press to Start' 失敗，程式結束。")
        return
      
    



"""功能測試迴圈
while True:
    if find_only_strict("set.png", confidence=0.94, grayscale=True):
        print("✅ 找到 'set.png'，成功進入遊戲！")
        break  # 找到目標了，打破迴圈往下執行
    else:
        print("⏳ 還沒看到畫面，等待 2 秒後重試...")
        time.sleep(0.5)  # 找不到就等 2 秒再找一次
        # 這裡不用寫 continue，迴圈本來就會自動重頭開始

"""       
        

"""
    #刷關迴圈
    while True:
        if keyboard.is_pressed('q'):
            print("🛑 程式停止。")
            break

        # --- 遊戲內決策流程 ---
        time.sleep(0.3) # 在活躍狀態下降低CPU使用率
        action_taken = False

        if handle_dialog_windows():
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
                 screen_width, screen_height = pyautogui.size()
                 pyautogui.click(screen_width // 2, screen_height // 2)
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
                print("❓ 連續100次無動作，保存截圖後持續監控...")
                save_debug_screenshot("lost_track_long")
                not_found_streak = 0 # 重置計數器
"""
if __name__ == "__main__":
    main()
