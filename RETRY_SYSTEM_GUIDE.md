# 自動重試防呆機制使用指南

## 概述

現在系統支持兩層重試機制：
1. **步驟層級重試** - 在 `tools.py` 的 `run_image_steps()` 中實現
2. **函數層級重試** - 在 `game_bot_daily_mission.py` 中透過 `@retry_on_failure` 裝飾器實現

---

## ⚙️ 一、步驟層級重試（在 `tools.py` 中）

`run_image_steps()` 函數已經增強，支持自動重試單個步驟：

### 新參數：
- `max_retries`：每個步驟失敗時重試次數（默認: 2）
- `retry_delay`：重試前等待時間，會指數增長（默認: 1.0 秒）

### 使用示例：

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
        max_retries=2,           # ← 新增：每個步驟最多重試 2 次
        retry_delay=1.0,         # ← 新增：初始延遲 1 秒（失敗後會變 2、4、8 秒...）
    )
```

### 重試邏輯：
- 如果步驟失敗，會等待 `retry_delay` 秒後重試
- 第 N 次重試的延遲時間為：`retry_delay × 2^N` 秒（指數退避）
- 例如：首次失敗等 1 秒，再失敗等 2 秒，再失敗等 4 秒

---

## 🔄 二、函數層級重試（在 `game_bot_daily_mission.py` 中）

使用 `@retry_on_failure` 裝飾器讓整個函數自動重試：

### 使用示例 1：基本用法

```python
@retry_on_failure(max_retries=2, retry_delay=2.0)
def consume_energy(battle):
    print("\n💪 === 開始執行消耗體力流程 ===")
    # ... 原有的函數邏輯 ...
    return True
```

### 使用示例 2：帶備用方案

```python
def fallback_dispatch():
    """派遣失敗時的備用方案"""
    print("⚠️ 派遣失敗，執行備用方案...")
    return True  # 返回 True 表示備用方案成功

@retry_on_failure(
    max_retries=3, 
    retry_delay=2.0,
    fallback_action=fallback_dispatch  # ← 當所有重試都失敗時執行此函數
)
def dispatch():
    print("\n📦 === 開始派遣 ===")
    steps = [
        ("dispatch.png", 0.85, 1),
        ("all_accept.png", 0.85, 1),
        # ...
    ]
    return run_image_steps(
        steps,
        wait_timeout=120,
        screenshot_prefix="dispatch",
        success_message="✅ 完成派遣。",
        max_retries=2,
        retry_delay=1.0,
    )
```

### 裝飾器參數：
- `max_retries`：最大重試次數（默認: 2）
- `retry_delay`：重試間隔（默認: 2.0 秒）
- `fallback_action`：所有重試都失敗時執行的備用函數（可選）

---

## 📋 如何應用到現有程式

### 方法 1：只改進 `run_image_steps` 調用（推薦最簡單）

只需在現有的 `run_image_steps()` 調用中加入新參數：

```python
# 舊代碼
return run_image_steps(
    steps,
    wait_timeout=120,
    screenshot_prefix="dispatch",
    success_message="✅ 完成派遣。",
)

# 新代碼
return run_image_steps(
    steps,
    wait_timeout=120,
    screenshot_prefix="dispatch",
    success_message="✅ 完成派遣。",
    max_retries=2,      # ← 添加這行
    retry_delay=1.0,    # ← 添加這行
)
```

### 方法 2：同時使用裝飾器（推薦最深入）

```python
@retry_on_failure(max_retries=2, retry_delay=2.0)
def swap_coins():
    steps = [
        ("fight.png", 0.85, 1),
        ("resource.png", 0.85, 1),
        # ...
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

---

## 🔍 重試流程示例

### 不加重試的舊行為：
```
嘗試點擊: abc.png (嘗試 1/1)
❌ 錯誤：找不到 'abc.png'
[程式中斷]
```

### 加重試的新行為：
```
嘗試點擊: abc.png (嘗試 1/3)
❌ 畫面未出現，1.0 秒後重試...

嘗試點擊: abc.png (嘗試 2/3)
❌ 點擊失敗，2.0 秒後重試...

嘗試點擊: abc.png (嘗試 3/3)
✅ 成功點擊 'abc.png'
[流程繼續]
```

---

## ⚡ 推薦配置

針對不同場景的推薦參數：

| 場景 | max_retries | retry_delay | 說明 |
|------|------------|------------|------|
| 快速反應步驟 | 1 | 0.5 | 重試 1 次，延遲短 |
| 一般步驟 | 2 | 1.0 | 默認配置，適合大多數情況 |
| 系統載入慢 | 3 | 2.0 | 重試 3 次，延遲較長 |
| 網路不穩定 | 4 | 3.0 | 最大容忍度 |

---

## 📝 使用建議

1. **先用預設值**：大多數情況下，`max_retries=2, retry_delay=1.0` 就夠
2. **監控日誌**：注意 `🔄` 和 `⚠️` 標記，了解重試頻率
3. **逐步增加**：如果重試還不夠，再增加 `max_retries` 或 `retry_delay`
4. **備用方案**：重點流程可添加 `fallback_action` 作為最後保障

---

## 🐛 troubleshooting

### 問題：程式還是常常失敗？
**解決**：
- ✓ 增加 `max_retries` 到 3 或 4
- ✓ 增加 `retry_delay` 到 2.0 或 3.0
- ✓ 檢查圖片識別準確度（confidence 設置）

### 問題：重試導致程式執行時間過長？
**解決**：
- ✓ 減少 `max_retries` 到 1
- ✓ 減少 `retry_delay` 到 0.5

### 問題：某特定步驟總是失敗？
**解決**：
- ✓ 對該函數使用 `@retry_on_failure` 裝飾器
- ✓ 添加 `fallback_action` 參數

---

## 💡 進階 - 自訂重試策略

如果需要更複雜的重試邏輯，可以修改裝飾器或建立新的重試函數。
例如：根據不同的錯誤類型採用不同策略。

---

**祝你的自動化更穩定！🚀**
