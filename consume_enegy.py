import datetime
import json
import os
import random
import time
import sys

# --- 新增這段將 Print 同步到 G 槽的程式碼 ---
log_dir = r"G:\我的雲端硬碟\auto_bot_log"
os.makedirs(log_dir, exist_ok=True) # 確保資料夾存在，避免報錯

class DriveLogger:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log_file = open(filename, "a", encoding="utf-8")
    def write(self, message):
        self.terminal.write(message)
        self.log_file.write(message)
        self.log_file.flush() # 確保每一行都馬上存檔
    def flush(self):
        self.terminal.flush()
        self.log_file.flush()

sys.stdout = DriveLogger(os.path.join(log_dir, "scheduled_run.txt"))
sys.stderr = sys.stdout # 讓紅字錯誤訊息也一起存進去
# ------------------------------------------

from tools import (
    IMAGE_FOLDER,
    change_game_account_from_steam,
    find_and_click,
    find_only,
    find_only_strict,
    human_click,
    launch_game_from_steam,
    leave_game,
    pyautogui,
    save_debug_screenshot,
    wait_for_image,
    wait_for_press_to_start,
    wait_seconds_with_abort,
    try_click,
    ensure_english_input,
    handle_dialog_windows,
    run_image_steps,
    type_text_with_verification,
)


SHOP_WHITELIST_FOLDER = os.path.join(IMAGE_FOLDER, "shop_whitelist")
SHOP_PURCHASE_HISTORY_FILE = os.path.join(SHOP_WHITELIST_FOLDER, "_bought_once.json")
REWARD_CODE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reward_code.txt")


def normalize_shop_item_name(item_filename):
    return os.path.basename(item_filename).strip().lower()


def load_shop_purchase_history():
    default_history = {"version": 1, "accounts": {}}
    if not os.path.exists(SHOP_PURCHASE_HISTORY_FILE):
        return default_history

    try:
        with open(SHOP_PURCHASE_HISTORY_FILE, "r", encoding="utf-8") as file:
            loaded = json.load(file)
    except Exception as exc:
        print(f"   -> ⚠️ 讀取購買紀錄失敗，改用空白紀錄: {exc}")
        return default_history

    if not isinstance(loaded, dict):
        return default_history
    if "accounts" not in loaded or not isinstance(loaded.get("accounts"), dict):
        loaded["accounts"] = {}
    if "version" not in loaded:
        loaded["version"] = 1
    return loaded


def save_shop_purchase_history(history):
    os.makedirs(SHOP_WHITELIST_FOLDER, exist_ok=True)
    temp_file = f"{SHOP_PURCHASE_HISTORY_FILE}.tmp"
    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(history, file, ensure_ascii=False, indent=2)
    os.replace(temp_file, SHOP_PURCHASE_HISTORY_FILE)


def get_account_shop_history(history, account_key):
    accounts = history.setdefault("accounts", {})
    return accounts.setdefault(account_key, {})


def mark_shop_item_bought(history, account_key, item_filename):
    account_history = get_account_shop_history(history, account_key)
    normalized_name = normalize_shop_item_name(item_filename)
    account_history[normalized_name] = {
        "filename": item_filename,
        "bought_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    save_shop_purchase_history(history)


def open_shop_page():
    print("\n🛒 === 嘗試進入商店 ===")
    if not find_and_click("store.png", custom_confidence=0.8):
        print("   -> ⚠️ 找不到 'store.png'，本輪略過商店購買。")
        return False

    time.sleep(2.0)
    if find_only("shops.png", custom_confidence=0.75):
        print("   -> ✅ 已進入商店畫面。")
    else:
        print("   -> ⚠️ 未偵測到 'shops.png'，仍嘗試以白名單掃描購買。")
    return True


def scroll_shop_page(direction="down", amount=600):
    center_x, center_y = pyautogui.size()
    pyautogui.moveTo(center_x // 2, center_y // 2, duration=random.uniform(0.2, 0.4))
    multiplier = -1 if direction == "down" else 1
    pyautogui.scroll(amount * multiplier)


def buy_daily_shop_items_once(account_key, max_scrolls=2):
    print(f"\n🛍️ === 每日商店白名單購買（帳號: {account_key}）===")

    if not open_shop_page():
        return 0

    if not os.path.exists(SHOP_WHITELIST_FOLDER):
        os.makedirs(SHOP_WHITELIST_FOLDER)
        print(f"   -> ⚠️ 找不到白名單資料夾，已建立: {SHOP_WHITELIST_FOLDER}")
        return 0

    whitelist_items = sorted(
        filename
        for filename in os.listdir(SHOP_WHITELIST_FOLDER)
        if filename.lower().endswith((".png", ".jpg", ".jpeg"))
    )
    if not whitelist_items:
        print(f"   -> ⚠️ 白名單為空，請放入商品截圖: {SHOP_WHITELIST_FOLDER}")
        find_and_click("main_page.png", custom_confidence=0.8)
        return 0

    purchase_history = load_shop_purchase_history()
    account_history = get_account_shop_history(purchase_history, account_key)
    pending_items = [
        filename for filename in whitelist_items if normalize_shop_item_name(filename) not in account_history
    ]

    if not pending_items:
        print("   -> ℹ️ 白名單商品都已買過，本輪不再購買。")
        find_and_click("main_page.png", custom_confidence=0.8)
        return 0

    print(f"   -> 本輪待購買 {len(pending_items)} 項: {', '.join(pending_items)}")
    items_bought = 0
    scrolls_done = 0

    while scrolls_done <= max_scrolls and pending_items:
        bought_something_on_this_screen = False

        for item_filename in list(pending_items):
            relative_path = os.path.join("shop_whitelist", item_filename)
            location = find_only_strict(relative_path, confidence=0.7, grayscale=False)
            if not location:
                continue

            print(f"   -> 🎯 找到白名單商品: {item_filename}")
            human_click(location)
            time.sleep(1.0)

            if find_and_click("buy_confirm_btn.png", custom_confidence=0.8):
                print("   -> ✅ 已完成購買並寫入一次性紀錄。")
                items_bought += 1
                mark_shop_item_bought(purchase_history, account_key, item_filename)
                pending_items.remove(item_filename)
                time.sleep(2.0)
                find_and_click("ok_03.png", custom_confidence=0.8)
                time.sleep(1.2)
            else:
                print("   -> ⚠️ 未找到確認按鈕，可能已售完或貨幣不足。")
                pyautogui.click(960, 200)
                time.sleep(1.0)

            bought_something_on_this_screen = True
            break

        if pending_items and not bought_something_on_this_screen:
            if scrolls_done < max_scrolls:
                print(f"   -> ⬇️ 本屏未命中，向下滾動繼續搜尋 ({scrolls_done + 1}/{max_scrolls})")
                scroll_shop_page(direction="down", amount=600)
                time.sleep(1.5)
                scrolls_done += 1
            else:
                print("   -> ℹ️ 已到達最大滾動次數，停止本輪商店掃描。")
                break

    if scrolls_done > 0:
        for _ in range(scrolls_done):
            scroll_shop_page(direction="up", amount=650)
            time.sleep(0.5)

    if pending_items:
        print(f"   -> 尚未購得 {len(pending_items)} 項（下次會再嘗試）: {', '.join(pending_items)}")
    print(f"✅ 商店購買結束，本輪成功購買 {items_bought} 項。")

    find_and_click("main_page.png", custom_confidence=0.8)
    time.sleep(1.0)
    return items_bought

def consume_energy(battle):
    print("\n💪 === 開始執行消耗體力流程 ===")
    wait_for_image("ongoing_activity.png", timeout=60.0)
    if not find_and_click("ongoing_activity.png", custom_confidence=0.8):
        print("   -> ❌ 錯誤：找不到 'ongoing_activity.png'。")
        save_debug_screenshot("no_ongoing_activity")
        return False

    wait_for_image("activity.png", timeout=5.0,try_click_name="ongoing_activity.png",try_click_point=(287,574))
    if not find_and_click("activity.png", custom_confidence=0.8, clicks=2):
        print("   -> ❌ 錯誤：找不到 'activity.png'。")
        save_debug_screenshot("no_activity_button")
        
    print("   -> 檢查是否有活動教學或多頁面需要切換...")
    max_clicks = 6  # 設定最大嘗試次數，防止無限迴圈
    click_count = 0

    while find_only("right_arrow.png", custom_confidence=0.8,region=(1078,963,70,70)) and click_count < max_clicks:
        print(f"   -> 發現右箭頭，嘗試點擊以切換活動頁面... (第 {click_count + 1} 次)")
        find_and_click("right_arrow.png", custom_confidence=0.8,region=(1078,963,70,70))
        time.sleep(1.0)  # 加上短暫等待，讓遊戲播放翻頁動畫
        click_count += 1

    if click_count >= max_clicks:
        print("   -> ⚠️ 警告：點擊右箭頭次數達上限，可能卡在教學畫面或發生異常！")
        # 這裡可以視情況決定是否要 return False 或是截圖存檔
        # save_debug_screenshot("stuck_at_tutorial")

    wait_for_image("battle.png", timeout=5.0,try_click_name="activity.png",try_click_point=(56,578))
    if not find_and_click("battle.png", custom_confidence=0.85):
        print("   -> ❌ 錯誤：找不到 'battle.png'。")
        save_debug_screenshot("no_battle_button")
        
    wait_for_image("battle7.png", timeout=15.0,try_click_name="battle.png",try_click_point=(56,578))
    
    
    if battle == 8:
        wait_for_image("battle7.png", timeout=5.0,try_click_name="battle.png",try_click_point=(56,578))
        print("   -> 嘗試點擊 'battle7' 按鈕右方的關卡...")
        battle_location = find_only("battle7.png", custom_confidence=0.9)
        if not battle_location:
            print("   -> ❌ 錯誤：找不到 'battle7.png'。")
            save_debug_screenshot("battle7_not_found")
            return False
        target_x = battle_location.x + random.randint(400, 600)
        target_y = battle_location.y
        print(f"   -> 計算出的關卡座標: ({target_x}, {target_y})")
        human_click((target_x, target_y))
    
    
    elif battle == 7:
        wait_for_image("battle7.png", timeout=5.0,try_click_name="battle.png",try_click_point=(56,578))
        print("   -> 嘗試點擊 'battle7' 按鈕右方的關卡...")
        find_and_click("battle7.png", custom_confidence=0.9)

    wait_for_image("swape.png", timeout=10.0,try_click_name="battle8.png")
    if not find_and_click("swape.png", custom_confidence=0.8):
        print("   -> ⚠️ 警告：找不到 'swape.png'，腳本將繼續。")
        save_debug_screenshot("swape_not_found")

    wait_for_image("max.png", timeout=10.0,try_click_name="swape.png")
    if not find_and_click("max.png", custom_confidence=0.8):
        print("   -> ❌ 錯誤：找不到 'max.png'。")
        save_debug_screenshot("max_not_found")
        return False
    if not find_and_click("confirm.png", custom_confidence=0.8):
        print("   -> ❌ 錯誤：找不到 'confirm.png'。")
        save_debug_screenshot("confirm_not_found")
        return False

    print("   -> ⏳ 正在檢查是否有升級畫面...")
    if not wait_seconds_with_abort(2, "等待升級判定"):
        return False

    if find_and_click("confirm.png", custom_confidence=0.8):
        print("   -> 🆙 偵測到升級視窗！執行補掃蕩流程...")
        wait_for_image("OK_02.png", timeout=10.0,try_click_name="confirm.png")
        if not find_and_click("OK_02.png", custom_confidence=0.8):
            print("   -> ⚠️ 升級後找不到 OK 按鈕，嘗試繼續...")

        print("   -> 🔄 利用升級體力，重新設定掃蕩...")
        wait_for_image("swape.png", timeout=10.0,try_click_name="OK_02.png")
        if find_and_click("swape.png", custom_confidence=0.8):
            wait_for_image("max.png", timeout=10.0,try_click_name="swape.png")
            find_and_click("max.png", custom_confidence=0.8)
            wait_for_image("confirm.png", timeout=10.0,try_click_name="max.png")
            find_and_click("confirm.png", custom_confidence=0.8)
            print("   -> ✅ 補掃蕩設定完成，等待結算...")
            wait_seconds_with_abort(2, "等待補掃蕩結算")
        else:
            print("   -> ❌ 找不到 swape 按鈕，無法執行補掃蕩。")
    else:
        print("   -> 👌 未偵測到升級畫面，繼續正常流程。")

    if not find_and_click("OK_02.png", custom_confidence=0.8):
        print("   -> ❌ 錯誤：找不到 'OK_02.png'。")
        try_click(735,869,447,80)
        save_debug_screenshot("ok_02_not_found")
        return False
    
    wait_for_image("mission_01.png", timeout=10.0,try_click_name="OK_02.png")
    if not find_and_click("mission_01.png", custom_confidence=0.8, clicks=2):
        print("   -> ❌ 錯誤：找不到 'mission_01.png'。")
        save_debug_screenshot("mission_01_not_found")
        return False
    
    wait_for_image("daily.png", timeout=10.0,try_click_name="mission_01.png")
    if not find_and_click("daily.png", custom_confidence=0.8, clicks=2):
        print("   -> ❌ 錯誤：找不到 'daily.png'。")
        save_debug_screenshot("daily_not_found")
        return False
    
    wait_for_image(["accept_all.png", "no_accept_all.png"], timeout=10.0,try_click_name="daily.png")
    if not find_and_click("accept_all.png", custom_confidence=0.8, clicks=2):
        print("   -> ❌ 錯誤：找不到 'accept_all.png'。")
        if find_only("no_accept_all.png", custom_confidence=0.75):
            find_and_click("main_page.png", custom_confidence=0.8)
            return True
        save_debug_screenshot("accept_all_not_found")
        return False
    wait_for_image("OK.png", timeout=10.0,try_click_name="accept_all.png")
    if not find_and_click("OK.png", custom_confidence=0.8):
        print("   -> ❌ 錯誤：找不到 'OK.png'。")
        save_debug_screenshot("OK_not_found")
        return False
    wait_for_image("main_page.png", timeout=10.0,try_click_name="OK.png")
    if not find_and_click("main_page.png", custom_confidence=0.8):
        print("   -> ❌ 錯誤：找不到 'main_page.png'。")
        save_debug_screenshot("main_page_not_found")
        return False
    return True

def parse_reward_code_file():
    try:
        with open(REWARD_CODE_FILE, "r", encoding="utf-8") as file:
            content = file.read()
    except FileNotFoundError:
        print(f"   -> 找不到 {REWARD_CODE_FILE} 文件")
        return [], {}, []
    except Exception as exc:
        print(f"   -> 讀取 reward_code.txt 失敗: {exc}")
        return [], {}, []

    available_codes = []
    history = {}
    account_order = []
    in_history = False
    collecting_codes = False
    current_account = None

    def add_history_code(account, code):
        if not code:
            return
        codes = history.setdefault(account, [])
        if code not in codes:
            codes.append(code)

    normalized_content = content.replace("\r\n", "\n").replace("\r", "\n")
    for raw_line in normalized_content.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        lower_line = line.lower()

        if lower_line.startswith("account :"):
            in_history = True
            collecting_codes = False
            account_name = line.split(":", 1)[1].strip()
            if not account_name:
                current_account = None
                continue
            current_account = account_name
            if current_account not in history:
                history[current_account] = []
                account_order.append(current_account)
            continue

        if lower_line.startswith("already changed:"):
            in_history = True
            collecting_codes = True
            code_part = line.split(":", 1)[1].strip()
            if current_account and code_part:
                add_history_code(current_account, code_part)
            continue

        if not in_history:
            for token in [t.strip() for t in line.split(",") if t.strip()]:
                available_codes.append(token)
        elif collecting_codes and current_account:
            for token in [t.strip() for t in line.split(",") if t.strip()]:
                add_history_code(current_account, token)

    return available_codes, history, account_order


def write_reward_code_file(available_codes, history, account_order):
    lines = []
    for code in available_codes:
        if code:
            lines.append(code)

    if history:
        if lines:
            lines.append("")
        for account in account_order:
            lines.append(f"account :{account}")
            lines.append("already changed:")
            for code in history.get(account, []):
                lines.append(code)
            lines.append("")
        if lines and lines[-1] == "":
            lines.pop()

    content = "\n".join(lines)
    if content:
        content += "\n"

    with open(REWARD_CODE_FILE, "w", encoding="utf-8") as file:
        file.write(content)


def load_reward_codes():
    available_codes, _, _ = parse_reward_code_file()
    return available_codes


import os

def parse_reward_code_file(filename="reward_code.txt"):
    available_codes = []
    history = {}
    account_order = []
    
    if not os.path.exists(filename):
        return available_codes, history, account_order
        
    with open(filename, 'r', encoding='utf-8') as f:
        # 讀取並去除每行頭尾空白
        lines = [line.strip() for line in f.readlines()]
        
    current_account = None
    for line in lines:
        if not line:
            continue  # 跳過空白行
            
        if line.startswith("account :"):
            # 取得帳號名稱
            current_account = line.split(":", 1)[1].strip()
            
            # 【關鍵修復】: 去除可能誤傳的 .png 副檔名，自動合併重複的帳號紀錄
            if current_account.endswith('.png'):
                current_account = current_account[:-4]
                
            if current_account not in history:
                history[current_account] = []
                account_order.append(current_account)
                
        elif line == "already changed:":
            continue
        else:
            if current_account is None:
                # 讀取最上方的可用序號
                if line not in available_codes:
                    available_codes.append(line)
            else:
                # 讀取該帳號已經兌換過的序號
                if line not in history[current_account]:
                    history[current_account].append(line)
                    
    return available_codes, history, account_order


def write_reward_code_file(available_codes, history, account_order, filename="reward_code.txt"):
    with open(filename, 'w', encoding='utf-8') as f:
        # 1. 寫入還未被全部帳號兌換完的可用序號
        for code in available_codes:
            f.write(f"{code}\n")
            
        # 如果上方有效序號區塊有內容，空一行作區隔
        if available_codes:
            f.write("\n")
            
        # 2. 寫入每個帳號的兌換紀錄
        for i, acc in enumerate(account_order):
            f.write(f"account :{acc}\n")
            f.write("already changed:\n")
            for code in history[acc]:
                f.write(f"{code}\n")
                
            # 每個帳號區塊之間保留一行空行，方便閱讀 (最後一個不空行)
            if i < len(account_order) - 1:
                f.write("\n")


def append_reward_exchange_record(account_name, code, filename="reward_code.txt"):
    # 避免傳入的是圖片檔名，確保邏輯一致
    if account_name.endswith('.png'):
        account_name = account_name[:-4]

    # 解析目前的文字檔狀態
    available_codes, history, account_order = parse_reward_code_file(filename)
    
    if not account_name:
        return
        
    # 如果是新帳號，加入清單
    if account_name not in history:
        history[account_name] = []
        account_order.append(account_name)
        
    # 將這次兌換的序號加入該帳號的歷史紀錄中
    if code and code not in history[account_name]:
        history[account_name].append(code)
        
    # 【新增機制】: 檢查是否有序號已經被「所有帳號」兌換過
    if account_order:
        codes_to_keep = []
        for avail_code in available_codes:
            # 判斷是否所有存檔中的帳號，都已經包含了這個序號
            is_used_by_all = all(avail_code in history[acc] for acc in account_order)
            
            # 如果沒有被全部人兌換過，就保留下來
            if not is_used_by_all:
                codes_to_keep.append(avail_code)
                
        # 更新可用序號清單
        available_codes = codes_to_keep

    # 覆寫回檔案，保持乾淨整齊的格式
    write_reward_code_file(available_codes, history, account_order, filename)

def get_reward_flow(account_name):
    codes = load_reward_codes()
    if not codes:
        print("   -> 沒有可用的序號，跳過兌換流程")
        return True

    print("\n== 開始兌換序號流程 ==")
    steps = [
        ("set.png", 0.85, "home.png", 1785, 16, 72, 71),
        ("change_reward.png", 0.85, "set.png"),
        ("input_code.png", 0.88, "change_reward.png", 869, 507, 203, 50),
        lambda: input_code(account_name),
    ]
    if not run_image_steps(
        steps,
        wait_timeout=120,
        screenshot_prefix="get_reward",
        success_message="兌換序號流程完成",
    ):
        return False

    try_click(1512, 253, 55, 49)
    return True

def input_code(account_name):
    codes = load_reward_codes()
    if not codes:
        print("   -> reward_code.txt 沒有可用的序號")
        return False

    print(f"   -> 讀到 {len(codes)} 組序號")
    input_box_x = 869 + 203 // 2
    input_box_y = 507 + 50 // 2

    for index, code in enumerate(codes, 1):
        print(f"   -> 正在輸入第 {index} 組：{code}")
        human_click((input_box_x, input_box_y))
        time.sleep(0.5)

        ensure_english_input()
        if not type_text_with_verification(code, max_attempts=3, use_paste=True):
            print(f"   -> 序號 {code} 輸入驗證失敗")
            save_debug_screenshot(f"input_code_verify_failed_{index}")
            return False
        time.sleep(1)

        if not find_and_click("confirm.png", custom_confidence=0.88):
            print(f"   -> 序號 {code} 找不到確認按鈕")
            save_debug_screenshot(f"input_code_no_confirm_{index}")
            return False

        handle_dialog_windows()
        time.sleep(2)

        print(f"   -> 序號 {code} 兌換完成")
        append_reward_exchange_record(account_name, code)
        find_and_click("change_reward.png", custom_confidence=0.88)

    print("   -> 所有序號已處理完畢")
    return True

def consume_flow(
    accout_name="loopcraft001.png",
    activity_battle=7,
):
    print("== 啟動帳號 " + accout_name + "==")
    time.sleep(0.5)
    launch_game_from_steam(accout_name)
    time.sleep(1)
    wait_for_press_to_start(
        max_wait_seconds=120,
        center_click_interval=120.0,
        post_click_verify_seconds=90.0,
    )
    time.sleep(1)
    handle_dialog_windows()
    time.sleep(1)
    consume_energy(activity_battle)
    time.sleep(0.5)
    get_reward_flow(accout_name)
    time.sleep(0.5)
    leave_game()
    print("🔍 完成每日消耗體力流程...")


def main():
    consume_flow(accout_name="e08s93.png",activity_battle=7)
    consume_flow(accout_name="e08s93.123.png",activity_battle=7)
    consume_flow(accout_name="loopcraft001.png",activity_battle=7)

if __name__ == "__main__":
    main()
