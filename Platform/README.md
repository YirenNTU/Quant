# 📊 Investment AI Platform

一個讓朋友們可以輕鬆使用的量化交易平台。

---

## 🚀 快速開始

### 1. 載入平台

```python
import sys
sys.path.insert(0, '/path/to/Investment_AI')

from Platform import FieldDB, Strategy, Backtester, get_allocation
from Platform.Factors import *
```

### 2. 建立你的策略

```python
class MyStrategy(Strategy):
    name = "我的策略"
    
    def compute(self, db):
        close = db.get('close')
        return zscore(ts_pct_change(close, 20))

# 回測
result = Backtester.run(MyStrategy())
print(result.summary())

# 取得配置
allocation = get_allocation(MyStrategy(), capital=1_000_000)
print(allocation)
```

### 3. 命令列使用

```bash
# 列出可用策略
python -m Platform list

# 回測
python -m Platform backtest momentum

# 取得配置
python -m Platform allocate combined --capital 1000000

# 執行自訂策略
python -m Platform run my_strategy.py --backtest --allocate
```

---

## 📁 資料庫 (FieldDB)

### 資料來源

資料來自 **TEJ API (初入江湖版)**，透過 `data_downloader.py` 下載並儲存於 `Stock_Pool/Database/`。

### 可用資料欄位 (83 個) 🆕

```python
from Platform import FieldDB
db = FieldDB()

# 取得所有公司某欄位
close = db.get('close')           # DataFrame (485天 × 158家)

# 取得單一公司某欄位
tsmc_close = db.get('close', '2330')  # Series

# 季報/月報資料會自動對齊到日報日期
ocf = db.get('ocf')               # 自動 reindex + ffill
sa_eps = db.get('sa_eps')         # 🆕 自結數 EPS
```

---

### 📈 Price 價格類 (21 個) - 完整度 99%+

| 欄位 | 說明 | 範例 |
|-----|------|------|
| `open` | 開盤價 | `db.get('open')` |
| `high` | 最高價 | `db.get('high')` |
| `low` | 最低價 | `db.get('low')` |
| `close` | 收盤價 | `db.get('close')` |
| `volume` | 成交量(股) | `db.get('volume')` |
| `amount` | 成交金額 | `db.get('amount')` |
| `trades` | 成交筆數 | `db.get('trades')` |
| `turnover` | 週轉率% | `db.get('turnover')` |
| `mktcap` | 市值 | `db.get('mktcap')` |
| `shares` | 流通股數 | `db.get('shares')` |
| `pe` | 本益比 | `db.get('pe')` |
| `pb` | 股價淨值比 | `db.get('pb')` |
| `psr` | 股價營收比 | `db.get('psr')` |
| `pe_tej` | PE(TEJ) | `db.get('pe_tej')` |
| `pb_tej` | PB(TEJ) | `db.get('pb_tej')` |
| `div_yield` | 殖利率% | `db.get('div_yield')` |
| `cdiv_yield` | 現金殖利率% | `db.get('cdiv_yield')` |
| `daily_return` | 日報酬率% | `db.get('daily_return')` |
| `amplitude` | 振幅% | `db.get('amplitude')` |
| `avgprc` | 均價 | `db.get('avgprc')` |
| `adjfac` | 還原因子 | `db.get('adjfac')` |

---

### 📊 Financials 財報類 (9 個) - 完整度 80%+

| 欄位 | 說明 | 範例 |
|-----|------|------|
| `revenue` | 營業收入 | `db.get('revenue')` |
| `gross_profit` | 毛利 | `db.get('gross_profit')` |
| `net_income` | 稅後淨利 | `db.get('net_income')` |
| `tej_gpm` | 毛利率% | `db.get('tej_gpm')` |
| `tej_opm` | 營益率% | `db.get('tej_opm')` |
| `inventory_turnover` | 存貨週轉率 | `db.get('inventory_turnover')` |
| `inventory_days` | 存貨天數 | `db.get('inventory_days')` |
| `dso` | 應收帳款天數 | `db.get('dso')` |
| `days_payable` | 應付帳款天數 | `db.get('days_payable')` |

---

### 🏦 Balance Sheet 資產負債類 (5 個) - 完整度 80%+

| 欄位 | 說明 | 範例 |
|-----|------|------|
| `total_assets` | 資產總額 | `db.get('total_assets')` |
| `total_debt` | 負債總額 | `db.get('total_debt')` |
| `total_liabilities` | 總負債 | `db.get('total_liabilities')` |
| `current_assets` | 流動資產 | `db.get('current_assets')` |
| `accounts_receivable` | 應收帳款 | `db.get('accounts_receivable')` |

> ⚠️ **TEJ 初入江湖版限制**：無存貨(Inventory)、現金(Cash)、流動負債細項

---

### 💰 Cashflow 現金流類 (1 個) - 完整度 94%

| 欄位 | 說明 | 範例 |
|-----|------|------|
| `ocf` | 營業現金流 | `db.get('ocf')` |

> ⚠️ **TEJ 初入江湖版限制**：無 ICF、FCF、CAPEX

---

### 🎯 Chip 籌碼類 (9 個) - 完整度 100%

| 欄位 | 說明 | 範例 |
|-----|------|------|
| `qfii_net` | 外資買賣超(張) | `db.get('qfii_net')` |
| `fund_net` | 投信買賣超(張) | `db.get('fund_net')` |
| `dealer_net` | 三大法人合計 | `db.get('dealer_net')` |
| `qfii_pct` | 外資持股% | `db.get('qfii_pct')` |
| `fund_pct` | 投信持股% | `db.get('fund_pct')` |
| `dealer_pct` | 自營商持股% | `db.get('dealer_pct')` |
| `margin_long` | 融資餘額(張) | `db.get('margin_long')` |
| `margin_short` | 融券餘額(張) | `db.get('margin_short')` |
| `short_ratio` | 券資比% | `db.get('short_ratio')` |

---

### 📅 Monthly Sales 月營收類 (7 個) - 完整度 94%

| 欄位 | 說明 | 範例 |
|-----|------|------|
| `monthly_rev` | 當月營收(千元) | `db.get('monthly_rev')` |
| `monthly_rev_alt` | 月營收(千元) | `db.get('monthly_rev_alt')` |
| `monthly_rev_yoy` | 月營收YoY% | `db.get('monthly_rev_yoy')` |
| `monthly_rev_mom` | 月營收MoM% | `db.get('monthly_rev_mom')` |
| `ytd_rev` | 累計營收(千元) | `db.get('ytd_rev')` |
| `ytd_rev_yoy` | 累計營收YoY% | `db.get('ytd_rev_yoy')` |
| `ytd_rev_yoy_pct` | 累計營收MoM% | `db.get('ytd_rev_yoy_pct')` |

---

### 💎 Dividend 股利資料 (5 個) - 🆕 新增

| 欄位 | 說明 | 範例 |
|-----|------|------|
| `cash_div` | 現金股利 | `db.get('cash_div')` |
| `stock_div` | 股票股利 | `db.get('stock_div')` |
| `div_type` | 配息類型 | `db.get('div_type')` |
| `ex_div_date` | 除息日 | `db.get('ex_div_date')` |
| `pay_date` | 發放日 | `db.get('pay_date')` |

**使用範例：高股息策略**
```python
# 取得現金股利
cash_div = db.get('cash_div', align=False)

# 計算殖利率
close = db.get('close')
div_yield = (cash_div / close) * 100
```

---

### 📋 Self Announced 自結數 (11 個) - 🆕 新增

**自結數比季報更即時！** 公司自行公布的財務數據，通常比正式財報早 1-2 個月。

| 欄位 | 說明 | 範例 |
|-----|------|------|
| `sa_revenue` | 自結營收 | `db.get('sa_revenue')` |
| `sa_opi` | 自結營業利益 | `db.get('sa_opi')` |
| `sa_pretax` | 自結稅前淨利 | `db.get('sa_pretax')` |
| `sa_net_income` | 自結稅後淨利 | `db.get('sa_net_income')` |
| `sa_eps` | 自結EPS | `db.get('sa_eps')` |
| `sa_gpm` | 自結毛利率% | `db.get('sa_gpm')` |
| `sa_opm` | 自結營益率% | `db.get('sa_opm')` |
| `sa_npm` | 自結淨利率% | `db.get('sa_npm')` |
| `sa_rev_yoy` | 自結營收成長率% | `db.get('sa_rev_yoy')` |
| `sa_opi_yoy` | 自結營業利益成長率% | `db.get('sa_opi_yoy')` |
| `sa_ni_yoy` | 自結淨利成長率% | `db.get('sa_ni_yoy')` |

**使用範例：即時獲利追蹤**
```python
# 自結數 EPS (比季報更即時)
sa_eps = db.get('sa_eps')

# 自結數營益率變化
sa_opm = db.get('sa_opm')
opm_trend = ts_delta(sa_opm, 4)  # 季度變化
```

---

### 🏢 Capital 資本形成 (7 個) - 🆕 新增

| 欄位 | 說明 | 範例 |
|-----|------|------|
| `capital_amt` | 股本(千元) | `db.get('capital_amt')` |
| `shares_outstanding` | 流通股數(千股) | `db.get('shares_outstanding')` |
| `cash_increase` | 現金增資 | `db.get('cash_increase')` |
| `earning_increase` | 盈餘轉增資 | `db.get('earning_increase')` |
| `capital_reserve` | 資本公積 | `db.get('capital_reserve')` |
| `employee_bonus` | 員工紅利 | `db.get('employee_bonus')` |
| `capital_decrease` | 減資 | `db.get('capital_decrease')` |

**使用範例：股本變化分析**
```python
# 股本變化
capital = db.get('capital_amt')
capital_change = ts_pct_change(capital, 4)

# 減資訊號 (可能是利多)
capital_dec = db.get('capital_decrease')
```

---

### 🔍 Chip Extended 籌碼擴充 (8 個) - 🆕 新增

更細緻的籌碼資料，包含買/賣量、維持率等。

| 欄位 | 說明 | 範例 |
|-----|------|------|
| `qfii_buy` | 外資買進量(張) | `db.get('qfii_buy')` |
| `qfii_sell` | 外資賣出量(張) | `db.get('qfii_sell')` |
| `fund_buy` | 投信買進量(張) | `db.get('fund_buy')` |
| `fund_sell` | 投信賣出量(張) | `db.get('fund_sell')` |
| `margin_maintenance` | 融資維持率% | `db.get('margin_maintenance')` |
| `short_maintenance` | 融券維持率% | `db.get('short_maintenance')` |
| `total_maintenance` | 整戶維持率% | `db.get('total_maintenance')` |
| `stock_lending` | 借券餘額(張) | `db.get('stock_lending')` |

**使用範例：法人動向分析**
```python
# 外資買賣力道
qfii_buy = db.get('qfii_buy')
qfii_sell = db.get('qfii_sell')
qfii_strength = qfii_buy / (qfii_buy + qfii_sell)

# 融資維持率 (低於 130% 可能有斷頭風險)
margin_maint = db.get('margin_maintenance')
risk_signal = margin_maint < 130
```

---

## 🔧 運算工具 (Factors)

```python
from Platform.Factors import *
```

### 時序運算 (Time-Series)

對單一股票的時間序列進行運算：

| 函數 | 說明 | 範例 |
|-----|------|------|
| `ts_delay(data, n)` | 取 N 期前的值 | `ts_delay(close, 1)` 昨日收盤 |
| `ts_delta(data, n)` | 與 N 期前的差值 | `ts_delta(close, 5)` 5日變化 |
| `ts_pct_change(data, n)` | N 期報酬率 | `ts_pct_change(close, 20)` 20日報酬 |
| `ts_mean(data, n)` | N 日移動平均 | `ts_mean(close, 20)` MA20 |
| `ts_sum(data, n)` | N 日加總 | `ts_sum(volume, 5)` |
| `ts_std(data, n)` | N 日標準差 | `ts_std(returns, 20)` |
| `ts_max(data, n)` | N 日最高 | `ts_max(high, 20)` |
| `ts_min(data, n)` | N 日最低 | `ts_min(low, 20)` |
| `ts_rank(data, n)` | 時序排名 (0~1) | `ts_rank(close, 20)` |
| `ts_zscore(data, n)` | 時序 Z-Score | `ts_zscore(volume, 20)` |
| `ts_corr(x, y, n)` | 滾動相關係數 | `ts_corr(close, volume, 20)` |
| `ts_argmax(data, n)` | 最大值幾期前 | `ts_argmax(close, 20)` |
| `ts_argmin(data, n)` | 最小值幾期前 | `ts_argmin(close, 20)` |
| `ts_skew(data, n)` | 滾動偏態 | `ts_skew(returns, 20)` |
| `ts_kurt(data, n)` | 滾動峰態 | `ts_kurt(returns, 20)` |

### 截面運算 (Cross-Section)

對同一時間點所有股票進行運算：

| 函數 | 說明 | 範例 |
|-----|------|------|
| `rank(data)` | 截面排名 (0~1) | `rank(pe)` |
| `zscore(data)` | 截面 Z-Score | `zscore(momentum)` |
| `demean(data)` | 截面去均值 | `demean(returns)` |
| `winsorize(data, lo, hi)` | 縮尾處理 | `winsorize(pe, 0.01, 0.99)` |

### 衰減運算 (Decay)

給近期資料更高權重：

| 函數 | 說明 | 範例 |
|-----|------|------|
| `decay_linear(data, n)` | 線性衰減加權 | `decay_linear(returns, 20)` |
| `decay_exp(data, n)` | 指數衰減 (EMA) | `decay_exp(close, 20)` |
| `decay_power(data, n, p)` | 冪次衰減 | `decay_power(volume, 10, 2)` |

### 組合因子

| 函數 | 說明 | 範例 |
|-----|------|------|
| `momentum(data, n)` | 動量因子 | `momentum(close, 20)` |
| `volatility(data, n)` | 波動率 | `volatility(close, 20)` |
| `rsi(data, n)` | RSI 指標 | `rsi(close, 14)` |
| `bollinger_position(data, n)` | 布林通道位置 | `bollinger_position(close, 20)` |

---

## 📝 策略撰寫範本

### 基本範本

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from Platform.Strategies import Strategy
from Platform.Factors import *


class MyStrategy(Strategy):
    """策略描述"""
    
    name = "我的策略"
    description = "策略說明"
    version = "1.0"
    author = "你的名字"
    
    params = {
        "lookback": 20,
        "top_n": 10,
    }
    
    def compute(self, db):
        """計算因子分數 (必須實作)"""
        close = db.get('close')
        return zscore(ts_pct_change(close, self.params["lookback"]))


if __name__ == '__main__':
    from Platform import quick_test
    quick_test(MyStrategy)
```

### 完整範例：動量 + 價值 + 籌碼

```python
from Platform.Strategies import Strategy
from Platform.Factors import *


class MultiFactorStrategy(Strategy):
    name = "多因子策略"
    description = "結合動量、價值、籌碼"
    
    params = {
        "mom_weight": 0.4,
        "val_weight": 0.3,
        "chip_weight": 0.3,
        "lookback": 20,
        "top_n": 10,
    }
    
    def compute(self, db):
        # 載入資料
        close = db.get('close')
        pe = db.get('pe')           # 日報資料
        qfii = db.get('qfii_net')   # 籌碼資料 (會自動對齊)
        
        # === 動量因子 ===
        momentum = ts_pct_change(close, self.params["lookback"])
        mom_score = zscore(momentum)
        
        # === 價值因子 ===
        val_score = zscore(-pe.ffill())
        
        # === 籌碼因子 ===
        chip_score = zscore(qfii)
        
        # === 組合 ===
        score = (self.params["mom_weight"] * mom_score +
                 self.params["val_weight"] * val_score +
                 self.params["chip_weight"] * chip_score)
        
        return score
    
    def filter_universe(self, db):
        """篩選投資範圍"""
        close = db.get('close')
        volume = db.get('volume')
        
        # 日成交金額 > 500 萬
        daily_amount = close * volume
        return ts_mean(daily_amount, 20) > 5_000_000
```

---

## 📊 回測與配置

### 回測

```python
from Platform import Backtester

result = Backtester.run(
    strategy=MyStrategy(),
    start_date="2024-01-01",
    end_date="2025-12-31",
    initial_capital=1_000_000,
    rebalance_freq="weekly",    # daily, weekly, monthly
    transaction_cost=0.001425,  # 手續費率
)

# 查看結果
print(result.summary())

# 繪製績效圖
result.plot(save_path="performance.png")

# 績效指標
print(f"年化報酬: {result.metrics['annual_return']*100:.1f}%")
print(f"夏普比率: {result.metrics['sharpe_ratio']:.2f}")
print(f"最大回撤: {result.metrics['max_drawdown']*100:.1f}%")
```

### 資產配置

```python
from Platform import get_allocation

allocation = get_allocation(
    strategy=MyStrategy(),
    capital=1_000_000,
    max_positions=10,
    max_weight=0.15,
)

print(allocation)

# 輸出 CSV
allocation.to_csv("my_allocation.csv")
```

---

## 📂 檔案結構

```
Platform/
├── __init__.py              # 主入口
├── __main__.py              # CLI 工具
├── README.md                # 本文件
├── Core/
│   └── build_field_database.py   # FieldDB 建構器
├── FieldDB/                 # 資料 (Parquet 格式)
│   ├── price/               # 價格資料 (21 欄位)
│   ├── financials/          # 財報資料 (9 欄位)
│   ├── balance_sheet/       # 資產負債表 (5 欄位)
│   ├── cashflow/            # 現金流 (1 欄位)
│   ├── chip/                # 籌碼資料 (9 欄位)
│   ├── monthly_sales/       # 月營收 (7 欄位)
│   ├── dividend/            # 🆕 股利資料 (5 欄位)
│   ├── self_announced/      # 🆕 自結數 (11 欄位)
│   ├── capital/             # 🆕 資本形成 (7 欄位)
│   ├── chip_extended/       # 🆕 籌碼擴充 (8 欄位)
│   └── _meta/               # 元資料
├── Factors/
│   └── operators.py         # 運算工具
├── Strategies/
│   ├── base.py              # Strategy 基礎類別
│   ├── manager.py           # StrategyManager
│   ├── examples/            # 範例策略
│   │   ├── momentum.py
│   │   ├── value.py
│   │   └── combined.py
│   └── user_strategies/     # ⬅️ 你的策略放這裡
│       └── template.py      # 策略範本
├── Backtest/
│   └── engine.py            # 回測引擎
└── Allocator/
    └── allocator.py         # 資產配置器
```

---

## 🎯 常見策略邏輯

### 動量策略
```python
momentum = ts_pct_change(close, 20)
score = zscore(momentum)
```

### 價值策略
```python
pe_score = rank(-pe)
pb_score = rank(-pb)
div_score = rank(div_yield)
score = 0.4 * pe_score + 0.3 * pb_score + 0.3 * div_score
```

### 成交量突破
```python
vol_ratio = volume / ts_mean(volume, 20)
score = zscore(vol_ratio)
```

### 均線多頭排列
```python
ma5 = ts_mean(close, 5)
ma20 = ts_mean(close, 20)
ma60 = ts_mean(close, 60)
score = zscore(ma5 - ma20) + zscore(ma20 - ma60)
```

### 籌碼面 (🆕 使用擴充資料)
```python
# 外資買賣力道
qfii_buy = db.get('qfii_buy')
qfii_sell = db.get('qfii_sell')
qfii_strength = qfii_buy / (qfii_buy + qfii_sell)
score = zscore(qfii_strength)
```

### 營收成長
```python
rev_yoy = db.get('monthly_rev_yoy')
score = zscore(rev_yoy)
```

### 低波動高股息 (🆕 使用股利資料)
```python
ret = ts_pct_change(close, 1)
volatility = ts_std(ret, 60)
cash_div = db.get('cash_div')
div_yield = cash_div / close * 100
score = 0.5 * rank(-volatility) + 0.5 * rank(div_yield)
```

### 品質因子
```python
gpm = db.get('tej_gpm')
opm = db.get('tej_opm')
score = 0.5 * rank(gpm) + 0.5 * rank(opm)
```

### 即時獲利追蹤 (🆕 使用自結數)
```python
# 自結數 EPS 成長
sa_eps = db.get('sa_eps')
eps_growth = ts_pct_change(sa_eps, 4)  # 季度成長
score = zscore(eps_growth)
```

---

## ❓ FAQ

### Q: 如何新增自己的策略？

在 `Platform/Strategies/user_strategies/` 目錄下建立 `.py` 檔案，繼承 `Strategy` 類別並實作 `compute()` 方法。可參考 `template.py`。

### Q: 資料範圍是多少？

| 類別 | 時間範圍 | 筆數 |
|------|---------|------|
| Price | 2024-02-15 ~ 2026-02-05 | ~485 天 |
| Financials | 約 5 年 | ~20 季 |
| Chip | 最近 2 個月 | ~42 天 |
| Monthly Sales | 最近 15 個月 | ~15 月 |
| Dividend | 最近 5 年 | ~20 筆 |
| Self Announced | 最近 2 年 | ~24 月 |
| Capital | 最近 3 年 | ~12 筆 |

### Q: 季報/月報資料如何使用？

**季報/月報資料會自動對齊到日報日期**，直接使用即可！

```python
close = db.get('close')   # 日報 485 天
ocf = db.get('ocf')       # 季報 → 自動對齊到 485 天並 ffill

# 直接運算
ocf_yield = ocf / db.get('mktcap')  # ✅ 可以直接計算
```

如果需要原始資料（不對齊），使用 `align=False`:

```python
ocf_raw = db.get('ocf', align=False)  # 原始 20 季資料
```

### Q: 如何更新資料？

```bash
# 1. 下載最新資料
cd Tools/StockAnalysis/Data
python data_downloader.py

# 2. 重建 FieldDB
cd Platform/Core
python build_field_database.py
```

### Q: 支援哪些股票？

目前支援 **158 家台股**，清單在 `Platform/FieldDB/_meta/tickers.json`。

### Q: TEJ 初入江湖版有什麼限制？

| 項目 | 狀態 |
|------|------|
| 存貨 (Inventory) | ❌ 無 |
| 現金 (Cash) | ❌ 無 |
| 資本支出 (CAPEX) | ❌ 無 |
| 投資現金流 (ICF) | ❌ 無 |
| 籌資現金流 (FCF) | ❌ 無 |
| 流動負債細項 | ❌ 無 |

**替代方案**：使用 TEJ 提供的比率指標（`inventory_turnover`, `inventory_days` 等）

### Q: 自結數和季報有什麼不同？

**自結數 (Self Announced)** 是公司自行公布的財務數據，通常比正式財報早 **1-2 個月**，可用於：
- 更即時的獲利追蹤
- 提前發現營運轉折點
- 搶先市場反應

---

## 🆕 更新日誌

### v2.0 (2026-02-06)
- ✅ 新增 **股利資料** (5 欄位) - 支援股息策略
- ✅ 新增 **自結數** (11 欄位) - 比季報更即時的財務數據
- ✅ 新增 **資本形成** (7 欄位) - 股本變化追蹤
- ✅ 新增 **籌碼擴充** (8 欄位) - 更細緻的法人動向分析
- ✅ 總欄位數從 51 個增加到 **83 個**
- ✅ 修復自結數日期重複問題
- ✅ 更新 README 文件

### v1.0 (2026-02-05)
- ✅ 初始版本發布
- ✅ 51 個基礎欄位
- ✅ 完整回測與配置系統

---

## 📞 聯絡

有問題請聯繫平台維護者 吳翌任。

Happy Trading! 🚀
