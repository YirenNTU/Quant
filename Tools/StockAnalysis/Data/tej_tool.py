import tejapi
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import json
import hashlib
from glob import glob
from io import StringIO

# ==========================================
# 請在此填入您的 TEJ API KEY
# ==========================================
TEJ_API_KEY = "IhsvheTNyKTZKBWPD60Pr60abQS5iA"

# ==========================================
# TEJ 資料表設定 (E-SHOP 初入江湖版)
# ==========================================
TEJ_CONFIG = {
    'TABLE_PRICE': 'TWN/APIPRCD',
    'TABLE_FINANCIALS': 'TWN/AINVFINB',
    'TABLE_BASIC': 'TWN/APISTOCK'
}

tejapi.ApiConfig.api_key = TEJ_API_KEY
tejapi.ApiConfig.ignoretz = True

# ==========================================
# 資料庫設定 (優先讀取本地資料庫)
# ==========================================
DATABASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "Stock_Pool", "Database")

# 快取設定 (當資料庫無資料時的備援)
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tej_cache")
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# ==========================================
# 模式設定: True = 僅讀取本地資料庫，不呼叫 API
# 注意: data_downloader.py 會直接設定 OFFLINE_MODE = False
# ==========================================
OFFLINE_MODE = True

def set_offline_mode(enabled: bool):
    """設定離線模式開關"""
    global OFFLINE_MODE
    OFFLINE_MODE = enabled

class TEJLoader:
    def __init__(self):
        self.api_key = TEJ_API_KEY
        if self.api_key == "YOUR_TEJ_API_KEY_HERE":
            print("⚠️ 警告: 請在 tej_tool.py 中設定您的 TEJ API KEY")
        
        # 載入本地資料庫
        self._database = {}
        self._load_database()

    def _load_database(self):
        """載入本地資料庫 (由 data_downloader.py 下載的資料)"""
        if not os.path.exists(DATABASE_DIR):
            if OFFLINE_MODE:
                print(f"⚠️ 警告: 資料庫目錄不存在: {DATABASE_DIR}")
                print("   請先執行 data_downloader.py 下載資料")
            return
        
        # 找出所有 JSON 檔案
        json_files = glob(os.path.join(DATABASE_DIR, "*.json"))
        
        for json_path in json_files:
            try:
                filename = os.path.basename(json_path)
                # 檔名格式: {code}_{date}.json
                parts = filename.replace('.json', '').split('_')
                if len(parts) >= 2:
                    code = parts[0]
                    
                    # 只保留最新的資料 (若有多個日期)
                    if code not in self._database:
                        self._database[code] = json_path
                    else:
                        # 比較日期，保留較新的
                        existing_date = os.path.basename(self._database[code]).replace('.json', '').split('_')[1]
                        new_date = parts[1]
                        if new_date > existing_date:
                            self._database[code] = json_path
            except Exception as e:
                continue
        
        if self._database:
            print(f"📂 已載入本地資料庫: {len(self._database)} 支股票")

    def _load_from_database(self, ticker):
        """從本地資料庫載入股票資料"""
        code = self._get_ticker_code(ticker)
        
        if code not in self._database:
            return None
        
        try:
            with open(self._database[code], 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except Exception as e:
            print(f"⚠️ 載入資料庫失敗 {code}: {e}")
            return None

    def _get_ticker_code(self, ticker):
        return ticker.split('.')[0]

    def _get_cache_path(self, ticker, data_type):
        today = datetime.now().strftime('%Y%m%d')
        filename = f"{ticker}_{data_type}_{today}.pkl"
        return os.path.join(CACHE_DIR, filename)

    def _load_from_cache(self, ticker, data_type):
        path = self._get_cache_path(ticker, data_type)
        if os.path.exists(path):
            try:
                return pd.read_pickle(path)
            except:
                return None
        return None

    def _save_to_cache(self, data, ticker, data_type):
        if data is not None and not data.empty:
            path = self._get_cache_path(ticker, data_type)
            pd.to_pickle(data, path)

    def get_history(self, ticker, start_date=None, end_date=None, period_days=365): 
        # 回復預設為 365 天 (一年)
        code = self._get_ticker_code(ticker)
        
        # ===== 1. 優先從本地資料庫載入 =====
        db_data = self._load_from_database(ticker)
        if db_data and db_data.get('price'):
            try:
                # 嘗試 split 格式 (新版)
                price_df = pd.read_json(StringIO(db_data['price']), orient='split')
                if not price_df.empty:
                    # 確保索引是日期
                    if 'Date' in price_df.columns:
                        price_df.set_index('Date', inplace=True)
                    return price_df
            except Exception:
                try:
                    # 降級嘗試 columns 格式 (舊版)
                    price_df = pd.read_json(StringIO(db_data['price']))
                    if not price_df.empty:
                        if 'Date' in price_df.columns:
                            price_df.set_index('Date', inplace=True)
                        return price_df
                except Exception:
                    pass  # 繼續嘗試其他來源
        
        # ===== 2. 從快取載入 =====
        cached_data = self._load_from_cache(code, 'price')
        if cached_data is not None:
            return cached_data

        # ===== 3. 離線模式下，若無本地資料則返回空 =====
        if OFFLINE_MODE:
            # print(f"⚠️ 離線模式: {code} 無本地股價資料")
            return pd.DataFrame()

        # ===== 4. 從 API 載入 (僅在非離線模式) =====
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=period_days)
            
        try:
            table = TEJ_CONFIG['TABLE_PRICE']
            
            data = tejapi.get(table,
                             coid=code,
                             mdate={'gte': start_date, 'lte': end_date},
                             opts={'sort': 'mdate.asc'},
                             paginate=True)
            
            if len(data) == 0:
                return pd.DataFrame()
            
            rename_map = {
                'mdate': 'Date',
                'open_d': 'Open',
                'high_d': 'High',
                'low_d': 'Low',
                'close_d': 'Close',
                'vol': 'Volume',
                'volume': 'Volume'
            }
            
            data = data.rename(columns=rename_map)
            
            if 'Volume' not in data.columns:
                data['Volume'] = 0
            else:
                data['Volume'] = data['Volume'] * 1000 
            
            data.set_index('Date', inplace=True)
            
            self._save_to_cache(data, code, 'price')
            
            return data
            
        except Exception as e:
            print(f"TEJ API Error (History): {e}")
            return pd.DataFrame()

    def get_financials(self, ticker, quarters=8): 
        # 回復預設為 8 季 (兩年)
        code = self._get_ticker_code(ticker)
        
        # ===== 1. 優先從本地資料庫載入 =====
        db_data = self._load_from_database(ticker)
        if db_data:
            def load_df_from_json(json_str):
                """載入 JSON 字串為 DataFrame，支援多種格式"""
                if not json_str:
                    return None
                try:
                    # 嘗試 split 格式 (新版)
                    return pd.read_json(StringIO(json_str), orient='split')
                except Exception:
                    try:
                        # 降級嘗試 columns 格式 (舊版)
                        return pd.read_json(StringIO(json_str))
                    except Exception:
                        return None
            
            try:
                fin_df = load_df_from_json(db_data.get('financials'))
                bs_df = load_df_from_json(db_data.get('balance_sheet'))
                cf_df = load_df_from_json(db_data.get('cashflow'))
                
                # 若有任何一個有效，就返回
                if fin_df is not None or bs_df is not None or cf_df is not None:
                    return fin_df, bs_df, cf_df
            except Exception as e:
                pass  # 繼續嘗試其他來源
        
        # ===== 2. 從快取載入 =====
        cached_data = self._load_from_cache(code, 'financials')
        if cached_data is not None:
            return cached_data 

        # ===== 3. 離線模式下，若無本地資料則返回空 =====
        if OFFLINE_MODE:
            # print(f"⚠️ 離線模式: {code} 無本地財報資料")
            return None, None, None

        # ===== 4. 從 API 載入 (僅在非離線模式) =====
        try:
            table = TEJ_CONFIG['TABLE_FINANCIALS']
            
            data = tejapi.get(table,
                             coid=code,
                             opts={'limit': quarters, 'sort': 'mdate.desc'},
                             paginate=True)
            
            if len(data) == 0:
                return None, None, None

            if 'a2200' in data.columns:
                data['Gross Profit'] = data['a2200']
            elif 'a3200' in data.columns and 'a3100' in data.columns:
                data['Gross Profit'] = data['a3100'] - data['a3200']
            else:
                data['Gross Profit'] = np.nan

            fin_map = {
                'Total Revenue': ['a2000', 'a3100'],
                'Revenue': ['a2000', 'a3100'],
                'Gross Profit': ['a2200', 'Gross Profit'],
                'Operating Income': ['a2500'],
                'EBIT': ['a2500'],
                'Net Income': ['a3900', 'a2402'],
                'Net Income Common Stockholders': ['a3900', 'a2402'],
                'Pretax Income': ['a3101'],  # 稅前淨利，用於計算業外收支
                'Research And Development': ['rd_expense'],
                # TEJ 官方計算比率
                'TEJ_GPM': ['r105'],
                'TEJ_OPM': ['r106'],
                # 存貨相關指標 (TEJ 已計算好的)
                'Inventory Turnover': ['r610'],      # 存貨週轉率（次）
                'Inventory Days': ['r611'],          # 平均售貨天數 (DOI)
                'Days Sales Outstanding': ['r609'],  # 平均收帳天數 (DSO)
                'Days Payable': ['r614']             # 應付帳款付現天數
            }
            
            bs_map = {
                'Total Assets': ['a0010'],
                'Total Debt': ['a1000'],
                'Total Liabilities Net Minority Interest': ['a1000'],
                'Current Assets': ['a1100'],
                'Total Current Assets': ['a1100'],
                'Current Liabilities': ['a1200'], 
                'Total Current Liabilities': ['a1200'],
                'Accounts Receivable': ['a211f', 'a2111'], 
                'Inventory': ['a2200'],
                'Total Inventory': ['a2200'],
                'Long Term Debt': ['a1400'],
                'Cash And Cash Equivalents': ['a1101']
            }
            
            cf_map = {
                'Operating Cash Flow': ['a7210'],
                'Investing Cash Flow': ['a7220'],
                'Financing Cash Flow': ['a7230'],
                'Capital Expenditure': ['capex']
            }
            
            def create_mock_df(mapping, source_data):
                result_dict = {}
                dates = source_data['mdate'].dt.strftime('%Y-%m-%d').tolist()
                
                for eng_key, chi_keys in mapping.items():
                    found_col = None
                    for chi_key in chi_keys:
                        if chi_key in source_data.columns:
                            found_col = chi_key
                            break
                    
                    if found_col:
                        result_dict[eng_key] = source_data[found_col].tolist()
                    else:
                        result_dict[eng_key] = [None] * len(dates)
                
                return pd.DataFrame(result_dict, index=dates).T

            financials_df = create_mock_df(fin_map, data)
            balance_sheet_df = create_mock_df(bs_map, data)
            cashflow_df = create_mock_df(cf_map, data)
            
            result = (financials_df, balance_sheet_df, cashflow_df)
            
            path = self._get_cache_path(code, 'financials')
            pd.to_pickle(result, path)
            
            return result

        except Exception as e:
            print(f"TEJ API Error (Financials): {e}")
            return None, None, None

    def get_info(self, ticker):
        code = self._get_ticker_code(ticker)
        
        # ===== 1. 優先從本地資料庫載入 =====
        db_data = self._load_from_database(ticker)
        if db_data and db_data.get('info'):
            info = db_data['info']
            if isinstance(info, dict) and info:
                # 從 PRICE 資料補充缺失的 marketCap, PE, PB
                if db_data.get('price') and (not info.get('marketCap') or not info.get('trailingPE')):
                    try:
                        price_df = pd.read_json(StringIO(db_data['price']), orient='split')
                        if not price_df.empty:
                            latest = price_df.iloc[-1]
                            if not info.get('marketCap') and 'mktcap' in latest:
                                info['marketCap'] = latest['mktcap']
                            if not info.get('trailingPE') and 'per' in latest:
                                info['trailingPE'] = latest['per']
                            if not info.get('priceToBook') and 'pbr' in latest:
                                info['priceToBook'] = latest['pbr']
                            if 'div_yid' in latest:
                                info['dividendYield'] = latest['div_yid']
                            if 'psr_tej' in latest:
                                info['priceToSales'] = latest['psr_tej']
                    except Exception:
                        pass
                return info
        
        # ===== 2. 從快取載入 =====
        cached_data = self._load_from_cache(code, 'info')
        if cached_data is not None:
            return cached_data.to_dict() if isinstance(cached_data, pd.Series) else cached_data

        # ===== 3. 離線模式下，若無本地資料則返回空 =====
        if OFFLINE_MODE:
            # print(f"⚠️ 離線模式: {code} 無本地基本資料")
            return {}

        # ===== 4. 從 API 載入 (僅在非離線模式) =====
        try:
            price_table = TEJ_CONFIG['TABLE_PRICE']
            end_date = datetime.now()
            start_date = end_date - timedelta(days=10)
            
            price_data = tejapi.get(price_table,
                                   coid=code,
                                   mdate={'gte': start_date, 'lte': end_date},
                                   opts={'sort': 'mdate.desc', 'limit': 1},
                                   paginate=True)
            
            current_price = None
            trailing_pe = None
            pb_ratio = None
            
            if len(price_data) > 0:
                row = price_data.iloc[0]
                current_price = row.get('close_d')
                trailing_pe = row.get('per')
                pb_ratio = row.get('pbr')
            
            basic_table = TEJ_CONFIG['TABLE_BASIC']
            try:
                basic = tejapi.get(basic_table, coid=code)
            except:
                basic = pd.DataFrame()
            
            # 從 APISTOCK 取得公司基本資料
            sector = 'Unknown'
            sub_industry = 'Unknown'
            company_name = ''
            company_name_full = ''
            list_date = None
            
            if len(basic) > 0:
                row = basic.iloc[0]
                sector = row.get('main_ind_c', 'Unknown')           # M2300 電子工業
                sub_industry = row.get('sub_ind_c', 'Unknown')      # M2324 半導體業
                company_name = row.get('stk_name', '')              # 台積電
                company_name_full = row.get('stk_f_chi', '')        # 台灣積體電路製造
                list_date = row.get('list_date', None)              # 上市日期
            
            info_dict = {
                'symbol': ticker,
                'shortName': company_name,                          # 股票簡稱
                'longName': company_name_full,                      # 公司全名
                'currentPrice': current_price,
                'regularMarketPrice': current_price,
                'sector': sector,                                   # 主產業
                'industry': sub_industry,                           # 次產業 (更細分)
                'subIndustry': sub_industry,                        # 次產業別名
                'marketCap': None,                                  # TEJ 此方案無市值
                'trailingPE': trailing_pe,
                'priceToBook': pb_ratio,
                'forwardPE': None,                                  # TEJ 此方案無預估PE
                'pegRatio': None,                                   # TEJ 此方案無PEG
                'listDate': list_date                               # 上市日期
            }
            
            self._save_to_cache(pd.Series(info_dict), code, 'info')
            
            return info_dict
            
        except Exception as e:
            print(f"TEJ API Error (Info): {e}")
            return {}
    
    def get_chip(self, ticker, days=60):
        """
        獲取籌碼資料 (三大法人買賣超、融資融券)
        
        優先順序: 本地資料庫 → API (若非離線模式)
        
        Returns:
            DataFrame with columns: mdate, qfii_ex, fund_ex, qfii_pct, tot_ex, etc.
        """
        code = self._get_ticker_code(ticker)
        
        # ===== 1. 優先從本地資料庫載入 =====
        db_data = self._load_from_database(ticker)
        if db_data and db_data.get('chip'):
            try:
                chip_df = pd.read_json(StringIO(db_data['chip']), orient='split')
                if not chip_df.empty:
                    return chip_df
            except Exception:
                try:
                    # 降級嘗試 records 格式
                    chip_df = pd.read_json(StringIO(db_data['chip']), orient='records')
                    if not chip_df.empty:
                        return chip_df
                except Exception:
                    pass
        
        # ===== 2. 離線模式下返回空 =====
        if OFFLINE_MODE:
            return pd.DataFrame()
        
        # ===== 3. 從 API 載入 =====
        try:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            data = tejapi.get(
                'TWN/APISHRACT',
                coid=code,
                mdate={'gte': start_date, 'lte': end_date},
                opts={'sort': 'mdate.desc'},
                paginate=True
            )
            
            if data.empty:
                return pd.DataFrame()
            
            # 只保留需要的欄位
            keep_cols = ['mdate', 'qfii_ex', 'fund_ex', 'qfii_pct', 'fd_pct', 
                         'tot_ex', 'long_t', 'short_t', 's_l_pct', 'dlr_ex', 'dlr_pct']
            available_cols = [c for c in keep_cols if c in data.columns]
            
            return data[available_cols]
        
        except Exception as e:
            print(f"TEJ API Error (Chip): {e}")
            return pd.DataFrame()

    def get_monthly_sales(self, ticker, months=15):
        """
        獲取月營收資料 (TWN/APISALE)
        
        優先順序: 本地資料庫 → API (若非離線模式)
        
        欄位說明:
        - d0002: 月營收 (千元)
        - d0003: 營收年增率 (%)
        - d0006: 累計營收年增率 (%)
        
        Returns:
            DataFrame with columns: mdate, d0002, d0003, d0006, etc.
        """
        code = self._get_ticker_code(ticker)
        
        # ===== 1. 優先從本地資料庫載入 =====
        db_data = self._load_from_database(ticker)
        if db_data and db_data.get('monthly_sales'):
            try:
                sales_df = pd.read_json(StringIO(db_data['monthly_sales']), orient='split')
                if not sales_df.empty:
                    return sales_df
            except Exception:
                try:
                    # 降級嘗試 records 格式
                    sales_df = pd.read_json(StringIO(db_data['monthly_sales']), orient='records')
                    if not sales_df.empty:
                        return sales_df
                except Exception:
                    pass
        
        # ===== 2. 離線模式下返回空 =====
        if OFFLINE_MODE:
            return pd.DataFrame()
        
        # ===== 3. 從 API 載入 =====
        try:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=months * 31)).strftime('%Y-%m-%d')
            
            data = tejapi.get(
                'TWN/APISALE',
                coid=code,
                mdate={'gte': start_date, 'lte': end_date},
                opts={'sort': 'mdate.desc'},
                paginate=True
            )
            
            if data.empty:
                return pd.DataFrame()
            
            # 只保留需要的欄位
            keep_cols = ['mdate', 'd0001', 'd0002', 'd0003', 'd0004', 'd0005', 'd0006']
            available_cols = [c for c in keep_cols if c in data.columns]
            
            return data[available_cols]
        
        except Exception as e:
            print(f"TEJ API Error (Monthly Sales): {e}")
            return pd.DataFrame()

loader = TEJLoader()

class TEJTicker:
    def __init__(self, ticker):
        self.ticker = ticker
        self.info = loader.get_info(ticker)
        self.quarterly_financials, self.quarterly_balance_sheet, self.quarterly_cashflow = loader.get_financials(ticker)
        
        self.financials = self.quarterly_financials
        self.balance_sheet = self.quarterly_balance_sheet
        self.cashflow = self.quarterly_cashflow

    def history(self, period="1mo", start=None, end=None):
        days = 30
        if "d" in period:
            days = int(period.replace("d", ""))
        elif "mo" in period:
            days = int(period.replace("mo", "")) * 30
        elif "y" in period:
            days = int(period.replace("y", "")) * 365
            
        # 額度夠多，不需要強制覆蓋天數了，但預設還是給個合理值
        if days > 730: days = 730 # 最多抓 2 年
            
        return loader.get_history(self.ticker, start_date=start, end_date=end, period_days=days)

class MockYFinance:
    def Ticker(self, ticker):
        return TEJTicker(ticker)

yf = MockYFinance()
