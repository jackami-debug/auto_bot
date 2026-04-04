import random
import time
from datetime import date

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
    get_wish,
    sleep,
    click_till_see,
    ensure_pass_tutorial,
    get_bond_level_by_date,
    swipe_screen,
    log,
)




def consume_energy(battle):
    print("\n💪 === 開始執行消耗體力流程 ===")
    wait_for_image("ongoing_activity.png", timeout=10.0)
    if not find_and_click("ongoing_activity.png", custom_confidence=0.8):
        return False

    wait_for_image("activity.png", timeout=10.0,try_click_name="ongoing_activity.png")
    if not find_and_click("activity.png", custom_confidence=0.8):
       return False

    wait_for_image("battle.png", timeout=10.0,try_click_name="activity.png")
    if not find_and_click("battle.png", custom_confidence=0.85):
       return False

    if not wait_seconds_with_abort(2, "等待關卡選擇畫面"):
        return False

    if battle == 8:
        wait_for_image("battle8.png", timeout=10.0)
        print("   -> 嘗試點擊 'battle8' 按鈕右方的關卡...")
        find_and_click("battle8.png", custom_confidence=0.9)
        wait_for_image("swape.png", timeout=10.0,try_click_name="battle8.png")
    elif battle == 7:
        wait_for_image("battle7.png", timeout=10.0)
        print("   -> 嘗試點擊 'battle7' 按鈕右方的關卡...")
        find_and_click("battle7.png", custom_confidence=0.9)
        wait_for_image("swape.png", timeout=10.0,try_click_name="battle7.png")


    if not find_and_click("swape.png", custom_confidence=0.8):
        print("   -> ⚠️ 警告：找不到 'swape.png'，腳本將繼續。")
        save_debug_screenshot("swape_not_found")

    wait_for_image("max.png", timeout=10.0,try_click_name="swape.png")
    if not find_and_click("max.png", custom_confidence=0.8):
        return False
    wait_for_image("confirm.png", timeout=10.0,try_click_name="swape.png")
    if not find_and_click("confirm.png", custom_confidence=0.8):
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
        else:
            print("   -> ❌ 找不到 swape 按鈕，無法執行補掃蕩。")
    else:
        print("   -> 👌 未偵測到升級畫面，繼續正常流程。")
    wait_for_image("OK_02.png", timeout=10.0,try_click_name="confirm.png")
    if not find_and_click("OK_02.png", custom_confidence=0.8):
        return False
    wait_for_image("main_page.png", timeout=10.0,try_click_name="OK_02.png")
    if not find_and_click("main_page.png", custom_confidence=0.8):
        return False
    return True

def if_upgrade():
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
            return True
    else:
        print("   -> 👌 未偵測到升級畫面，繼續正常流程。")
        return True

def dispatch():
    print("\n📦 === 開始派遣 ===")
    steps = [
        ("dispatch.png", 0.85, "close.png"),
        ("all_accept.png", 0.85, "dispatch.png"),
        ("all_accept.png", 0.88, None),#這裡原本是點擊OK，但是連續點兩次"all_accept.png"也可以。
        (sleep, 3),
        ("all_dispatch.png", 0.85, "ok.png"),
        (click_till_see, "speed_up.png",(1220,1006)),
        ("backward_02.png", 0.8, "all_dispatch.png"),
    ]
    return run_image_steps(
        steps,
        wait_timeout=120,
        screenshot_prefix="dispatch",
        success_message="✅ 完成派遣。",
    )


def swap_coins():
    steps = [
        ("fight.png", 0.85, "backward_02.png"),
        ("resource.png", 0.85, "fight.png"),
        ("coins.png", 0.88, "resource.png"),
        ("level_05.png", 0.96, "coins.png"),
        ("swap04.png", 0.8, "level_05.png"),
        ("confirm.png", 0.8, "swap04.png"),
        ("OK.png", 0.8, "confirm.png"),
        ("backward_03.png", 0.8, "OK.png"),
    ]
    return run_image_steps(
        steps,
        wait_timeout=120,
        screenshot_prefix="swap_coins",
        success_message="✅ 完成每日金幣掃蕩。",
    )


def swap_refine(element="water"):
    steps = [
        ("refine.png", 0.85, "backward_03.png"),
        (f"{element}_refine.png", 0.85, "refine.png"),
        sleep,
        ("level_04.png", 0.88, "level_04.png"),
        ("swap04.png", 0.85, "level_04.png"),
        ("confirm.png", 0.8, "swap04.png"),
        ("OK.png", 0.8, "confirm.png"),
        ("backward_03.png", 0.8, "OK.png"),
    ]
    return run_image_steps(
        steps,
        wait_timeout=120,
        screenshot_prefix="swap_refine",
        success_message="✅ 完成每日試煉掃蕩。",
    )


def swap_bond(level="01"):
    # 1. 先放入共通的開頭步驟（點擊進入神伴介面並等待）
    steps = [
        ("bond.png", 0.85, "backward_03.png"),
        sleep,
    ]
    
    # 2. 加入判斷：如果 level 是 "04" 或 "05"，就執行向左滑動
    if level in ["04", "05"]:
        log(f"   -> 偵測到關卡為 {level}，執行向左滑動尋找關卡...")
        # 利用你 run_image_steps 支援的 (函式, 參數1, 參數2...) 格式
        # 對應 swipe_screen 的位置參數: direction, distance, start_location, duration
        steps.append((swipe_screen, "left", 1400, (1503, 596), 0.2))
        
        # 強烈建議滑動完再加一個 sleep，讓畫面停穩了再開始找關卡圖片，避免殘影導致找不到
        steps.append(sleep) 
        
    # 3. 接著補上後續的點擊與掃蕩步驟
    steps.extend([
        (f"bond_level_{level}.png", 0.85, "bond.png"),
        (f"{level}_level.png", 0.85, f"bond_level_{level}.png"),
        ("swap04.png", 0.85, f"{level}_level.png"),
        ("max.png", 0.8, "swap04.png"),
        ("confirm.png", 0.8, "max.png"),
        ("OK.png", 0.8, "confirm.png"),
        ("backward_03.png", 0.8, "OK.png"),
    ])
    
    # 4. 丟給 run_image_steps 執行
    return run_image_steps(
        steps,
        wait_timeout=120,
        screenshot_prefix="swap_bond",
        success_message=f"✅ 完成每日神伴掃蕩 (Level {level})。",
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
    wait_for_image("confirm.png", timeout=5)
    if not find_and_click("confirm.png", custom_confidence=0.85):
        print("   -> ❌ 錯誤：找不到 'confirm.png'。")
        find_and_click("cancel.png", custom_confidence=0.85)
        return True
    return True


def swap_activity(battle=7):
    steps = [
        ("daily_activity.png", 0.85, "backward_03.png"),
        ("activity.png", 0.85, "daily_activity.png"),
        ("battle.png", 0.85, "activity.png"),
        (sleep, 3),
        ensure_pass_tutorial,
        (f"battle{battle}.png", 0.95, "battle.png"),
        ("plus.png", 0.85, f"battle{battle}.png"),
        use_expiring_energy,
        ("swap04.png", 0.8, f"battle{battle}.png"),
        ("max.png", 0.8, "swap04.png"),
        ("confirm.png", 0.8, "max.png"),
        if_upgrade,
        ("ok_03.png", 0.8, "confirm.png"),
        ("home.png", 0.8, "ok_03.png"),
    ]
    return run_image_steps(
        steps,
        wait_timeout=60,
        screenshot_prefix="swap_activity",
        success_message="✅ 完成每日活動掃蕩。",
    )


def swap_pvp_normal(round=5):
    print("-> 嘗試點擊: PVP")
    wait_for_image("pvp.png", timeout=10,try_click_name="home.png")
    if not find_and_click("pvp.png", custom_confidence=0.85):
        return False

    print("-> 嘗試點擊: 一般")
    wait_for_image("normal.png", timeout=12,try_click_name="pvp.png")
    if not find_and_click("normal.png", custom_confidence=0.85):
        return False
    
    wait_for_image("accumulate_rewards.png", timeout=12,try_click_name="normal.png")
    if not find_and_click("accumulate_rewards.png", custom_confidence=0.85):
        return False
    
    wait_for_image("get_rewards.png", timeout=12,try_click_name="accumulate_rewards.png")
    if not find_and_click("get_rewards.png", custom_confidence=0.85):
        return False

    wait_for_image(["confirm_08.png","OK.png"], timeout=12,try_click_name="get_rewards.png")
    if not find_and_click(["confirm_08.png","OK.png"], custom_confidence=0.85):
        return False

    wait_for_image("backward_08.png", timeout=12,try_click_name=["confirm_08.png","OK.png"])
    if not find_and_click("backward_08.png", custom_confidence=0.85):
        return False

    for _ in range(round):
        print("-> 嘗試點擊: 出戰")
        wait_for_image("fight_02.png", timeout=12,try_click_name="normal.png")
        if not find_and_click("fight_02.png", custom_confidence=0.85):
            return False

        print("-> 嘗試點擊: skip")
        sleep()
        wait_for_image("skip.png", timeout=12)
        if not find_and_click("skip.png", custom_confidence=0.85):
            try_click(74,849,360,71)
            find_and_click("skip.png", custom_confidence=0.85)

        if find_only("warn_01.png", custom_confidence=0.85):
            print("-> 發現眷族技能配置警告！")
            find_and_click("yes_01.png", custom_confidence=0.85)

        print("-> 等待戰鬥結果...")
        wait_for_image(["new_rank.png", "defeated.png"], timeout=120)
        if find_only("new_rank.png", custom_confidence=0.85):
            print("-> 本輪 PVP 勝利！")
            find_and_click("ok.png", custom_confidence=0.85)
            wait_for_image("back.png", timeout=5,try_click_name="ok.png")
            find_and_click("back.png", custom_confidence=0.85)
        elif find_only("defeated.png", custom_confidence=0.85):
            print("-> 本輪 PVP 失敗...")
            find_and_click("back.png", custom_confidence=0.85)

    print("-> 嘗試點擊: backward_04")
    wait_for_image("backward_04.png", timeout=12,try_click_name="back.png")
    if not find_and_click("backward_04.png", custom_confidence=0.85):
        return False

    print("✅ 完成每日一般競技場出戰。")
    return True


def swap_god_fight():
    print("-> 嘗試點擊:特殊")
    wait_for_image("special_01.png", timeout=12,try_click_name="backward_03.png")
    if not find_and_click("special_01.png", custom_confidence=0.85):
        return False
    
    wait_for_image("swap_it.png", timeout=12,try_click_name="special_01.png")
    if not find_and_click("swap_it.png", custom_confidence=0.85):
        return False
    
    wait_for_image("swap_01.png", timeout=12,try_click_name="swap_it.png")
    if not find_and_click("swap_01.png", custom_confidence=0.85):
        return False

    wait_for_image(["max_01.png","warn_02.png"], timeout=12,try_click_name="swap_01.png")
    if not find_and_click(["max_01.png","warn_02.png"], custom_confidence=0.85):
        return False

    wait_for_image("confirm.png", timeout=12,try_click_name=["max_01.png","warn_02.png"])
    if not find_and_click("confirm.png", custom_confidence=0.85):
        return False

    if find_only("OK.png", custom_confidence=0.85):
        find_and_click("OK.png", custom_confidence=0.85)

    wait_for_image("category.png", timeout=12,try_click_name=["confirm.png","OK.png"])
    if not find_and_click("category.png", custom_confidence=0.85):
        return False
    
    wait_for_image(["accept_all.png","accept_all_blank.png"], timeout=12,try_click_name="category.png")
    if not find_and_click("accept_all.png", custom_confidence=0.85):
        find_and_click("back_05.png", custom_confidence=0.85)
        find_and_click("back_06.png", custom_confidence=0.85)
        return True
    
    wait_for_image("OK.png", timeout=12,try_click_name="accept_all.png")
    if not find_and_click("OK.png", custom_confidence=0.85):
        return False
    
    wait_for_image("back_05.png", timeout=12,try_click_name="OK.png")
    if not find_and_click("back_05.png", custom_confidence=0.85):
        return False

    wait_for_image("back_06.png", timeout=12,try_click_name="back_05.png")
    if not find_and_click("back_06.png", custom_confidence=0.85):
        return False

    print("✅ 完成每日神力殊死戰掃蕩。")
    return True

def swap_pvp_special(round=5):
    print("-> 嘗試點擊: special")
    wait_for_image("special.png", timeout=12,try_click_name="backward_04.png")
    if not find_and_click("special.png", custom_confidence=0.85):
        return False
    
    wait_for_image("accumulate_rewards.png", timeout=12,try_click_name="normal.png")
    if not find_and_click("accumulate_rewards.png", custom_confidence=0.85):
        return False
    
    wait_for_image("get_rewards.png", timeout=12,try_click_name="accumulate_rewards.png")
    if not find_and_click("get_rewards.png", custom_confidence=0.85):
        return False

    wait_for_image(["confirm_08.png","OK.png"], timeout=12,try_click_name="get_rewards.png")
    if not find_and_click(["confirm_08.png","OK.png"], custom_confidence=0.85):
        return False

    wait_for_image("backward_08.png", timeout=12,try_click_name=["confirm_08.png","OK.png"])
    if not find_and_click("backward_08.png", custom_confidence=0.85):
        return False


    for _ in range(round):
        print("-> 嘗試點擊: 出戰")
        wait_for_image("fight_02.png", timeout=12,try_click_name="special.png")
        if not find_and_click("fight_02.png", custom_confidence=0.85):
            return False

        print("-> 嘗試點擊: skip")
        sleep()
        wait_for_image("skip.png", timeout=12,try_click_name="fight_02.png")
        if not find_and_click("skip.png", custom_confidence=0.85):
            return False
        if find_only("warn_01.png", custom_confidence=0.85):
            print("-> 發現眷族技能配置警告！")
            find_and_click("yes_01.png", custom_confidence=0.85)

        print("-> 等待戰鬥結果...")
        wait_for_image(["new_rank.png", "defeated.png"], timeout=120)
        if find_only("new_rank.png", custom_confidence=0.85):
            print("-> 本輪 PVP 勝利！")
            find_and_click("ok.png", custom_confidence=0.85)
            wait_for_image("back.png", timeout=5,try_click_name="ok.png")
            find_and_click("back.png", custom_confidence=0.85)
        elif find_only("defeated.png", custom_confidence=0.85):
            print("-> 本輪 PVP 失敗...")
            find_and_click("back.png", custom_confidence=0.85)

    print("-> 嘗試點擊: backward_05")
    wait_for_image("backward_05.png", timeout=12,try_click_name="back.png")
    if not find_and_click("backward_05.png", custom_confidence=0.85):
        return False

    print("-> 嘗試點擊: backward_05")
    wait_for_image("backward_05.png", timeout=12,try_click_name="back.png")
    if not find_and_click("backward_05.png", custom_confidence=0.85):
        return False

    print("✅ 完成每日特殊競技場出戰。")
    return True


def daily_job(
    accout_name="loopcraft001.png",
    element="thorns",
    activity_battle=7,
    pvp_normal_round=1,
    pvpspecial_round=1,
):
    print("🔍 正在尋找遊戲畫面...")
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
    sleep()
    dispatch()
    swap_coins()
    swap_refine(element)
    today_level = get_bond_level_by_date()
    print(f"🎯 依據今日日期，神伴掃蕩關卡為: Level {today_level}")
    swap_bond(today_level)
    swap_god_fight()
    swap_activity(activity_battle)
    time.sleep(0.5)
    swap_pvp_normal(pvp_normal_round)
    swap_pvp_special(pvpspecial_round)
    time.sleep(0.5)
    get_daily_rewards()
    time.sleep(0.5)
    get_wish()

    time.sleep(0.5)
    leave_game()
    print("🔍 完成每日任務...")


def main():
    daily_job(accout_name="e08s93.png", element="water", activity_battle=8, pvp_normal_round=1, pvpspecial_round=1)
    daily_job(accout_name="e08s93.123.png", element="thorns", activity_battle=7, pvp_normal_round=1, pvpspecial_round=1)
    daily_job(accout_name="loopcraft001.png", element="thorns", activity_battle=7, pvp_normal_round=1, pvpspecial_round=1)


if __name__ == "__main__":
    main()
