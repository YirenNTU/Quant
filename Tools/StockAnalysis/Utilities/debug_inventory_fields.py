#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEJ 存貨欄位 Debug Script
=========================

目的：找出 TEJ AINVFINB 資料表中「存貨 (Inventory)」的正確欄位代碼

使用方式：
    python debug_inventory_fields.py

注意：使用 tej_tool.py 中的 API Key 設定
"""

import os
import sys
from pathlib import Path

# 確保可以 import tej_tool - 添加 Data 資料夾到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent / "Data"))

try:
    import tejapi
    from tej_tool import TEJ_API_KEY, TEJ_CONFIG
except ImportError as e:
    print(f"❌ Import 錯誤: {e}")
    print("   請確保 tej_tool.py 存在且 tejapi 已安裝")
    sys.exit(1)

import pandas as pd

# 使用 tej_tool.py 中的 API Key
tejapi.ApiConfig.api_key = TEJ_API_KEY
tejapi.ApiConfig.ignoretz = True

print(f"🔑 使用 API Key: {TEJ_API_KEY[:8]}...{TEJ_API_KEY[-4:]}")

# 測試標的
TEST_TICKERS = ['2330', '1216', '2027']  # 台積電、統一、大成鋼


def get_table_info(table_name: str) -> dict:
    """
    取得資料表的欄位資訊
    """
    print(f"\n{'='*70}")
    print(f"📋 查詢資料表結構: {table_name}")
    print('='*70)
    
    try:
        # 方法1: 使用 table_info (如果可用)
        info = tejapi.table_info(table_name)
        return info
    except AttributeError:
        print("   ⚠️ table_info 方法不可用，改用查詢方式取得欄位")
        return None
    except Exception as e:
        print(f"   ⚠️ 取得資料表資訊失敗: {e}")
        return None


def query_sample_data(table_name: str, ticker: str, limit: int = 1) -> pd.DataFrame:
    """
    查詢樣本資料以取得所有欄位
    """
    print(f"\n📊 查詢 {ticker} 的樣本資料 (最近 {limit} 筆)")
    print("-" * 50)
    
    try:
        data = tejapi.get(
            table_name,
            coid=ticker,
            mdate={'gte': '2024-01-01'},  # 近期資料
            paginate=True,
            opts={'sort': 'mdate.desc', 'limit': limit}
        )
        
        if data is None or data.empty:
            print(f"   ❌ {ticker} 無資料")
            return pd.DataFrame()
        
        print(f"   ✅ 取得 {len(data)} 筆資料")
        print(f"   📅 資料日期: {data['mdate'].iloc[0] if 'mdate' in data.columns else 'N/A'}")
        return data
    
    except Exception as e:
        print(f"   ❌ 查詢失敗: {e}")
        return pd.DataFrame()


def find_inventory_fields(df: pd.DataFrame) -> list:
    """
    找出可能是存貨的欄位
    """
    inventory_keywords = [
        'inventory', 'inventories', 'stock', '存貨', '庫存', 
        'merchandise', 'finished goods', 'raw material', 'wip',
        'work in process', '原料', '在製品', '製成品', '商品'
    ]
    
    # 數字代碼可能對應存貨 (2000 系列通常是流動資產)
    inventory_codes = ['2000', '2100', '2110', '2120', '2130', '2140', '2150', '2200']
    
    found_fields = []
    
    for col in df.columns:
        col_lower = col.lower()
        
        # 1. 關鍵字匹配
        for kw in inventory_keywords:
            if kw in col_lower:
                found_fields.append({
                    'column': col,
                    'match_type': f'關鍵字: {kw}',
                    'value': df[col].iloc[0] if len(df) > 0 else None
                })
                break
        
        # 2. 代碼匹配
        for code in inventory_codes:
            if col.startswith(code) or col.endswith(code) or f'a{code}' in col_lower:
                if not any(f['column'] == col for f in found_fields):
                    found_fields.append({
                        'column': col,
                        'match_type': f'代碼: {code}',
                        'value': df[col].iloc[0] if len(df) > 0 else None
                    })
                break
    
    return found_fields


def analyze_all_fields(df: pd.DataFrame, ticker: str):
    """
    分析所有欄位，找出非空值的資產類欄位
    """
    print(f"\n{'='*70}")
    print(f"🔍 分析 {ticker} 所有欄位 (共 {len(df.columns)} 個)")
    print('='*70)
    
    # 1. 列出所有欄位名稱
    print("\n📋 所有欄位列表:")
    print("-" * 50)
    
    cols_sorted = sorted(df.columns.tolist())
    for i, col in enumerate(cols_sorted, 1):
        val = df[col].iloc[0] if len(df) > 0 else None
        val_str = f"{val:,.0f}" if pd.notna(val) and isinstance(val, (int, float)) else str(val)
        print(f"   {i:3d}. {col:30s} = {val_str}")
    
    # 2. 找出存貨相關欄位
    print("\n\n📦 存貨相關欄位 (關鍵字/代碼匹配):")
    print("-" * 50)
    
    inventory_fields = find_inventory_fields(df)
    
    if inventory_fields:
        for f in inventory_fields:
            val = f['value']
            val_str = f"{val:,.0f}" if pd.notna(val) and isinstance(val, (int, float)) else str(val)
            print(f"   ✅ {f['column']:30s} = {val_str}")
            print(f"      匹配方式: {f['match_type']}")
    else:
        print("   ❌ 未找到任何匹配欄位")
    
    # 3. 列出所有非空的數值欄位 (可能藏有存貨)
    print("\n\n📊 所有非空數值欄位 (可能包含存貨):")
    print("-" * 50)
    
    non_empty_numeric = []
    for col in df.columns:
        val = df[col].iloc[0] if len(df) > 0 else None
        if pd.notna(val) and isinstance(val, (int, float)) and val != 0:
            non_empty_numeric.append((col, val))
    
    # 按值排序 (大到小)
    non_empty_numeric.sort(key=lambda x: abs(x[1]) if isinstance(x[1], (int, float)) else 0, reverse=True)
    
    for col, val in non_empty_numeric[:50]:  # 只顯示前 50 個
        val_str = f"{val:>20,.0f}" if isinstance(val, (int, float)) else str(val)
        print(f"   {col:30s} = {val_str}")
    
    return inventory_fields


def query_balance_sheet_tables():
    """
    查詢可能包含存貨的資產負債表相關資料表
    """
    print("\n" + "="*70)
    print("🔍 查詢其他可能包含存貨的資料表")
    print("="*70)
    
    # TEJ 常見的資產負債表相關資料表
    tables_to_check = [
        'TWN/AINVFINB',      # 財報資料 - 資產負債表
        'TWN/AFINB',         # 財報資料 - 基本
        'TWN/AFINST',        # 財報資料 - 存貨明細 (可能)
        'TWN/AFINSMT',       # 財報資料 - 管理報表
    ]
    
    for table in tables_to_check:
        print(f"\n📋 嘗試查詢: {table}")
        print("-" * 40)
        
        try:
            data = tejapi.get(
                table,
                coid='2330',
                mdate={'gte': '2024-01-01'},
                paginate=True,
                opts={'sort': 'mdate.desc', 'limit': 1}
            )
            
            if data is not None and not data.empty:
                print(f"   ✅ 資料表存在，共 {len(data.columns)} 個欄位")
                
                # 找存貨欄位
                inv_cols = [c for c in data.columns if any(kw in c.lower() for kw in ['inventory', 'inventories', '存貨', '2100', '2110', '2120'])]
                if inv_cols:
                    print(f"   📦 找到存貨相關欄位: {inv_cols}")
                    for col in inv_cols:
                        val = data[col].iloc[0]
                        print(f"      {col} = {val}")
            else:
                print("   ⚠️ 無資料或資料表不存在")
                
        except Exception as e:
            print(f"   ❌ 查詢失敗: {e}")


def main():
    """
    主程式
    """
    print("="*70)
    print("🔍 TEJ 存貨欄位 Debug Script")
    print("="*70)
    print(f"📅 執行時間: {pd.Timestamp.now()}")
    print(f"🔑 API Key: {TEJ_API_KEY[:8]}...{TEJ_API_KEY[-4:]}")
    
    # 1. 查詢 AINVFINB 資料表結構
    table_info = get_table_info('TWN/AINVFINB')
    
    if table_info:
        print("\n📋 資料表欄位清單:")
        print("-" * 50)
        # 根據 table_info 的格式輸出
        if hasattr(table_info, 'columns'):
            for col in table_info.columns:
                print(f"   {col}")
        elif isinstance(table_info, dict):
            for key, value in table_info.items():
                print(f"   {key}: {value}")
        else:
            print(f"   {table_info}")
    
    # 2. 對每個測試標的查詢並分析
    for ticker in TEST_TICKERS:
        print(f"\n\n{'#'*70}")
        print(f"# 測試標的: {ticker}")
        print('#'*70)
        
        df = query_sample_data('TWN/AINVFINB', ticker, limit=1)
        
        if not df.empty:
            analyze_all_fields(df, ticker)
    
    # 3. 查詢其他可能的資料表
    query_balance_sheet_tables()
    
    print("\n\n" + "="*70)
    print("✅ Debug 完成")
    print("="*70)
    print("\n📝 建議:")
    print("   1. 檢查上方輸出中「存貨相關欄位」區塊")
    print("   2. 若 AINVFINB 無存貨，可能需要使用其他資料表")
    print("   3. 注意 TEJ E-SHOP 初入江湖版可能不包含某些欄位")


if __name__ == '__main__':
    main()

