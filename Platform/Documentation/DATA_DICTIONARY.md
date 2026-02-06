# 📚 Investment AI Platform - 資料字典 (Data Dictionary)

**版本**: 1.0  
**建立日期**: 2026-02-06  
**資料來源**: TEJ API (E-SHOP 初入江湖版) + Local Database

---

## 📋 目錄

1. [資料結構總覽](#資料結構總覽)
2. [INFO - 公司基本資料](#1️⃣-info---公司基本資料)
3. [PRICE - 股價資料](#2️⃣-price---股價資料)
4. [FINANCIALS - 損益表](#3️⃣-financials---損益表)
5. [BALANCE_SHEET - 資產負債表](#4️⃣-balance_sheet---資產負債表)
6. [CASHFLOW - 現金流量表](#5️⃣-cashflow---現金流量表)
7. [CHIP - 籌碼資料](#6️⃣-chip---籌碼資料)
8. [MONTHLY_SALES - 月營收](#7️⃣-monthly_sales---月營收)
9. [可計算的衍生指標](#📊-可計算的衍生指標)
10. [策略應用對照表](#🎯-策略應用對照表)

---

## 資料結構總覽

每支股票的資料以 JSON 格式儲存於 `Stock_Pool/Database/` 目錄下。

```
Stock_Pool/Database/{股票代碼}_{日期}.json
例如: 1101_20260206.json
```

### JSON 結構

```json
{
  "ticker": "1101.TW",
  "info": { ... },           // 公司基本資料 (dict)
  "price": "...",            // 股價資料 (JSON string, pandas split format)
  "financials": "...",       // 損益表 (JSON string)
  "balance_sheet": "...",    // 資產負債表 (JSON string)
  "cashflow": "...",         // 現金流量表 (JSON string)
  "chip": "...",             // 籌碼資料 (JSON string)
  "monthly_sales": "...",    // 月營收 (JSON string)
  "updated_at": "2026-02-06T00:14:28"
}
```

---

## 1️⃣ INFO - 公司基本資料

| 欄位名稱 | 資料類型 | 說明 | 範例值 | 策略用途 |
|----------|----------|------|--------|----------|
| `symbol` | string | 股票代碼 | "1101.TW" | 主鍵 |
| `shortName` | string | 股票簡稱 | "台泥" | 顯示名稱 |
| `longName` | string | 公司全名 | "台灣水泥" | 完整名稱 |
| `currentPrice` | float | 最新收盤價 | 25.7 | 價格參考 |
| `regularMarketPrice` | float | 市價 | 25.7 | 同上 |
| `sector` | string | **產業別** | "M1100 水泥工業" | 🔥 產業輪動 |
| `industry` | string | 次產業 | "" | 細分產業 |
| `subIndustry` | string | 子產業 | "" | 細分產業 |
| `marketCap` | float/null | 市值 | null (需從 price 取) | 規模篩選 |
| `trailingPE` | float/null | 本益比 | null (需從 price 取) | 估值 |
| `priceToBook` | float | **股價淨值比** | 0.88 | ✅ 價值投資 |
| `forwardPE` | float/null | 預估PE | null | 估值 |
| `pegRatio` | float/null | PEG比率 | null | 成長估值 |
| `listDate` | datetime | **上市日期** | "1962-02-09" | 公司歷史 |

---

## 2️⃣ PRICE - 股價資料

**資料格式**: pandas DataFrame (JSON split format)  
**資料量**: ~485 筆 (約 2 年日資料)  
**更新頻率**: 每日

| # | 欄位名稱 | 資料類型 | 說明 | 範例值 | 策略用途 |
|---|----------|----------|------|--------|----------|
| 1 | `coid` | int | 股票代碼 | 1101 | 識別碼 |
| 2 | `mkt` | string | 市場別 | "TWSE" | 上市/上櫃 |
| 3 | `Open` | float | **開盤價** | 25.8 | K線 |
| 4 | `High` | float | **最高價** | 26.1 | K線 |
| 5 | `Low` | float | **最低價** | 25.65 | K線 |
| 6 | `Close` | float | **收盤價** | 25.7 | 🔥 核心價格 |
| 7 | `adjfac` | float | 還原調整因子 | 1.0 | 還原價計算 |
| 8 | `Volume` | int | **成交量 (股)** | 27607000 | 🔥 流動性過濾 |
| 9 | `amt` | int | 成交金額 | 713014802 | 成交值 |
| 10 | `trn` | int | 成交筆數 | 5697 | 散戶參與度 |
| 11 | `bid` | float | 買進價 | 25.65 | 買賣價差 |
| 12 | `offer` | float | 賣出價 | 25.7 | 買賣價差 |
| 13 | `avgprc` | float | 均價 | 25.83 | 成本估算 |
| 14 | `roi` | float | **日報酬率 (%)** | -0.39 | 🔥 動能計算 |
| 15 | `hmlpct` | float | 振幅 (%) | 1.74 | 波動度 |
| 16 | `turnover` | float | **週轉率 (%)** | 0.367 | 🔥 流動性 |
| 17 | `shares` | int | 流通股數 (千股) | 7523182 | 股本 |
| 18 | `mktcap` | int | **市值** | 193345771000 | 🔥 規模篩選 |
| 19 | `mktcap_pct` | float | 市值佔比 (%) | 0.19 | 大盤權重 |
| 20 | `amt_pct` | float | 成交佔比 (%) | 0.11 | 市場熱度 |
| 21 | `per` | float | **本益比 (PE)** | NaN | ✅ 估值分析 |
| 22 | `pbr` | float | **股價淨值比 (PB)** | 0.88 | ✅ 估值分析 |
| 23 | `div_yid` | float | **殖利率 (%)** | 3.89 | 💰 股利策略 |
| 24 | `cdiv_yid` | float | 現金殖利率 (%) | 3.91 | 股利策略 |
| 25 | `adjfac_a` | int | 年度調整因子 | 1 | 還原價 |
| 26 | `per_tej` | float | PE (TEJ算法) | NaN | 估值 |
| 27 | `pbr_tej` | float | PB (TEJ算法) | 0.87 | 估值 |
| 28 | `psr_tej` | float | **PSR (股價營收比)** | 1.22 | 🔥 成長股估值 |

### 可計算的價格衍生指標

| 指標 | 計算方式 | 說明 |
|------|----------|------|
| **MA5/10/20/60/120/240** | `Close.rolling(n).mean()` | 移動平均線 |
| **RSI** | `delta.gain.ewm() / delta.loss.ewm()` | 相對強弱指標 |
| **MACD** | `EMA12 - EMA26` | 趨勢指標 |
| **布林通道** | `MA20 ± 2*std(20)` | 波動區間 |
| **ATR** | `TR.rolling(14).mean()` | 平均真實範圍 |
| **動能 N日** | `(Close - Close.shift(N)) / Close.shift(N)` | N日報酬 |
| **相對強度 RS** | `Stock_Return / Index_Return` | 相對大盤強弱 |
| **52週新高距離** | `(52W_High - Close) / 52W_High` | 離高點距離 |

---

## 3️⃣ FINANCIALS - 損益表

**資料格式**: pandas DataFrame (rows=科目, columns=季度)  
**資料量**: ~15 季 (約 4 年季報)  
**更新頻率**: 每季

| # | 科目名稱 | 單位 | 說明 | 範例值 (千元) | 策略用途 |
|---|----------|------|------|--------------|----------|
| 1 | `Total Revenue` | 千元 | **營業收入** | 280,567,870 | 🔥 營收分析 |
| 2 | `Revenue` | 千元 | 營業收入 | 280,567,870 | 同上 |
| 3 | `Gross Profit` | 千元 | **毛利** | 31,500,612 | 🔥 GPM 計算 |
| 4 | `Operating Income` | 千元 | 營業淨利 | N/A | OPM 計算 |
| 5 | `EBIT` | 千元 | 營業利益 | N/A | 獲利能力 |
| 6 | `Net Income` | 千元 | **稅後淨利** | 465,945 | 🔥 EPS/ROE |
| 7 | `Net Income Common Stockholders` | 千元 | 歸屬母公司淨利 | 465,945 | 核心獲利 |
| 8 | `Pretax Income` | 千元 | 稅前淨利 | N/A | 稅前獲利 |
| 9 | `Research And Development` | 千元 | 研發費用 | N/A | R&D 動能 |
| 10 | `TEJ_GPM` | % | **毛利率 (TEJ 算好)** | 20 | ✅ 核心指標 |
| 11 | `TEJ_OPM` | % | **營益率 (TEJ 算好)** | 9 | ✅ 核心指標 |
| 12 | `Inventory Turnover` | 次 | 存貨週轉率 | 8 | 營運效率 |
| 13 | `Inventory Days` | 天 | **存貨天數 (DOI)** | 44 | 🔥 庫存風險 |
| 14 | `Days Sales Outstanding` | 天 | **應收帳款天數 (DSO)** | 50 | 🔥 收款風險 |
| 15 | `Days Payable` | 天 | 應付帳款天數 | 36 | 付款能力 |

### 可計算的損益衍生指標

| 指標 | 計算方式 | 說明 |
|------|----------|------|
| **GPM (毛利率)** | `Gross Profit / Revenue` | 或直接用 `TEJ_GPM` |
| **OPM (營益率)** | `Operating Income / Revenue` | 或直接用 `TEJ_OPM` |
| **NPM (淨利率)** | `Net Income / Revenue` | 淨利能力 |
| **GPM Slope (YoY)** | `GPM_Q - GPM_Q-4` | 🔥 結構性擴張 |
| **OPM Slope (YoY)** | `OPM_Q - OPM_Q-4` | 🔥 結構性擴張 |
| **營運槓桿** | `OPM_Slope / GPM_Slope` | 規模效益 |
| **營收成長 YoY** | `(Rev_Q - Rev_Q-4) / Rev_Q-4` | 營收動能 |

---

## 4️⃣ BALANCE_SHEET - 資產負債表

**資料格式**: pandas DataFrame (rows=科目, columns=季度)  
**資料量**: ~12 季 (約 3 年)  
**更新頻率**: 每季

| # | 科目名稱 | 單位 | 說明 | 範例值 (千元) | 策略用途 |
|---|----------|------|------|--------------|----------|
| 1 | `Total Assets` | 千元 | **資產總額** | 581,076,431 | 🔥 ROA 分母 |
| 2 | `Total Debt` | 千元 | **負債總額** | 300,508,561 | 槓桿分析 |
| 3 | `Total Liabilities Net Minority Interest` | 千元 | 負債淨額 | 300,508,561 | 同上 |
| 4 | `Current Assets` | 千元 | 流動資產 | 94,125,885 | 流動性 |
| 5 | `Total Current Assets` | 千元 | 流動資產合計 | 94,125,885 | 同上 |
| 6 | `Current Liabilities` | 千元 | 流動負債 | N/A | 短期償債 |
| 7 | `Total Current Liabilities` | 千元 | 流動負債合計 | N/A | 同上 |
| 8 | `Accounts Receivable` | 千元 | **應收帳款** | 7,525,849 | 🔥 DSO 計算 |
| 9 | `Inventory` | 千元 | 存貨 | N/A | DOI 計算 |
| 10 | `Total Inventory` | 千元 | 存貨合計 | N/A | 同上 |
| 11 | `Long Term Debt` | 千元 | 長期負債 | N/A | 槓桿分析 |
| 12 | `Cash And Cash Equivalents` | 千元 | 現金及約當現金 | N/A | 現金部位 |

### 可計算的資產負債衍生指標

| 指標 | 計算方式 | 說明 |
|------|----------|------|
| **ROE** | `Net Income TTM / Avg Equity` | 🔥 股東權益報酬率 |
| **ROA** | `Net Income TTM / Total Assets` | 資產報酬率 |
| **負債比** | `Total Debt / Total Assets` | 財務槓桿 |
| **流動比率** | `Current Assets / Current Liabilities` | 短期償債能力 |
| **速動比率** | `(Current Assets - Inventory) / Current Liabilities` | 快速償債 |
| **權益** | `Total Assets - Total Debt` | 股東權益 |
| **BPS (每股淨值)** | `Equity / Shares` | 帳面價值 |

---

## 5️⃣ CASHFLOW - 現金流量表

**資料格式**: pandas DataFrame (rows=科目, columns=季度)  
**資料量**: ~4 季 (約 1 年)  
**更新頻率**: 每季

| # | 科目名稱 | 單位 | 說明 | 範例值 (千元) | 策略用途 |
|---|----------|------|------|--------------|----------|
| 1 | `Operating Cash Flow` | 千元 | **營業活動現金流** | 35,872,859 | 🔥 OCF/獲利品質 |
| 2 | `Investing Cash Flow` | 千元 | 投資活動現金流 | N/A | CapEx 估算 |
| 3 | `Financing Cash Flow` | 千元 | 籌資活動現金流 | N/A | 財務策略 |
| 4 | `Capital Expenditure` | 千元 | 資本支出 | N/A | FCF 計算 |

### 可計算的現金流衍生指標

| 指標 | 計算方式 | 說明 |
|------|----------|------|
| **CCR (現金覆蓋率)** | `OCF / Net Income` | 🔥 盈餘品質 (>1 為佳) |
| **FCF (自由現金流)** | `OCF - CapEx` | 🔥 或 `OCF - abs(ICF)` |
| **FCF Yield** | `FCF / Market Cap` | 自由現金流殖利率 |
| **Sloan Ratio** | `(NI - OCF - ICF) / Total Assets` | 盈餘品質 (<0.1 為佳) |

---

## 6️⃣ CHIP - 籌碼資料

**資料格式**: pandas DataFrame  
**資料量**: ~42 日 (約 2 個月)  
**更新頻率**: 每日

| # | 欄位名稱 | 資料類型 | 說明 | 範例值 | 策略用途 |
|---|----------|----------|------|--------|----------|
| 1 | `mdate` | datetime | 交易日期 | 2026-02-05 | 時間索引 |
| 2 | `qfii_ex` | int | **外資買賣超 (張)** | -721 | 🔥 法人動向 |
| 3 | `fund_ex` | int | **投信買賣超 (張)** | 28 | 🔥 法人動向 |
| 4 | `qfii_pct` | float | **外資持股比例 (%)** | 18.11 | 🔥 籌碼集中度 |
| 5 | `fd_pct` | float | 投信持股比例 (%) | 0.19 | 籌碼分析 |
| 6 | `tot_ex` | int | **三大法人合計買賣超** | -582 | 🔥 總體法人 |
| 7 | `long_t` | int | **融資餘額 (張)** | 35974 | 🔥 散戶情緒 |
| 8 | `short_t` | int | 融券餘額 (張) | 325 | 放空部位 |
| 9 | `s_l_pct` | float | **券資比 (%)** | 0.9 | 🔥 軋空指標 |
| 10 | `dlr_pct` | float | 自營商持股比例 (%) | 0.0 | 自營動向 |

### 可計算的籌碼衍生指標

| 指標 | 計算方式 | 說明 |
|------|----------|------|
| **外資連買天數** | `(qfii_ex > 0).rolling().sum()` | 法人認同度 |
| **外資 N 日累積** | `qfii_ex.rolling(N).sum()` | 近期動向 |
| **投信 N 日累積** | `fund_ex.rolling(N).sum()` | 近期動向 |
| **融資增減** | `long_t - long_t.shift(1)` | 散戶進出 |
| **融資比例** | `long_t / shares * 1000` | 散戶槓桿 |
| **籌碼趨勢** | 外資+投信買超組合 | 雙多/雙空/外資主導... |

---

## 7️⃣ MONTHLY_SALES - 月營收

**資料格式**: pandas DataFrame  
**資料量**: ~14 月 (約 1 年)  
**更新頻率**: 每月10日

| # | 欄位名稱 | 資料類型 | 說明 | 範例值 | 策略用途 |
|---|----------|----------|------|--------|----------|
| 1 | `mdate` | datetime | 營收月份 | 2025-12-01 | 時間索引 |
| 2 | `d0001` | int | **當月營收 (千元)** | 16,502,520 | 🔥 即時營收 |
| 3 | `d0002` | int | 去年同月營收 | 8,786,909 | YoY 基準 |
| 4 | `d0003` | float | **月營收 YoY (%)** | 87.81 | 🔥 成長動能 |
| 5 | `d0004` | float | **月營收 MoM (%)** | 1.42 | 環比變化 |
| 6 | `d0005` | int | **累計營收 (YTD)** | 138,365,933 | 年度進度 |
| 7 | `d0006` | int | 去年累計營收 | 99,100,658 | YoY 基準 |

### 可計算的月營收衍生指標

| 指標 | 計算方式 | 說明 |
|------|----------|------|
| **營收加速度** | `YoY_M - YoY_M-1` | 🔥 成長是否加速 |
| **營收 3MA** | `d0001.rolling(3).mean()` | 平滑營收 |
| **營收創高** | `d0001 == d0001.rolling(12).max()` | 12個月新高 |
| **累計 YoY** | `(d0005 - d0006) / d0006 * 100` | 年度成長 |

---

## 📊 可計算的衍生指標 - 完整清單

### 動能類 (Momentum)

| 指標名稱 | 計算公式 | 資料來源 |
|----------|----------|----------|
| `Return_1D` | `Close / Close.shift(1) - 1` | PRICE |
| `Return_1W` | `Close / Close.shift(5) - 1` | PRICE |
| `Return_1M` | `Close / Close.shift(20) - 1` | PRICE |
| `Return_3M` | `Close / Close.shift(60) - 1` | PRICE |
| `Return_6M` | `Close / Close.shift(120) - 1` | PRICE |
| `Return_12M` | `Close / Close.shift(240) - 1` | PRICE |
| `Momentum_12_1` | `Return_12M - Return_1M` | PRICE |
| `RS_Ratio` | `Stock_Return / Index_Return` | PRICE |
| `RSI_14` | `100 - 100/(1 + RS)` | PRICE |
| `MACD` | `EMA12 - EMA26` | PRICE |

### 估值類 (Valuation)

| 指標名稱 | 計算公式 | 資料來源 |
|----------|----------|----------|
| `PE` | 直接使用 `per` | PRICE |
| `PB` | 直接使用 `pbr` | PRICE |
| `PSR` | 直接使用 `psr_tej` | PRICE |
| `Dividend_Yield` | 直接使用 `div_yid` | PRICE |
| `PE_Percentile` | `PE 在歷史中的百分位` | PRICE |
| `PB_Percentile` | `PB 在歷史中的百分位` | PRICE |
| `FCF_Yield` | `FCF / mktcap` | CASHFLOW + PRICE |

### 品質類 (Quality)

| 指標名稱 | 計算公式 | 資料來源 |
|----------|----------|----------|
| `GPM` | 直接使用 `TEJ_GPM` | FINANCIALS |
| `OPM` | 直接使用 `TEJ_OPM` | FINANCIALS |
| `ROE` | `NI_TTM / Avg_Equity` | FINANCIALS + BALANCE |
| `ROA` | `NI_TTM / Total_Assets` | FINANCIALS + BALANCE |
| `CCR` | `OCF / Net_Income` | CASHFLOW + FINANCIALS |
| `Sloan_Ratio` | `(NI - OCF - ICF) / TA` | CASHFLOW + BALANCE |
| `F_Score` | Piotroski 9 點評分 | 多表合計 |

### 結構類 (Structural)

| 指標名稱 | 計算公式 | 資料來源 |
|----------|----------|----------|
| `GPM_Slope` | `GPM_Q - GPM_Q-4` | FINANCIALS |
| `OPM_Slope` | `OPM_Q - OPM_Q-4` | FINANCIALS |
| `Operating_Leverage` | `OPM_Slope / GPM_Slope` | FINANCIALS |
| `Rev_YoY` | `(Rev_Q - Rev_Q-4) / Rev_Q-4` | FINANCIALS |
| `Rev_Acceleration` | `Rev_YoY_Q - Rev_YoY_Q-1` | FINANCIALS |
| `Monthly_Rev_YoY` | 直接使用 `d0003` | MONTHLY_SALES |
| `Monthly_Rev_Acc` | `d0003_M - d0003_M-1` | MONTHLY_SALES |

### 籌碼類 (Chip)

| 指標名稱 | 計算公式 | 資料來源 |
|----------|----------|----------|
| `QFII_Net_5D` | `qfii_ex.rolling(5).sum()` | CHIP |
| `QFII_Net_20D` | `qfii_ex.rolling(20).sum()` | CHIP |
| `Fund_Net_5D` | `fund_ex.rolling(5).sum()` | CHIP |
| `Fund_Net_20D` | `fund_ex.rolling(20).sum()` | CHIP |
| `Margin_Change` | `long_t - long_t.shift(1)` | CHIP |
| `Short_Ratio` | `s_l_pct` | CHIP |

---

## 🎯 策略應用對照表

### 策略 → 所需資料

| 策略類型 | 核心資料 | 主要指標 | 資料表 |
|----------|----------|----------|--------|
| **動能策略** | 價格 | Return_12M, RS_Ratio, Momentum_12_1 | PRICE |
| **價值策略** | 價格+財報 | PE, PB, PSR, PE_Percentile | PRICE |
| **品質策略** | 財報+現金流 | ROE, F_Score, CCR, Sloan_Ratio | FINANCIALS, CASHFLOW |
| **成長策略** | 月營收 | Rev_YoY, Rev_Acceleration | MONTHLY_SALES |
| **結構拐點** | 財報 | GPM_Slope, OPM_Slope, Op_Leverage | FINANCIALS |
| **籌碼策略** | 籌碼 | QFII_Net, Fund_Net, Margin_Change | CHIP |
| **高殖利率** | 價格 | div_yid, Dividend_Growth | PRICE |
| **複合策略** | 全部 | 多因子加權 | ALL |

### 常見策略範例

#### 1. 動能 + 品質

```
篩選條件:
  - Return_12M > 20%
  - RS_Ratio > 1.0
  - F_Score >= 6
  - CCR > 0.8
```

#### 2. 價值 + 結構拐點

```
篩選條件:
  - PE_Percentile < 50%
  - GPM_Slope > 0
  - OPM_Slope > 0
  - ROE > 10%
```

#### 3. 營收動能 + 法人買超

```
篩選條件:
  - Monthly_Rev_YoY > 10%
  - Rev_Acceleration > 0
  - QFII_Net_20D > 0 OR Fund_Net_20D > 0
```

---

## 📝 資料注意事項

### 1. 缺值處理

| 資料表 | 常見缺值 | 建議處理 |
|--------|----------|----------|
| PRICE | `per`, `per_tej` (虧損公司) | 使用 PB 替代 |
| FINANCIALS | `Operating Income`, `EBIT` | 用 `TEJ_OPM * Revenue` 估算 |
| BALANCE | `Current Liabilities`, `Inventory` | 跳過相關指標 |
| CASHFLOW | `Investing Cash Flow`, `CapEx` | 用 OCF 近似 FCF |

### 2. 單位統一

| 資料類型 | 原始單位 | 建議統一 |
|----------|----------|----------|
| Volume | 股 | 張 (÷1000) |
| 財報金額 | 千元 | 百萬元 (÷1000) |
| 比率 | % | 小數 (÷100) 或保持 % |

### 3. 資料時效

| 資料表 | 更新頻率 | 延遲 |
|--------|----------|------|
| PRICE | 每日 | T+0 |
| CHIP | 每日 | T+0 |
| MONTHLY_SALES | 每月10日 | 約10天 |
| FINANCIALS | 每季 | 45天內 |

---

*文件由 Investment AI Platform 自動生成*  
*最後更新: 2026-02-06*
