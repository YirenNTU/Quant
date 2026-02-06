#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
🔍 Field Database Validator - 欄位資料庫驗證器
================================================================================

驗證項目:
1. 完整性檢查 - 所有欄位檔案是否存在
2. 資料品質檢查 - 缺值比例、異常值
3. 數值正確性 - 與原始資料比對
4. 一致性檢查 - 跨欄位邏輯一致性
5. 時間範圍檢查 - 日期連續性

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
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# 路徑設定
SCRIPT_DIR = Path(__file__).parent
PLATFORM_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = PLATFORM_DIR.parent

# 資料庫路徑
FIELD_DB_DIR = PLATFORM_DIR / "FieldDB"
SOURCE_DB_DIR = PROJECT_ROOT / "Stock_Pool" / "Database"


class FieldDatabaseValidator:
    """欄位資料庫驗證器"""
    
    def __init__(self):
        self.field_db_path = FIELD_DB_DIR
        self.source_db_path = SOURCE_DB_DIR
        self.results = {
            "completeness": {},
            "quality": {},
            "accuracy": {},
            "consistency": {},
            "summary": {}
        }
        
        # 載入 metadata
        self.field_map = self._load_json("_meta/field_map.json")
        self.tickers_info = self._load_json("_meta/tickers.json")
    
    def _load_json(self, rel_path: str) -> dict:
        """載入 JSON"""
        path = self.field_db_path / rel_path
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _load_field(self, field: str) -> pd.DataFrame:
        """載入欄位資料"""
        info = self.field_map.get(field, {})
        category = info.get("category", "price")
        path = self.field_db_path / category / f"{field}.parquet"
        if path.exists():
            return pd.read_parquet(path)
        return pd.DataFrame()
    
    def _load_source(self, ticker: str) -> dict:
        """載入原始資料"""
        # 找最新的檔案
        pattern = f"{ticker}_*.json"
        files = list(self.source_db_path.glob(pattern))
        if not files:
            return {}
        
        latest = sorted(files)[-1]
        with open(latest, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # ═══════════════════════════════════════════════════════════════════════
    # 1. 完整性檢查
    # ═══════════════════════════════════════════════════════════════════════
    
    def check_completeness(self) -> dict:
        """檢查資料完整性"""
        print("\n" + "=" * 70)
        print("1️⃣  完整性檢查 (Completeness)")
        print("=" * 70)
        
        results = {
            "fields_expected": len(self.field_map),
            "fields_found": 0,
            "fields_missing": [],
            "tickers_expected": len(self.tickers_info.get("tickers", [])),
            "by_category": {}
        }
        
        # 檢查每個欄位檔案
        for field, info in self.field_map.items():
            category = info["category"]
            path = self.field_db_path / category / f"{field}.parquet"
            
            if category not in results["by_category"]:
                results["by_category"][category] = {
                    "expected": 0,
                    "found": 0,
                    "missing": []
                }
            
            results["by_category"][category]["expected"] += 1
            
            if path.exists():
                results["fields_found"] += 1
                results["by_category"][category]["found"] += 1
            else:
                results["fields_missing"].append(field)
                results["by_category"][category]["missing"].append(field)
        
        # 輸出結果
        print(f"\n   📊 欄位檔案:")
        print(f"      預期: {results['fields_expected']} 個")
        print(f"      找到: {results['fields_found']} 個")
        
        if results["fields_missing"]:
            print(f"      ❌ 缺少: {results['fields_missing']}")
        else:
            print(f"      ✅ 全部存在")
        
        print(f"\n   📁 分類統計:")
        for cat, stats in results["by_category"].items():
            status = "✅" if stats["found"] == stats["expected"] else "⚠️"
            print(f"      {status} {cat}: {stats['found']}/{stats['expected']}")
        
        print(f"\n   👥 股票數: {results['tickers_expected']} 家")
        
        self.results["completeness"] = results
        return results
    
    # ═══════════════════════════════════════════════════════════════════════
    # 2. 資料品質檢查
    # ═══════════════════════════════════════════════════════════════════════
    
    def check_quality(self) -> dict:
        """檢查資料品質"""
        print("\n" + "=" * 70)
        print("2️⃣  資料品質檢查 (Data Quality)")
        print("=" * 70)
        
        results = {
            "by_field": {},
            "summary": {
                "total_fields": 0,
                "high_quality": 0,  # 缺值 < 10%
                "medium_quality": 0,  # 缺值 10-30%
                "low_quality": 0,  # 缺值 > 30%
            }
        }
        
        # 抽樣檢查關鍵欄位
        key_fields = [
            "close", "volume", "pe", "pb", "div_yield",
            "tej_gpm", "tej_opm", "net_income",
            "ocf", "total_assets",
            "qfii_net", "fund_net",
            "monthly_rev_yoy"
        ]
        
        print(f"\n   📊 欄位品質分析:")
        print(f"   {'欄位':<20} {'Shape':<15} {'缺值%':<10} {'零值%':<10} {'狀態':<10}")
        print("   " + "-" * 65)
        
        for field in key_fields:
            if field not in self.field_map:
                continue
            
            try:
                df = self._load_field(field)
                
                total_cells = df.size
                null_count = df.isnull().sum().sum()
                zero_count = (df == 0).sum().sum()
                
                null_pct = null_count / total_cells * 100 if total_cells > 0 else 0
                zero_pct = zero_count / total_cells * 100 if total_cells > 0 else 0
                
                # 判斷品質
                if null_pct < 10:
                    status = "✅ 優"
                    results["summary"]["high_quality"] += 1
                elif null_pct < 30:
                    status = "⚠️ 中"
                    results["summary"]["medium_quality"] += 1
                else:
                    status = "❌ 差"
                    results["summary"]["low_quality"] += 1
                
                results["summary"]["total_fields"] += 1
                
                results["by_field"][field] = {
                    "shape": df.shape,
                    "null_pct": round(null_pct, 2),
                    "zero_pct": round(zero_pct, 2),
                    "status": status
                }
                
                shape_str = f"{df.shape[0]}×{df.shape[1]}"
                print(f"   {field:<20} {shape_str:<15} {null_pct:>6.1f}%    {zero_pct:>6.1f}%    {status}")
                
            except Exception as e:
                print(f"   {field:<20} ❌ 載入失敗: {e}")
        
        # 品質摘要
        s = results["summary"]
        print(f"\n   📈 品質摘要:")
        print(f"      優 (缺值<10%): {s['high_quality']}/{s['total_fields']}")
        print(f"      中 (缺值10-30%): {s['medium_quality']}/{s['total_fields']}")
        print(f"      差 (缺值>30%): {s['low_quality']}/{s['total_fields']}")
        
        self.results["quality"] = results
        return results
    
    # ═══════════════════════════════════════════════════════════════════════
    # 3. 數值正確性檢查 (與原始資料比對)
    # ═══════════════════════════════════════════════════════════════════════
    
    def check_accuracy(self, sample_tickers: List[str] = None) -> dict:
        """檢查數值正確性"""
        print("\n" + "=" * 70)
        print("3️⃣  數值正確性檢查 (Accuracy vs Source)")
        print("=" * 70)
        
        # 抽樣股票
        if sample_tickers is None:
            all_tickers = self.tickers_info.get("tickers", [])
            # 抽樣 5 檔: 大型股 + 中型股 + 小型股
            sample_tickers = ["2330", "2317", "2882", "1101", "2308"]
            sample_tickers = [t for t in sample_tickers if t in all_tickers][:5]
        
        results = {
            "sample_tickers": sample_tickers,
            "comparisons": {},
            "mismatches": []
        }
        
        print(f"\n   🔍 抽樣比對: {sample_tickers}")
        
        # 比對欄位定義
        field_source_map = {
            "close": ("price", "Close"),
            "open": ("price", "Open"),
            "volume": ("price", "Volume"),
            "pe": ("price", "per"),
            "pb": ("price", "pbr"),
            "tej_gpm": ("financials", "TEJ_GPM"),
            "tej_opm": ("financials", "TEJ_OPM"),
            "qfii_net": ("chip", "qfii_ex"),
            "monthly_rev_yoy": ("monthly_sales", "d0003"),
        }
        
        for ticker in sample_tickers:
            print(f"\n   📊 {ticker}:")
            source_data = self._load_source(ticker)
            
            if not source_data:
                print(f"      ⚠️ 找不到原始資料")
                continue
            
            comparisons = {}
            
            for field, (source_type, source_col) in field_source_map.items():
                try:
                    # 載入 FieldDB 資料
                    field_df = self._load_field(field)
                    if ticker not in field_df.columns:
                        continue
                    
                    field_values = field_df[ticker].dropna()
                    if len(field_values) == 0:
                        continue
                    
                    # 載入原始資料
                    source_raw = source_data.get(source_type)
                    if not source_raw:
                        continue
                    
                    source_df = pd.read_json(StringIO(source_raw), orient='split')
                    
                    # 處理不同資料結構
                    if source_type in ["financials", "balance_sheet", "cashflow"]:
                        # 財報資料是轉置的
                        source_df = source_df.T
                    
                    if source_col not in source_df.columns and source_col in source_df.index:
                        source_series = source_df.loc[source_col]
                    elif source_col in source_df.columns:
                        source_series = source_df[source_col]
                    else:
                        continue
                    
                    source_series = pd.to_numeric(source_series, errors='coerce').dropna()
                    
                    # 比較最新值
                    field_latest = field_values.iloc[-1]
                    source_latest = source_series.iloc[-1] if len(source_series) > 0 else None
                    
                    if source_latest is not None:
                        # 數值比對 (允許小數點誤差)
                        if pd.notna(field_latest) and pd.notna(source_latest):
                            diff = abs(field_latest - source_latest)
                            rel_diff = diff / abs(source_latest) * 100 if source_latest != 0 else 0
                            
                            match = rel_diff < 1  # 1% 誤差以內
                            
                            comparisons[field] = {
                                "field_value": round(field_latest, 4),
                                "source_value": round(source_latest, 4),
                                "diff_pct": round(rel_diff, 2),
                                "match": match
                            }
                            
                            status = "✅" if match else "❌"
                            print(f"      {status} {field:<15}: FieldDB={field_latest:>12.2f} | Source={source_latest:>12.2f} | Diff={rel_diff:.2f}%")
                            
                            if not match:
                                results["mismatches"].append({
                                    "ticker": ticker,
                                    "field": field,
                                    "field_value": field_latest,
                                    "source_value": source_latest,
                                    "diff_pct": rel_diff
                                })
                
                except Exception as e:
                    pass
            
            results["comparisons"][ticker] = comparisons
        
        # 摘要
        total_comparisons = sum(len(c) for c in results["comparisons"].values())
        mismatch_count = len(results["mismatches"])
        
        print(f"\n   📈 比對摘要:")
        print(f"      總比對數: {total_comparisons}")
        print(f"      不符數: {mismatch_count}")
        print(f"      準確率: {(total_comparisons - mismatch_count) / total_comparisons * 100:.1f}%" if total_comparisons > 0 else "      準確率: N/A")
        
        self.results["accuracy"] = results
        return results
    
    # ═══════════════════════════════════════════════════════════════════════
    # 4. 一致性檢查
    # ═══════════════════════════════════════════════════════════════════════
    
    def check_consistency(self) -> dict:
        """檢查資料一致性"""
        print("\n" + "=" * 70)
        print("4️⃣  一致性檢查 (Consistency)")
        print("=" * 70)
        
        results = {
            "checks": [],
            "issues": []
        }
        
        # 檢查 1: High >= Low
        print("\n   🔍 檢查 1: High >= Low")
        try:
            high = self._load_field("high")
            low = self._load_field("low")
            
            violations = (high < low).sum().sum()
            total = high.size
            
            if violations == 0:
                print(f"      ✅ 通過 (0 violations)")
            else:
                print(f"      ❌ 發現 {violations} 筆 High < Low")
                results["issues"].append(f"High < Low: {violations} cases")
            
            results["checks"].append({
                "name": "High >= Low",
                "passed": violations == 0,
                "violations": int(violations)
            })
        except Exception as e:
            print(f"      ⚠️ 無法檢查: {e}")
        
        # 檢查 2: Close 在 High 和 Low 之間
        print("\n   🔍 檢查 2: Low <= Close <= High")
        try:
            close = self._load_field("close")
            high = self._load_field("high")
            low = self._load_field("low")
            
            violations = ((close > high) | (close < low)).sum().sum()
            
            if violations == 0:
                print(f"      ✅ 通過 (0 violations)")
            else:
                print(f"      ⚠️ 發現 {violations} 筆 Close 超出範圍")
                results["issues"].append(f"Close out of range: {violations} cases")
            
            results["checks"].append({
                "name": "Low <= Close <= High",
                "passed": violations == 0,
                "violations": int(violations)
            })
        except Exception as e:
            print(f"      ⚠️ 無法檢查: {e}")
        
        # 檢查 3: Volume >= 0
        print("\n   🔍 檢查 3: Volume >= 0")
        try:
            volume = self._load_field("volume")
            
            violations = (volume < 0).sum().sum()
            
            if violations == 0:
                print(f"      ✅ 通過 (0 violations)")
            else:
                print(f"      ❌ 發現 {violations} 筆負成交量")
                results["issues"].append(f"Negative volume: {violations} cases")
            
            results["checks"].append({
                "name": "Volume >= 0",
                "passed": violations == 0,
                "violations": int(violations)
            })
        except Exception as e:
            print(f"      ⚠️ 無法檢查: {e}")
        
        # 檢查 4: PE, PB > 0 (排除負值公司)
        print("\n   🔍 檢查 4: PE, PB 合理範圍 (0 < x < 1000)")
        try:
            pe = self._load_field("pe")
            pb = self._load_field("pb")
            
            pe_extreme = ((pe > 1000) | (pe < 0)).sum().sum()
            pb_extreme = ((pb > 100) | (pb < 0)).sum().sum()
            
            if pe_extreme == 0 and pb_extreme == 0:
                print(f"      ✅ 通過")
            else:
                if pe_extreme > 0:
                    print(f"      ⚠️ PE 極端值: {pe_extreme} 筆")
                if pb_extreme > 0:
                    print(f"      ⚠️ PB 極端值: {pb_extreme} 筆")
            
            results["checks"].append({
                "name": "PE/PB reasonable range",
                "passed": pe_extreme == 0 and pb_extreme == 0,
                "pe_extreme": int(pe_extreme),
                "pb_extreme": int(pb_extreme)
            })
        except Exception as e:
            print(f"      ⚠️ 無法檢查: {e}")
        
        # 檢查 5: 毛利率 GPM 合理範圍 (0-100%)
        print("\n   🔍 檢查 5: 毛利率 GPM 合理範圍 (0-100%)")
        try:
            gpm = self._load_field("tej_gpm")
            
            violations = ((gpm > 100) | (gpm < -50)).sum().sum()
            
            if violations == 0:
                print(f"      ✅ 通過")
            else:
                print(f"      ⚠️ GPM 極端值: {violations} 筆")
            
            results["checks"].append({
                "name": "GPM reasonable range",
                "passed": violations == 0,
                "violations": int(violations)
            })
        except Exception as e:
            print(f"      ⚠️ 無法檢查: {e}")
        
        # 摘要
        passed = sum(1 for c in results["checks"] if c["passed"])
        total = len(results["checks"])
        
        print(f"\n   📈 一致性摘要:")
        print(f"      通過: {passed}/{total}")
        
        self.results["consistency"] = results
        return results
    
    # ═══════════════════════════════════════════════════════════════════════
    # 5. 時間範圍檢查
    # ═══════════════════════════════════════════════════════════════════════
    
    def check_date_ranges(self) -> dict:
        """檢查時間範圍"""
        print("\n" + "=" * 70)
        print("5️⃣  時間範圍檢查 (Date Ranges)")
        print("=" * 70)
        
        results = {"by_category": {}}
        
        categories = ["price", "financials", "chip", "monthly_sales"]
        sample_fields = {
            "price": "close",
            "financials": "tej_gpm",
            "chip": "qfii_net",
            "monthly_sales": "monthly_rev_yoy"
        }
        
        print(f"\n   {'類別':<15} {'欄位':<20} {'起始日期':<12} {'結束日期':<12} {'資料點數':<10}")
        print("   " + "-" * 70)
        
        for cat, field in sample_fields.items():
            try:
                df = self._load_field(field)
                
                start_date = str(df.index.min())[:10]
                end_date = str(df.index.max())[:10]
                rows = len(df)
                
                results["by_category"][cat] = {
                    "field": field,
                    "start_date": start_date,
                    "end_date": end_date,
                    "rows": rows
                }
                
                print(f"   {cat:<15} {field:<20} {start_date:<12} {end_date:<12} {rows:<10}")
                
            except Exception as e:
                print(f"   {cat:<15} ⚠️ 無法檢查: {e}")
        
        self.results["date_ranges"] = results
        return results
    
    # ═══════════════════════════════════════════════════════════════════════
    # 6. 綜合報告
    # ═══════════════════════════════════════════════════════════════════════
    
    def run_full_validation(self) -> dict:
        """執行完整驗證"""
        print("\n" + "🔍" * 35)
        print("   Field Database Validator - 完整驗證報告")
        print("🔍" * 35)
        print(f"\n   時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   資料庫: {self.field_db_path}")
        
        # 執行所有檢查
        self.check_completeness()
        self.check_quality()
        self.check_accuracy()
        self.check_consistency()
        self.check_date_ranges()
        
        # 綜合評分
        self._print_summary()
        
        return self.results
    
    def _print_summary(self):
        """印出綜合摘要"""
        print("\n" + "=" * 70)
        print("📊 綜合驗證結果")
        print("=" * 70)
        
        # 計算整體評分
        scores = []
        
        # 完整性得分
        comp = self.results.get("completeness", {})
        if comp.get("fields_expected", 0) > 0:
            comp_score = comp.get("fields_found", 0) / comp.get("fields_expected", 1) * 100
            scores.append(("完整性", comp_score))
        
        # 品質得分
        qual = self.results.get("quality", {}).get("summary", {})
        if qual.get("total_fields", 0) > 0:
            qual_score = qual.get("high_quality", 0) / qual.get("total_fields", 1) * 100
            scores.append(("資料品質", qual_score))
        
        # 準確性得分
        acc = self.results.get("accuracy", {})
        total_comp = sum(len(c) for c in acc.get("comparisons", {}).values())
        if total_comp > 0:
            acc_score = (total_comp - len(acc.get("mismatches", []))) / total_comp * 100
            scores.append(("準確性", acc_score))
        
        # 一致性得分
        cons = self.results.get("consistency", {})
        checks = cons.get("checks", [])
        if checks:
            cons_score = sum(1 for c in checks if c["passed"]) / len(checks) * 100
            scores.append(("一致性", cons_score))
        
        # 輸出
        print("\n   各項評分:")
        total_score = 0
        for name, score in scores:
            status = "✅" if score >= 90 else "⚠️" if score >= 70 else "❌"
            print(f"      {status} {name}: {score:.1f}%")
            total_score += score
        
        avg_score = total_score / len(scores) if scores else 0
        
        print(f"\n   ─────────────────────────")
        overall_status = "✅ 通過" if avg_score >= 90 else "⚠️ 需注意" if avg_score >= 70 else "❌ 需修復"
        print(f"   🏆 綜合評分: {avg_score:.1f}% ({overall_status})")
        
        # 建議
        print("\n   💡 建議:")
        if avg_score >= 95:
            print("      資料庫狀態極佳，可以放心使用！")
        elif avg_score >= 90:
            print("      資料庫狀態良好，少數缺值屬正常現象。")
        elif avg_score >= 80:
            print("      部分欄位存在缺值，建議了解原因。")
        else:
            print("      建議檢查資料來源並重新建構資料庫。")


def main():
    """主程式"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Field Database Validator")
    parser.add_argument('--quick', action='store_true', help='快速驗證 (跳過準確性比對)')
    parser.add_argument('--tickers', type=str, help='指定驗證股票 (逗號分隔)')
    
    args = parser.parse_args()
    
    validator = FieldDatabaseValidator()
    
    if args.quick:
        # 快速驗證
        validator.check_completeness()
        validator.check_quality()
        validator.check_consistency()
    else:
        # 完整驗證
        if args.tickers:
            sample_tickers = args.tickers.split(',')
            validator.check_completeness()
            validator.check_quality()
            validator.check_accuracy(sample_tickers)
            validator.check_consistency()
            validator.check_date_ranges()
            validator._print_summary()
        else:
            validator.run_full_validation()


if __name__ == "__main__":
    main()
