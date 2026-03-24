import datetime
import importlib.util
import os
import random
import subprocess
import sys
import time
import ctypes
import ctypes.wintypes


def install_requirements():
    required = {
        "pyautogui": "pyautogui",
        "keyboard": "keyboard",
        "pillow": "PIL",
        "opencv-python": "cv2",
        "numpy": "numpy",
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
        os.execv(sys.executable, [sys.executable, *sys.argv])


install_requirements()

try:
    import cv2
    import keyboard
    import numpy as np
    import pyautogui
except ImportError:
    sys.exit(1)

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

IMAGE_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pictures")

if not os.path.isdir(IMAGE_FOLDER):
    raise RuntimeError(f"Image folder does not exist: {IMAGE_FOLDER}")


_LOGGER = None

WM_INPUTLANGCHANGEREQUEST = 0x0050
KLF_ACTIVATE = 0x00000001
ENGLISH_LAYOUT_ID = "00000409"
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002


def set_logger(logger):
    global _LOGGER
    _LOGGER = logger

def log(message):
    print(message)
    if _LOGGER is None:
        return
    try:
        if callable(_LOGGER):
            _LOGGER(message)
        else:
            _LOGGER.log(message)
    except Exception:
        pass


def _get_foreground_window():
    if not sys.platform.startswith("win"):
        return None
    try:
        return ctypes.windll.user32.GetForegroundWindow()
    except Exception:
        return None


def get_current_keyboard_layout():
    if not sys.platform.startswith("win"):
        return None

    try:
        hwnd = _get_foreground_window()
        thread_id = ctypes.windll.user32.GetWindowThreadProcessId(hwnd, None)
        return ctypes.windll.user32.GetKeyboardLayout(thread_id)
    except Exception:
        return None


def is_english_input():
    layout = get_current_keyboard_layout()
    if layout is None:
        return False
    language_id = layout & 0xFFFF
    return language_id == 0x0409


def switch_to_english_input():
    if not sys.platform.startswith("win"):
        return False

    try:
        user32 = ctypes.windll.user32
        hwnd = _get_foreground_window()
        if not hwnd:
            return False

        english_hkl = user32.LoadKeyboardLayoutW(ENGLISH_LAYOUT_ID, KLF_ACTIVATE)
        if not english_hkl:
            return False

        user32.PostMessageW(hwnd, WM_INPUTLANGCHANGEREQUEST, 0, english_hkl)
        user32.ActivateKeyboardLayout(english_hkl, 0)
        time.sleep(0.2)
        return is_english_input()
    except Exception:
        return False


def ensure_english_input(max_attempts=3):
    if is_english_input():
        return True

    for attempt in range(1, max_attempts + 1):
        if switch_to_english_input():
            log(f"   -> 已切換為英文輸入法（第 {attempt} 次嘗試）")
            return True
        time.sleep(0.15)

    log("   -> ⚠️ 無法確認已切換成英文輸入法，序號輸入可能失敗。")
    return False


def get_clipboard_text():
    # always return a string (empty on failure) so callers don't have to
    # special-case None values. original implementation returned None
    # in several failure paths which caused "實際='None'" logs when the
    # clipboard could not be opened.
    if not sys.platform.startswith("win"):
        return ""

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    if not user32.OpenClipboard(None):
        return ""

    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return ""
        pointer = kernel32.GlobalLock(handle)
        if not pointer:
            return ""
        try:
            return ctypes.wstring_at(pointer)
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def set_clipboard_text(text):
    if not sys.platform.startswith("win"):
        return False

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    data = str(text).replace("\r\n", "\n").replace("\r", "\n")
    size = (len(data) + 1) * ctypes.sizeof(ctypes.c_wchar)

    handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, size)
    if not handle:
        return False

    pointer = kernel32.GlobalLock(handle)
    if not pointer:
        kernel32.GlobalFree(handle)
        return False

    try:
        ctypes.memmove(pointer, ctypes.create_unicode_buffer(data), size)
    finally:
        kernel32.GlobalUnlock(handle)

    if not user32.OpenClipboard(None):
        kernel32.GlobalFree(handle)
        return False

    try:
        user32.EmptyClipboard()
        if not user32.SetClipboardData(CF_UNICODETEXT, handle):
            kernel32.GlobalFree(handle)
            return False
        handle = None
        return True
    finally:
        user32.CloseClipboard()


def type_text_with_verification(text, max_attempts=3, use_paste=True):
    original_clipboard = get_clipboard_text()
    # ensure we're always working with strings so comparisons are stable
    expected_text = str(text)

    for attempt in range(1, max_attempts + 1):
        ensure_english_input()
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.1)
        pyautogui.press("delete")
        time.sleep(0.1)

        if use_paste and set_clipboard_text(expected_text):
            pyautogui.hotkey("ctrl", "v")
        else:
            pyautogui.typewrite(expected_text, interval=0.05)

        time.sleep(0.2)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.1)
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.2)

        actual_text = get_clipboard_text() or ""
        # if we couldn't read the clipboard at all, skip verification rather
        # than repeatedly logging 'None' which is confusing.
        if actual_text == "":
            log("   -> ⚠️ 無法從剪貼簿讀取內容，略過輸入驗證。")
            if original_clipboard is not None:
                set_clipboard_text(original_clipboard)
            return True

        if actual_text == expected_text:
            if original_clipboard is not None:
                set_clipboard_text(original_clipboard)
            return True

        log(
            f"   -> ⚠️ 輸入驗證失敗，第 {attempt} 次重試。"
            f" 預期='{expected_text}'，實際='{actual_text}'"
        )

    if original_clipboard is not None:
        set_clipboard_text(original_clipboard)
    return False

def save_debug_screenshot(reason):
    debug_dir = os.path.join(IMAGE_FOLDER, "debug_screenshots")
    os.makedirs(debug_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = os.path.join(debug_dir, f"{reason}_{timestamp}.png")
    try:
        pyautogui.screenshot(path)
    except Exception:
        pass

def wake_up_gpu():
    try:
        x, y = pyautogui.position()
        pyautogui.moveTo(x + 1, y + 1)
        pyautogui.moveTo(x, y)
        pyautogui.press("shift")
    except Exception:
        pass

def read_image_safe(path):
    try:
        img_array = np.fromfile(path, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_UNCHANGED)
        if img is None:
            return None
        if img.ndim == 3 and img.shape[2] == 3:
            return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        if img.ndim == 3 and img.shape[2] == 4:
            return cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA)
        return img
    except Exception:
        return None

def _coerce_point(location):
    if location is None:
        return None
    if hasattr(location, "x") and hasattr(location, "y"):
        return int(location.x), int(location.y)
    return int(location[0]), int(location[1])

def human_click(location, clicks=1):
    point = _coerce_point(location)
    if point is None:
        return False

    original_failsafe_state = pyautogui.FAILSAFE
    try:
        pyautogui.FAILSAFE = False
        x, y = point
        offset_x = x + random.randint(-8, 8)
        offset_y = y + random.randint(-5, 5)

        screen_width, screen_height = pyautogui.size()
        offset_x = min(screen_width - 1, max(0, offset_x))
        offset_y = min(screen_height - 1, max(0, offset_y))

        pyautogui.moveTo(offset_x, offset_y, duration=random.uniform(0.01, 0.05))
        for _ in range(clicks):
            pyautogui.mouseDown(offset_x, offset_y)
            time.sleep(random.uniform(0.05, 0.15))
            pyautogui.mouseUp(offset_x, offset_y)
            if clicks > 1:
                time.sleep(random.uniform(0.05, 0.12))
        return True
    except Exception as exc:
        log(f"   -> ⚠️ human_click 發生錯誤: {exc}")
        return False
    finally:
        pyautogui.FAILSAFE = original_failsafe_state

def get_image_path(image_name):
    possible_names = [image_name, image_name.upper(), image_name.lower()]
    if not image_name.lower().endswith((".png", ".jpg", ".jpeg")):
        possible_names.append(f"{image_name}.png")
    for name in possible_names:
        temp_path = os.path.join(IMAGE_FOLDER, name)
        if os.path.exists(temp_path):
            return temp_path
    return None

def find_only(image_name, custom_confidence=None, region=None):
    target_path = get_image_path(image_name)
    if not target_path:
        return None

    needle_image = read_image_safe(target_path)
    if needle_image is None:
        return None

    base_conf = 0.85 if custom_confidence is None else custom_confidence
    confidence_levels = [base_conf, base_conf - 0.1, 0.7, 0.6]
    unique_confidences = sorted({c for c in confidence_levels if c >= 0.6}, reverse=True)

    for confidence in unique_confidences:
        try:
            kwargs = {
                "confidence": confidence,
                "grayscale": True,
            }
            if region is not None:
                kwargs["region"] = region
            location = pyautogui.locateCenterOnScreen(needle_image, **kwargs)
            if location:
                return location
        except pyautogui.PyAutoGUIException:
            continue
        except Exception:
            return None
    return None

def find_only_strict(image_name, confidence=0.97, region=None, grayscale=False):
    target_path = get_image_path(image_name)
    if not target_path:
        return None

    needle_image = read_image_safe(target_path)
    if needle_image is None:
        return None

    try:
        kwargs = {
            "confidence": confidence,
            "grayscale": grayscale,
        }
        if region is not None:
            kwargs["region"] = region
        return pyautogui.locateCenterOnScreen(needle_image, **kwargs)
    except pyautogui.PyAutoGUIException:
        return None
    except Exception:
        return None

def find_and_click(image_name, custom_confidence=None, clicks=1, region=None):
    location = find_only(image_name, custom_confidence=custom_confidence, region=region)
    if location:
        log(f"🎯 發現: {image_name} @ {location}")
        return human_click(location, clicks=clicks)
    return False

def get_center_region(width_ratio=0.8, height_ratio=0.8):
    screen_width, screen_height = pyautogui.size()
    region_width = int(screen_width * width_ratio)
    region_height = int(screen_height * height_ratio)
    left = (screen_width - region_width) // 2
    top = (screen_height - region_height) // 2
    return (left, top, region_width, region_height)

def get_region_around_point(x, y, width=900, height=420):
    screen_width, screen_height = pyautogui.size()
    left = max(0, int(x - width // 2))
    top = max(0, int(y - height // 2))
    right = min(screen_width, left + width)
    bottom = min(screen_height, top + height)
    return (left, top, right - left, bottom - top)

def wait_seconds_with_abort(seconds, title):
    log(f"\n⏳ {title} ({seconds} 秒)...")
    for remaining in range(seconds, 0, -1):
        if keyboard.is_pressed("q"):
            log("🛑 使用者中止。")
            return False
        if remaining % 5 == 0 or remaining <= 5:
            log(f"   -> 倒數 {remaining} 秒")
        time.sleep(1)
    return True

def click_screen_center():
    screen_width, screen_height = pyautogui.size()
    return human_click((screen_width // 2, screen_height // 2))

def handle_dialog_windows():
    center_region = get_center_region(0.82, 0.82)
    full_region = None

    def click_buttons(buttons, region):
        for image_name, confidence, clicks in buttons:
            if find_and_click(image_name, custom_confidence=confidence, clicks=clicks, region=region):
                log(f"   -> 已處理對話框: {image_name}")
                return True
        return False

    warn_buttons = [("warn.png", 0.88, 1)]
    followup_buttons = [
        ("yes.png", 0.9, 1),
        ("yes_02.PNG", 0.9, 1),
        ("confirm.png", 0.9, 1),
        ("ok.png", 0.92, 1),
        ("OK.png", 0.92, 1),
        ("OK03.png", 0.92, 1),
        ("close.png", 0.92, 1),
        ("close_02.png", 0.92, 1),
        ("close_03.png", 0.92, 1),
        ("close_06.png", 0.9, 1),
        ("close_07.png", 0.9, 1),
    ]
    common_buttons = [
        ("confirm.png", 0.9, 1),
        ("ok.png", 0.92, 1),
        ("OK.png", 0.92, 1),
        ("OK03.png", 0.92, 1),
        ("close.png", 0.92, 1),
        ("close_02.png", 0.92, 1),
        ("close_03.png", 0.92, 1),
        ("close_06.png", 0.9, 1),
        ("close_07.png", 0.9, 1),
    ]

    if click_buttons(warn_buttons, center_region):
        time.sleep(0.35)
        if not click_buttons(followup_buttons, center_region):
            click_buttons(followup_buttons, full_region)
        return True

    if click_buttons(common_buttons, center_region):
        return True
    if click_buttons(common_buttons, full_region):
        return True
    return False

def wait_for_press_to_start(
    max_wait_seconds=120,
    center_click_interval=60.0,
    post_click_verify_seconds=10.0,
):
    log("\n⏳ 全螢幕持續偵測 'press_to_start.png'（含中央點擊備援）...")
    start_time = time.time()
    last_center_click_time = 0.0
    last_progress_log_time = 0.0
    game_sign_checked = False
    game_sign_region = (77,1020,1689,59)
    while time.time() - start_time < max_wait_seconds:
        if keyboard.is_pressed("q"):
            log("🛑 使用者中止。")
            return False

        if not game_sign_checked and time.time() - start_time >= 15:
            game_sign_checked = True
            game_sign_location = find_only(
                "game_sign_02.png",
                custom_confidence=0.85,
                region=game_sign_region,
            )
            if game_sign_location:
                log("   -> 偵測到 'game_sign_02.png'，先點擊一次。")
                human_click(game_sign_location)
                time.sleep(0.5)


        if handle_dialog_windows():
            time.sleep(0)
            continue
        if find_only("monthy_card_close.png",custom_confidence=0.9,region=(1804,96,93,100)):
            human_click((1804+93//2,96+100//2))

        if find_only_strict("set.png", confidence=0.94, grayscale=True):
            log("✅ 偵測到遊戲內介面元素，視為已成功進入。")
            return True
        if find_only("set_02.png", custom_confidence=0.94):
            log("✅ 偵測到遊戲內介面元素，視為已成功進入。")
            return True

        if find_and_click("press_to_start.png", custom_confidence=0.85):
            log("✅ 已點擊 'Press to Start'，確認是否成功進入...")
            verify_deadline = time.time() + post_click_verify_seconds
            while time.time() < verify_deadline:
                if find_only_strict("set.png", confidence=0.94, grayscale=True):
                    log("✅ 按下後已進入遊戲。")
                    return True
                if handle_dialog_windows():
                    time.sleep(0.6)
                time.sleep(0.3)
            log("   -> 已點擊但尚未進入，繼續偵測...")

        now = time.time()
        if now - last_center_click_time >= center_click_interval:
            log("   👉 未找到 'Press to Start'，點擊螢幕中央嘗試喚醒流程...")
            click_screen_center()
            time.sleep(0.8)
            if handle_dialog_windows():
                time.sleep(0.8)
            last_center_click_time = now
            time.sleep(0.8)
            continue

        if now - last_progress_log_time >= 5:
            remaining = int(max_wait_seconds - (now - start_time))
            log(f"   -> 尚未找到 'Press to Start'，持續偵測中... (剩餘 {remaining} 秒)")
            last_progress_log_time = now
            wake_up_gpu()

        time.sleep(0.4)

    log("❌ 等待 'Press to Start' 超時。")
    save_debug_screenshot("press_to_start_timeout")
    return False

def wait_for_image(image_name, timeout=15.0, custom_confidence=None, try_click_name=None,clicks=1):
    image_targets = [image_name] if isinstance(image_name, str) else list(image_name)
    target_names_str = ", ".join(image_targets)
    log(f"   ⏳ 等待畫面: {target_names_str} (最多等 {timeout} 秒)...")

    start_time = time.time()
    while time.time() - start_time < timeout:
        # 1. 優先檢查要等待的目標圖片是否出現
        for img in image_targets:
            location = find_only(img, custom_confidence)
            if location:
                elapsed = time.time() - start_time
                log(f"   ✅ 畫面出現了！({img}) (耗時 {elapsed:.1f} 秒)")
                return True
        
        # 2. 如果這一輪沒看到目標圖片，且有指定 try_click_name，就嘗試點擊它
        if try_click_name is not None:
            # 這裡假設 find_and_click 會自己尋找並點擊，如果找不到也不會讓程式崩潰
            find_and_click(try_click_name, clicks=clicks)

        # 3. 稍等一下再進行下一次尋找
        time.sleep(0.5)

    log(f"   ❌ 等待超時 ({timeout} 秒)，沒看到 {target_names_str}！")
    return False

def try_click(x, y, width, height, clicks=1):
    log(f"   -> 嘗試點擊區域: ({x}, {y}, {width}, {height})")
    try:
        safe_margin_x = int(width * 0.2)
        safe_margin_y = int(height * 0.2)
        click_x = x + random.randint(safe_margin_x, width - safe_margin_x)
        click_y = y + random.randint(safe_margin_y, height - safe_margin_y)
        return human_click((click_x, click_y), clicks=clicks)
    except Exception as exc:
        log(f"   -> ⚠️ 點擊區域時發生錯誤: {exc}")
        return False

def run_image_steps(
    steps, 
    wait_timeout=120, 
    screenshot_prefix="step", 
    success_message=None,
    max_retries=2,
    retry_delay=2.0,
):
    """
    執行一系列圖像識別和點擊步驟，支援自動重試機制。
    
    參數:
    - steps: 步驟列表
    - wait_timeout: 等待畫面的超時時間 (秒)
    - screenshot_prefix: 截圖前綴
    - success_message: 成功時的訊息
    - max_retries: 每個步驟失敗時重試次數 (預設: 2)
    - retry_delay: 重試前等待時間，會指數增長 (預設: 2.0 秒)
    """
    for step_index, step in enumerate(steps):
        if callable(step):
            log(f"   -> 執行函式: {step.__name__}")
            if not step():
                log(f"   -> ❌ 錯誤：函式 '{step.__name__}' 執行失敗。")
                if screenshot_prefix:
                    save_debug_screenshot(f"{screenshot_prefix}_failed_{step.__name__}")
                return False
            continue

        if len(step) == 3:
            image_name, confidence, try_click_name = step
            fallback_rect = None
        elif len(step) >= 7:
            image_name, confidence, try_click_name, x, y, width, height = step[:7]
            fallback_rect = (x, y, width, height)
        else:
            log(f"   -> ❌ 錯誤：步驟參數數量不正確 {step}")
            return False

        # 重試邏輯
        for attempt in range(max_retries + 1):
            log(f"   -> 嘗試點擊: {image_name} (嘗試 {attempt + 1}/{max_retries + 1})")
            
            if wait_for_image(image_name, timeout=wait_timeout,try_click_name=try_click_name):
                if find_and_click(image_name, custom_confidence=confidence):
                    log(f"   -> ✅ 成功點擊 '{image_name}'")
                   

                else:
                    # 找到畫面但點擊失敗，嘗試備用位置
                    if fallback_rect:
                        log(f"   -> ⚠️ 無法點擊圖像，嘗試備用位置 {fallback_rect}")
                        try_click(*fallback_rect)

                    else:
                        # 沒有備用位置，需要重試
                        if attempt < max_retries:
                            wait_delay = retry_delay * (2 ** attempt)  # 指數退避
                            log(f"   -> 🔄 點擊失敗，{wait_delay:.1f} 秒後重試...")
                            time.sleep(wait_delay)
                        else:
                            log(f"   -> ❌ 錯誤：找不到或無法點擊 '{image_name}' (已重試 {max_retries} 次)。")
                            if screenshot_prefix:
                                stem = os.path.splitext(os.path.basename(image_name))[0]
                                save_debug_screenshot(f"{screenshot_prefix}_no_{stem}")
                            return False
            else:
                # 畫面未出現（超時）
                if attempt < max_retries:
                    wait_delay = retry_delay * (2 ** attempt)  # 指數退避
                    log(f"   -> 🔄 畫面未出現，{wait_delay:.1f} 秒後重試...")
                    time.sleep(wait_delay)
                else:
                    log(f"   -> ❌ 錯誤：等待超時，找不到 '{image_name}' (已重試 {max_retries} 次)。")
                    if screenshot_prefix:
                        stem = os.path.splitext(os.path.basename(image_name))[0]
                        save_debug_screenshot(f"{screenshot_prefix}_timeout_{stem}")
                    return False

    if success_message:
        log(success_message)
    return True

def human_scroll(target_x, target_y, total_scroll, direction="down"):
    log(f"👉 準備移動至 ({target_x}, {target_y}) 並向{direction}滾動...")

    offset_x = target_x + random.randint(-15, 15)
    offset_y = target_y + random.randint(-15, 15)
    move_duration = random.uniform(0.3, 0.8)

    pyautogui.moveTo(offset_x, offset_y, duration=move_duration, tween=pyautogui.easeOutQuad)
    time.sleep(random.uniform(0.1, 0.3))

    multiplier = -1 if direction == "down" else 1
    chunks = random.randint(2, 4)
    base_scroll_per_chunk = total_scroll // chunks

    log(f"   ⚙️ 分 {chunks} 段滾動...")
    for _ in range(chunks):
        actual_scroll = base_scroll_per_chunk + random.randint(-20, 20)
        pyautogui.scroll(actual_scroll * multiplier)
        time.sleep(random.uniform(0.05, 0.15))

    time.sleep(random.uniform(0.2, 0.5))
    log("   ✅ 滾動完成！")

def scroll_at_image(image_name, total_scroll, direction="down", custom_confidence=None, region=None):
    log(f"🔍 尋找目標: {image_name} 以執行滾動...")
    location = find_only(image_name, custom_confidence, region)
    if not location:
        log(f"❌ 找不到圖片 {image_name}，取消滾動操作。")
        return False

    x, y = _coerce_point(location)
    log(f"🎯 成功找到目標，座標: ({x}, {y})")
    human_scroll(x, y, total_scroll, direction)
    return True

def _select_steam_account(target_account_images):
    wait_for_image("who.png", timeout=60.0,try_click_name="steam_icon.png",clicks=2)
    log("   -> 開始尋找 Steam 帳號...")

    account_found_and_clicked = False
    who_buttons_found = False
    original_failsafe_state = pyautogui.FAILSAFE

    try:
        who_image_path = get_image_path("who.png")
        if not who_image_path:
            log("   -> ℹ️ 未在資料夾中找到 'who.png' 圖片，跳過帳號選擇。")
            return True

        pyautogui.FAILSAFE = False
        who_buttons = list(pyautogui.locateAllOnScreen(who_image_path, confidence=0.99, grayscale=True))
        who_buttons_found = len(who_buttons) > 0
        who_buttons.sort(key=lambda box: box.left)

        if not who_buttons:
            log("   -> ℹ️ 未在畫面上找到 'who.png' 按鈕，假設 Steam 會自動登入。")
            return True

        log(f"   -> 找到 {len(who_buttons)} 個潛在帳號，開始從左到右檢查...")
        match_profiles = [
            ("strict_color", 0.97, False, 2),
            ("balanced_color", 0.94, False, 2),
            ("balanced_gray", 0.92, True, 1),
        ]

        for button_box in who_buttons:
            button_center = pyautogui.center(button_box)
            pyautogui.moveTo(button_center.x, button_center.y, duration=0.2)
            time.sleep(0.65)

            hover_region = get_region_around_point(button_center.x, button_center.y, width=1200, height=520)
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
                            grayscale=profile_gray,
                        ):
                            matched = True
                            break
                    if matched:
                        stable_hits += 1
                    time.sleep(0.12)

                log(
                    f"   -> 帳號比對 {profile_name}: "
                    f"hits={stable_hits}/2, conf={profile_conf}, gray={profile_gray}"
                )

                if stable_hits >= required_hits:
                    account_matched = True
                    break

            if account_matched:
                log(f"   -> 找到目標帳號！正在點擊位於 ({button_center.x}, {button_center.y}) 的按鈕...")
                human_click(button_center)
                account_found_and_clicked = True
                break

    except Exception as exc:
        log(f"   -> ⚠️ 尋找帳號時發生錯誤: {exc}")
    finally:
        pyautogui.FAILSAFE = original_failsafe_state

    if not account_found_and_clicked and who_buttons_found:
        log("   -> ⚠️ 檢查了所有帳號，但未找到目標帳號截圖。請確認截圖是否正確。")
    elif not account_found_and_clicked:
        log("   -> ℹ️ 未找到任何帳號按鈕，假設 Steam 會自動登入。")

    return True

def _finish_steam_launch():
    log("   -> 等待 Steam 登入與載入主介面...")
    wait_for_image("steam_library.png", timeout=60.0)

    log("   -> 正在嘗試關閉 Steam 彈出廣告...")
    if find_and_click("steam_close_ad.png", custom_confidence=0.85):
        log("   -> 已關閉廣告視窗。")
        time.sleep(0)
    else:
        log("   -> 未發現廣告視窗。")

    log("   -> 正在點擊「收藏庫」...")
    wait_for_image("steam_library.png", timeout=60.0)
    if not find_and_click("steam_library.png", custom_confidence=0.8):
        log("   -> ❌ 錯誤：找不到「收藏庫」按鈕 'steam_library.png'。")
        return False
    time.sleep(0)

    log("   -> 正在從收藏庫選擇 'Rise of Eros'...")
    wait_for_image("rise_of_eros_list.png", timeout=60.0)
    if not find_and_click("rise_of_eros_list.png", custom_confidence=0.9):
        log("   -> ❌ 錯誤：在收藏庫中找不到遊戲 'rise_of_eros_list.png'。")
        return False
    time.sleep(0)

    log("   -> 正在點擊「開始遊戲」按鈕...")
    wait_for_image("steam_play_btn.png", timeout=60.0)
    if not find_and_click("steam_play_btn.png", custom_confidence=1):
        log("   -> ❌ 錯誤：找不到「開始遊戲」按鈕 'steam_play_btn.png'。")
        return False
    time.sleep(0)

    log("✅ === 遊戲啟動指令已發送！ ===")
    return True

def launch_game_from_steam(name="loopcraft001.png"):
    log("\n🚀 === 開始從 Steam 啟動遊戲 ===")
    log("   -> 正在點擊右下角以顯示桌面...")
    try:
        pyautogui.FAILSAFE = False
        screen_width, screen_height = pyautogui.size()
        pyautogui.click(screen_width - 1, screen_height - 1)
        time.sleep(1)
    except Exception as exc:
        log(f"   -> ⚠️ 點擊右下角時發生錯誤: {exc}")
    finally:
        pyautogui.FAILSAFE = True

    log("   -> 正在尋找並雙擊 Steam 圖示...")
    if not find_and_click("steam_icon.png", custom_confidence=0.8, clicks=2):
        log("   -> ❌ 錯誤：在桌面或工作列上找不到 'steam_icon.png'。")
        return False

    if not _select_steam_account([name]):
        return False
    return _finish_steam_launch()

def change_game_account_from_steam(name="loopcraft001.png"):
    log("\n🚀 === 開始切換 Steam 帳號並啟動遊戲 ===")

    log("   -> 正在尋找 draw 圖示...")
    if not find_and_click("draw.png", custom_confidence=0.8):
        log("   -> ❌ 錯誤：在桌面或工作列上找不到 'draw.png'。")
        try_click(1677, 12, 25, 31)
        return False

    log("   -> 正在尋找 change_account 圖示...")
    if not find_and_click("change_account.png", custom_confidence=0.8):
        log("   -> ❌ 錯誤：在桌面或工作列上找不到 'change_account.png'。")
        return False

    log("   -> 正在尋找 continue 圖示...")
    if not find_and_click("continue.png", custom_confidence=0.8):
        log("   -> ❌ 錯誤：在桌面或工作列上找不到 'continue.png'。")
        try_click(686, 408, 119, 31)
        return False

    if not _select_steam_account([name]):
        return False
    return _finish_steam_launch()

def find_set():
    time.sleep(2)
    log("   -> 嘗試點擊: set.png")
    if find_and_click("set.png", custom_confidence=0.8):
        return True

    log("   -> ❌ 錯誤：找不到 'set.png'。")
    log("   -> 嘗試先點擊 'main_page.png' 再點選 'set.png'")

    if not find_and_click("main_page.png", custom_confidence=0.8):
        log("   -> ❌ 錯誤：找不到 'main_page.png'。")
        save_debug_screenshot("main_page_not_found")
        return False

    time.sleep(2)
    if not find_and_click("set.png", custom_confidence=0.8):
        log("   -> ❌ 錯誤：找不到 'set.png'。")
        save_debug_screenshot("set_not_found")
        return False
    return True

def leave_game():
    log("\n🚪 === 開始執行離開遊戲流程 ===")
    steps = [
        find_set,
        ("quit_game.png", 0.85, 1, 1484, 950, 331, 77),
        ("confirm.png", 0.88, 10, 915, 680, 446, 77),
        ("steam_sign.png", 0.85, 1),
        ("quit.png", 0.85, 0),
    ]
    return run_image_steps(
        steps,
        wait_timeout=120,
        screenshot_prefix="leave_game",
        success_message="✅ 離開遊戲流程完成。",
    )

def get_daily_rewards():
    log("\n🎁 === 開始領取獎勵流程 ===")
    steps = [
        ("rewards.png", 0.85, 1),
        ("get_all.png", 0.85, 1),
        ("ok.png", 0.88, 10),
        ("backward_02.png", 0.85, 1),
    ]
    return run_image_steps(
        steps,
        wait_timeout=120,
        screenshot_prefix="daily_rewards",
        success_message="✅ 完成領獎流程。",
    )


__all__ = [
    "IMAGE_FOLDER",
    "change_game_account_from_steam",
    "click_screen_center",
    "cv2",
    "ensure_english_input",
    "find_and_click",
    "find_only",
    "find_only_strict",
    "find_set",
    "get_center_region",
    "get_clipboard_text",
    "get_daily_rewards",
    "get_image_path",
    "get_region_around_point",
    "handle_dialog_windows",
    "human_click",
    "human_scroll",
    "install_requirements",
    "is_english_input",
    "keyboard",
    "launch_game_from_steam",
    "leave_game",
    "log",
    "np",
    "pyautogui",
    "read_image_safe",
    "run_image_steps",
    "save_debug_screenshot",
    "scroll_at_image",
    "set_clipboard_text",
    "set_logger",
    "type_text_with_verification",
    "try_click",
    "wait_for_image",
    "wait_for_press_to_start",
    "wait_seconds_with_abort",
    "wake_up_gpu",
]
