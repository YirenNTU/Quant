#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
📊 Field Database Builder - 欄位資料庫建構器
================================================================================

將「按公司分類」的 JSON 資料轉換成「按欄位分類」的資料庫。

【轉換前】Stock_Pool/Database/
├── 1101_20260206.json  → 台泥的所有資料
├── 2330_20260206.json  → 台積電的所有資料
└── ...

【轉換後】Platform/FieldDB/
├── price/
│   ├── open.parquet    → 所有公司的 Open (rows=日期, cols=股票代碼)
│   ├── close.parquet   → 所有公司的 Close
│   ├── volume.parquet  → 所有公司的 Volume
│   └── ...
├── financials/
│   ├── tej_gpm.parquet → 所有公司的毛利率 (rows=季度, cols=股票代碼)
│   ├── tej_opm.parquet → 所有公司的營益率
│   └── ...
├── chip/
│   ├── qfii_ex.parquet → 所有公司的外資買賣超
│   └── ...
├── monthly_sales/
│   ├── d0003.parquet   → 所有公司的月營收 YoY
│   └── ...
└── _meta/
    ├── tickers.json    → 股票代碼清單
    ├── field_map.json  → 欄位對照表
    └── build_info.json → 建構資訊

【使用方式】
>>> from Platform.Core.field_db import FieldDB
>>> db = FieldDB()
>>> df = db.get('close')  # 取得所有公司收盤價
>>> df['2330']            # 台積電收盤價

Author: Investment AI Platform
Version: 1.0
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from io import StringIO
from glob import glob
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')


# ═══════════════════════════════════════════════════════════════════════════════
# 設定
# ═══════════════════════════════════════════════════════════════════════════════

# 路徑設定
SCRIPT_DIR = Path(__file__).parent
PLATFORM_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = PLATFORM_DIR.parent

# 來源與目標
SOURCE_DIR = PROJECT_ROOT / "Stock_Pool" / "Database"
OUTPUT_DIR = PLATFORM_DIR / "FieldDB"

# 輸出格式 (parquet 更快更小, csv 更通用)
OUTPUT_FORMAT = "parquet"  # "parquet" or "csv"


# ═══════════════════════════════════════════════════════════════════════════════
# 欄位定義 - 定義要提取的欄位
# ═══════════════════════════════════════════════════════════════════════════════

FIELD_DEFINITIONS = {
    # ═══════════════════════════════════════════════════════════════════════════
    # PRICE - 股價資料 (日頻，約 485 天)
    # ═══════════════════════════════════════════════════════════════════════════
    # 來源: data_downloader.py → loader.get_history(ticker, period_days=730)
    # API: TWN/APIPRCD
    # 格式: orient='split', index=日期, columns=欄位
    # 完整度: 99%+ (所有欄位都有資料)
    # ═══════════════════════════════════════════════════════════════════════════
    "price": {
        "source_key": "price",
        "date_column": None,  # 使用 DataFrame index (已經是日期)
        "fields": {
            # 價格
            "open": {"column": "Open", "description": "開盤價"},
            "high": {"column": "High", "description": "最高價"},
            "low": {"column": "Low", "description": "最低價"},
            "close": {"column": "Close", "description": "收盤價"},
            "adjfac": {"column": "adjfac", "description": "還原因子"},
            
            # 成交
            "volume": {"column": "Volume", "description": "成交量(股)"},
            "amount": {"column": "amt", "description": "成交金額"},
            "trades": {"column": "trn", "description": "成交筆數"},
            "avgprc": {"column": "avgprc", "description": "均價"},
            "turnover": {"column": "turnover", "description": "週轉率%"},
            
            # 市場
            "mktcap": {"column": "mktcap", "description": "市值"},
            "shares": {"column": "shares", "description": "流通股數"},
            
            # 估值
            "pe": {"column": "per", "description": "本益比"},
            "pb": {"column": "pbr", "description": "股價淨值比"},
            "psr": {"column": "psr_tej", "description": "股價營收比"},
            "pe_tej": {"column": "per_tej", "description": "PE(TEJ)"},
            "pb_tej": {"column": "pbr_tej", "description": "PB(TEJ)"},
            
            # 殖利率
            "div_yield": {"column": "div_yid", "description": "殖利率%"},
            "cdiv_yield": {"column": "cdiv_yid", "description": "現金殖利率%"},
            
            # 報酬
            "daily_return": {"column": "roi", "description": "日報酬率%"},
            "amplitude": {"column": "hmlpct", "description": "振幅%"},
        }
    },
    
    # ═══════════════════════════════════════════════════════════════════════════
    # FINANCIALS - 損益表 (季頻，約 20 季)
    # ═══════════════════════════════════════════════════════════════════════════
    # 來源: data_downloader.py → loader.get_financials(ticker, quarters=8)
    # API: TWN/AINVFINB
    # 格式: orient='split', index=科目名稱, columns=日期
    # 需要轉置: row=科目 → row=日期
    # 
    # ⚠️ TEJ 初入江湖版限制：
    # - 沒有 Operating Income, EBIT, Pretax Income 等細項
    # - 但有 TEJ 計算好的比率 (GPM, OPM, 週轉率等)
    # ═══════════════════════════════════════════════════════════════════════════
    "financials": {
        "source_key": "financials",
        "date_column": None,
        "transpose": True,
        "fields": {
            # 損益項目 (有資料)
            "revenue": {"column": "Total Revenue", "description": "營業收入"},
            "gross_profit": {"column": "Gross Profit", "description": "毛利"},
            "net_income": {"column": "Net Income", "description": "稅後淨利"},
            
            # TEJ 計算的比率 (有資料)
            "tej_gpm": {"column": "TEJ_GPM", "description": "毛利率%"},
            "tej_opm": {"column": "TEJ_OPM", "description": "營益率%"},
            
            # 週轉率指標 (有資料)
            "inventory_turnover": {"column": "Inventory Turnover", "description": "存貨週轉率"},
            "inventory_days": {"column": "Inventory Days", "description": "存貨天數"},
            "dso": {"column": "Days Sales Outstanding", "description": "應收帳款天數"},
            "days_payable": {"column": "Days Payable", "description": "應付帳款天數"},
        }
    },
    
    # ═══════════════════════════════════════════════════════════════════════════
    # BALANCE_SHEET - 資產負債表 (季頻，約 20 季)
    # ═══════════════════════════════════════════════════════════════════════════
    # 來源: data_downloader.py → loader.get_financials(ticker, quarters=8)
    # API: TWN/AINVFINB
    # 
    # ⚠️ TEJ 初入江湖版限制：
    # - 只有彙總數字 (Total Assets, Total Debt 等)
    # - 沒有細項 (Inventory, Cash, Current Liabilities 等)
    # ═══════════════════════════════════════════════════════════════════════════
    "balance_sheet": {
        "source_key": "balance_sheet",
        "date_column": None,
        "transpose": True,
        "fields": {
            # 有資料的欄位
            "total_assets": {"column": "Total Assets", "description": "資產總額"},
            "total_debt": {"column": "Total Debt", "description": "負債總額"},
            "total_liabilities": {"column": "Total Liabilities Net Minority Interest", "description": "總負債"},
            "current_assets": {"column": "Current Assets", "description": "流動資產"},
            "accounts_receivable": {"column": "Accounts Receivable", "description": "應收帳款"},
            
            # 以下欄位 TEJ 初入江湖版無資料，但保留定義以備升級
            # "inventory": {"column": "Inventory", "description": "存貨"},
            # "cash": {"column": "Cash And Cash Equivalents", "description": "現金"},
            # "current_liabilities": {"column": "Current Liabilities", "description": "流動負債"},
            # "long_term_debt": {"column": "Long Term Debt", "description": "長期負債"},
        }
    },
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CASHFLOW - 現金流量表 (季頻，約 20 季)
    # ═══════════════════════════════════════════════════════════════════════════
    # 來源: data_downloader.py → loader.get_financials(ticker, quarters=8)
    # API: TWN/AINVFINB
    # 
    # ⚠️ TEJ 初入江湖版限制：
    # - 只有 OCF (營業現金流)
    # - 沒有 ICF, FCF, CAPEX
    # ═══════════════════════════════════════════════════════════════════════════
    "cashflow": {
        "source_key": "cashflow",
        "date_column": None,
        "transpose": True,
        "fields": {
            # 有資料的欄位
            "ocf": {"column": "Operating Cash Flow", "description": "營業現金流"},
            
            # 以下欄位 TEJ 初入江湖版無資料，但保留定義以備升級
            # "icf": {"column": "Investing Cash Flow", "description": "投資現金流"},
            # "fcf": {"column": "Financing Cash Flow", "description": "籌資現金流"},
            # "capex": {"column": "Capital Expenditure", "description": "資本支出"},
        }
    },
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CHIP - 籌碼資料 (日頻，約 42 天)
    # ═══════════════════════════════════════════════════════════════════════════
    # 來源: data_downloader.py → download_chip_data(ticker, days=60)
    # API: TWN/APISHRACT
    # 格式: orient='split', index=row number, columns=欄位 (含 mdate)
    # 完整度: 100% (所有欄位都有資料)
    # ═══════════════════════════════════════════════════════════════════════════
    "chip": {
        "source_key": "chip",
        "date_column": "mdate",
        "fields": {
            # 法人買賣超
            "qfii_net": {"column": "qfii_ex", "description": "外資買賣超(張)"},
            "fund_net": {"column": "fund_ex", "description": "投信買賣超(張)"},
            "dealer_net": {"column": "tot_ex", "description": "三大法人合計"},
            
            # 法人持股比例
            "qfii_pct": {"column": "qfii_pct", "description": "外資持股%"},
            "fund_pct": {"column": "fd_pct", "description": "投信持股%"},
            "dealer_pct": {"column": "dlr_pct", "description": "自營商持股%"},
            
            # 融資融券
            "margin_long": {"column": "long_t", "description": "融資餘額(張)"},
            "margin_short": {"column": "short_t", "description": "融券餘額(張)"},
            "short_ratio": {"column": "s_l_pct", "description": "券資比%"},
        }
    },
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MONTHLY_SALES - 月營收 (月頻，約 15 個月)
    # ═══════════════════════════════════════════════════════════════════════════
    # 來源: data_downloader.py → download_monthly_sales(ticker, months=15)
    # API: TWN/APISALE
    # 格式: orient='split', index=row number, columns=欄位 (含 mdate)
    # 完整度: 94%+ (所有欄位都有資料)
    # ═══════════════════════════════════════════════════════════════════════════
    "monthly_sales": {
        "source_key": "monthly_sales",
        "date_column": "mdate",
        "fields": {
            "monthly_rev": {"column": "d0001", "description": "當月營收(千元)"},
            "monthly_rev_alt": {"column": "d0002", "description": "月營收(千元)"},
            "monthly_rev_yoy": {"column": "d0003", "description": "月營收YoY%"},
            "monthly_rev_mom": {"column": "d0004", "description": "月營收MoM%"},
            "ytd_rev": {"column": "d0005", "description": "累計營收(千元)"},
            "ytd_rev_yoy": {"column": "d0006", "description": "累計營收YoY%"},
            "ytd_rev_yoy_pct": {"column": "d0007", "description": "累計營收MoM%"},
        }
    },
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DIVIDEND - 股利資料 (🆕 新增)
    # ═══════════════════════════════════════════════════════════════════════════
    # 來源: data_downloader.py → download_dividend_data(ticker, years=5)
    # API: TWN/APIDV1
    # 格式: orient='split', index=row number, columns=欄位 (含 mdate)
    # ═══════════════════════════════════════════════════════════════════════════
    "dividend": {
        "source_key": "dividend",
        "date_column": "mdate",
        "fields": {
            "cash_div": {"column": "divc", "description": "現金股利"},
            "stock_div": {"column": "divs", "description": "股票股利"},
            "div_type": {"column": "distri_type", "description": "配息類型"},
            "ex_div_date": {"column": "edexdate", "description": "除息日"},
            "pay_date": {"column": "div_date", "description": "發放日"},
        }
    },
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SELF_ANNOUNCED - 自結數 (🆕 新增)
    # ═══════════════════════════════════════════════════════════════════════════
    # 來源: data_downloader.py → download_self_announced(ticker, months=24)
    # API: TWN/AFESTM1
    # 格式: orient='split', index=row number, columns=欄位 (含 mdate)
    # 
    # 自結數比季報更即時，公司自行公布的財務數據
    # ═══════════════════════════════════════════════════════════════════════════
    "self_announced": {
        "source_key": "self_announced",
        "date_column": "mdate",
        "fields": {
            "sa_revenue": {"column": "ip12", "description": "自結營收"},
            "sa_opi": {"column": "opi", "description": "自結營業利益"},
            "sa_pretax": {"column": "isibt", "description": "自結稅前淨利"},
            "sa_net_income": {"column": "isnip", "description": "自結稅後淨利"},
            "sa_eps": {"column": "eps", "description": "自結EPS"},
            "sa_gpm": {"column": "r105", "description": "自結毛利率%"},
            "sa_opm": {"column": "r106", "description": "自結營益率%"},
            "sa_npm": {"column": "r107", "description": "自結淨利率%"},
            "sa_rev_yoy": {"column": "r401", "description": "自結營收成長率%"},
            "sa_opi_yoy": {"column": "r403", "description": "自結營業利益成長率%"},
            "sa_ni_yoy": {"column": "r404", "description": "自結淨利成長率%"},
        }
    },
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CAPITAL - 資本形成 (🆕 新增)
    # ═══════════════════════════════════════════════════════════════════════════
    # 來源: data_downloader.py → download_capital_change(ticker, years=3)
    # API: TWN/APISTK1
    # 格式: orient='split', index=row number, columns=欄位 (含 mdate)
    # ═══════════════════════════════════════════════════════════════════════════
    "capital": {
        "source_key": "capital",
        "date_column": "mdate",
        "fields": {
            "capital_amt": {"column": "stk_amt", "description": "股本(千元)"},
            "shares_outstanding": {"column": "slamt", "description": "流通股數(千股)"},
            "cash_increase": {"column": "cash", "description": "現金增資"},
            "earning_increase": {"column": "earning", "description": "盈餘轉增資"},
            "capital_reserve": {"column": "capital", "description": "資本公積"},
            "employee_bonus": {"column": "bonus", "description": "員工紅利"},
            "capital_decrease": {"column": "cap_dec", "description": "減資"},
        }
    },
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CHIP_EXTENDED - 籌碼資料擴充 (🆕 新增更多欄位)
    # ═══════════════════════════════════════════════════════════════════════════
    # 來源: data_downloader.py → download_chip_data (擴充版)
    # API: TWN/APISHRACT
    # ═══════════════════════════════════════════════════════════════════════════
    "chip_extended": {
        "source_key": "chip",
        "date_column": "mdate",
        "fields": {
            # 外資買/賣量
            "qfii_buy": {"column": "qfii_buy", "description": "外資買進量(張)"},
            "qfii_sell": {"column": "qfii_sell", "description": "外資賣出量(張)"},
            # 投信買/賣量
            "fund_buy": {"column": "fund_buy", "description": "投信買進量(張)"},
            "fund_sell": {"column": "fund_sell", "description": "投信賣出量(張)"},
            # 維持率
            "margin_maintenance": {"column": "lmr", "description": "融資維持率%"},
            "short_maintenance": {"column": "smr", "description": "融券維持率%"},
            "total_maintenance": {"column": "tmr", "description": "整戶維持率%"},
            # 借券
            "stock_lending": {"column": "borr_t1", "description": "借券餘額(張)"},
        }
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# 主程式
# ═══════════════════════════════════════════════════════════════════════════════

class FieldDatabaseBuilder:
    """欄位資料庫建構器"""
    
    def __init__(self, source_dir: Path = SOURCE_DIR, output_dir: Path = OUTPUT_DIR):
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.tickers = []
        self.ticker_names = {}
        self.field_map = {}
        self.stats = {
            "total_files": 0,
            "success_files": 0,
            "failed_files": 0,
            "total_fields": 0,
            "build_time": None,
        }
    
    def build(self):
        """執行完整建構流程"""
        start_time = datetime.now()
        
        print("=" * 70)
        print("📊 Field Database Builder - 欄位資料庫建構器")
        print("=" * 70)
        print(f"來源目錄: {self.source_dir}")
        print(f"輸出目錄: {self.output_dir}")
        print(f"輸出格式: {OUTPUT_FORMAT}")
        print("=" * 70)
        
        # Step 1: 掃描來源檔案
        print("\n📂 Step 1: 掃描來源檔案...")
        source_files = self._scan_source_files()
        if not source_files:
            print("❌ 找不到來源檔案！")
            return False
        
        # Step 2: 載入所有公司資料
        print(f"\n📥 Step 2: 載入 {len(source_files)} 家公司資料...")
        all_data = self._load_all_data(source_files)
        
        # Step 3: 建立輸出目錄
        print("\n📁 Step 3: 建立輸出目錄結構...")
        self._create_output_dirs()
        
        # Step 4: 依欄位類別處理
        print("\n🔄 Step 4: 轉換資料...")
        for category, config in FIELD_DEFINITIONS.items():
            self._process_category(category, config, all_data)
        
        # Step 5: 儲存 metadata
        print("\n💾 Step 5: 儲存 metadata...")
        self._save_metadata()
        
        # 完成
        self.stats["build_time"] = str(datetime.now() - start_time)
        
        print("\n" + "=" * 70)
        print("✅ 建構完成！")
        print("=" * 70)
        self._print_summary()
        
        return True
    
    def _scan_source_files(self) -> List[Path]:
        """掃描來源 JSON 檔案"""
        pattern = str(self.source_dir / "*.json")
        files = glob(pattern)
        
        # 過濾並取得最新版本
        ticker_files = {}
        for f in files:
            filename = os.path.basename(f)
            parts = filename.replace('.json', '').split('_')
            if len(parts) >= 2:
                ticker = parts[0]
                date = parts[1]
                
                # 保留最新日期的檔案
                if ticker not in ticker_files or date > ticker_files[ticker][1]:
                    ticker_files[ticker] = (f, date)
        
        result = [Path(v[0]) for v in ticker_files.values()]
        print(f"   找到 {len(result)} 家公司資料")
        self.stats["total_files"] = len(result)
        
        return sorted(result)
    
    def _load_all_data(self, files: List[Path]) -> Dict[str, dict]:
        """載入所有公司資料"""
        all_data = {}
        
        for i, file_path in enumerate(files):
            ticker = file_path.stem.split('_')[0]
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                all_data[ticker] = data
                self.tickers.append(ticker)
                
                # 記錄公司名稱
                if data.get('info'):
                    self.ticker_names[ticker] = data['info'].get('shortName', ticker)
                
                self.stats["success_files"] += 1
                
            except Exception as e:
                print(f"   ⚠️ 載入失敗 {ticker}: {e}")
                self.stats["failed_files"] += 1
            
            # 進度顯示
            if (i + 1) % 50 == 0 or (i + 1) == len(files):
                print(f"   進度: {i+1}/{len(files)} ({(i+1)/len(files)*100:.1f}%)")
        
        return all_data
    
    def _create_output_dirs(self):
        """建立輸出目錄結構"""
        # 主目錄
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 各類別子目錄
        for category in FIELD_DEFINITIONS.keys():
            (self.output_dir / category).mkdir(exist_ok=True)
        
        # metadata 目錄
        (self.output_dir / "_meta").mkdir(exist_ok=True)
        
        print(f"   建立目錄: {self.output_dir}")
    
    def _process_category(self, category: str, config: dict, all_data: Dict[str, dict]):
        """處理一個資料類別"""
        print(f"\n   📊 {category.upper()}")
        
        source_key = config["source_key"]
        date_column = config.get("date_column")
        transpose = config.get("transpose", False)
        fields = config["fields"]
        
        # 收集所有公司該類別的資料
        category_data = {}
        for ticker, data in all_data.items():
            raw = data.get(source_key)
            if not raw:
                continue
            
            try:
                # 解析 JSON string → DataFrame
                if isinstance(raw, str):
                    df = pd.read_json(StringIO(raw), orient='split')
                else:
                    df = pd.DataFrame(raw)
                
                # 處理轉置 (財報資料: row=科目, col=日期 → row=日期, col=科目)
                if transpose:
                    # 財報資料特殊處理：columns 可能有重複 (2025-09-01, 2025-09-01.1, ...)
                    # 需要去除重複，只保留第一個 (通常是最新/正確的)
                    
                    # 清理欄位名稱，取得唯一日期
                    clean_cols = []
                    seen_dates = set()
                    for col in df.columns:
                        # 移除 .1, .2 等後綴
                        base_date = str(col).split('.')[0]
                        if base_date not in seen_dates:
                            clean_cols.append(col)
                            seen_dates.add(base_date)
                    
                    # 只保留唯一日期的欄位
                    df = df[clean_cols]
                    
                    # 重新命名欄位為乾淨的日期
                    df.columns = [str(c).split('.')[0] for c in df.columns]
                    
                    # 轉置
                    df = df.T
                    
                    # 設定日期索引
                    df.index = pd.to_datetime(df.index)
                    df = df.sort_index()
                
                # 設定日期索引 (非轉置的情況)
                if date_column and date_column in df.columns:
                    df[date_column] = pd.to_datetime(df[date_column])
                    
                    # 處理日期重複的情況: 只保留每個日期的第一筆
                    if df[date_column].duplicated().any():
                        df = df.drop_duplicates(subset=[date_column], keep='first')
                    
                    df.set_index(date_column, inplace=True)
                    df = df.sort_index()  # 確保時間順序
                elif not transpose:
                    # Price 資料的 index 可能已經是日期
                    if df.index.dtype == 'object' or 'datetime' in str(df.index.dtype):
                        df.index = pd.to_datetime(df.index)
                        df = df.sort_index()
                
                category_data[ticker] = df
                
            except Exception as e:
                # 靜默跳過解析失敗的資料
                continue
        
        if not category_data:
            print(f"      ⚠️ 無有效資料")
            return
        
        # 對每個欄位建立 wide-format DataFrame
        for field_name, field_config in fields.items():
            col_name = field_config["column"]
            desc = field_config["description"]
            
            try:
                # 收集該欄位所有公司資料
                series_dict = {}
                for ticker, df in category_data.items():
                    if col_name in df.columns:
                        series_dict[ticker] = df[col_name]
                    elif col_name in df.index:
                        # 財報資料可能 column 和 index 互換
                        series_dict[ticker] = df.loc[col_name]
                
                if not series_dict:
                    continue
                
                # 合併成 wide-format (rows=日期, cols=股票代碼)
                wide_df = pd.DataFrame(series_dict)
                wide_df = wide_df.sort_index()
                
                # 儲存
                output_path = self.output_dir / category / f"{field_name}.{OUTPUT_FORMAT}"
                
                if OUTPUT_FORMAT == "parquet":
                    wide_df.to_parquet(output_path)
                else:
                    wide_df.to_csv(output_path)
                
                # 記錄 field map
                self.field_map[field_name] = {
                    "category": category,
                    "source_column": col_name,
                    "description": desc,
                    "shape": list(wide_df.shape),
                    "date_range": [str(wide_df.index.min()), str(wide_df.index.max())],
                    "tickers": len(wide_df.columns),
                }
                
                self.stats["total_fields"] += 1
                print(f"      ✅ {field_name:<20} ({wide_df.shape[0]} rows × {wide_df.shape[1]} cols)")
                
            except Exception as e:
                print(f"      ⚠️ {field_name}: {e}")
    
    def _save_metadata(self):
        """儲存 metadata"""
        meta_dir = self.output_dir / "_meta"
        
        # 1. 股票清單
        tickers_path = meta_dir / "tickers.json"
        with open(tickers_path, 'w', encoding='utf-8') as f:
            json.dump({
                "tickers": sorted(self.tickers),
                "names": self.ticker_names,
                "count": len(self.tickers),
            }, f, ensure_ascii=False, indent=2)
        print(f"   ✅ tickers.json ({len(self.tickers)} 檔股票)")
        
        # 2. 欄位對照表
        field_map_path = meta_dir / "field_map.json"
        with open(field_map_path, 'w', encoding='utf-8') as f:
            json.dump(self.field_map, f, ensure_ascii=False, indent=2)
        print(f"   ✅ field_map.json ({len(self.field_map)} 個欄位)")
        
        # 3. 建構資訊
        build_info_path = meta_dir / "build_info.json"
        with open(build_info_path, 'w', encoding='utf-8') as f:
            json.dump({
                "build_time": datetime.now().isoformat(),
                "source_dir": str(self.source_dir),
                "output_format": OUTPUT_FORMAT,
                "stats": self.stats,
            }, f, ensure_ascii=False, indent=2)
        print(f"   ✅ build_info.json")
    
    def _print_summary(self):
        """印出摘要"""
        print(f"\n📊 建構摘要:")
        print(f"   來源檔案: {self.stats['total_files']} 家公司")
        print(f"   成功載入: {self.stats['success_files']} 家")
        print(f"   載入失敗: {self.stats['failed_files']} 家")
        print(f"   產出欄位: {self.stats['total_fields']} 個")
        print(f"   建構時間: {self.stats['build_time']}")
        print(f"\n📁 輸出目錄: {self.output_dir}")
        
        # 列出所有欄位
        print(f"\n📋 欄位清單:")
        for category in FIELD_DEFINITIONS.keys():
            category_fields = [f for f, info in self.field_map.items() if info['category'] == category]
            if category_fields:
                print(f"   {category}/")
                for field in category_fields:
                    info = self.field_map[field]
                    print(f"      ├── {field}.{OUTPUT_FORMAT} ({info['description']})")


# ═══════════════════════════════════════════════════════════════════════════════
# 便捷讀取類別
# ═══════════════════════════════════════════════════════════════════════════════

class FieldDB:
    """
    欄位資料庫讀取器
    
    使用方式:
    >>> db = FieldDB()
    >>> df = db.get('close')           # 取得所有公司收盤價
    >>> df = db.get('close', '2330')   # 取得台積電收盤價
    >>> df = db.get('tej_gpm')         # 取得所有公司毛利率
    """
    
    def __init__(self, db_path: Path = None):
        if db_path is None:
            db_path = OUTPUT_DIR
        self.db_path = Path(db_path)
        
        # 載入 metadata
        self.field_map = self._load_json("_meta/field_map.json")
        self.tickers_info = self._load_json("_meta/tickers.json")
        
        # 快取
        self._cache = {}
    
    def _load_json(self, rel_path: str) -> dict:
        """載入 JSON 檔案"""
        path = self.db_path / rel_path
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    @property
    def fields(self) -> List[str]:
        """列出所有可用欄位"""
        return list(self.field_map.keys())
    
    @property
    def tickers(self) -> List[str]:
        """列出所有股票代碼"""
        return self.tickers_info.get("tickers", [])
    
    def get(self, field: str, ticker: str = None, align: bool = True) -> pd.DataFrame:
        """
        取得欄位資料
        
        Args:
            field: 欄位名稱 (如 'close', 'tej_gpm', 'qfii_net')
            ticker: 股票代碼 (可選，若提供則只回傳該股票)
            align: 是否自動對齊到日報日期 (預設 True)
                   季報/月報資料會自動 reindex 並 ffill
        
        Returns:
            DataFrame (rows=日期, cols=股票代碼)
        """
        if field not in self.field_map:
            raise ValueError(f"欄位不存在: {field}。可用欄位: {self.fields}")
        
        # 檢查快取 (用 (field, align) 作為 key)
        cache_key = (field, align)
        if cache_key in self._cache:
            df = self._cache[cache_key]
        else:
            # 載入資料
            info = self.field_map[field]
            category = info["category"]
            
            file_path = self.db_path / category / f"{field}.{OUTPUT_FORMAT}"
            
            if OUTPUT_FORMAT == "parquet":
                df = pd.read_parquet(file_path)
            else:
                df = pd.read_csv(file_path, index_col=0, parse_dates=True)
            
            # 自動對齊: 如果不是 price 類資料，對齊到日報日期
            if align and category != "price":
                df = self._align_to_daily(df)
            
            # 快取
            self._cache[cache_key] = df
        
        # 若指定股票代碼
        if ticker:
            if ticker not in df.columns:
                raise ValueError(f"股票代碼不存在: {ticker}")
            return df[[ticker]]
        
        return df
    
    def _align_to_daily(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        將非日報資料對齊到日報日期
        
        Args:
            df: 原始資料 (可能是季報、月報、籌碼等)
        
        Returns:
            對齊到日報日期的資料，用前值填充
        """
        # 取得日報日期索引 (用 close)
        if 'close' not in self._cache.get(('close', True), {}) if isinstance(self._cache.get(('close', True)), dict) else False:
            close_path = self.db_path / "price" / f"close.{OUTPUT_FORMAT}"
            if OUTPUT_FORMAT == "parquet":
                daily_index = pd.read_parquet(close_path).index
            else:
                daily_index = pd.read_csv(close_path, index_col=0, parse_dates=True).index
        else:
            daily_index = self._cache[('close', True)].index
        
        # 對齊並填充
        df_aligned = df.reindex(daily_index).ffill()
        
        return df_aligned
    
    def info(self, field: str = None) -> dict:
        """取得欄位資訊"""
        if field:
            return self.field_map.get(field, {})
        return self.field_map
    
    def describe(self):
        """印出資料庫摘要"""
        print("=" * 60)
        print("📊 Field Database")
        print("=" * 60)
        print(f"路徑: {self.db_path}")
        print(f"股票數: {len(self.tickers)}")
        print(f"欄位數: {len(self.fields)}")
        print("\n可用欄位:")
        
        by_category = {}
        for field, info in self.field_map.items():
            cat = info['category']
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append((field, info['description']))
        
        for cat, fields in by_category.items():
            print(f"\n  {cat}/")
            for field, desc in fields:
                print(f"    • {field:<20} - {desc}")


# ═══════════════════════════════════════════════════════════════════════════════
# 主程式入口
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """主程式"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Field Database Builder - 欄位資料庫建構器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  python build_field_database.py              # 建構資料庫
  python build_field_database.py --format csv # 使用 CSV 格式
  python build_field_database.py --list       # 列出已建構的欄位
        """
    )
    parser.add_argument('--format', choices=['parquet', 'csv'], default='parquet',
                        help='輸出格式 (預設: parquet)')
    parser.add_argument('--source', type=str, default=None,
                        help='來源目錄 (預設: Stock_Pool/Database)')
    parser.add_argument('--output', type=str, default=None,
                        help='輸出目錄 (預設: Platform/FieldDB)')
    parser.add_argument('--list', action='store_true',
                        help='列出已建構的欄位')
    
    args = parser.parse_args()
    
    # 修改全域設定
    global OUTPUT_FORMAT
    OUTPUT_FORMAT = args.format
    
    if args.list:
        # 列出已建構的欄位
        db = FieldDB()
        db.describe()
        return
    
    # 建構資料庫
    source = Path(args.source) if args.source else SOURCE_DIR
    output = Path(args.output) if args.output else OUTPUT_DIR
    
    builder = FieldDatabaseBuilder(source, output)
    builder.build()
    
    print("\n" + "=" * 70)
    print("🎉 使用方式:")
    print("=" * 70)
    print("""
>>> from Platform.Core.build_field_database import FieldDB
>>> db = FieldDB()
>>> 
>>> # 取得所有公司收盤價
>>> close = db.get('close')
>>> 
>>> # 取得台積電收盤價
>>> tsmc_close = db.get('close', '2330')
>>> 
>>> # 取得所有公司毛利率
>>> gpm = db.get('tej_gpm')
>>> 
>>> # 列出所有可用欄位
>>> print(db.fields)
>>> 
>>> # 查看欄位資訊
>>> db.describe()
""")


if __name__ == "__main__":
    main()
