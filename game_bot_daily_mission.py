import random
import time

from tools import (
    find_and_click,
    find_only,
    get_daily_rewards,
    handle_dialog_windows,
    human_click,
    launch_game_from_steam,
    leave_game,
    run_image_steps,
    save_debug_screenshot,
    wait_for_image,
    wait_for_press_to_start,
    wait_seconds_with_abort,
    try_click,
)


def consume_energy(battle):
    print("\n💪 === 開始執行消耗體力流程 ===")
    wait_for_image("ongoing_activity.png", timeout=60.0)
    if not find_and_click("ongoing_activity.png", custom_confidence=0.8):
        print("   -> ❌ 錯誤：找不到 'ongoing_activity.png'。")
        save_debug_screenshot("no_ongoing_activity")
        return False

    wait_for_image("activity.png", timeout=60.0)
    if not find_and_click("activity.png", custom_confidence=0.8):
        print("   -> ❌ 錯誤：找不到 'activity.png'。")
        save_debug_screenshot("no_activity_button")
        return False

    wait_for_image("battle.png", timeout=60.0)
    if not find_and_click("battle.png", custom_confidence=0.85):
        print("   -> ❌ 錯誤：找不到 'battle.png'。")
        save_debug_screenshot("no_battle_button")
        return False

    if not wait_seconds_with_abort(2, "等待關卡選擇畫面"):
        return False

    if battle == 8:
        wait_for_image("battle7.png", timeout=60.0)
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
        wait_for_image("battle7.png", timeout=60.0)
        print("   -> 嘗試點擊 'battle7' 按鈕右方的關卡...")
        find_and_click("battle7.png", custom_confidence=0.9)

    if not wait_seconds_with_abort(3, "等待關卡資訊載入"):
        return False

    if not find_and_click("swape.png", custom_confidence=0.8):
        print("   -> ⚠️ 警告：找不到 'swape.png'，腳本將繼續。")
        save_debug_screenshot("swape_not_found")

    if not wait_seconds_with_abort(2, "等待掃蕩視窗"):
        return False

    if not find_and_click("max.png", custom_confidence=0.8):
        print("   -> ❌ 錯誤：找不到 'max.png'。")
        save_debug_screenshot("max_not_found")
        return False
    if not find_and_click("confirm.png", custom_confidence=0.8):
        print("   -> ❌ 錯誤：找不到 'confirm.png'。")
        save_debug_screenshot("confirm_not_found")
        return False

    print("   -> ⏳ 正在檢查是否有升級畫面...")
    if not wait_seconds_with_abort(4, "等待升級判定"):
        return False

    if find_and_click("confirm.png", custom_confidence=0.8):
        print("   -> 🆙 偵測到升級視窗！執行補掃蕩流程...")
        wait_seconds_with_abort(2, "等待 OK 按鈕")
        if not find_and_click("OK_02.png", custom_confidence=0.8):
            print("   -> ⚠️ 升級後找不到 OK 按鈕，嘗試繼續...")

        print("   -> 🔄 利用升級體力，重新設定掃蕩...")
        wait_seconds_with_abort(2, "等待回到關卡畫面")
        if find_and_click("swape.png", custom_confidence=0.8):
            wait_seconds_with_abort(1, "等待 Max")
            find_and_click("max.png", custom_confidence=0.8)
            wait_seconds_with_abort(1, "等待確認")
            find_and_click("confirm.png", custom_confidence=0.8)
            print("   -> ✅ 補掃蕩設定完成，等待結算...")
            wait_seconds_with_abort(3, "等待補掃蕩結算")
        else:
            print("   -> ❌ 找不到 swape 按鈕，無法執行補掃蕩。")
    else:
        print("   -> 👌 未偵測到升級畫面，繼續正常流程。")

    if not find_and_click("OK_02.png", custom_confidence=0.8):
        print("   -> ❌ 錯誤：找不到 'OK_02.png'。")
        save_debug_screenshot("ok_02_not_found")
        return False
    if not find_and_click("main_page.png", custom_confidence=0.8):
        print("   -> ❌ 錯誤：找不到 'main_page.png'。")
        save_debug_screenshot("main_page_not_found")
        return False
    return True

def if_upgrade():
    if find_and_click("confirm.png", custom_confidence=0.8):
        print("   -> 🆙 偵測到升級視窗！執行補掃蕩流程...")
        wait_seconds_with_abort(2, "等待 OK 按鈕")
        if not find_and_click("OK_02.png", custom_confidence=0.8):
            print("   -> ⚠️ 升級後找不到 OK 按鈕，嘗試繼續...")

        print("   -> 🔄 利用升級體力，重新設定掃蕩...")
        wait_seconds_with_abort(2, "等待回到關卡畫面")
        if find_and_click("swape.png", custom_confidence=0.8):
            wait_seconds_with_abort(1, "等待 Max")
            find_and_click("max.png", custom_confidence=0.8)
            wait_seconds_with_abort(1, "等待確認")
            find_and_click("confirm.png", custom_confidence=0.8)
            print("   -> ✅ 補掃蕩設定完成，等待結算...")
            wait_seconds_with_abort(3, "等待補掃蕩結算")
        else:
            print("   -> ❌ 找不到 swape 按鈕，無法執行補掃蕩。")
            return True
    else:
        print("   -> 👌 未偵測到升級畫面，繼續正常流程。")
        return True

def dispatch():
    print("\n📦 === 開始派遣 ===")
    steps = [
        ("dispatch.png", 0.85, 1),
        ("all_accept.png", 0.85, 1),
        ("ok.png", 0.88, 10),
        ("all_dispatch.png", 0.85, 1),
        ("backward_02.png", 0.8, 0),
    ]
    return run_image_steps(
        steps,
        wait_timeout=120,
        screenshot_prefix="dispatch",
        success_message="✅ 完成派遣。",
    )


def swap_coins():
    steps = [
        ("fight.png", 0.85, 1),
        ("resource.png", 0.85, 1),
        ("coins.png", 0.88, 10),
        ("level_5.png", 0.9, 1),
        ("swap04.png", 0.8, 0),
        ("confirm.png", 0.8, 0),
        ("OK.png", 0.8, 0),
        ("backward_03.png", 0.8, 0),
    ]
    return run_image_steps(
        steps,
        wait_timeout=120,
        screenshot_prefix="swap_coins",
        success_message="✅ 完成每日金幣掃蕩。",
    )


def swap_refine(element="water"):
    steps = [
        ("refine.png", 0.85, 1),
        (f"{element}_refine.png", 0.85, 1),
        ("level_04.png", 0.88, 10),
        ("swap04.png", 0.85, 1),
        ("confirm.png", 0.8, 0),
        ("OK.png", 0.8, 0),
        ("backward_03.png", 0.8, 0),
    ]
    return run_image_steps(
        steps,
        wait_timeout=120,
        screenshot_prefix="swap_refine",
        success_message="✅ 完成每日試煉掃蕩。",
    )


def swap_bond(level="01"):
    steps = [
        ("bond.png", 0.85, 1),
        (f"bond_level_{level}.png", 0.85, 1),
        (f"{level}_level.png", 0.85, 1),
        ("swap04.png", 0.85, 1),
        ("max.png", 0.8, 0),
        ("confirm.png", 0.8, 0),
        ("OK.png", 0.8, 0),
        ("backward_03.png", 0.8, 0),
    ]
    return run_image_steps(
        steps,
        wait_timeout=120,
        screenshot_prefix="swap_bond",
        success_message="✅ 完成每日神伴掃蕩。",
    )


def use_expiring_energy():
    search_area = (406, 427, 881, 233)
    while True:
        location = find_only("hour_label.png", custom_confidence=0.7, region=search_area)
        if not location:
            break
        human_click(location)

    print("-> 嘗試點擊: OK03.png")
    wait_for_image("OK03.png", timeout=60)
    if not find_and_click("OK03.png", custom_confidence=0.85):
        print("   -> ❌ 錯誤：找不到 'OK03.png'。")
        try_click(1519,55,62,57)
        save_debug_screenshot("leave_game_no_ok03")
        return True

    print("-> 嘗試點擊: confirm.png")
    wait_for_image("confirm.png", timeout=30)
    if not find_and_click("confirm.png", custom_confidence=0.85):
        print("   -> ❌ 錯誤：找不到 'confirm.png'。")
        find_and_click("cancel.png", custom_confidence=0.85)
        save_debug_screenshot("leave_game_no_confirm")
        return True
    return True


def swap_activity(battle=7):
    steps = [
        ("daily_activity.png", 0.85, 1),
        ("activity.png", 0.85, 1),
        ("battle.png", 0.85, 1),
        (f"battle{battle}.png", 0.85, 1),
        ("plus.png", 0.85, 1),
        use_expiring_energy,
        ("swap04.png", 0.8, 0),
        ("max.png", 0.8, 0),
        ("confirm.png", 0.8, 0),
        if_upgrade,
        ("ok_03.png", 0.8, 0),
        ("home.png", 0.8, 0),
    ]
    return run_image_steps(
        steps,
        wait_timeout=60,
        screenshot_prefix="swap_activity",
        success_message="✅ 完成每日活動掃蕩。",
    )


def swap_pvp_normal(round=5):
    print("-> 嘗試點擊: PVP")
    wait_for_image("pvp.png", timeout=120)
    if not find_and_click("pvp.png", custom_confidence=0.85):
        print("   -> ❌ 錯誤：找不到 'pvp.png'。")
        save_debug_screenshot("leave_game_no_pvp")
        return False

    print("-> 嘗試點擊: 一般")
    wait_for_image("normal.png", timeout=120)
    if not find_and_click("normal.png", custom_confidence=0.85):
        print("   -> ❌ 錯誤：找不到 'normal.png'。")
        save_debug_screenshot("leave_game_no_normal")
        return False

    for _ in range(round):
        print("-> 嘗試點擊: 出戰")
        wait_for_image("fight_02.png", timeout=120)
        if not find_and_click("fight_02.png", custom_confidence=0.85):
            print("   -> ❌ 錯誤：找不到 'fight_02.png'。")
            save_debug_screenshot("leave_game_no_fight_02")
            return False

        print("-> 嘗試點擊: skip")
        wait_for_image("skip.png", timeout=120)
        if not find_and_click("skip.png", custom_confidence=0.85):
            print("   -> ❌ 錯誤：找不到 'skip.png'。")
            save_debug_screenshot("leave_game_no_skip")
            return False

        print("-> 等待戰鬥結果...")
        wait_for_image(["new_rank.png", "defeated.png"], timeout=120)
        if find_only("new_rank.png", custom_confidence=0.85):
            print("-> 本輪 PVP 勝利！")
            find_and_click("ok.png", custom_confidence=0.85)
            find_and_click("back.png", custom_confidence=0.85)
        elif find_only("defeated.png", custom_confidence=0.85):
            print("-> 本輪 PVP 失敗...")
            find_and_click("back.png", custom_confidence=0.85)

    print("-> 嘗試點擊: backward_04")
    wait_for_image("backward_04.png", timeout=120)
    if not find_and_click("backward_04.png", custom_confidence=0.85):
        print("   -> ❌ 錯誤：找不到 'backward_04.png'。")
        save_debug_screenshot("leave_game_no_backward_04")
        return False

    print("✅ 完成每日一般競技場出戰。")
    return True


def swap_pvp_special(round=5):
    print("-> 嘗試點擊: special")
    wait_for_image("special.png", timeout=120)
    if not find_and_click("special.png", custom_confidence=0.85):
        print("   -> ❌ 錯誤：找不到 'special.png'。")
        save_debug_screenshot("leave_game_no_special")
        return False

    for _ in range(round):
        print("-> 嘗試點擊: 出戰")
        wait_for_image("fight_02.png", timeout=120)
        if not find_and_click("fight_02.png", custom_confidence=0.85):
            print("   -> ❌ 錯誤：找不到 'fight_02.png'。")
            save_debug_screenshot("leave_game_no_fight_02")
            return False

        print("-> 嘗試點擊: skip")
        wait_for_image("skip.png", timeout=120)
        if not find_and_click("skip.png", custom_confidence=0.85):
            print("   -> ❌ 錯誤：找不到 'skip.png'。")
            save_debug_screenshot("leave_game_no_skip")
            return False

        print("-> 等待戰鬥結果...")
        wait_for_image(["new_rank.png", "defeated.png"], timeout=120)
        if find_only("new_rank.png", custom_confidence=0.85):
            print("-> 本輪 PVP 勝利！")
            find_and_click("ok.png", custom_confidence=0.85)
            find_and_click("back.png", custom_confidence=0.85)
        elif find_only("defeated.png", custom_confidence=0.85):
            print("-> 本輪 PVP 失敗...")
            find_and_click("back.png", custom_confidence=0.85)

    print("-> 嘗試點擊: backward_05")
    wait_for_image("backward_05.png", timeout=120)
    if not find_and_click("backward_05.png", custom_confidence=0.85):
        print("   -> ❌ 錯誤：找不到 'backward_05.png'。")
        save_debug_screenshot("leave_game_no_backward_05")
        return False

    print("-> 嘗試點擊: backward_05")
    wait_for_image("backward_05.png", timeout=120)
    if not find_and_click("backward_05.png", custom_confidence=0.85):
        print("   -> ❌ 錯誤：找不到 'backward_05.png'。")
        save_debug_screenshot("leave_game_no_backward_05")
        return False

    print("✅ 完成每日特殊競技場出戰。")
    return True


def daily_job(
    accout_name="loopcraft001.png",
    element="thorns",
    activity_battle=7,
    pvp_normal_round=2,
    pvpspecial_round=2,
):
    print("🔍 正在尋找遊戲畫面...")
    time.sleep(5)
    launch_game_from_steam(accout_name)
    time.sleep(5)
    wait_for_press_to_start(
        max_wait_seconds=120,
        center_click_interval=120.0,
        post_click_verify_seconds=90.0,
    )
    time.sleep(5)
    handle_dialog_windows()
    time.sleep(5)
    dispatch()
    swap_coins()
    swap_refine(element)
    swap_bond(level="03")
    swap_activity(activity_battle)
    time.sleep(5)
    swap_pvp_normal(pvp_normal_round)
    swap_pvp_special(pvpspecial_round)
    time.sleep(8)
    get_daily_rewards()
    time.sleep(5)
    leave_game()
    print("🔍 完成每日任務...")


def main():
    daily_job(accout_name="e08s93.png", element="water", activity_battle=8, pvp_normal_round=1, pvpspecial_round=1)
    daily_job(accout_name="e08s93.123.png", element="thorns", activity_battle=7, pvp_normal_round=5, pvpspecial_round=1)
    daily_job(accout_name="loopcraft001.png", element="thorns", activity_battle=8, pvp_normal_round=5, pvpspecial_round=1)


if __name__ == "__main__":
    main()
