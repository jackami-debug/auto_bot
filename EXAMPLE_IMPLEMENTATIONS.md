# 防呆機制應用示例

## 示例 1：基本的步驟重試（最簡單）

原本的代碼：
```python
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
```

改進後（只加入重試參數）：
```python
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
        max_retries=2,           # ← 新增：失敗後自動重試 2 次
        retry_delay=1.0,         # ← 新增：初始延遲 1 秒
    )
```

---

## 示例 2：函數層級重試（中等難度）

對整個函數進行重試保護：

```python
from functools import wraps

# 在 game_bot_daily_mission.py 的頂部添加裝飾器（已經做過了）
@retry_on_failure(max_retries=2, retry_delay=2.0)
def consume_energy(battle):
    print("\n💪 === 開始執行消耗體力流程 ===")
    wait_for_image("ongoing_activity.png", timeout=60.0)
    if not find_and_click("ongoing_activity.png", custom_confidence=0.8):
        print("   -> ❌ 錯誤：找不到 'ongoing_activity.png'。")
        save_debug_screenshot("no_ongoing_activity")
        return False
    
    # ... 其餘步驟 ...
    return True
```

這樣做的好處：
- 如果 `consume_energy()` 失敗，會自動重試 2 次
- 每次重試前等待 2 秒，然後 4 秒，然後 8 秒...
- 如果 3 次都失敗，才會返回 False

---

## 示例 3：加入備用方案（最深入）

當主流程全部失敗時，執行替代方案：

```python
def fallback_swap_coins():
    """金幣掃蕩失敗時的備用方案"""
    print("⚠️ 金幣掃蕩失敗，嘗試備用方案...")
    # 例如：跳過此步驟，直接返回成功
    return True

@retry_on_failure(
    max_retries=3,
    retry_delay=2.0,
    fallback_action=fallback_swap_coins  # ← 所有重試失敗時執行這個函數
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
        max_retries=2,
        retry_delay=1.0,
    )
```

流程圖：
```
開始執行 swap_coins()
  ↓
[嘗試 1] 執行主流程 → 失敗
  ↓
等待 2 秒
  ↓
[嘗試 2] 執行主流程 → 失敗
  ↓
等待 4 秒
  ↓
[嘗試 3] 執行主流程 → 失敗
  ↓
等待 8 秒
  ↓
[嘗試 4] 執行主流程 → 失敗
  ↓
執行備用方案 (fallback_swap_coins) → 成功
  ↓
返回 True
```

---

## 示例 4：組合使用（推薦做法）

同時使用裝飾器和步驟重試：

```python
@retry_on_failure(max_retries=2, retry_delay=3.0)
def complete_daily_mission():
    """完成全部日常任務"""
    print("\n🎮 === 開始日常任務流程 ===")
    
    # 消耗體力
    steps = [
        (consume_energy, 8),  # 如果 consume_energy() 返回 False，會自動重試
        # ...
    ]
    
    # 派遣、掃蕩等...
    if not dispatch():
        print("❌ 派遣失敗")
        return False
    
    if not swap_coins():
        print("❌ 金幣掃蕩失敗")
        return False
    
    print("✅ 成功完成所有日常任務！")
    return True
```

---

## 示例 5：漸進式增強

根據系統狀況動態調整：

```python
# 階段 1：初始值（推薦）
max_retries = 2
retry_delay = 1.0

# 階段 2：如果系統載入慢
max_retries = 3
retry_delay = 2.0

# 階段 3：如果還是不穩定
max_retries = 4
retry_delay = 3.0

def dispatch():
    steps = [...]
    return run_image_steps(
        steps,
        wait_timeout=120,
        screenshot_prefix="dispatch",
        success_message="✅ 完成派遣。",
        max_retries=max_retries,
        retry_delay=retry_delay,
    )
```

---

## 實際應用清單

應用重試機制的優先順序：

1. ✓ **高優先級**（立即應用）
   - `dispatch()` - 派遣很容易因系統延遲失敗
   - `consume_energy()` - 複雜流程，容易出錯

2. ✓ **中優先級**
   - `swap_coins()` - 金幣掃蕩
   - `swap_refine()` - 試煉掃蕩
   - `swap_bond()` - 神伴掃蕩

3. ✓ **低優先級**
   - `use_expiring_energy()` - 檢查邏輯簡單

---

## 調試技巧

### 查看重試日誌
```
🔄 執行 'dispatch' (嘗試 1/3)
   ⚠️ 執行失敗，1.0 秒後重試...

🔄 執行 'dispatch' (嘗試 2/3)
   ✅ 成功完成 dispatch
```

### 如果重試還是不成功
1. 檢查圖片識別準確度
2. 增加 `max_retries` 和 `retry_delay`
3. 檢查遊戲是否卡死

---

## 快速開始

最簡單的做法，只需 2 步：

### 步驟 1：找到要改進的函數

```python
def dispatch():
    # ...
    return run_image_steps(steps, ...)
```

### 步驟 2：添加重試參數

```python
def dispatch():
    # ...
    return run_image_steps(
        steps, 
        ...,
        max_retries=2,
        retry_delay=1.0,
    )
```

完成！🎉

---

**需要幫助？檢查 `RETRY_SYSTEM_GUIDE.md` 了解更多！**
