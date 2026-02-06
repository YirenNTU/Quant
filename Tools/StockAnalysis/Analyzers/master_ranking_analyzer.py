#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Master Ranking Analyzer v2.0 - 綜合排名分析器（終極版）
=========================================================
整合 Stock_Pool 所有數據源，運用六大因子框架進行量化評分

【因子權重配置】
┌──────────────────┬──────────┬──────────────────────────────────┐
│ 因子             │ 權重     │ 核心邏輯                          │
├──────────────────┼──────────┼──────────────────────────────────┤
│ 動能 Momentum    │ 20%      │ 12-1月動能、RS相對強度、趨勢狀態 │
│ 品質 Quality     │ 25%      │ Sloan、F-Score、CCR、健康評級     │
│ 結構 Structural  │ 18%      │ GPM/OPM拐點、營運槓桿、營收加速   │
│ 估值 Valuation   │ 17%      │ PE/PB/PSR百分位、FCF殖利率        │
│ 籌碼 Chip        │ 12%      │ 外資/投信、融資融券、籌碼趨勢     │
│ 策略 Strategy    │ 8%       │ Alpha/Early Bird/Contrarian/Gem  │
└──────────────────┴──────────┴──────────────────────────────────┘

Author: Investment AI System
Version: 2.0 (Final)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import json
import warnings
import argparse
warnings.filterwarnings('ignore')


class MasterRankingAnalyzer:
    """
    綜合排名分析器 v2.0
    
    整合所有 Stock_Pool 數據源，運用機構級量化框架進行評分排名
    """
    
    # ═══════════════════════════════════════════════════════════════
    # 【權重配置】- 可依市場環境調整
    # ═══════════════════════════════════════════════════════════════
    
    # 追漲型策略 (適合牛市初期)
    WEIGHTS_MOMENTUM_CHASING = {
        'momentum': 0.20,      # 動能因子 - 追漲趨勢
        'quality': 0.25,       # 財務品質 - 核心防禦
        'structural': 0.18,    # 結構變化 - 盈利拐點
        'valuation': 0.17,     # 估值因子 - 安全邊際
        'chip': 0.12,          # 籌碼因子 - 資金動向
        'strategy': 0.08,      # 策略加成 - 信號確認
    }
    
    # 爆發前佈局策略 (適合找尋潛力股) ⭐ 新增
    WEIGHTS_PRE_BREAKOUT = {
        'momentum': 0.08,      # 降低 - 避免追高已漲股票
        'quality': 0.18,       # 維持 - 基本面品質
        'structural': 0.25,    # 提高 - 拐點信號最重要 (盈利改善=未來動能)
        'valuation': 0.22,     # 提高 - 低估是安全邊際
        'chip': 0.20,          # 提高 - 籌碼佈局是關鍵信號
        'strategy': 0.07,      # 略降
    }
    
    # 預設使用：爆發前佈局策略
    WEIGHTS = WEIGHTS_PRE_BREAKOUT
    
    # ═══════════════════════════════════════════════════════════════
    # 【分數映射表】
    # ═══════════════════════════════════════════════════════════════
    
    # 健康評級分數
    HEALTH_RATING_SCORES = {
        '🏆 S級：優質生': 100,
        '⭐ A級：質優生': 85,
        '✅ B級：正常': 70,
        '⚠️ C級：警示': 45,
        '⚠️ C級：警示 (Sloan+CCR雙殺)': 35,
        '🛑 D級：高風險': 25,
        '🛑 D級：高風險 (財務虛胖)': 20,
        '🚫 F級：拒絕往來 (財報警示)': 0,
    }
    
    # 結構變化評分
    STRUCTURAL_TAG_SCORES = {
        '🏆 SSS級：雙拐點確認': 100,
        '🔥 S級：結構性拐點': 85,
        '⭐ A級：持續性擴張': 75,
        '⭐ A級：轉型初期': 68,
        '✅ B級：趨勢改善': 55,
        '➡️ C級：觀望': 40,
    }
    
    # 估值決策評分
    DECISION_SCORES = {
        '🔥 Strong Buy': 100,
        '📈 Accumulate': 82,
        '✅ Hold': 60,
        '➡️ Hold': 55,
        '⚠️ Hold (Caution)': 45,
        '📉 Trim': 25,
        '🛑 Sell': 10,
    }
    
    # Forensic 評級
    FORENSIC_VERDICT_SCORES = {
        '🏆 AAA：財務透明優質': 100,
        '⭐ AA：財務健康': 85,
        '✅ A：財務正常': 70,
        '⚠️ B：需留意': 50,
        '🛑 C：高風險': 25,
    }
    
    # Gem 類型分數
    GEM_TYPE_SCORES = {
        '💎💎💎 SSS級隱藏寶石': 100,
        '💎💎 S級隱藏寶石': 80,
        '💎 A級隱藏寶石': 60,
    }
    
    # ═══════════════════════════════════════════════════════════════
    # 【初始化】
    # ═══════════════════════════════════════════════════════════════
    
    def __init__(self, stock_pool_path: str = None):
        """
        初始化分析器
        
        Args:
            stock_pool_path: Stock_Pool 資料夾路徑，None 則自動偵測
        """
        if stock_pool_path is None:
            current_file = Path(__file__).resolve()
            self.stock_pool_path = current_file.parent.parent.parent.parent / "Stock_Pool"
        else:
            self.stock_pool_path = Path(stock_pool_path)
        
        self.data = {}                  # 所有數據源
        self.stock_names = {}           # 股票名稱對照
        self.final_ranking = None       # 最終排名結果
        self.merged_df = None           # 合併後的完整數據
        self.stats = {}                 # 統計資訊
        
    # ═══════════════════════════════════════════════════════════════
    # 【數據載入】
    # ═══════════════════════════════════════════════════════════════
    
    def load_all_data(self) -> dict:
        """載入所有分析報告"""
        print("=" * 70)
        print("📊 載入所有 Stock_Pool 數據源...")
        print("=" * 70)
        
        # 定義所有數據源
        files_to_load = {
            # 主數據源
            'cross_factor': 'cross_factor_full_analysis.csv',
            'factor_v3': 'factor_analysis_v3.csv',
            
            # 健康與品質
            'health': 'final_health_check_report_v2.csv',
            'forensic': 'institutional_forensic_report_v2.csv',
            'hidden_gems_forensic': 'hidden_gems_forensic_report_v2.csv',
            'hidden_gems_health': 'hidden_gems_health_check_report_v2.csv',
            
            # 結構與估值
            'structural': 'structural_change_report_v2.csv',
            'structural_full': 'structural_change_report_v2_full.csv',
            'valuation': 'final_valuation_report_v2.csv',
            'hidden_gems_valuation': 'hidden_gems_valuation_report_v2.csv',
            
            # 隱藏寶石
            'hidden_gems': 'hidden_gems_report_v2.csv',
            
            # 策略信號
            'alpha': 'alpha_stocks.csv',
            'alpha_top20': 'alpha_hunter_top20.csv',
            'early_bird': 'early_bird_stocks.csv',
            'contrarian': 'contrarian_stocks.csv',
        }
        
        loaded_count = 0
        for key, filename in files_to_load.items():
            filepath = self.stock_pool_path / filename
            if filepath.exists():
                try:
                    df = pd.read_csv(filepath)
                    self.data[key] = df
                    print(f"  ✅ {filename:<45} {len(df):>4} 筆")
                    loaded_count += 1
                except Exception as e:
                    print(f"  ⚠️ {filename}: 載入失敗 - {e}")
            else:
                print(f"  ⚠️ {filename}: 檔案不存在")
        
        # 載入股票名稱對照表
        list_path = self.stock_pool_path / "list.json"
        if list_path.exists():
            with open(list_path, 'r', encoding='utf-8') as f:
                self.stock_names = json.load(f)
            print(f"  ✅ {'list.json':<45} {len(self.stock_names):>4} 檔股票")
        
        print(f"\n📁 成功載入 {loaded_count} 個數據源")
        return self.data
    
    # ═══════════════════════════════════════════════════════════════
    # 【數據合併】
    # ═══════════════════════════════════════════════════════════════
    
    def merge_all_data(self) -> pd.DataFrame:
        """合併所有數據源為單一 DataFrame"""
        print("\n🔄 合併所有數據...")
        
        if 'cross_factor' not in self.data:
            raise ValueError("❌ 缺少核心數據: cross_factor_full_analysis.csv")
        
        # 以 cross_factor 為基礎
        df = self.data['cross_factor'].copy()
        initial_cols = set(df.columns)
        
        # 1. 合併完整結構數據（取得更多細節）
        if 'structural_full' in self.data:
            struct_cols = ['Ticker', 'GPM_YoY_Slope', 'GPM_Consecutive', 
                          'OPM_YoY_Slope', 'OPM_Consecutive', 'Non_Op_Ratio', 'Score_Percentile']
            # 過濾出存在的欄位
            available_cols = [c for c in struct_cols if c in self.data['structural_full'].columns]
            if available_cols:
                struct_df = self.data['structural_full'][available_cols].copy()
                df = df.merge(struct_df, on='Ticker', how='left', suffixes=('', '_struct_full'))
        
        # 2. 合併 Factor V3 細節分數
        if 'factor_v3' in self.data:
            factor_cols = ['Ticker', 'FCF_Yield_Status', 'Stability_Status', 
                          'Asset_Growth_Status', 'Drawdown_Status']
            available_cols = [c for c in factor_cols if c in self.data['factor_v3'].columns]
            if available_cols:
                factor_df = self.data['factor_v3'][available_cols].copy()
                df = df.merge(factor_df, on='Ticker', how='left', suffixes=('', '_factor'))
        
        # 3. 合併 Forensic 數據（優先使用機構版）
        if 'forensic' in self.data:
            forensic_cols = ['Ticker', 'Forensic_Score', 'Forensic_Verdict', 
                            'Hollow_Ratio', 'Quality_Warning', 'ROIC', 'Warnings']
            available_cols = [c for c in forensic_cols if c in self.data['forensic'].columns]
            if available_cols:
                forensic_df = self.data['forensic'][available_cols].copy()
                # 重命名以避免衝突
                forensic_df = forensic_df.rename(columns={
                    'Forensic_Score': 'Forensic_Score_Inst',
                    'Forensic_Verdict': 'Forensic_Verdict_Inst'
                })
                df = df.merge(forensic_df, on='Ticker', how='left', suffixes=('', '_forensic'))
        
        # 4. 合併健康數據細節
        if 'health' in self.data:
            health_cols = ['Ticker', 'FCF_Value', 'Inv_Days', 'Inv_Days_Change',
                          'Score_V1', 'Result_Tag_V1']
            available_cols = [c for c in health_cols if c in self.data['health'].columns]
            if available_cols:
                health_df = self.data['health'][available_cols].copy()
                df = df.merge(health_df, on='Ticker', how='left', suffixes=('', '_health'))
        
        # 5. 合併隱藏寶石細節
        if 'hidden_gems' in self.data:
            gem_cols = ['Ticker', 'RD_Momentum', 'In_Elite_List']
            available_cols = [c for c in gem_cols if c in self.data['hidden_gems'].columns]
            if available_cols:
                gem_df = self.data['hidden_gems'][available_cols].copy()
                df = df.merge(gem_df, on='Ticker', how='left', suffixes=('', '_gem'))
        
        # 6. 標記策略信號
        df['Is_Alpha'] = df['Ticker'].isin(self.data.get('alpha', pd.DataFrame()).get('Ticker', []))
        df['Is_EarlyBird'] = df['Ticker'].isin(self.data.get('early_bird', pd.DataFrame()).get('Ticker', []))
        df['Is_Contrarian'] = df['Ticker'].isin(self.data.get('contrarian', pd.DataFrame()).get('Ticker', []))
        df['Is_HiddenGem'] = df['Ticker'].isin(self.data.get('hidden_gems', pd.DataFrame()).get('Ticker', []))
        
        # 7. 取得策略分數
        if 'alpha' in self.data and 'Alpha_Score' in self.data['alpha'].columns:
            alpha_scores = self.data['alpha'][['Ticker', 'Alpha_Score', 'Alpha_Tag']].copy()
            df = df.merge(alpha_scores, on='Ticker', how='left', suffixes=('', '_alpha'))
        
        if 'early_bird' in self.data and 'EarlyBird_Score' in self.data['early_bird'].columns:
            eb_scores = self.data['early_bird'][['Ticker', 'EarlyBird_Score', 'EarlyBird_Tag']].copy()
            df = df.merge(eb_scores, on='Ticker', how='left', suffixes=('', '_eb'))
        
        if 'contrarian' in self.data and 'Contrarian_Score' in self.data['contrarian'].columns:
            con_scores = self.data['contrarian'][['Ticker', 'Contrarian_Score', 'Contrarian_Tag']].copy()
            df = df.merge(con_scores, on='Ticker', how='left', suffixes=('', '_con'))
        
        new_cols = set(df.columns) - initial_cols
        print(f"  ✅ 合併完成: {len(df)} 筆資料，新增 {len(new_cols)} 個欄位")
        
        self.merged_df = df
        return df
    
    # ═══════════════════════════════════════════════════════════════
    # 【因子一：動能因子 Momentum (20%)】
    # ═══════════════════════════════════════════════════════════════
    
    def calc_momentum_score(self, row: pd.Series) -> dict:
        """
        計算動能因子分數 (Physics-Informed Continuous Scoring)
        
        組成:
        - 12-1月動能 (40%): Momentum_12_1
        - 相對強度 (30%): RS_Ratio
        - 近期表現 (20%): Return_12M, Return_1M
        - 動能狀態 (10%): Momentum_Status
        
        Refactored: Uses sigmoid functions for continuous, differentiable scoring.
        Eliminates boundary effects from discrete step functions.
        """
        scores = {'momentum_12_1': 50, 'rs_ratio': 50, 'returns': 50, 'status': 50}
        
        # ─────────────────────────────────────────────────────────────
        # 1. 12-1月動能 (核心動能指標)
        #    Sigmoid parameters calibrated to match original business logic:
        #    - midpoint=25: Neutral zone around +25% (slight positive bias for momentum stocks)
        #    - steepness=0.04: Gradual transition across typical momentum range [-50, 100]
        #    - min_score=5: Floor to avoid zero scores for very negative momentum
        # ─────────────────────────────────────────────────────────────
        mom_12_1 = self._safe_get(row, 'Momentum_12_1', 0)
        scores['momentum_12_1'] = self._sigmoid_score(
            x=mom_12_1,
            midpoint=25,      # +25% is neutral; aligns with old threshold of ~15-30
            steepness=0.04,   # Moderate transition speed
            min_score=5,      # Floor score for extreme losers
            max_score=100
        )
        
        # ─────────────────────────────────────────────────────────────
        # 2. RS 相對強度
        #    Sigmoid centered at RS=1.0 (market-neutral)
        #    - midpoint=1.0: RS=1 means equal to market
        #    - steepness=4.0: Sharper transition since RS typically ranges 0.5-1.5
        # ─────────────────────────────────────────────────────────────
        rs = self._safe_get(row, 'RS_Ratio', 1.0)
        scores['rs_ratio'] = self._sigmoid_score(
            x=rs,
            midpoint=1.0,     # Market-neutral point
            steepness=4.0,    # Faster transition for tight RS range
            min_score=10,
            max_score=100
        )
        
        # ─────────────────────────────────────────────────────────────
        # 3. 報酬表現 (Composite of 12M and 1M returns)
        #    Using log-transform for large returns to prevent outlier dominance
        # ─────────────────────────────────────────────────────────────
        ret_12m = self._safe_get(row, 'Return_12M', 0)
        ret_1m = self._safe_get(row, 'Return_1M', 0)
        
        # 12M 報酬: Log-sigmoid hybrid for wide range (-50% to 200%+)
        # Apply signed log transform to compress extreme winners
        ret_12m_transformed = self._signed_log_transform(ret_12m, base_scale=20)
        score_12m = self._sigmoid_score(
            x=ret_12m_transformed,
            midpoint=0.5,     # Corresponds to ~10% return after transform
            steepness=1.2,
            min_score=10,
            max_score=100
        )
        
        # 1M 短期動能: Narrower range, faster response
        score_1m = self._sigmoid_score(
            x=ret_1m,
            midpoint=3,       # +3% monthly return is neutral
            steepness=0.15,   # Moderate sensitivity
            min_score=20,
            max_score=90      # Capped to reduce short-term noise influence
        )
        
        scores['returns'] = round(score_12m * 0.7 + score_1m * 0.3, 2)
        
        # ─────────────────────────────────────────────────────────────
        # 4. 動能狀態 (Categorical - kept as lookup with smooth interpolation)
        #    Status tags are categorical; map to scores with slight noise tolerance
        # ─────────────────────────────────────────────────────────────
        status = str(row.get('Momentum_Status', ''))
        status_score_map = {
            '極強': 100, '🚀': 100,
            '強勢': 80,
            '正向': 60,
            '中性': 50,
            '弱勢': 35, '⚠️': 35,
            '極弱': 15, '🛑': 15
        }
        # Find best matching status
        matched_score = 50  # Default neutral
        for key, pts in status_score_map.items():
            if key in status:
                matched_score = pts
                break
        scores['status'] = matched_score
        
        # ─────────────────────────────────────────────────────────────
        # 5. 過熱懲罰 (Pre-Breakout Strategy Enhancement)
        #    如果股價已經大幅拉升，給予懲罰，因為爆發力已經釋放
        #    - Return_12M > 80%: 嚴重過熱
        #    - Return_12M > 50%: 中度過熱
        #    - RS_Ratio > 1.5: 已顯著跑贏大盤
        # ─────────────────────────────────────────────────────────────
        overheat_penalty = 0
        
        # 年度報酬過熱檢測
        if ret_12m > 80:
            overheat_penalty += 25  # 漲幅過大，爆發力已釋放
        elif ret_12m > 50:
            overheat_penalty += 15  # 中度過熱
        elif ret_12m > 30:
            overheat_penalty += 5   # 輕微過熱
        
        # RS 過熱檢測
        if rs > 1.8:
            overheat_penalty += 15  # 已大幅跑贏大盤
        elif rs > 1.5:
            overheat_penalty += 8   # 顯著跑贏
        
        # 近期過熱檢測（1個月漲太多 = 短期過熱）
        if ret_1m > 20:
            overheat_penalty += 12  # 短期暴漲
        elif ret_1m > 15:
            overheat_penalty += 6
        
        scores['overheat_penalty'] = overheat_penalty
        
        # 加權彙總
        raw_final = (scores['momentum_12_1'] * 0.40 +
                    scores['rs_ratio'] * 0.30 +
                    scores['returns'] * 0.20 +
                    scores['status'] * 0.10)
        
        # 套用過熱懲罰
        final = max(5, raw_final - overheat_penalty)
        
        return {'score': round(final, 2), 'details': scores, 'overheat_penalty': overheat_penalty}
    
    # ═══════════════════════════════════════════════════════════════
    # 【因子二：品質因子 Quality (25%)】
    # ═══════════════════════════════════════════════════════════════
    
    def calc_quality_score(self, row: pd.Series) -> dict:
        """
        計算財務品質分數 (Physics-Informed Continuous Scoring)
        
        組成:
        - 健康評分 (30%): Health_Score (直接使用原始分數)
        - Forensic 評分 (25%): Forensic_Score (直接使用原始分數)
        - Sloan 比率 (20%): Sloan_Ratio (盈餘品質)
        - F-Score (15%): Piotroski F-Score
        - 現金覆蓋 (10%): CCR_TTM
        
        Refactored: 避免字串標籤轉換的資訊損失，直接使用原始分數 + sigmoid 映射
        """
        scores = {'health': 50, 'forensic': 50, 'sloan': 50, 'fscore': 50, 'ccr': 50}
        
        # ─────────────────────────────────────────────────────────────
        # 1. 健康評分 - 直接使用 Health_Score，避免標籤轉換的資訊損失
        #    如果有 Health_Score 原始分數，優先使用；否則 fallback 到標籤映射
        # ─────────────────────────────────────────────────────────────
        health_score_raw = self._safe_get(row, 'Health_Score', None)
        
        if health_score_raw is not None:
            # 直接使用原始分數，通過 sigmoid 平滑映射到 0-100
            # Health_Score 通常在 30-100 範圍，midpoint=70 對應「正常」
            scores['health'] = self._sigmoid_score(
                x=health_score_raw,
                midpoint=70,      # 70 分為中性點
                steepness=0.08,   # 平緩過渡
                min_score=10,
                max_score=100
            )
        else:
            # Fallback: 從字串標籤映射（兼容舊數據）
            health_rating = str(row.get('Health_Rating', ''))
            for rating, pts in self.HEALTH_RATING_SCORES.items():
                if rating in health_rating or any(key in health_rating for key in rating.split('：')):
                    scores['health'] = pts
                    break
        
        # ─────────────────────────────────────────────────────────────
        # 2. Forensic 評分 - 直接使用原始分數，不再通過 Verdict 標籤
        #    Forensic_Score 通常在 40-100 範圍
        # ─────────────────────────────────────────────────────────────
        forensic_score_raw = self._safe_get(row, 'Forensic_Score', None)
        forensic_score_inst = self._safe_get(row, 'Forensic_Score_Inst', None)
        
        # 優先使用機構版分數
        forensic_final = forensic_score_inst if forensic_score_inst is not None else forensic_score_raw
        
        if forensic_final is not None:
            # 直接使用原始分數，sigmoid 平滑映射
            scores['forensic'] = self._sigmoid_score(
                x=forensic_final,
                midpoint=75,      # 75 分為中性點（A級門檻）
                steepness=0.1,
                min_score=15,
                max_score=100
            )
        # 不再使用 Forensic_Verdict 字串標籤（避免資訊損失）
        
        # ─────────────────────────────────────────────────────────────
        # 3. Sloan Ratio (盈餘品質，越低越好) - Inverted Sigmoid
        #    標準範圍: -0.15 (優秀) ~ +0.20 (危險)
        # ─────────────────────────────────────────────────────────────
        sloan = self._safe_get(row, 'Sloan_Ratio', 0)
        # 注意：Sloan 是反向因子，越低越好，所以使用 -sloan
        scores['sloan'] = self._sigmoid_score(
            x=-sloan,             # 取負號，使低 Sloan 得高分
            midpoint=0,           # Sloan=0 為中性點
            steepness=15,         # 在 ±0.1 範圍內快速過渡
            min_score=5,
            max_score=100
        )
        
        # ─────────────────────────────────────────────────────────────
        # 4. F-Score (Piotroski) - 離散整數 0-9，使用 sigmoid 平滑化
        # ─────────────────────────────────────────────────────────────
        f_score = self._safe_get(row, 'F_Score', None)
        
        if f_score is not None:
            # F-Score 範圍 0-9，midpoint=5.5 為中性點
            scores['fscore'] = self._sigmoid_score(
                x=f_score,
                midpoint=5.5,
                steepness=0.8,    # 每 1 分差異約 15-20 分變化
                min_score=10,
                max_score=100
            )
        else:
            scores['fscore'] = 50  # 無數據時給中性分
        
        # ─────────────────────────────────────────────────────────────
        # 5. 現金覆蓋率 CCR_TTM - Sigmoid 連續化
        #    CCR > 1.0 表示現金流大於淨利（健康）
        # ─────────────────────────────────────────────────────────────
        ccr = self._safe_get(row, 'CCR_TTM', None)
        
        if ccr is not None:
            scores['ccr'] = self._sigmoid_score(
                x=ccr,
                midpoint=1.0,     # CCR=1.0 為中性點
                steepness=3.0,    # 在 0.5-1.5 範圍內平滑過渡
                min_score=15,
                max_score=100
            )
        
        # 加權彙總
        final = (scores['health'] * 0.30 +
                scores['forensic'] * 0.25 +
                scores['sloan'] * 0.20 +
                scores['fscore'] * 0.15 +
                scores['ccr'] * 0.10)
        
        return {'score': round(final, 2), 'details': scores}
    
    # ═══════════════════════════════════════════════════════════════
    # 【因子三：結構因子 Structural (18%)】
    # ═══════════════════════════════════════════════════════════════
    
    def calc_structural_score(self, row: pd.Series) -> dict:
        """
        計算結構性變化分數
        
        組成:
        - 結構評級 (35%): Result_Tag (SSS/S/A/B級)
        - 拐點確認 (25%): GPM_Inflection, OPM_Inflection
        - 營運槓桿 (20%): Operating_Leverage
        - 營收動能 (20%): Rev_YoY, Rev_Acceleration, Rev_New_High
        """
        scores = {'tag': 50, 'inflection': 50, 'leverage': 50, 'revenue': 50}
        
        # 1. 結構評級
        result_tag = str(row.get('Result_Tag', ''))
        for tag, pts in self.STRUCTURAL_TAG_SCORES.items():
            if tag in result_tag or any(key in result_tag for key in ['SSS', 'S級', 'A級', 'B級']):
                if 'SSS' in result_tag:
                    scores['tag'] = 100
                elif 'S級' in result_tag and 'SSS' not in result_tag:
                    scores['tag'] = 85
                elif 'A級' in result_tag:
                    scores['tag'] = 72
                elif 'B級' in result_tag:
                    scores['tag'] = 55
                break
        
        # 2. 拐點確認 (重要信號)
        gpm_inflection = row.get('GPM_Inflection', False)
        opm_inflection = row.get('OPM_Inflection', False)
        
        if gpm_inflection and opm_inflection:
            scores['inflection'] = 100  # 雙拐點確認
        elif opm_inflection:
            scores['inflection'] = 80   # OPM拐點更重要
        elif gpm_inflection:
            scores['inflection'] = 70   # GPM拐點
        else:
            scores['inflection'] = 40
        
        # GPM/OPM 連續改善加成
        gpm_consec = self._safe_get(row, 'GPM_Consecutive', 0)
        opm_consec = self._safe_get(row, 'OPM_Consecutive', 0)
        if gpm_consec >= 2 or opm_consec >= 2:
            scores['inflection'] = min(100, scores['inflection'] + 10)
        
        # 3. 營運槓桿
        ol = self._safe_get(row, 'Operating_Leverage', 1.0)
        if ol > 3.0:
            scores['leverage'] = 100  # 極高營運槓桿
        elif ol > 2.0:
            scores['leverage'] = 85
        elif ol > 1.5:
            scores['leverage'] = 75
        elif ol > 1.0:
            scores['leverage'] = 60
        elif ol > 0.5:
            scores['leverage'] = 45
        elif ol > 0:
            scores['leverage'] = 35
        else:
            scores['leverage'] = 20  # 負向槓桿
        
        # 4. 營收動能
        rev_yoy = self._safe_get(row, 'Rev_YoY', 0)
        rev_acc = self._safe_get(row, 'Rev_Acceleration', 0)
        rev_new_high = row.get('Rev_New_High', False)
        
        # 營收年增率
        if rev_yoy > 30:
            rev_score = 100
        elif rev_yoy > 20:
            rev_score = 85
        elif rev_yoy > 10:
            rev_score = 70
        elif rev_yoy > 5:
            rev_score = 60
        elif rev_yoy > 0:
            rev_score = 50
        elif rev_yoy > -10:
            rev_score = 35
        else:
            rev_score = 20
        
        # 營收加速度加成
        if rev_acc > 0:
            rev_score = min(100, rev_score + 10)
        
        # 營收創高加成
        if rev_new_high:
            rev_score = min(100, rev_score + 10)
        
        scores['revenue'] = rev_score
        
        # 加權彙總
        final = (scores['tag'] * 0.35 +
                scores['inflection'] * 0.25 +
                scores['leverage'] * 0.20 +
                scores['revenue'] * 0.20)
        
        return {'score': round(final, 2), 'details': scores}
    
    # ═══════════════════════════════════════════════════════════════
    # 【因子四：估值因子 Valuation (17%)】
    # ═══════════════════════════════════════════════════════════════
    
    def calc_valuation_score(self, row: pd.Series) -> dict:
        """
        計算估值因子分數 (越便宜越高分)
        
        組成:
        - PE 百分位 (30%): PE_Percentile (歷史相對估值)
        - PB 百分位 (25%): PB_Percentile
        - PSR 百分位 (15%): PSR_Percentile
        - FCF 殖利率 (15%): FCF_Yield
        - 買賣決策 (15%): Decision
        """
        scores = {'pe': 50, 'pb': 50, 'psr': 50, 'fcf': 50, 'decision': 50}
        
        # 1. PE 百分位 (越低越便宜)
        pe_pct = self._safe_get(row, 'PE_Percentile', 50)
        if pe_pct < 10:
            scores['pe'] = 100  # 極度低估
        elif pe_pct < 25:
            scores['pe'] = 85
        elif pe_pct < 40:
            scores['pe'] = 70
        elif pe_pct < 60:
            scores['pe'] = 55
        elif pe_pct < 75:
            scores['pe'] = 40
        elif pe_pct < 90:
            scores['pe'] = 25
        else:
            scores['pe'] = 10  # 極度高估
        
        # 2. PB 百分位
        pb_pct = self._safe_get(row, 'PB_Percentile', 50)
        if pb_pct < 10:
            scores['pb'] = 100
        elif pb_pct < 25:
            scores['pb'] = 85
        elif pb_pct < 40:
            scores['pb'] = 70
        elif pb_pct < 60:
            scores['pb'] = 55
        elif pb_pct < 75:
            scores['pb'] = 40
        else:
            scores['pb'] = 25
        
        # 3. PSR 百分位
        psr_pct = self._safe_get(row, 'PSR_Percentile', 50)
        if psr_pct < 20:
            scores['psr'] = 90
        elif psr_pct < 40:
            scores['psr'] = 70
        elif psr_pct < 60:
            scores['psr'] = 55
        elif psr_pct < 80:
            scores['psr'] = 40
        else:
            scores['psr'] = 25
        
        # 4. FCF 殖利率 (越高越有價值)
        fcf_yield = self._safe_get(row, 'FCF_Yield', 0)
        if fcf_yield > 0.10:
            scores['fcf'] = 100
        elif fcf_yield > 0.07:
            scores['fcf'] = 85
        elif fcf_yield > 0.05:
            scores['fcf'] = 72
        elif fcf_yield > 0.03:
            scores['fcf'] = 60
        elif fcf_yield > 0.01:
            scores['fcf'] = 48
        elif fcf_yield > 0:
            scores['fcf'] = 35
        else:
            scores['fcf'] = 20  # 負FCF
        
        # 5. 買賣決策
        decision = str(row.get('Decision', ''))
        for dec, pts in self.DECISION_SCORES.items():
            if dec in decision:
                scores['decision'] = pts
                break
        
        # 加權彙總
        final = (scores['pe'] * 0.30 +
                scores['pb'] * 0.25 +
                scores['psr'] * 0.15 +
                scores['fcf'] * 0.15 +
                scores['decision'] * 0.15)
        
        return {'score': round(final, 2), 'details': scores}
    
    # ═══════════════════════════════════════════════════════════════
    # 【因子五：籌碼因子 Chip (12%)】
    # ═══════════════════════════════════════════════════════════════
    
    def calc_chip_score(self, row: pd.Series) -> dict:
        """
        計算籌碼因子分數 (Physics-Informed Continuous Scoring)
        
        組成:
        - 外資動向 (35%): QFII_Net_4W
        - 投信動向 (25%): Fund_Net_4W
        - 籌碼趨勢 (25%): Chip_Trend
        - 融資融券 (15%): Margin_Score, Margin_Sentiment
        
        Refactored: Uses signed log-transform + sigmoid to eliminate:
        1. Size Bias: Log compression makes scoring market-cap neutral
        2. Boundary Effects: Sigmoid provides smooth, differentiable transitions
        
        Design Rationale:
        - Raw QFII/Fund values span huge ranges (e.g., -500K to +1M shares)
        - Large-cap stocks naturally have higher absolute flows → unfair advantage
        - Solution: Apply log-transform to compress scale, then sigmoid for scoring
        """
        scores = {'qfii': 50, 'fund': 50, 'trend': 50, 'margin': 50}
        
        # ─────────────────────────────────────────────────────────────
        # 1. 外資動向 (4週淨買超) - Log-Sigmoid Hybrid
        #    
        #    Pipeline: Raw QFII → Signed Log Transform → Sigmoid Score
        #    
        #    Log transform parameters:
        #    - base_scale=5000: Normalizes so typical institutional flows (~5K) → ~1.0
        #    
        #    Sigmoid parameters:
        #    - midpoint=0.5: Slight positive bias (net buying is bullish signal)
        #    - steepness=0.8: Moderate transition for log-transformed range
        # ─────────────────────────────────────────────────────────────
        qfii_raw = self._safe_get(row, 'QFII_Net_4W', 0)
        qfii_transformed = self._signed_log_transform(qfii_raw, base_scale=5000)
        scores['qfii'] = self._sigmoid_score(
            x=qfii_transformed,
            midpoint=0.5,     # Slight bullish bias
            steepness=0.8,    # Moderate transition in log-space
            min_score=10,     # Floor for heavy selling
            max_score=100
        )
        
        # ─────────────────────────────────────────────────────────────
        # 2. 投信動向 (4週淨買超)
        #    Smaller scale than QFII; adjust base_scale accordingly
        # ─────────────────────────────────────────────────────────────
        fund_raw = self._safe_get(row, 'Fund_Net_4W', 0)
        fund_transformed = self._signed_log_transform(fund_raw, base_scale=1000)
        scores['fund'] = self._sigmoid_score(
            x=fund_transformed,
            midpoint=0.3,     # Trust fund buying signal slightly
            steepness=0.9,
            min_score=10,
            max_score=100
        )
        
        # ─────────────────────────────────────────────────────────────
        # 3. 籌碼趨勢 (Categorical with ordinal encoding)
        #    Map categorical trends to ordinal scale, then apply sigmoid
        # ─────────────────────────────────────────────────────────────
        chip_trend = str(row.get('Chip_Trend', ''))
        
        # Ordinal encoding for trend categories
        trend_ordinal = 0  # Neutral baseline
        if '雙多' in chip_trend:
            trend_ordinal = 3       # Best: Both QFII and Fund buying
        elif '外資' in chip_trend and '買超' in chip_trend:
            trend_ordinal = 2       # Good: QFII buying
        elif '投信' in chip_trend and '買超' in chip_trend:
            trend_ordinal = 1.5     # Good: Fund buying
        elif '賣超' in chip_trend and '雙空' not in chip_trend:
            trend_ordinal = -1      # Mild selling
        elif '雙空' in chip_trend:
            trend_ordinal = -2      # Worst: Both selling
        
        # Apply sigmoid to ordinal value
        scores['trend'] = self._sigmoid_score(
            x=trend_ordinal,
            midpoint=0.5,     # Slight positive bias
            steepness=1.5,    # Moderate transition for discrete ordinals
            min_score=15,
            max_score=100
        )
        
        # ─────────────────────────────────────────────────────────────
        # 4. 融資融券情緒 (Composite sigmoid)
        #    Base score + sentiment adjustments via additive sigmoid boosts
        # ─────────────────────────────────────────────────────────────
        margin_score_raw = self._safe_get(row, 'Margin_Score', 50)
        margin_sentiment = str(row.get('Margin_Sentiment', ''))
        
        # Normalize raw margin score to sigmoid (already 0-100, just smooth it)
        base_margin = self._sigmoid_score(
            x=margin_score_raw,
            midpoint=50,      # Center at 50
            steepness=0.08,   # Gentle transition
            min_score=15,
            max_score=95
        )
        
        # Sentiment adjustments as additive offsets
        sentiment_adjustment = 0
        
        # 融資大減 = 籌碼沉澱 (散戶退出 → 正面信號)
        if '融資大減' in margin_sentiment:
            sentiment_adjustment += 12
        
        # 融券大增 = 軋空潛力 (做空增加 → 可能反轉 → 正面)
        if '融券大增' in margin_sentiment:
            sentiment_adjustment += 8
        
        # 融資大增 = 散戶追高 (危險信號 → 負面)
        if '融資大增' in margin_sentiment:
            sentiment_adjustment -= 15
        
        # Final margin score with bounds
        scores['margin'] = round(np.clip(base_margin + sentiment_adjustment, 0, 100), 2)
        
        # ─────────────────────────────────────────────────────────────
        # 5. 靜默佈局偵測 (Stealth Accumulation) - Pre-Breakout Enhancement
        #    當機構買入但股價尚未拉升時 = 爆發前佈局的最佳信號
        #    判斷: 籌碼正向 BUT 動能低迷 = 蓄勢待發
        # ─────────────────────────────────────────────────────────────
        stealth_bonus = 0
        
        # 檢測籌碼與價格的背離
        ret_12m = self._safe_get(row, 'Return_12M', 0)
        ret_1m = self._safe_get(row, 'Return_1M', 0)
        rs_ratio = self._safe_get(row, 'RS_Ratio', 1.0)
        
        # 條件1: 機構在買 (籌碼正向)
        is_chip_positive = (qfii_raw > 0 or fund_raw > 0 or 
                           '買超' in chip_trend or '雙多' in chip_trend)
        
        # 條件2: 股價尚未拉升 (動能低迷)
        is_price_dormant = (ret_12m < 20 and ret_1m < 5 and rs_ratio < 1.2)
        
        # 條件3: 股價超跌但機構進場 (逆勢佈局)
        is_contrarian_accumulation = (ret_12m < -10 and (qfii_raw > 0 or fund_raw > 0))
        
        if is_chip_positive and is_price_dormant:
            stealth_bonus = 18  # 靜默佈局中，爆發力高
            scores['stealth_signal'] = '🎯 靜默佈局'
        elif is_contrarian_accumulation:
            stealth_bonus = 15  # 逆勢佈局，高風險高報酬
            scores['stealth_signal'] = '🔥 逆勢佈局'
        elif is_chip_positive and ret_12m < 35:
            stealth_bonus = 8   # 籌碼正向但尚未過熱
            scores['stealth_signal'] = '✅ 籌碼蓄勢'
        else:
            scores['stealth_signal'] = ''
        
        scores['stealth_bonus'] = stealth_bonus
        
        # 加權彙總 (加入靜默佈局加成)
        base_final = (scores['qfii'] * 0.30 +
                     scores['fund'] * 0.22 +
                     scores['trend'] * 0.23 +
                     scores['margin'] * 0.15)
        
        # 靜默佈局加成 (最高額外10分)
        final = min(100, base_final + stealth_bonus * 0.10 * 100 / 18)
        
        return {'score': round(final, 2), 'details': scores, 'stealth_bonus': stealth_bonus}
    
    # ═══════════════════════════════════════════════════════════════
    # 【因子六：策略加成 Strategy (8%)】
    # ═══════════════════════════════════════════════════════════════
    
    def calc_strategy_score(self, row: pd.Series, ticker: str) -> dict:
        """
        計算策略信號加成分數
        
        組成:
        - Alpha Stock: +25分 (動能爆發)
        - Early Bird: +22分 (拐點早鳥)
        - Contrarian: +20分 (逆向機會)
        - Hidden Gem: SSS +25, S +18, A +12
        """
        score = 0
        strategies = []
        details = {}
        
        # 1. Alpha Stock
        is_alpha = row.get('Is_Alpha', False)
        alpha_score = self._safe_get(row, 'Alpha_Score', 0)
        if is_alpha or alpha_score > 0:
            bonus = min(25, alpha_score * 0.3) if alpha_score > 0 else 25
            score += bonus
            strategies.append('🔥 Alpha')
            details['alpha'] = bonus
        
        # 2. Early Bird
        is_eb = row.get('Is_EarlyBird', False)
        eb_score = self._safe_get(row, 'EarlyBird_Score', 0)
        if is_eb or eb_score > 0:
            bonus = min(22, eb_score * 0.3) if eb_score > 0 else 22
            score += bonus
            strategies.append('💎 Early Bird')
            details['early_bird'] = bonus
        
        # 3. Contrarian
        is_con = row.get('Is_Contrarian', False)
        con_score = self._safe_get(row, 'Contrarian_Score', 0)
        if is_con or con_score > 0:
            bonus = min(20, con_score * 0.24) if con_score > 0 else 20
            score += bonus
            strategies.append('🎯 Contrarian')
            details['contrarian'] = bonus
        
        # 4. Hidden Gem
        is_gem = row.get('Is_HiddenGem', False)
        gem_score = self._safe_get(row, 'Gem_Score', 0)
        gem_type = str(row.get('Gem_Type', ''))
        
        if is_gem or gem_score > 0:
            if 'SSS' in gem_type or gem_score >= 100:
                bonus = 25
                strategies.append('💎💎💎 SSS')
            elif 'S級' in gem_type or gem_score >= 80:
                bonus = 18
                strategies.append('💎💎 S')
            elif 'A級' in gem_type or gem_score >= 60:
                bonus = 12
                strategies.append('💎 A')
            else:
                bonus = 8
                strategies.append('💎 Gem')
            score += bonus
            details['hidden_gem'] = bonus
        
        # 上限100分
        score = min(100, score)
        
        return {
            'score': round(score, 2),
            'strategies': strategies,
            'strategy_str': ', '.join(strategies) if strategies else '',
            'details': details
        }
    
    # ═══════════════════════════════════════════════════════════════
    # 【風險調整 Risk Adjustment】
    # ═══════════════════════════════════════════════════════════════
    
    def calc_risk_penalty(self, row: pd.Series) -> dict:
        """
        計算風險扣分
        
        扣分項目:
        - 最大回撤 (0-15分)
        - 當前回撤 (0-12分)
        - 健康風險 (0-15分)
        - 資產膨脹 (0-8分)
        - 品質警示 (0-10分)
        """
        penalty = 0
        details = {}
        
        # 1. 最大回撤風險
        max_dd = self._safe_get(row, 'Max_Drawdown', 0)
        if max_dd < -60:
            dd_penalty = 15
        elif max_dd < -50:
            dd_penalty = 12
        elif max_dd < -40:
            dd_penalty = 8
        elif max_dd < -30:
            dd_penalty = 5
        else:
            dd_penalty = 0
        penalty += dd_penalty
        details['max_drawdown'] = dd_penalty
        
        # 2. 當前回撤
        curr_dd = self._safe_get(row, 'Current_Drawdown', 0)
        if curr_dd < -50:
            curr_penalty = 12
        elif curr_dd < -40:
            curr_penalty = 8
        elif curr_dd < -30:
            curr_penalty = 5
        elif curr_dd < -20:
            curr_penalty = 2
        else:
            curr_penalty = 0
        penalty += curr_penalty
        details['current_drawdown'] = curr_penalty
        
        # 3. 健康風險
        health_rating = str(row.get('Health_Rating', ''))
        if 'F級' in health_rating:
            health_penalty = 15
        elif 'D級' in health_rating:
            health_penalty = 10
        elif 'C級' in health_rating and '雙殺' in health_rating:
            health_penalty = 8
        elif 'C級' in health_rating:
            health_penalty = 4
        else:
            health_penalty = 0
        penalty += health_penalty
        details['health'] = health_penalty
        
        # 4. 資產膨脹風險
        asset_growth = self._safe_get(row, 'Asset_Growth', 0)
        if asset_growth > 50:
            asset_penalty = 8
        elif asset_growth > 40:
            asset_penalty = 5
        elif asset_growth > 30:
            asset_penalty = 2
        else:
            asset_penalty = 0
        penalty += asset_penalty
        details['asset_growth'] = asset_penalty
        
        # 5. 品質警示
        quality_warning = row.get('Quality_Warning', False)
        warnings = str(row.get('Warnings', ''))
        if quality_warning or '盈餘品質差' in warnings:
            warning_penalty = 10
        elif warnings and len(warnings) > 2:
            warning_penalty = 5
        else:
            warning_penalty = 0
        penalty += warning_penalty
        details['quality_warning'] = warning_penalty
        
        # 上限50分
        penalty = min(50, penalty)
        
        return {'penalty': round(penalty, 2), 'details': details}
    
    # ═══════════════════════════════════════════════════════════════
    # 【蓄勢待發評分 Coiled Spring Score】⭐ 新增
    # ═══════════════════════════════════════════════════════════════
    
    def calc_coiled_spring_score(self, row: pd.Series) -> dict:
        """
        計算「蓄勢待發」分數 - 尋找爆發力尚未釋放的潛力股
        
        核心邏輯:
        1. 基本面正在改善 (結構拐點、品質提升)
        2. 籌碼正在集中 (機構佈局)
        3. 但股價尚未反映 (低動能、低估值)
        
        高分股票特徵:
        - 結構改善 + 籌碼進場 + 價格低迷 = 彈簧蓄勢中
        - 這類股票一旦啟動，爆發力最大
        
        Returns:
            dict: {score, signals, spring_level, details}
        """
        signals = []
        details = {}
        score = 0
        
        # ─────────────────────────────────────────────────────────────
        # 1. 基本面改善信號 (彈簧內力)
        # ─────────────────────────────────────────────────────────────
        
        # 結構拐點
        gpm_inflection = row.get('GPM_Inflection', False)
        opm_inflection = row.get('OPM_Inflection', False)
        result_tag = str(row.get('Result_Tag', ''))
        
        if gpm_inflection and opm_inflection:
            score += 25
            signals.append('🔥 雙拐點確認')
            details['dual_inflection'] = True
        elif opm_inflection:
            score += 18
            signals.append('📈 OPM拐點')
            details['opm_inflection'] = True
        elif gpm_inflection:
            score += 15
            signals.append('📈 GPM拐點')
            details['gpm_inflection'] = True
        elif 'SSS' in result_tag or 'S級' in result_tag:
            score += 12
            signals.append('⭐ 結構改善')
        
        # 營收加速
        rev_accel = self._safe_get(row, 'Rev_Acceleration', 0)
        if rev_accel > 5:
            score += 12
            signals.append('🚀 營收加速')
            details['rev_acceleration'] = rev_accel
        elif rev_accel > 0:
            score += 6
        
        # F-Score 財務實力
        f_score = self._safe_get(row, 'F_Score', None)
        if f_score is not None and f_score >= 7:
            score += 10
            signals.append('💪 F-Score強')
            details['f_score'] = f_score
        elif f_score is not None and f_score >= 5:
            score += 5
        
        # ─────────────────────────────────────────────────────────────
        # 2. 籌碼佈局信號 (彈簧張力)
        # ─────────────────────────────────────────────────────────────
        
        qfii_raw = self._safe_get(row, 'QFII_Net_4W', 0)
        fund_raw = self._safe_get(row, 'Fund_Net_4W', 0)
        chip_trend = str(row.get('Chip_Trend', ''))
        
        # 機構雙買
        if qfii_raw > 0 and fund_raw > 0:
            score += 20
            signals.append('🏛️ 法人雙買')
            details['dual_buying'] = True
        elif qfii_raw > 0:
            score += 12
            signals.append('🌍 外資買超')
        elif fund_raw > 0:
            score += 10
            signals.append('🏦 投信買超')
        
        # 雙多趨勢
        if '雙多' in chip_trend:
            score += 8
            signals.append('📊 籌碼雙多')
        
        # 融資減少 (籌碼沉澱)
        margin_sentiment = str(row.get('Margin_Sentiment', ''))
        if '融資大減' in margin_sentiment:
            score += 8
            signals.append('📉 融資沉澱')
            details['margin_shrinking'] = True
        
        # ─────────────────────────────────────────────────────────────
        # 3. 價格尚未反映 (彈簧壓縮) - 越低越有潛力
        # ─────────────────────────────────────────────────────────────
        
        ret_12m = self._safe_get(row, 'Return_12M', 0)
        ret_1m = self._safe_get(row, 'Return_1M', 0)
        rs_ratio = self._safe_get(row, 'RS_Ratio', 1.0)
        pe_pct = self._safe_get(row, 'PE_Percentile', 50)
        
        # 價格低迷加分 (爆發力未釋放)
        if ret_12m < 0:
            score += 15  # 年度負報酬 = 彈簧深度壓縮
            signals.append('🎯 年度負報酬')
            details['annual_down'] = ret_12m
        elif ret_12m < 15:
            score += 10  # 溫和表現
            signals.append('⚡ 價格待發')
        elif ret_12m < 30:
            score += 5   # 略有上漲但不過熱
        else:
            score -= 10  # 已經跑過了，扣分
        
        # RS 低迷加分
        if rs_ratio < 0.9:
            score += 8   # 弱於大盤 = 彈簧蓄勢
            signals.append('📊 RS待發')
        elif rs_ratio < 1.0:
            score += 4
        elif rs_ratio > 1.3:
            score -= 5   # 已經強勢，扣分
        
        # 估值低迷加分
        if pe_pct < 25:
            score += 10
            signals.append('💰 估值低檔')
            details['undervalued'] = True
        elif pe_pct < 40:
            score += 5
        
        # ─────────────────────────────────────────────────────────────
        # 4. 計算彈簧等級
        # ─────────────────────────────────────────────────────────────
        
        score = max(0, min(100, score))
        
        if score >= 70:
            spring_level = '🔥🔥🔥 極度蓄勢 (爆發力最強)'
        elif score >= 55:
            spring_level = '🔥🔥 高度蓄勢'
        elif score >= 40:
            spring_level = '🔥 蓄勢中'
        elif score >= 25:
            spring_level = '⚡ 正在壓縮'
        else:
            spring_level = '➡️ 一般'
        
        return {
            'score': round(score, 2),
            'signals': signals,
            'spring_level': spring_level,
            'signal_str': ' | '.join(signals[:4]) if signals else '',  # 最多顯示4個
            'details': details
        }
    
    # ═══════════════════════════════════════════════════════════════
    # 【綜合評分計算】
    # ═══════════════════════════════════════════════════════════════
    
    def calculate_final_score(self) -> pd.DataFrame:
        """計算所有股票的綜合評分"""
        print("\n🧮 計算綜合評分...")
        
        if self.merged_df is None:
            raise ValueError("請先執行 merge_all_data()")
        
        results = []
        
        for idx, row in self.merged_df.iterrows():
            ticker = row['Ticker']
            company = row.get('Company_Name', self.stock_names.get(ticker, ''))
            
            # 計算各因子分數
            momentum = self.calc_momentum_score(row)
            quality = self.calc_quality_score(row)
            structural = self.calc_structural_score(row)
            valuation = self.calc_valuation_score(row)
            chip = self.calc_chip_score(row)
            strategy = self.calc_strategy_score(row, ticker)
            risk = self.calc_risk_penalty(row)
            coiled_spring = self.calc_coiled_spring_score(row)  # ⭐ 新增
            
            # 加權計算最終分數
            raw_score = (
                momentum['score'] * self.WEIGHTS['momentum'] +
                quality['score'] * self.WEIGHTS['quality'] +
                structural['score'] * self.WEIGHTS['structural'] +
                valuation['score'] * self.WEIGHTS['valuation'] +
                chip['score'] * self.WEIGHTS['chip'] +
                strategy['score'] * self.WEIGHTS['strategy']
            )
            
            # ⭐ 蓄勢待發加成 (Pre-Breakout Bonus)
            # 高蓄勢分數的股票額外加分，最高 +10 分
            spring_bonus = coiled_spring['score'] * 0.10 if coiled_spring['score'] >= 40 else 0
            
            # 風險調整
            final_score = raw_score + spring_bonus - risk['penalty'] * 0.25
            final_score = max(0, min(100, final_score))
            
            # 投資建議
            if final_score >= 75:
                recommendation = '🔥 強力買進'
                rec_level = 5
            elif final_score >= 65:
                recommendation = '📈 積極配置'
                rec_level = 4
            elif final_score >= 55:
                recommendation = '✅ 穩健持有'
                rec_level = 3
            elif final_score >= 45:
                recommendation = '⚠️ 謹慎觀望'
                rec_level = 2
            else:
                recommendation = '🛑 建議迴避'
                rec_level = 1
            
            results.append({
                'Ticker': ticker,
                'Company_Name': company,
                'Final_Score': round(final_score, 2),
                'Raw_Score': round(raw_score, 2),
                'Recommendation': recommendation,
                'Rec_Level': rec_level,
                'Strategy': strategy['strategy_str'],
                
                # 六大因子分數
                'Momentum': momentum['score'],
                'Quality': quality['score'],
                'Structural': structural['score'],
                'Valuation': valuation['score'],
                'Chip': chip['score'],
                'Strategy_Bonus': strategy['score'],
                'Risk_Penalty': risk['penalty'],
                
                # ⭐ 蓄勢待發分析 (新增)
                'Coiled_Spring': coiled_spring['score'],
                'Spring_Level': coiled_spring['spring_level'],
                'Spring_Signals': coiled_spring['signal_str'],
                'Spring_Bonus': round(spring_bonus, 2),
                
                # 關鍵指標
                'Health_Rating': row.get('Health_Rating', ''),
                'Decision': row.get('Decision', ''),
                'Result_Tag': row.get('Result_Tag', ''),
                'Gem_Type': row.get('Gem_Type', ''),
                
                # 價格與估值
                'Current_Price': row.get('Current_Price', ''),
                'PE': row.get('PE', ''),
                'PE_Percentile': row.get('PE_Percentile', ''),
                'PB_Percentile': row.get('PB_Percentile', ''),
                
                # 動能
                'Momentum_12_1': row.get('Momentum_12_1', ''),
                'Return_12M': row.get('Return_12M', ''),
                'RS_Ratio': row.get('RS_Ratio', ''),
                
                # 籌碼
                'QFII_Net_4W': row.get('QFII_Net_4W', ''),
                'Fund_Net_4W': row.get('Fund_Net_4W', ''),
                'Chip_Trend': row.get('Chip_Trend', ''),
                
                # 風險
                'Max_Drawdown': row.get('Max_Drawdown', ''),
                'Current_Drawdown': row.get('Current_Drawdown', ''),
                
                # 原始分數 (用於比較)
                'Composite_Score': row.get('Composite_Score', ''),
                'Cross_Composite_Score': row.get('Cross_Composite_Score', ''),
            })
        
        # 排序並加入排名
        result_df = pd.DataFrame(results)
        result_df = result_df.sort_values('Final_Score', ascending=False).reset_index(drop=True)
        result_df.insert(0, 'Rank', range(1, len(result_df) + 1))
        
        self.final_ranking = result_df
        
        # 統計資訊
        self.stats = {
            'total': len(result_df),
            'strong_buy': len(result_df[result_df['Rec_Level'] == 5]),
            'accumulate': len(result_df[result_df['Rec_Level'] == 4]),
            'hold': len(result_df[result_df['Rec_Level'] == 3]),
            'caution': len(result_df[result_df['Rec_Level'] == 2]),
            'avoid': len(result_df[result_df['Rec_Level'] == 1]),
            'avg_score': result_df['Final_Score'].mean(),
            'median_score': result_df['Final_Score'].median(),
        }
        
        print(f"  ✅ 評分完成: {len(result_df)} 筆")
        return result_df
    
    # ═══════════════════════════════════════════════════════════════
    # 【輸出與報告】
    # ═══════════════════════════════════════════════════════════════
    
    def print_ranking(self, top_n: int = 30):
        """印出詳細排名報告"""
        if self.final_ranking is None:
            print("❌ 請先執行分析")
            return
        
        df = self.final_ranking
        
        # 標題
        print("\n" + "═" * 100)
        print(f"{'':^100}")
        print(f"{'📊 股票池綜合排名報告 v2.0':^95}")
        print(f"{'':^100}")
        print(f"{'Generated: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'):^100}")
        print("═" * 100)
        
        # 權重說明
        print("\n【因子權重配置】")
        print(f"  動能 {self.WEIGHTS['momentum']*100:.0f}% | 品質 {self.WEIGHTS['quality']*100:.0f}% | "
              f"結構 {self.WEIGHTS['structural']*100:.0f}% | 估值 {self.WEIGHTS['valuation']*100:.0f}% | "
              f"籌碼 {self.WEIGHTS['chip']*100:.0f}% | 策略 {self.WEIGHTS['strategy']*100:.0f}%")
        
        # 統計摘要
        print("\n【分級統計】")
        for rec, count_key, emoji in [
            ('強力買進', 'strong_buy', '🔥'),
            ('積極配置', 'accumulate', '📈'),
            ('穩健持有', 'hold', '✅'),
            ('謹慎觀望', 'caution', '⚠️'),
            ('建議迴避', 'avoid', '🛑'),
        ]:
            count = self.stats[count_key]
            pct = count / self.stats['total'] * 100
            bar = '█' * int(pct / 5)
            print(f"  {emoji} {rec}: {count:>3} 檔 ({pct:>5.1f}%) {bar}")
        
        print(f"\n  平均分數: {self.stats['avg_score']:.1f} | 中位數: {self.stats['median_score']:.1f}")
        
        # TOP N 排名
        print("\n" + "─" * 100)
        print(f"{'🏆 TOP ' + str(top_n) + ' 排名':^50}")
        print("─" * 100)
        print(f"{'Rank':<5} {'Ticker':<12} {'名稱':<8} {'總分':>6} {'建議':<12} "
              f"{'動能':>5} {'品質':>5} {'結構':>5} {'估值':>5} {'策略':<20}")
        print("─" * 100)
        
        for _, row in df.head(top_n).iterrows():
            strategy_short = row['Strategy'][:18] + '...' if len(str(row['Strategy'])) > 20 else row['Strategy']
            print(f"{row['Rank']:<5} {row['Ticker']:<12} {row['Company_Name']:<8} "
                  f"{row['Final_Score']:>6.1f} {row['Recommendation']:<12} "
                  f"{row['Momentum']:>5.0f} {row['Quality']:>5.0f} {row['Structural']:>5.0f} "
                  f"{row['Valuation']:>5.0f} {strategy_short:<20}")
        
        print("─" * 100)
        
        # TOP 10 詳細分析
        print("\n" + "═" * 100)
        print("🔥 TOP 10 詳細分析")
        print("═" * 100)
        
        for _, row in df.head(10).iterrows():
            print(f"\n【#{row['Rank']} {row['Ticker']} {row['Company_Name']}】")
            print(f"  📊 總分: {row['Final_Score']:.2f} (原始: {row['Raw_Score']:.2f}) | {row['Recommendation']}")
            print(f"  🎯 策略: {row['Strategy'] if row['Strategy'] else '無特殊策略'}")
            print(f"  📈 動能: {row['Momentum']:.0f} | 品質: {row['Quality']:.0f} | "
                  f"結構: {row['Structural']:.0f} | 估值: {row['Valuation']:.0f} | 籌碼: {row['Chip']:.0f}")
            print(f"  🔖 健康: {row['Health_Rating']} | 決策: {row['Decision']}")
            if row['Current_Price']:
                print(f"  💰 現價: {row['Current_Price']} | PE百分位: {row['PE_Percentile']}%")
            if row['Chip_Trend']:
                print(f"  🏦 籌碼: {row['Chip_Trend']} | 外資4週: {row['QFII_Net_4W']}")
        
        # 策略分類
        print("\n" + "═" * 100)
        print("📌 各策略推薦")
        print("═" * 100)
        
        strategy_groups = {
            '🔥 Alpha Stock': 'Alpha',
            '💎 Hidden Gem': '💎',
            '💎 Early Bird': 'Early Bird',
            '🎯 Contrarian': 'Contrarian',
        }
        
        for display_name, filter_key in strategy_groups.items():
            strategy_df = df[df['Strategy'].str.contains(filter_key, na=False)]
            if len(strategy_df) > 0:
                print(f"\n{display_name} ({len(strategy_df)} 檔):")
                for _, row in strategy_df.head(5).iterrows():
                    print(f"  #{row['Rank']:>3} {row['Ticker']:<10} {row['Company_Name']:<8} "
                          f"- {row['Final_Score']:.1f}分 | {row['Recommendation']}")
        
        # 應迴避名單
        avoid_df = df[df['Rec_Level'] == 1]
        if len(avoid_df) > 0:
            print(f"\n⚠️ 應迴避名單 ({len(avoid_df)} 檔):")
            for _, row in avoid_df.head(5).iterrows():
                print(f"  {row['Ticker']:<10} {row['Company_Name']:<8} "
                      f"- 分數: {row['Final_Score']:.1f} | 風險扣分: {row['Risk_Penalty']:.0f}")
        
        print("\n" + "═" * 100)
        print("✅ 分析完成!")
        print("═" * 100)
    
    def export_results(self, filename: str = None) -> Path:
        """匯出結果到 CSV"""
        if self.final_ranking is None:
            print("❌ 請先執行分析")
            return None
        
        if filename is None:
            filename = f"master_ranking_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        output_path = self.stock_pool_path / filename
        self.final_ranking.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"\n✅ 結果已匯出: {output_path}")
        return output_path
    
    # ═══════════════════════════════════════════════════════════════
    # 【主流程】
    # ═══════════════════════════════════════════════════════════════
    
    def analyze(self, export: bool = True, top_n: int = 30) -> pd.DataFrame:
        """執行完整分析流程"""
        print("\n" + "🚀" * 25)
        print("   MASTER RANKING ANALYZER v2.0 - 綜合排名分析器（終極版）")
        print("🚀" * 25 + "\n")
        
        # Step 1: 載入所有數據
        self.load_all_data()
        
        # Step 2: 合併數據
        self.merge_all_data()
        
        # Step 3: 計算分數
        self.calculate_final_score()
        
        # Step 4: 印出報告
        self.print_ranking(top_n)
        
        # Step 5: 匯出
        if export:
            self.export_results()
        
        return self.final_ranking
    
    # ═══════════════════════════════════════════════════════════════
    # 【便捷方法】
    # ═══════════════════════════════════════════════════════════════
    
    def get_top_picks(self, n: int = 10) -> pd.DataFrame:
        """取得前 N 名推薦"""
        if self.final_ranking is None:
            self.analyze(export=False, top_n=n)
        return self.final_ranking.head(n)
    
    def get_by_strategy(self, strategy: str) -> pd.DataFrame:
        """依策略篩選"""
        if self.final_ranking is None:
            self.analyze(export=False)
        return self.final_ranking[self.final_ranking['Strategy'].str.contains(strategy, na=False)]
    
    def get_strong_buys(self) -> pd.DataFrame:
        """取得強力買進名單"""
        if self.final_ranking is None:
            self.analyze(export=False)
        return self.final_ranking[self.final_ranking['Rec_Level'] == 5]
    
    def get_avoid_list(self) -> pd.DataFrame:
        """取得應迴避名單"""
        if self.final_ranking is None:
            self.analyze(export=False)
        return self.final_ranking[self.final_ranking['Rec_Level'] == 1]
    
    def get_by_recommendation(self, rec_level: int) -> pd.DataFrame:
        """依建議等級篩選 (5=強力買進, 4=積極配置, 3=持有, 2=觀望, 1=迴避)"""
        if self.final_ranking is None:
            self.analyze(export=False)
        return self.final_ranking[self.final_ranking['Rec_Level'] == rec_level]
    
    # ═══════════════════════════════════════════════════════════════
    # 【工具函數】
    # ═══════════════════════════════════════════════════════════════
    
    def _safe_get(self, row: pd.Series, key: str, default=0):
        """安全取得數值"""
        val = row.get(key, default)
        if pd.isna(val):
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default
    
    def _sigmoid_score(self, x: float, midpoint: float, steepness: float = 1.0,
                       min_score: float = 0, max_score: float = 100) -> float:
        """
        Physics-Informed Continuous Scoring via Sigmoid (Logistic) Function
        
        Maps any real-valued input to a smooth score in [min_score, max_score].
        Eliminates boundary effects from discrete thresholds.
        
        Formula: score = min_score + (max_score - min_score) / (1 + exp(-steepness * (x - midpoint)))
        
        Args:
            x: Input value (can be any real number)
            midpoint: The x value at which the function outputs the median score (50th percentile)
            steepness: Controls transition sharpness (higher = steeper curve, lower = gentler)
                       Typical range: 0.01 ~ 5.0 depending on input scale
            min_score: Minimum output score (default: 0)
            max_score: Maximum output score (default: 100)
        
        Returns:
            Continuous score in [min_score, max_score]
        
        Example:
            For momentum scoring with midpoint=0, steepness=0.05:
            - x = -50 → score ≈ 7.6
            - x = 0   → score = 50
            - x = 50  → score ≈ 92.4
        """
        # Clamp extreme values to avoid numerical overflow
        z = steepness * (x - midpoint)
        z = np.clip(z, -500, 500)
        
        sigmoid = 1.0 / (1.0 + np.exp(-z))
        score = min_score + (max_score - min_score) * sigmoid
        
        return round(score, 2)
    
    def _signed_log_transform(self, x: float, base_scale: float = 1000) -> float:
        """
        Signed Log Transform to Compress Outliers (Size-Neutral Normalization)
        
        Applies: sign(x) * log(1 + |x| / base_scale)
        
        This transformation:
        1. Preserves sign (positive/negative sentiment)
        2. Compresses large absolute values (reduces size bias)
        3. Maintains relative ordering
        
        Args:
            x: Raw input value (e.g., QFII net buy in shares)
            base_scale: Normalization factor (controls compression strength)
        
        Returns:
            Transformed value with compressed magnitude
        
        Example (base_scale=1000):
            - x = 100,000 → 4.61
            - x = 10,000  → 2.40
            - x = 1,000   → 0.69
            - x = -50,000 → -3.93
        """
        if x == 0:
            return 0.0
        return np.sign(x) * np.log1p(abs(x) / base_scale)
    
    def _percentile_score(self, x: float, series: pd.Series, invert: bool = False) -> float:
        """
        Percentile-Based Scoring (Rank Normalization)
        
        Converts a value to its percentile rank within a distribution.
        Eliminates absolute value bias by using relative positioning.
        
        Args:
            x: Value to score
            series: Reference distribution (e.g., all stocks' QFII values)
            invert: If True, lower values get higher scores (e.g., for PE)
        
        Returns:
            Score from 0-100 based on percentile rank
        """
        if series is None or len(series) == 0:
            return 50.0
        
        # Calculate percentile rank
        rank = (series < x).sum() / len(series) * 100
        
        if invert:
            rank = 100 - rank
        
        return round(rank, 2)


def main():
    """主程式入口"""
    parser = argparse.ArgumentParser(
        description="Master Ranking Analyzer v2.0 - 股票池綜合排名分析器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  python master_ranking_analyzer.py                  # 執行完整分析
  python master_ranking_analyzer.py --top 50         # 顯示前50名
  python master_ranking_analyzer.py --no-export      # 不匯出CSV
  python master_ranking_analyzer.py --strategy alpha # 只看Alpha策略
        """
    )
    parser.add_argument('--top', type=int, default=30, help='顯示前 N 名 (預設: 30)')
    parser.add_argument('--no-export', action='store_true', help='不匯出CSV檔案')
    parser.add_argument('--strategy', type=str, help='依策略篩選 (alpha/early/gem/contrarian)')
    parser.add_argument('--avoid', action='store_true', help='顯示應迴避名單')
    parser.add_argument('--path', type=str, help='Stock_Pool 資料夾路徑')
    
    args = parser.parse_args()
    
    # 建立分析器
    analyzer = MasterRankingAnalyzer(args.path)
    
    # 執行分析
    ranking = analyzer.analyze(export=not args.no_export, top_n=args.top)
    
    # 額外輸出
    if args.strategy:
        strategy_map = {
            'alpha': 'Alpha',
            'early': 'Early Bird',
            'gem': '💎',
            'contrarian': 'Contrarian'
        }
        filter_key = strategy_map.get(args.strategy.lower(), args.strategy)
        filtered = analyzer.get_by_strategy(filter_key)
        print(f"\n📌 {args.strategy} 策略篩選 ({len(filtered)} 檔):")
        for _, row in filtered.head(20).iterrows():
            print(f"  #{row['Rank']:>3} {row['Ticker']:<10} {row['Company_Name']:<8} - {row['Final_Score']:.1f}分")
    
    if args.avoid:
        avoid = analyzer.get_avoid_list()
        print(f"\n⚠️ 完整應迴避名單 ({len(avoid)} 檔):")
        for _, row in avoid.iterrows():
            print(f"  {row['Ticker']:<10} {row['Company_Name']:<8} - 分數: {row['Final_Score']:.1f}")
    
    return ranking


if __name__ == "__main__":
    main()
