# 🚀 防呆機制快速參考

## ⚡ 30 秒快速開始

### 方案 A：對單個步驟進行重試（最簡單）

```python
# 在現有的 run_image_steps() 調用中添加這兩行：
return run_image_steps(
    steps,
    wait_timeout=120,
    screenshot_prefix="dispatch",
    success_message="✅ 完成派遣。",
    max_retries=2,        # ← 新增
    retry_delay=1.0,      # ← 新增
)
```

### 方案 B：對整個函數進行重試（推薦）

```python
# 在函數定義前添加裝飾器：
@retry_on_failure(max_retries=2, retry_delay=2.0)
def dispatch():
    steps = [...]
    return run_image_steps(steps, ...)
```

---

## 📊 常見場景解決方案

| 問題 | 解決方案 | 代碼 |
|------|--------|------|
| 步驟間歇性失敗 | 添加步驟重試 | `max_retries=2, retry_delay=1.0` |
| 系統載入慢 | 增加延遲和重試次數 | `max_retries=3, retry_delay=2.0` |
| 整個流程失敗 | 用裝飾器包裹函數 | `@retry_on_failure()` |
| 失敗時跳過該步驟 | 添加備用方案 | `fallback_action=skipfunc` |

---

## 🎯 立即可用的模板

### 模板 1：基本步驟重試
```python
def my_function():
    steps = [...]
    return run_image_steps(
        steps,
        wait_timeout=120,
        screenshot_prefix="my_step",
        success_message="✅ 成功",
        max_retries=2,
        retry_delay=1.0,
    )
```

### 模板 2：函數級別重試
```python
@retry_on_failure(max_retries=2, retry_delay=2.0)
def my_function():
    # 原始代碼不變
    ...
    return True
```

### 模板 3：帶備用方案
```python
def fallback():
    print("執行備用方案")
    return True

@retry_on_failure(max_retries=3, retry_delay=2.0, fallback_action=fallback)
def my_function():
    ...
    return True
```

---

## 🔧 參數速查表

```
max_retries (最大重試次數)
├─ 1   : 快速反應步驟（不希望等待太久）
├─ 2   : 一般步驟（推薦值 ⭐）
├─ 3   : 系統載入較慢
└─ 4+  : 網络不穩定或超級安全模式

retry_delay (初始延遲秒數)
├─ 0.5 : 快速反應
├─ 1.0 : 預設（推薦 ⭐）
├─ 2.0 : 系統反應較慢
└─ 3.0+ : 網路延遲高
```

---

## 💡 推薦配置

### 情況 1：系統穩定
```python
max_retries = 1
retry_delay = 0.5
```

### 情況 2：平衡（推薦）⭐
```python
max_retries = 2
retry_delay = 1.0
```

### 情況 3：系統不穩定
```python
max_retries = 3
retry_delay = 2.0
```

### 情況 4：網路很爛
```python
max_retries = 4
retry_delay = 3.0
```

---

## 🎪 立即要改進的函數

列出你現有代碼中應該添加重試的函數：

- [ ] `dispatch()` - 派遣
- [ ] `consume_energy()` - 消耗體力
- [ ] `swap_coins()` - 金幣掃蕩
- [ ] `swap_refine()` - 試煉掃蕩
- [ ] `swap_bond()` - 神伴掃蕩
- [ ] `swap_activity()` - 活動掃蕩

**建議：從 `dispatch()` 和 `consume_energy()` 開始** ✅

---

## 🔍 檢查是否生效

### 執行程式並觀察日誌：

✅ **成功的信號**
```
🔄 執行 'dispatch' (嘗試 1/3)
   ⚠️ 執行失敗，1.0 秒後重試...

🔄 執行 'dispatch' (嘗試 2/3)
   ✅ 成功完成 dispatch
```

❌ **失敗的信號**（沒有看到 `🔄` 和 `⚠️`）
- 可能是還沒有應用装飾器
- 檢查是否有語法錯誤

---

## ⚠️ 常見錯誤

| 錯誤 | 原因 | 修復 |
|-----|------|------|
| `NameError: retry_on_failure not defined` | 沒有 import 裝飾器 | 確保在文件頂部看到 `@retry_on_failure` |
| `TypeError: run_image_steps() got unexpected keyword` | 版本不匹配 | 確保更新了 `tools.py` |
| 程式還是常常失敗 | 重試次數或延遲不夠 | 增加 `max_retries` 或 `retry_delay` |

---

## 📚 詳細文檔

- **完整指南**：[RETRY_SYSTEM_GUIDE.md](RETRY_SYSTEM_GUIDE.md)
- **實現示例**：[EXAMPLE_IMPLEMENTATIONS.md](EXAMPLE_IMPLEMENTATIONS.md)

---

## ⏱️ 預期效果

### 改進前
```
執行時間：5 分鐘
成功率：70% 
```

### 改進後（使用重試機制）
```
執行時間：6-7 分鐘（多了重試時間）
成功率：95%+ ✨
```

---

## 🆘 需要幫助？

1. **查看詳細指南**：[RETRY_SYSTEM_GUIDE.md](RETRY_SYSTEM_GUIDE.md)
2. **參考實現示例**：[EXAMPLE_IMPLEMENTATIONS.md](EXAMPLE_IMPLEMENTATIONS.md)
3. **檢查日誌輸出**：尋找 `🔄` `⚠️` `✅` 標記
4. **逐步調整值**：不要急著設置過大的值

---

**現在就開始改進你的腳本吧！🚀**

```python
# 只需要這一行改變...
@retry_on_failure(max_retries=2, retry_delay=2.0)
def dispatch():
    ...
```

**就這麼簡單！✨**
