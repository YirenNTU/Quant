import json
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import random


def convert_numpy_types(obj):
    """遞迴轉換 numpy 型別為 Python 原生型別"""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_numpy_types(v) for v in obj]
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    if isinstance(obj, (np.floating, np.float64, np.float32)):
        if np.isnan(obj):
            return None
        return float(obj)
    if isinstance(obj, np.ndarray):
        return [convert_numpy_types(v) for v in obj.tolist()]
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if isinstance(obj, np.bool_):
        return bool(obj)
    try:
        if pd.isna(obj):
            return None
    except (TypeError, ValueError):
        pass
    return obj

# 引用 tej_tool 的設定與 loader
try:
    from tej_tool import loader, TEJ_CONFIG, set_offline_mode
    import tejapi
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from tej_tool import loader, TEJ_CONFIG, set_offline_mode
    import tejapi

# 下載時需要關閉離線模式以使用 API
set_offline_mode(False)

# 設定資料庫路徑
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "Stock_Pool", "Database")
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)


def download_chip_data(ticker_code: str, days: int = 1460) -> pd.DataFrame | None:
    """
    從 TEJ API 下載籌碼資料 (APISHRACT)
    
    欄位說明:
    - qfii_ex: 外資買賣超
    - fund_ex: 投信買賣超
    - qfii_pct: 外資持股比例
    - fd_pct: 投信持股比例
    - tot_ex: 三大法人合計買賣超
    - long_t: 融資餘額
    - short_t: 融券餘額
    - s_l_pct: 券資比
    - dlr_ex: 自營商買賣超
    - dlr_pct: 自營商持股比例
    - lmr: 融資維持率
    - smr: 融券維持率
    """
    try:
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        data = tejapi.get(
            'TWN/APISHRACT',
            coid=ticker_code,
            mdate={'gte': start_date, 'lte': end_date},
            opts={'sort': 'mdate.desc'},
            paginate=True
        )
        
        if data.empty:
            return None
        
        # 保留所有需要的欄位
        keep_cols = [
            'mdate', 
            'qfii_ex', 'fund_ex', 'tot_ex', 'dlr_ex',      # 買賣超
            'qfii_pct', 'fd_pct', 'dlr_pct',               # 持股比例
            'qfii_buy', 'qfii_sell',                       # 外資買/賣量
            'fund_buy', 'fund_sell',                       # 投信買/賣量
            'long_t', 'short_t', 's_l_pct',                # 融資融券
            'lmr', 'smr', 'tmr',                           # 維持率
            'borr_t1',                                     # 借券餘額
        ]
        available_cols = [c for c in keep_cols if c in data.columns]
        
        return data[available_cols]
    
    except Exception as e:
        print(f"   ⚠️  籌碼下載失敗: {e}")
        return None


def download_monthly_sales(ticker_code: str, months: int = 48) -> pd.DataFrame | None:
    """
    從 TEJ API 下載月營收資料 (APISALE)
    
    欄位說明:
    - d0001: 月營收 (千元) - 合併
    - d0002: 月營收 (千元)
    - d0003: 營收年增率 (%)
    - d0004: 營收月增率 (%)
    - d0005: 累計營收 (千元)
    - d0006: 累計營收年增率 (%)
    - d0007: 累計營收月增率 (%)
    """
    try:
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=months * 31)).strftime('%Y-%m-%d')
        
        data = tejapi.get(
            'TWN/APISALE',
            coid=ticker_code,
            mdate={'gte': start_date, 'lte': end_date},
            opts={'sort': 'mdate.desc'},
            paginate=True
        )
        
        if data.empty:
            return None
        
        # 保留月營收相關欄位
        keep_cols = ['mdate', 'd0001', 'd0002', 'd0003', 'd0004', 'd0005', 'd0006', 'd0007']
        available_cols = [c for c in keep_cols if c in data.columns]
        
        return data[available_cols]
    
    except Exception as e:
        print(f"   ⚠️  月營收下載失敗: {e}")
        return None


def download_dividend_data(ticker_code: str, years: int = 4) -> pd.DataFrame | None:
    """
    從 TEJ API 下載股利資料 (APIDV1)
    
    欄位說明:
    - divc: 現金股利
    - divs: 股票股利
    - distri_type: 配息類型 (Q1, Q2, Q3, Q4, FY)
    - edexdate: 除息日
    - div_date: 發放日
    """
    try:
        data = tejapi.get(
            'TWN/APIDV1',
            coid=ticker_code,
            opts={'sort': 'mdate.desc', 'limit': years * 4}  # 約 5 年 * 4 季
        )
        
        if data.empty:
            return None
        
        keep_cols = ['mdate', 'distri_type', 'divc', 'divs', 'edexdate', 'div_date', 
                     'distri_beg', 'distri_end']
        available_cols = [c for c in keep_cols if c in data.columns]
        
        return data[available_cols]
    
    except Exception as e:
        print(f"   ⚠️  股利下載失敗: {e}")
        return None


def download_self_announced(ticker_code: str, months: int = 48) -> pd.DataFrame | None:
    """
    從 TEJ API 下載自結數資料 (AFESTM1)
    
    自結數是公司自行公布的財務數據，比季報更即時
    
    欄位說明:
    - ip12: 營收
    - opi: 營業利益
    - isibt: 稅前淨利
    - isnip: 稅後淨利
    - eps: 每股盈餘
    - r106: 營益率%
    - r107: 稅前淨利率%
    - r401: 營收成長率%
    """
    try:
        data = tejapi.get(
            'TWN/AFESTM1',
            coid=ticker_code,
            opts={'sort': 'mdate.desc', 'limit': months}
        )
        
        if data.empty:
            return None
        
        keep_cols = ['mdate', 'annd', 'sem', 'ip12', 'opi', 'isibt', 'isnip', 
                     'eps', 'r105', 'r106', 'r107', 'r401', 'r403', 'r404']
        available_cols = [c for c in keep_cols if c in data.columns]
        
        return data[available_cols]
    
    except Exception as e:
        print(f"   ⚠️  自結數下載失敗: {e}")
        return None


def download_stock_info(ticker_code: str) -> dict | None:
    """
    從 TEJ API 下載證券屬性 (APISTOCK)
    
    欄位說明:
    - stk_name: 股票簡稱
    - stk_f_chi: 公司全名
    - main_ind_c: 主產業
    - sub_ind_c: 次產業
    - list_date: 上市日期
    """
    try:
        data = tejapi.get(
            'TWN/APISTOCK',
            coid=ticker_code,
            opts={'limit': 1}
        )
        
        if data.empty:
            return None
        
        row = data.iloc[0]
        return {
            'stk_name': row.get('stk_name'),
            'stk_f_chi': row.get('stk_f_chi'),
            'enm': row.get('enm'),
            'stk_eng': row.get('stk_eng'),
            'main_ind_c': row.get('main_ind_c'),
            'main_ind_e': row.get('main_ind_e'),
            'sub_ind_c': row.get('sub_ind_c'),
            'sub_ind_e': row.get('sub_ind_e'),
            'list_date': row.get('list_date'),
        }
    
    except Exception as e:
        print(f"   ⚠️  證券屬性下載失敗: {e}")
        return None


def download_capital_change(ticker_code: str, years: int = 4) -> pd.DataFrame | None:
    """
    從 TEJ API 下載資本形成資料 (APISTK1)
    
    欄位說明:
    - stk_amt: 股本 (千元)
    - slamt: 流通股數 (千股)
    - cash: 現金增資
    - earning: 盈餘轉增資
    - bonus: 員工紅利
    """
    try:
        data = tejapi.get(
            'TWN/APISTK1',
            coid=ticker_code,
            opts={'sort': 'mdate.desc', 'limit': years * 4}
        )
        
        if data.empty:
            return None
        
        keep_cols = ['mdate', 'stk_amt', 'slamt', 'cash', 'earning', 'capital', 
                     'bonus', 'cap_dec', 'x_cap_date']
        available_cols = [c for c in keep_cols if c in data.columns]
        
        return data[available_cols]
    
    except Exception as e:
        print(f"   ⚠️  資本形成下載失敗: {e}")
        return None


def download_all_data(tickers, force_update=False):
    """
    下載所有股票的完整資料
    
    Args:
        tickers: 股票代碼清單
        force_update: 是否強制重新下載 (忽略快取)
    """
    print("="*60)
    print(f"🚀 TEJ 完整資料下載器 (Full Data Mode)")
    print(f"🎯 目標: {len(tickers)} 支股票")
    print(f"💾 儲存: {DB_DIR}")
    print("="*60)
    
    success_count = 0
    skip_count = 0
    fail_count = 0
    
    today_str = datetime.now().strftime('%Y%m%d')
    
    # 預先掃描已存在的股票代碼 (只看代碼，不看日期)
    existing_codes = set()
    if not force_update:
        for filename in os.listdir(DB_DIR):
            if filename.endswith('.json'):
                code_part = filename.rsplit('_', 1)[0]
                existing_codes.add(code_part)
    
    print(f"📂 快取中已有 {len(existing_codes)} 支股票資料")
    print("💡 如需全部重新下載，請手動刪除 Database 資料夾內的檔案\n")
    
    for i, ticker in enumerate(tickers):
        # 1. 檢查股票代碼是否已存在快取
        code = ticker.split('.')[0]
        
        if code in existing_codes and not force_update:
            print(f"[{i+1}/{len(tickers)}] {ticker} ✅ 快取已存在，跳過")
            skip_count += 1
            continue
        
        print(f"\n[{i+1}/{len(tickers)}] 處理 {ticker} ...")
        file_path = os.path.join(DB_DIR, f"{code}_{today_str}.json")
            
        try:
            # ============================================================
            # A. 股價：抓取 4 年 (1460天)
            # ============================================================
            print("   📉 下載股價 (最近4年)...") 
            price = loader.get_history(ticker, period_days=1460)
            
            if price.empty:
                print("   ⚠️ 無股價資料")
            
            # ============================================================
            # B. 財報：抓最近 16 季 (4年)
            # ============================================================
            print("   📊 下載財報 (近16季)...")
            fin, bs, cf = loader.get_financials(ticker, quarters=16)
            
            # ============================================================
            # C. 基本資料
            # ============================================================
            print("   ℹ️  下載基本資料...")
            info = loader.get_info(ticker)
            
            # ============================================================
            # D. 籌碼資料：抓取最近 4 年 (1460天)
            # ============================================================
            print("   🎯 下載籌碼 (近4年)...")
            chip = download_chip_data(code, days=1460)
            
            # ============================================================
            # E. 月營收資料：抓取最近 48 個月 (4年)
            # ============================================================
            print("   📈 下載月營收 (近48個月)...")
            monthly_sales = download_monthly_sales(code, months=48)
            
            # ============================================================
            # F. 股利資料：抓取最近 4 年
            # ============================================================
            print("   💰 下載股利 (近4年)...")
            dividend = download_dividend_data(code, years=4)
            
            # ============================================================
            # G. 自結數：抓取最近 48 個月 (4年)
            # ============================================================
            print("   📋 下載自結數 (近48個月)...")
            self_announced = download_self_announced(code, months=48)
            
            # ============================================================
            # H. 證券屬性
            # ============================================================
            print("   🏢 下載證券屬性...")
            stock_info = download_stock_info(code)
            
            # ============================================================
            # I. 資本形成：抓取最近 4 年
            # ============================================================
            print("   📑 下載資本形成 (近4年)...")
            capital = download_capital_change(code, years=4)
            
            # ============================================================
            # 整合並儲存
            # ============================================================
            def safe_to_json(df):
                if df is None or (hasattr(df, 'empty') and df.empty):
                    return None
                try:
                    return df.to_json(date_format='iso', orient='split')
                except Exception:
                    return df.to_json(date_format='iso', orient='records')
            
            def serialize_value(v):
                """將單一值轉換為可 JSON 序列化的格式"""
                if v is None:
                    return None
                if hasattr(v, 'isoformat'):
                    return v.isoformat()
                if isinstance(v, (np.integer, np.int64)):
                    return int(v)
                if isinstance(v, (np.floating, np.float64)):
                    return float(v) if not np.isnan(v) else None
                if isinstance(v, np.ndarray):
                    return v.tolist()
                if pd.isna(v):
                    return None
                return v
            
            def serialize_info(info_dict):
                """將 info 字典中的值轉換為可序列化格式"""
                if not info_dict:
                    return {}
                return {k: serialize_value(v) for k, v in info_dict.items()}
            
            data_package = {
                "ticker": ticker,
                "info": serialize_info(info),
                "stock_info": serialize_info(stock_info),        # 🆕 證券屬性
                "price": safe_to_json(price),
                "financials": safe_to_json(fin),
                "balance_sheet": safe_to_json(bs),
                "cashflow": safe_to_json(cf),
                "chip": safe_to_json(chip),
                "monthly_sales": safe_to_json(monthly_sales),
                "dividend": safe_to_json(dividend),               # 🆕 股利資料
                "self_announced": safe_to_json(self_announced),   # 🆕 自結數
                "capital": safe_to_json(capital),                 # 🆕 資本形成
                "updated_at": datetime.now().isoformat()
            }
            
            # 轉換所有 numpy 型別為 Python 原生型別
            data_package_clean = convert_numpy_types(data_package)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data_package_clean, f, ensure_ascii=False, indent=2)
                
            print(f"   💾 已儲存至 {code}_{today_str}.json")
            success_count += 1
            
            # API 禮貌延遲
            time.sleep(0.1)
            
        except Exception as e:
            print(f"   ❌ 下載失敗: {e}")
            fail_count += 1

    print("\n" + "="*60)
    print(f"🏁 下載作業結束")
    print(f"✅ 成功: {success_count}")
    print(f"⏩ 跳過: {skip_count}")
    print(f"❌ 失敗: {fail_count}")
    print("="*60)


def test_single_download(ticker='2330.TW'):
    """測試單一股票下載 (用於驗證新增欄位)"""
    print("="*60)
    print(f"🧪 測試下載: {ticker}")
    print("="*60)
    
    code = ticker.split('.')[0]
    
    # 測試各個下載函數
    print("\n1. 籌碼資料 (APISHRACT):")
    chip = download_chip_data(code, days=10)
    if chip is not None:
        print(f"   ✅ 成功! {len(chip)} 筆, 欄位: {list(chip.columns)}")
    else:
        print("   ❌ 失敗")
    
    print("\n2. 月營收 (APISALE):")
    sales = download_monthly_sales(code, months=3)
    if sales is not None:
        print(f"   ✅ 成功! {len(sales)} 筆, 欄位: {list(sales.columns)}")
    else:
        print("   ❌ 失敗")
    
    print("\n3. 股利資料 (APIDV1):")
    div = download_dividend_data(code, years=2)
    if div is not None:
        print(f"   ✅ 成功! {len(div)} 筆, 欄位: {list(div.columns)}")
        print(f"   範例: {div.iloc[0].to_dict()}")
    else:
        print("   ❌ 失敗")
    
    print("\n4. 自結數 (AFESTM1):")
    self_ann = download_self_announced(code, months=6)
    if self_ann is not None:
        print(f"   ✅ 成功! {len(self_ann)} 筆, 欄位: {list(self_ann.columns)}")
        print(f"   範例: {self_ann.iloc[0].to_dict()}")
    else:
        print("   ❌ 失敗")
    
    print("\n5. 證券屬性 (APISTOCK):")
    stock_info = download_stock_info(code)
    if stock_info:
        print(f"   ✅ 成功!")
        for k, v in stock_info.items():
            print(f"      {k}: {v}")
    else:
        print("   ❌ 失敗")
    
    print("\n6. 資本形成 (APISTK1):")
    capital = download_capital_change(code, years=1)
    if capital is not None:
        print(f"   ✅ 成功! {len(capital)} 筆, 欄位: {list(capital.columns)}")
    else:
        print("   ❌ 失敗")
    
    print("\n" + "="*60)
    print("🧪 測試完成!")
    print("="*60)


if __name__ == "__main__":
    import sys
    
    # 如果有 --test 參數，執行測試
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        ticker = sys.argv[2] if len(sys.argv) > 2 else '2330.TW'
        test_single_download(ticker)
    else:
        # 正常下載模式
        list_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "Stock_Pool", "list.json")
        try:
            with open(list_path, 'r', encoding='utf-8') as f:
                tickers = list(json.load(f).keys())
            
            download_all_data(tickers)
            
        except Exception as e:
            print(f"❌ 無法讀取股票清單: {e}")
