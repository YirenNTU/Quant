# 🚀 Investment AI - 智能投資分析系統

> 一套結構化、多維度的台股投資分析系統，採用「漏斗式篩選 + 交叉驗證」策略，從基本面、技術面、財務品質等角度，系統性地發掘優質投資標的。

---

## 📖 投資哲學 (Investment Philosophy)

### 核心理念

本系統基於以下投資原則設計：

1. **結構性成長優先**：尋找「獲利能力正在系統性改善」的公司，而非單純追逐高成長或低估值
2. **去季節化分析**：使用 YoY（同比）數據，避免淡旺季造成的假象
3. **多維度交叉驗證**：單一指標容易被操控，多維度驗證更可靠
4. **風險貼水機制**：用扣分制取代硬性剔除，保留灰色地帶的投資機會
5. **市場狀態自適應**：牛市追強勢股，熊市守抗跌股

### 策略框架

```
                    ┌─────────────────────────┐
                    │     Stock Universe      │
                    │      (282 支股票)       │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │   Step 1: 動能篩選      │
                    │   GPM/OPM 結構性擴張    │
                    │   → ~35 支 Elite        │
                    └───────────┬─────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          │                     │                     │
          ▼                     ▼                     ▼
    ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
    │ Step 2: 寶石 │      │ Step 3: 體檢 │      │   (並行)    │
    │ 偵測潛力股   │      │ 驗證財務品質 │      │             │
    └──────┬──────┘      └──────┬──────┘      └─────────────┘
           │                    │
           └────────┬───────────┘
                    │
          ┌─────────▼─────────┐
          │  Step 4: 估值分析  │
          │  PE Band + RS     │
          └─────────┬─────────┘
                    │
          ┌─────────▼─────────┐
          │  Step 5: 財務取證  │
          │  排除造假風險      │
          └─────────┬─────────┘
                    │
          ┌─────────▼─────────┐
          │   Final Output    │
          │  可投資標的清單    │
          └───────────────────┘
```

---

## 🏗️ 系統架構

```
Investment_AI/
├── README.md                          # 本文件
├── Stock_Pool/
│   ├── list.json                      # 股票清單 (股票代碼 → 公司名稱)
│   ├── Database/                      # 本地資料庫 (JSON 格式)
│   │   ├── 2330_20260130.json        # 各股票的財報與股價資料
│   │   └── ...
│   ├── structural_change_report_v2.csv       # Step 1 輸出
│   ├── hidden_gems_report_v2.csv             # Step 2 輸出
│   ├── final_health_check_report_v2.csv      # Step 3 輸出
│   ├── final_valuation_report_v2.csv         # Step 4 輸出
│   └── institutional_forensic_report_v2.csv  # Step 5 輸出 (最終報告)
│
└── Tools/Searching/
    ├── tej_tool.py                   # TEJ API 封裝 + 本地資料庫讀取
    ├── data_downloader.py            # 資料下載器 (唯一呼叫 API 的腳本)
    ├── pool_analyser_v2.py           # Step 1: 動能篩選
    ├── shadow_gem_detector_v2.py     # Step 2: 寶石偵測
    ├── health_checker_v2.py          # Step 3: 體質檢查
    ├── valuation_analyzer_v2.py      # Step 4: 估值分析
    ├── forensic_analyzer_v2.py       # Step 5: 財務取證
    └── run_full_pipeline.py          # 一鍵執行完整流程
```

---

## 🚀 快速開始

### 1. 環境準備

```bash
# 安裝依賴
cd Investment_AI/Tools/Searching
pip install -r requirements.txt
```

### 2. 下載資料 (需要 TEJ API Key)

```bash
# 首次執行或需要更新資料時
python data_downloader.py
```

> ⚠️ 這是**唯一會呼叫 API** 的步驟，會消耗 API 額度

### 3. 執行分析 (離線模式)

```bash
# 方法 A：一鍵執行完整流程
python run_full_pipeline.py --skip-download

# 方法 B：單獨執行各步驟
python pool_analyser_v2.py           # Step 1
python shadow_gem_detector_v2.py     # Step 2
python health_checker_v2.py          # Step 3
python valuation_analyzer_v2.py      # Step 4
python forensic_analyzer_v2.py       # Step 5
```

### 4. 查看結果

最終報告位於：`Stock_Pool/institutional_forensic_report_v2.csv`

**建議閱讀順序**：
1. `institutional_forensic_report_v2.csv` → 看 Forensic Score 與評級
2. `final_valuation_report_v2.csv` → 看買賣決策與估值位置
3. `hidden_gems_report_v2.csv` → 發掘尚未入選的潛力股

---

## 📊 各階段策略詳解

### Step 1: Pool Analyser (動能篩選)

**目標**：找出「結構性擴張」的公司

| 指標 | 計算方式 | 意義 |
|------|----------|------|
| GPM YoY 斜率 | GPM_t - GPM_t-4 | 毛利率同比改善 |
| OPM YoY 斜率 | OPM_t - OPM_t-4 | 營益率同比改善 |
| 營業槓桿 (OL) | OPM斜率 / GPM斜率 | >1.2 表示規模效益放大 |
| 營收動能 | 最新季 YoY - 前季 YoY | 營收正在加速 |

**評分制度**：
- 基礎分 60 分
- OL > 1.2: +20 分
- GPM 斜率 > 0: +10 分
- OPM 斜率 > 0: +10 分
- 營收加速 > 5%: +10 分
- 業外比重 ≤ 30%: +10 分 / > 30%: -20 分

**分級**：
- 🏆 SSS級：≥90 分 + OL>1.2
- 🔥 S級：≥80 分 + OL>1.2
- ⭐ A級：≥80 分
- ✅ B級：≥70 分

---

### Step 2: Shadow Gem Detector (寶石偵測)

**目標**：找出被 Step 1 遺漏的潛力股

| 指標 | 意義 |
|------|------|
| 營收加速度 | 季度 YoY 加速度，捕捉「生意突然好到爆」 |
| 相對強度 (RS) | 與大盤比較，發現主力提前進場 |
| PSR 百分位 | 低估值轉機股 |
| R&D 動能 | 研發投入增加，預示未來產品 |

**寶石分類**：
- 💎💎💎 SSS級：≥100 分
- 💎💎 S級：≥80 分（法人共識 / 價值轉機 / 強勢）
- 💎 A級：≥60 分（營收爆發 / 籌碼卡位）
- ⭐ B級：≥50 分（觀察名單）

---

### Step 3: Health Checker (財務體檢)

**目標**：確認獲利有「含金量」

| 指標 | 計算方式 | 警戒線 |
|------|----------|--------|
| CCR TTM | Σ(近4季 OCF) / Σ(近4季 NI) | < 0.8 警示 |
| FCF | OCF - CapEx | 負數需留意 |
| 存貨天數變化 | (存貨/營收)×90 的 YoY | > 15天 高風險 |

**健康等級**：
- 🏆 S級：≥90 分（優質）
- ⭐ A級：≥80 分
- ✅ B級：≥70 分
- ⚠️ C級：警示
- 🛑 D級：高風險

---

### Step 4: Valuation Analyzer (估值分析)

**目標**：根據市場狀態判斷買賣時機

**市場狀態判斷**：
- 🐂 牛市：大盤 > MA200 → RS 門檻 > 1.05（強者恆強）
- 🐻 熊市：大盤 < MA200 → RS 門檻 > 0.95（抗跌即可）

**混合估值法**：
- EPS > 0：使用 PE 百分位
- EPS ≤ 0：使用 PB 百分位（抓轉機股）

**決策矩陣**：

| 估值位置 | RS通過 | 牛市決策 | 熊市決策 |
|----------|--------|----------|----------|
| 低估 (<30%) | ✅ | 🔥 Strong Buy | 📊 Accumulate |
| 低估 (<30%) | ❌ | 📈 Accumulate | 👀 Watch |
| 高估 (>70%) | ❌ | 📉 Trim | 🛑 Trim |
| 高估 (>70%) | ✅ | ⚠️ Hold | ⚠️ Hold |

---

### Step 5: Forensic Analyzer (財務取證)

**目標**：排除財務造假風險

| 指標 | 計算方式 | 警戒線 |
|------|----------|--------|
| Sloan Ratio | (NI - OCF - ICF) / TA | > 0.1 盈餘品質差 |
| F-Score | Piotroski 9點評分 | < 4 財務弱 |
| 虛胖獲利比 | 營業利益 / 淨利 | < 50% 業外過高 |
| ROIC | EBIT TTM / TA | > 15% 優良 |

**取證評級**：
- 🏆 AAA：≥90 分（財務透明優質）
- ⭐ AA：≥80 分
- ✅ A：≥70 分
- ⚠️ B：≥60 分（需留意）
- 🛑 C：≥40 分（財務風險）
- 🚫 D：<40 分（高風險）

---

## 📁 輸出檔案說明

| 檔案 | 說明 | 關鍵欄位 |
|------|------|----------|
| `structural_change_report_v2.csv` | 結構性擴張股 | Score, Result_Tag, OL |
| `hidden_gems_report_v2.csv` | 隱藏寶石 | Gem_Score, Gem_Type, Rev_Acc |
| `final_health_check_report_v2.csv` | 健康體檢 | Health_Score, CCR_TTM, FCF |
| `final_valuation_report_v2.csv` | 估值決策 | Decision, RS_Ratio, PE_Percentile |
| `institutional_forensic_report_v2.csv` | 最終報告 | Forensic_Score, Sloan, F_Score |

---

## 💡 使用建議

### 選股流程

1. **從最終報告開始**：
   - 篩選 `Forensic_Score ≥ 80` 的標的
   - 再看 `Decision` 是否為 Strong Buy / Accumulate

2. **交叉驗證**：
   - 確認 `Health_Score ≥ 70`
   - 確認 `Sloan_Ratio < 0.1`

3. **留意隱藏寶石**：
   - 查看 `hidden_gems_report_v2.csv` 中 `Gem_Score ≥ 60` 的標的
   - 這些可能是尚未被市場發現的潛力股

### 風險控制

- **避免高虛胖比**：`Hollow_Ratio < 50%` 表示業外收入過高
- **注意存貨風險**：`Inv_Days_Change > 15` 可能有庫存積壓
- **關注 F-Score**：`F_Score < 4` 表示財務體質弱

---

## ⚙️ 進階設定

### 離線/線上模式切換

編輯 `Tools/Searching/tej_tool.py`：

```python
OFFLINE_MODE = True   # 離線模式：僅讀取本地資料庫
OFFLINE_MODE = False  # 線上模式：可呼叫 API
```

### 更新資料

```bash
# 重新下載最新資料
python data_downloader.py

# 然後執行分析
python run_full_pipeline.py --skip-download
```

### 自訂股票清單

編輯 `Stock_Pool/list.json`：

```json
{
    "2330.TW": "台積電",
    "2317.TW": "鴻海",
    "2454.TW": "聯發科"
}
```

---

## 📝 版本歷史

- **V2.0** (2026-01)
  - 全面支援離線模式
  - YoY 去季節化斜率
  - 評分制取代硬性過濾
  - 市場狀態自適應估值

---

## 📜 免責聲明

本系統僅供研究與學習使用，不構成任何投資建議。投資有風險，入市需謹慎。使用者應自行承擔投資決策的全部責任。

---

## 🤝 貢獻

歡迎提交 Issue 或 Pull Request 來改進本系統。

---

*Built with ❤️ for systematic investing*

