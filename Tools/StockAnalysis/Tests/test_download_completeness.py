#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
資料下載完整性測試
==================

目的：測試單一股票的資料下載是否包含所有分析所需欄位
避免完整下載前浪費 API 額度

使用方式：
    python test_download_completeness.py
"""

import os
import sys
import json
import pandas as pd
from datetime import datetime, timedelta
from io import StringIO

# 引用 tej_tool - 添加 Data 資料夾到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Data'))
from tej_tool import TEJ_API_KEY, TEJ_CONFIG, set_offline_mode
import tejapi

# 設定 API
tejapi.ApiConfig.api_key = TEJ_API_KEY
tejapi.ApiConfig.ignoretz = True

# 關閉離線模式以測試 API
set_offline_mode(False)

# 測試股票 (台積電)
TEST_TICKER = '2330'

print("="*70)
print("🧪 資料下載完整性測試")
print("="*70)
print(f"📅 測試時間: {datetime.now()}")
print(f"🎯 測試股票: {TEST_TICKER}")
print(f"🔑 API Key: {TEJ_API_KEY[:8]}...{TEJ_API_KEY[-4:]}")
print("="*70)


def test_price_data():
    """測試股價資料"""
    print("\n📉 [1/5] 測試股價資料 (TWN/APIPRCD)...")
    
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)  # 只測試 30 天
        
        data = tejapi.get(
            TEJ_CONFIG['TABLE_PRICE'],
            coid=TEST_TICKER,
            mdate={'gte': start_date, 'lte': end_date},
            opts={'sort': 'mdate.desc', 'limit': 5},
            paginate=True
        )
        
        if data.empty:
            print("   ❌ 無資料")
            return False
        
        print(f"   ✅ 取得 {len(data)} 筆資料")
        
        # 檢查必要欄位
        required = ['mdate', 'close_d', 'open_d', 'high_d', 'low_d']
        available = [c for c in required if c in data.columns]
        missing = [c for c in required if c not in data.columns]
        
        print(f"   📋 必要欄位: {available}")
        if missing:
            print(f"   ⚠️  缺少: {missing}")
        
        # 額外欄位 (用於估值)
        extras = ['per', 'pbr', 'psr_tej', 'div_yid', 'mktcap']
        extra_available = [c for c in extras if c in data.columns]
        print(f"   📊 估值欄位: {extra_available}")
        
        return True
    
    except Exception as e:
        print(f"   ❌ 錯誤: {e}")
        return False


def test_financials_data():
    """測試財報資料"""
    print("\n📊 [2/5] 測試財報資料 (TWN/AINVFINB)...")
    
    try:
        data = tejapi.get(
            TEJ_CONFIG['TABLE_FINANCIALS'],
            coid=TEST_TICKER,
            opts={'sort': 'mdate.desc', 'limit': 2},
            paginate=True
        )
        
        if data.empty:
            print("   ❌ 無資料")
            return False
        
        print(f"   ✅ 取得 {len(data)} 筆資料")
        
        # 檢查核心欄位
        core_fields = {
            'a3100': '營收',
            'a3295': '毛利',
            'a3395': '營業利益',
            'a2402': '稅前息前淨利 (EBIT)',
            'a0010': '總資產',
            'a7210': 'OCF',
            'a7300': 'ICF',
        }
        
        print("   📋 核心欄位:")
        for code, name in core_fields.items():
            if code in data.columns:
                val = data[code].iloc[0]
                print(f"      ✅ {code} ({name}): {val:,.0f}" if pd.notna(val) else f"      ⚠️ {code} ({name}): NULL")
            else:
                print(f"      ❌ {code} ({name}): 缺少")
        
        # 檢查存貨相關欄位 (r611, r610, r609)
        inv_fields = {
            'r611': '存貨週轉天數',
            'r610': '存貨週轉率',
            'r609': 'DSO (收帳天數)',
            'r614': '付款天數',
            'r105': '毛利率',
            'r106': '營益率',
        }
        
        print("   📦 財務比率欄位:")
        for code, name in inv_fields.items():
            if code in data.columns:
                val = data[code].iloc[0]
                print(f"      ✅ {code} ({name}): {val}" if pd.notna(val) else f"      ⚠️ {code} ({name}): NULL")
            else:
                print(f"      ❌ {code} ({name}): 缺少")
        
        return True
    
    except Exception as e:
        print(f"   ❌ 錯誤: {e}")
        return False


def test_chip_data():
    """測試籌碼資料"""
    print("\n🎯 [3/5] 測試籌碼資料 (TWN/APISHRACT)...")
    
    try:
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        data = tejapi.get(
            'TWN/APISHRACT',
            coid=TEST_TICKER,
            mdate={'gte': start_date, 'lte': end_date},
            opts={'sort': 'mdate.desc', 'limit': 5},
            paginate=True
        )
        
        if data.empty:
            print("   ❌ 無資料")
            return False
        
        print(f"   ✅ 取得 {len(data)} 筆資料")
        
        # 檢查必要欄位
        chip_fields = {
            'qfii_ex': '外資買賣超',
            'fund_ex': '投信買賣超',
            'qfii_pct': '外資持股%',
            'fd_pct': '投信持股%',
            'tot_ex': '三大法人合計',
            'long_t': '融資餘額',
            'short_t': '融券餘額',
            's_l_pct': '券資比',
        }
        
        print("   📋 籌碼欄位:")
        for code, name in chip_fields.items():
            if code in data.columns:
                val = data[code].iloc[0]
                val_str = f"{val:,.0f}" if pd.notna(val) and isinstance(val, (int, float)) else str(val)
                print(f"      ✅ {code} ({name}): {val_str}")
            else:
                print(f"      ❌ {code} ({name}): 缺少")
        
        return True
    
    except Exception as e:
        print(f"   ❌ 錯誤: {e}")
        return False


def test_monthly_sales():
    """測試月營收資料"""
    print("\n📈 [4/5] 測試月營收資料 (TWN/APISALE)...")
    
    try:
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        
        data = tejapi.get(
            'TWN/APISALE',
            coid=TEST_TICKER,
            mdate={'gte': start_date, 'lte': end_date},
            opts={'sort': 'mdate.desc', 'limit': 3},
            paginate=True
        )
        
        if data.empty:
            print("   ❌ 無資料")
            return False
        
        print(f"   ✅ 取得 {len(data)} 筆資料")
        
        # 檢查必要欄位
        sales_fields = {
            'd0002': '月營收 (千元)',
            'd0003': '營收YoY%',
            'd0006': '累計營收YoY%',
        }
        
        print("   📋 月營收欄位:")
        for code, name in sales_fields.items():
            if code in data.columns:
                val = data[code].iloc[0]
                val_str = f"{val:,.0f}" if pd.notna(val) and isinstance(val, (int, float)) else str(val)
                print(f"      ✅ {code} ({name}): {val_str}")
            else:
                print(f"      ❌ {code} ({name}): 缺少")
        
        return True
    
    except Exception as e:
        print(f"   ❌ 錯誤: {e}")
        return False


def test_basic_info():
    """測試基本資料"""
    print("\n ℹ️  [5/5] 測試基本資料 (TWN/APISTOCK)...")
    
    try:
        data = tejapi.get(
            TEJ_CONFIG['TABLE_BASIC'],
            coid=TEST_TICKER,
            paginate=True
        )
        
        if data.empty:
            print("   ❌ 無資料")
            return False
        
        print(f"   ✅ 取得 {len(data)} 筆資料")
        
        # 檢查必要欄位
        info_fields = {
            'stk_name': '股票名稱',
            'main_ind_c': '主產業',
            'sub_ind_c': '次產業',
            'list_date': '上市日期',
        }
        
        print("   📋 基本資料欄位:")
        for code, name in info_fields.items():
            if code in data.columns:
                val = data[code].iloc[0]
                print(f"      ✅ {code} ({name}): {val}")
            else:
                print(f"      ❌ {code} ({name}): 缺少")
        
        return True
    
    except Exception as e:
        print(f"   ❌ 錯誤: {e}")
        return False


def main():
    results = {
        '股價 (APIPRCD)': test_price_data(),
        '財報 (AINVFINB)': test_financials_data(),
        '籌碼 (APISHRACT)': test_chip_data(),
        '月營收 (APISALE)': test_monthly_sales(),
        '基本資料 (APISTOCK)': test_basic_info(),
    }
    
    print("\n" + "="*70)
    print("📋 測試結果摘要")
    print("="*70)
    
    all_pass = True
    for name, passed in results.items():
        icon = "✅" if passed else "❌"
        print(f"   {icon} {name}")
        if not passed:
            all_pass = False
    
    print("-"*70)
    if all_pass:
        print("🎉 所有測試通過！可以執行完整下載。")
        print("\n執行完整下載:")
        print("   python data_downloader.py")
    else:
        print("⚠️  部分測試失敗，請檢查 API 權限或網路連線。")
    
    print("="*70)


if __name__ == '__main__':
    main()

