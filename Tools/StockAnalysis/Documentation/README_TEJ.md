# TEJ 遷移指南

本目錄下的分析工具已遷移至使用 TEJ (台灣經濟新報) API 作為資料來源。

## 1. 安裝必要套件

請確保已安裝 `tejapi`：

```bash
pip install tejapi pandas numpy
```

## 2. 設定 API Key

請打開 `Tools/Searching/tej_tool.py`，找到以下段落並填入您的 API Key：

```python
# ==========================================
# 請在此填入您的 TEJ API KEY
# ==========================================
TEJ_API_KEY = "YOUR_TEJ_API_KEY_HERE"  <-- 填入您的 Key
```

## 3. 使用的 TEJ 資料表

本系統依賴以下 TEJ 資料表，請確認您的帳號擁有存取權限：

*   **`TWN/APR01`**: 上市(櫃)股價-除權息調整(日)
    *   用於計算技術指標、相對強度 (RS)、歷史 PE。
*   **`TWN/AIM1A`**: IFRS財務會計科目說明(季)
    *   用於抓取財報數據 (營收、毛利、EPS、現金流等)。
*   **`TWN/AIND`**: 公司基本資料
    *   用於判斷產業分類。

## 4. 運作原理

*   **`tej_tool.py`**: 這是核心適配器。它會模擬 `yfinance` 的操作介面，將 TEJ 的資料轉換成與舊程式碼相容的格式。
*   **欄位映射**: 系統會自動將 TEJ 的中文欄位 (如 `營業收入淨額`) 轉換為英文 Key (如 `Total Revenue`)，因此原有的分析邏輯 (Pool Analyser, Health Checker 等) 無需大幅修改即可運作。

## 5. 執行方式

與之前相同，直接執行各個分析腳本即可：

```bash
python pool_analyser.py
python health_checker.py
python valuation_analyzer.py
# ...
```

