#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=====================================================
🚀 Investment AI - Full Analysis Pipeline
=====================================================
一鍵執行完整的投資分析流程。

【工作流程】

Step 0: 資料下載 (data_downloader.py)
        ↓ 從 TEJ API 抓取股價與財報 (唯一消耗 API 額度的步驟)
        
Step 1: 動能篩選 (pool_analyser.py)
        ↓ 找出 GPM/OPM 斜率正在改善的「結構性擴張」股票
        
Step 2: 寶石偵測 (shadow_gem_detector.py)
        ↓ 找出尚未入選但具潛力的「隱藏寶石」
        
Step 3: 體質檢查 (health_checker.py)
        ↓ 檢查現金流含金量、存貨風險、DSO 趨勢
        
Step 4: 估值分析 (valuation_analyzer.py)
        ↓ PE Band 歷史百分位 + 相對強度 (RS) 分析
        
Step 5: 財務取證 (forensic_analyzer.py)
        ↓ Sloan Ratio + Piotroski F-Score 風險檢測

【輸出報告】
- structural_change_report.csv      : 結構性擴張股票清單
- hidden_gems_report.csv            : 隱藏寶石清單
- final_health_check_report.csv     : 結構股健康報告
- hidden_gems_health_check_report.csv : 寶石健康報告
- final_valuation_report.csv        : 結構股估值報告
- hidden_gems_valuation_report.csv  : 寶石估值報告
- institutional_forensic_report.csv : 結構股取證報告
- hidden_gems_forensic_report.csv   : 寶石取證報告

【使用方式】
$ python run_full_pipeline.py           # 完整流程 (含下載)
$ python run_full_pipeline.py --skip-download  # 跳過下載，直接分析
"""

import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path

# 設定腳本路徑
SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR.parent  # StockAnalysis 目錄

# 定義執行順序
PIPELINE_STEPS = [
    {
        "name": "Step 0: 資料下載",
        "script": BASE_DIR / "Data" / "data_downloader.py",
        "description": "從 TEJ API 下載股價與財報資料",
        "emoji": "📡",
        "skip_flag": "--skip-download"
    },
    {
        "name": "Step 1: 動能篩選",
        "script": BASE_DIR / "Analyzers" / "pool_analyser_v2.py",
        "description": "GPM/OPM 斜率分析，找出結構性擴張股",
        "emoji": "📊"
    },
    {
        "name": "Step 2: 寶石偵測",
        "script": BASE_DIR / "Analyzers" / "shadow_gem_detector_v2.py",
        "description": "偵測尚未入選但具潛力的隱藏寶石",
        "emoji": "💎"
    },
    {
        "name": "Step 3: 體質檢查",
        "script": BASE_DIR / "Analyzers" / "health_checker_v2.py",
        "description": "現金流含金量、存貨風險、DSO 趨勢檢查",
        "emoji": "🏥"
    },
    {
        "name": "Step 4: 估值分析",
        "script": BASE_DIR / "Analyzers" / "valuation_analyzer_v2.py",
        "description": "PE Band 歷史百分位 + RS 相對強度分析",
        "emoji": "💰"
    },
    {
        "name": "Step 5: 財務取證",
        "script": BASE_DIR / "Analyzers" / "forensic_analyzer_v2.py",
        "description": "Sloan Ratio + F-Score 財務風險檢測",
        "emoji": "🔍"
    }
]


def print_banner():
    """顯示開場 Banner"""
    print()
    print("=" * 70)
    print("🚀 Investment AI - Full Analysis Pipeline")
    print("=" * 70)
    print(f"⏰ 開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("📋 執行流程:")
    for step in PIPELINE_STEPS:
        print(f"   {step['emoji']} {step['name']}: {step['description']}")
    print()
    print("=" * 70)


def run_step(step: dict, skip_download: bool = False) -> bool:
    """
    執行單一步驟
    
    Returns:
        True if success, False if failed
    """
    # 檢查是否跳過下載步驟
    if skip_download and step.get("skip_flag") == "--skip-download":
        print(f"\n⏩ 跳過 {step['name']} (使用 --skip-download 參數)")
        return True
    
    script_path = step["script"]  # 已經是完整路徑
    
    print()
    print("=" * 70)
    print(f"{step['emoji']} {step['name']}")
    print(f"   {step['description']}")
    print("=" * 70)
    
    if not script_path.exists():
        print(f"❌ 錯誤: 找不到腳本 {script_path}")
        return False
    
    try:
        # 執行腳本 - 使用腳本所在目錄作為工作目錄
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(script_path.parent),
            check=False  # 不自動拋出異常
        )
        
        if result.returncode != 0:
            print(f"⚠️ {step['name']} 完成但有警告 (return code: {result.returncode})")
            # 繼續執行下一步，因為部分錯誤是可接受的（如某些股票無數據）
        
        return True
        
    except Exception as e:
        print(f"❌ {step['name']} 執行失敗: {e}")
        return False


def print_summary():
    """顯示完成摘要"""
    print()
    print("=" * 70)
    print("✅ 全部分析流程執行完成！")
    print("=" * 70)
    print()
    print("📁 產出報告位置: Stock_Pool/")
    print()
    print("📊 主要報告:")
    print("   • structural_change_report.csv   → 結構性擴張股票")
    print("   • hidden_gems_report.csv         → 隱藏寶石")
    print("   • final_valuation_report.csv     → 最終估值 (含 RS)")
    print("   • institutional_forensic_report.csv → 財務取證結果")
    print()
    print("💡 建議閱讀順序:")
    print("   1. institutional_forensic_report.csv → 看哪些是 SSS/S/A 級")
    print("   2. final_valuation_report.csv → 看估值狀態與 RS 趨勢")
    print("   3. hidden_gems_forensic_report.csv → 發掘未被發現的潛力股")
    print()
    print(f"⏰ 完成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


def main():
    """主程式"""
    # 解析參數
    skip_download = "--skip-download" in sys.argv
    
    if skip_download:
        print("🔄 模式: 離線分析 (跳過資料下載)")
    else:
        print("🌐 模式: 完整流程 (含資料下載)")
    
    print_banner()
    
    # 依序執行每個步驟
    success_count = 0
    for step in PIPELINE_STEPS:
        if run_step(step, skip_download):
            success_count += 1
        else:
            print(f"\n⚠️ {step['name']} 失敗，但繼續執行後續步驟...")
    
    print_summary()
    
    if success_count == len(PIPELINE_STEPS):
        print("🎉 所有步驟成功完成！")
    else:
        print(f"⚠️ {len(PIPELINE_STEPS) - success_count} 個步驟有問題，請檢查上方日誌")


if __name__ == "__main__":
    main()

