# 📋 欄位速查表 (Field Quick Reference)

> 一頁看完你能用的所有資料欄位

---

## 🔥 最常用欄位 TOP 30

| # | 欄位名稱 | 來源 | 說明 | 策略用途 |
|---|----------|------|------|----------|
| 1 | `Close` | PRICE | 收盤價 | 價格基準、技術分析 |
| 2 | `Volume` | PRICE | 成交量 (股) | 流動性過濾 |
| 3 | `mktcap` | PRICE | 市值 | 規模篩選 |
| 4 | `per` | PRICE | 本益比 PE | 估值分析 |
| 5 | `pbr` | PRICE | 股價淨值比 PB | 估值分析 |
| 6 | `psr_tej` | PRICE | 股價營收比 PSR | 成長股估值 |
| 7 | `div_yid` | PRICE | 殖利率 % | 股利策略 |
| 8 | `roi` | PRICE | 日報酬率 % | 動能計算 |
| 9 | `turnover` | PRICE | 週轉率 % | 流動性 |
| 10 | `TEJ_GPM` | FINANCIALS | 毛利率 % | 獲利品質 |
| 11 | `TEJ_OPM` | FINANCIALS | 營益率 % | 核心獲利 |
| 12 | `Net Income` | FINANCIALS | 稅後淨利 | EPS/ROE |
| 13 | `Total Revenue` | FINANCIALS | 營業收入 | 營收分析 |
| 14 | `Gross Profit` | FINANCIALS | 毛利 | GPM 計算 |
| 15 | `Inventory Days` | FINANCIALS | 存貨天數 | 庫存風險 |
| 16 | `Days Sales Outstanding` | FINANCIALS | 應收帳款天數 | 收款風險 |
| 17 | `Total Assets` | BALANCE | 資產總額 | ROA 分母 |
| 18 | `Total Debt` | BALANCE | 負債總額 | 槓桿分析 |
| 19 | `Accounts Receivable` | BALANCE | 應收帳款 | DSO 計算 |
| 20 | `Operating Cash Flow` | CASHFLOW | 營業現金流 OCF | 獲利品質 |
| 21 | `qfii_ex` | CHIP | 外資買賣超 (張) | 法人動向 |
| 22 | `fund_ex` | CHIP | 投信買賣超 (張) | 法人動向 |
| 23 | `qfii_pct` | CHIP | 外資持股比例 % | 籌碼集中 |
| 24 | `tot_ex` | CHIP | 三大法人合計 | 總體法人 |
| 25 | `long_t` | CHIP | 融資餘額 (張) | 散戶情緒 |
| 26 | `s_l_pct` | CHIP | 券資比 % | 軋空指標 |
| 27 | `d0001` | MONTHLY_SALES | 當月營收 (千元) | 即時營收 |
| 28 | `d0003` | MONTHLY_SALES | 月營收 YoY % | 成長動能 |
| 29 | `d0004` | MONTHLY_SALES | 月營收 MoM % | 環比變化 |
| 30 | `sector` | INFO | 產業別 | 產業輪動 |

---

## 📊 完整欄位清單 (按資料表分類)

### PRICE - 股價資料 (28 欄)

```
基本價格:
├── Open          開盤價
├── High          最高價
├── Low           最低價
├── Close         收盤價 ⭐
└── adjfac        還原因子

成交資訊:
├── Volume        成交量 (股) ⭐
├── amt           成交金額
├── trn           成交筆數
├── avgprc        均價
└── turnover      週轉率 % ⭐

市場指標:
├── mktcap        市值 ⭐
├── mktcap_pct    市值佔比 %
├── amt_pct       成交佔比 %
└── shares        流通股數

估值指標:
├── per           本益比 PE ⭐
├── pbr           股價淨值比 PB ⭐
├── psr_tej       股價營收比 PSR ⭐
├── per_tej       PE (TEJ版)
└── pbr_tej       PB (TEJ版)

殖利率:
├── div_yid       殖利率 % ⭐
└── cdiv_yid      現金殖利率 %

報酬:
├── roi           日報酬率 %
└── hmlpct        振幅 %

其他:
├── coid          股票代碼
├── mkt           市場別 (TWSE/OTC)
├── bid           買進價
├── offer         賣出價
└── adjfac_a      年度調整因子
```

### FINANCIALS - 損益表 (15 欄)

```
營收獲利:
├── Total Revenue         營業收入 ⭐
├── Revenue               營業收入 (同上)
├── Gross Profit          毛利 ⭐
├── Operating Income      營業淨利
├── EBIT                  營業利益
├── Net Income            稅後淨利 ⭐
├── Net Income Common     歸屬母公司淨利
├── Pretax Income         稅前淨利
└── Research And Dev      研發費用

TEJ 計算好的比率:
├── TEJ_GPM               毛利率 % ⭐
└── TEJ_OPM               營益率 % ⭐

效率指標:
├── Inventory Turnover    存貨週轉率 (次)
├── Inventory Days        存貨天數 ⭐
├── Days Sales Out        應收帳款天數 ⭐
└── Days Payable          應付帳款天數
```

### BALANCE_SHEET - 資產負債表 (12 欄)

```
資產:
├── Total Assets          資產總額 ⭐
├── Current Assets        流動資產
├── Total Current Assets  流動資產合計
├── Cash And Equivalents  現金
├── Accounts Receivable   應收帳款 ⭐
├── Inventory             存貨
└── Total Inventory       存貨合計

負債:
├── Total Debt            負債總額 ⭐
├── Total Liabilities     負債淨額
├── Current Liabilities   流動負債
├── Total Current Liab    流動負債合計
└── Long Term Debt        長期負債
```

### CASHFLOW - 現金流量表 (4 欄)

```
├── Operating Cash Flow   營業現金流 OCF ⭐
├── Investing Cash Flow   投資現金流 ICF
├── Financing Cash Flow   籌資現金流
└── Capital Expenditure   資本支出 CapEx
```

### CHIP - 籌碼資料 (10 欄)

```
法人買賣超:
├── qfii_ex       外資買賣超 (張) ⭐
├── fund_ex       投信買賣超 (張) ⭐
├── tot_ex        三大法人合計 ⭐
├── dlr_pct       自營商持股 %

持股比例:
├── qfii_pct      外資持股比例 % ⭐
└── fd_pct        投信持股比例 %

融資融券:
├── long_t        融資餘額 (張) ⭐
├── short_t       融券餘額 (張)
└── s_l_pct       券資比 % ⭐

時間:
└── mdate         交易日期
```

### MONTHLY_SALES - 月營收 (7 欄)

```
├── mdate         營收月份
├── d0001         當月營收 (千元) ⭐
├── d0002         去年同月營收
├── d0003         月營收 YoY % ⭐
├── d0004         月營收 MoM % ⭐
├── d0005         累計營收 YTD
└── d0006         去年累計營收
```

### INFO - 公司基本資料 (14 欄)

```
識別:
├── symbol        股票代碼
├── shortName     股票簡稱
├── longName      公司全名
└── listDate      上市日期

產業:
├── sector        產業別 ⭐
├── industry      次產業
└── subIndustry   子產業

即時估值:
├── currentPrice      最新價
├── regularMarketPrice 市價
├── marketCap         市值
├── trailingPE        本益比
├── priceToBook       股價淨值比 ⭐
├── forwardPE         預估PE
└── pegRatio          PEG
```

---

## 🧮 可衍生計算的指標

### 動能因子 (從 PRICE 計算)

| 指標 | 公式 |
|------|------|
| Return_1M | `Close / Close.shift(20) - 1` |
| Return_3M | `Close / Close.shift(60) - 1` |
| Return_6M | `Close / Close.shift(120) - 1` |
| Return_12M | `Close / Close.shift(240) - 1` |
| Momentum_12_1 | `Return_12M - Return_1M` |
| RS_Ratio | `Stock_Return / Benchmark_Return` |
| MA5/10/20/60 | `Close.rolling(N).mean()` |
| RSI_14 | 標準 RSI 公式 |
| MACD | `EMA12 - EMA26` |

### 估值因子 (從 PRICE 計算)

| 指標 | 公式 |
|------|------|
| PE_Percentile | `per 在歷史中的百分位` |
| PB_Percentile | `pbr 在歷史中的百分位` |
| FCF_Yield | `FCF / mktcap` |

### 品質因子 (從 FINANCIALS + CASHFLOW 計算)

| 指標 | 公式 |
|------|------|
| ROE | `Net Income TTM / Equity` |
| ROA | `Net Income TTM / Total Assets` |
| CCR | `OCF / Net Income` |
| Sloan | `(NI - OCF - ICF) / TA` |
| F_Score | Piotroski 9 點評分 |

### 結構因子 (從 FINANCIALS 計算)

| 指標 | 公式 |
|------|------|
| GPM_Slope | `TEJ_GPM[Q] - TEJ_GPM[Q-4]` |
| OPM_Slope | `TEJ_OPM[Q] - TEJ_OPM[Q-4]` |
| Op_Leverage | `OPM_Slope / GPM_Slope` |
| Rev_YoY | `(Revenue[Q] - Revenue[Q-4]) / Revenue[Q-4]` |

### 籌碼因子 (從 CHIP 計算)

| 指標 | 公式 |
|------|------|
| QFII_Net_5D | `qfii_ex.rolling(5).sum()` |
| QFII_Net_20D | `qfii_ex.rolling(20).sum()` |
| Fund_Net_20D | `fund_ex.rolling(20).sum()` |
| Margin_Change | `long_t - long_t.shift(1)` |

### 營收因子 (從 MONTHLY_SALES 計算)

| 指標 | 公式 |
|------|------|
| Rev_YoY_Monthly | 直接用 `d0003` |
| Rev_MoM_Monthly | 直接用 `d0004` |
| Rev_Acceleration | `d0003[M] - d0003[M-1]` |
| Rev_3MA | `d0001.rolling(3).mean()` |

---

## 📌 欄位命名對照 (TEJ 原始名稱 vs 系統名稱)

| TEJ 原始 | 系統名稱 | 說明 |
|----------|----------|------|
| `close_d` | `Close` | 收盤價 |
| `open_d` | `Open` | 開盤價 |
| `high_d` | `High` | 最高價 |
| `low_d` | `Low` | 最低價 |
| `vol` | `Volume` | 成交量 |
| `r105` | `TEJ_GPM` | 毛利率 |
| `r106` | `TEJ_OPM` | 營益率 |
| `a3100` | `Total Revenue` | 營業收入 |
| `a2402` | `Net Income` | 稅後淨利 |
| `a7210` | `Operating Cash Flow` | 營業現金流 |
| `a0010` | `Total Assets` | 資產總額 |
| `a1000` | `Total Debt` | 負債總額 |

---

## 🎯 策略對應速查

| 我要做... | 需要的欄位 | 資料表 |
|-----------|------------|--------|
| 動能策略 | Close, roi | PRICE |
| 價值投資 | per, pbr, psr_tej | PRICE |
| 品質篩選 | TEJ_GPM, TEJ_OPM, Net Income | FINANCIALS |
| 現金流分析 | Operating Cash Flow | CASHFLOW |
| 跟著法人 | qfii_ex, fund_ex | CHIP |
| 營收成長 | d0003, d0001 | MONTHLY_SALES |
| 高殖利率 | div_yid | PRICE |
| 結構拐點 | TEJ_GPM, TEJ_OPM (多季) | FINANCIALS |
| 產業輪動 | sector | INFO |
| 流動性過濾 | Volume, turnover | PRICE |

---

*欄位總數統計:*
- **PRICE**: 28 欄
- **FINANCIALS**: 15 欄
- **BALANCE_SHEET**: 12 欄  
- **CASHFLOW**: 4 欄
- **CHIP**: 10 欄
- **MONTHLY_SALES**: 7 欄
- **INFO**: 14 欄
- **總計**: 90 個原始欄位 + 無限衍生指標 🚀
