import time
import pyautogui   
import time
import os

from tools import (
    IMAGE_FOLDER,
    find_only_strict,
    human_click,
    pyautogui,
    wait_for_image,
    log,
)

def get_image_path(image_name):
    possible_names = [image_name, image_name.upper(), image_name.lower()]
    if not image_name.lower().endswith((".png", ".jpg", ".jpeg")):
        possible_names.append(f"{image_name}.png")
    for name in possible_names:
        temp_path = os.path.join(IMAGE_FOLDER, name)
        if os.path.exists(temp_path):
            return temp_path
    return None


def _select_steam_account(target_account_images):
    wait_for_image("who.png", timeout=600.0)
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