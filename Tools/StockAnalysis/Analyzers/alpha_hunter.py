#!/usr/bin/env python3
"""
Alpha Hunter v1.0 - 超額報酬獵手
================================
兩大策略：
1. 🔥 Alpha Stock (強勢股) - 動能+品質+結構三強合一
2. 💎 Early Bird (早鳥股) - 在別人注意到之前先買好

Author: Investment AI System
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


class AlphaHunter:
    """Hunt for alpha-generating stocks with two distinct strategies."""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            # 從 Analyzers/alpha_hunter.py 往上4層到達專案根目錄
            self.data_dir = Path(__file__).parent.parent.parent.parent / "Stock_Pool"
        else:
            self.data_dir = Path(data_dir)
        
        self.file_map = {
            'factor': 'factor_analysis_v3.csv',
            'health': 'final_health_check_report_v2.csv',
            'valuation': 'final_valuation_report_v2.csv',
            'hidden_forensic': 'hidden_gems_forensic_report_v2.csv',
            'hidden_health': 'hidden_gems_health_check_report_v2.csv',
            'hidden_gems': 'hidden_gems_report_v2.csv',
            'hidden_valuation': 'hidden_gems_valuation_report_v2.csv',
            'inst_forensic': 'institutional_forensic_report_v2.csv',
            'structural': 'structural_change_report_v2.csv'
        }
        
        self.data = {}
        self.merged_df = None
        
    def load_all_data(self) -> dict:
        """Load all data files."""
        print("📊 Loading data...")
        for key, filename in self.file_map.items():
            filepath = self.data_dir / filename
            if filepath.exists():
                self.data[key] = pd.read_csv(filepath)
            else:
                self.data[key] = pd.DataFrame()
        return self.data
    
    def _safe_numeric(self, df: pd.DataFrame, col: str, default: float = 0) -> pd.Series:
        if col not in df.columns:
            return pd.Series([default] * len(df), index=df.index)
        return pd.to_numeric(df[col], errors='coerce').fillna(default)
    
    def merge_data(self) -> pd.DataFrame:
        """Merge all datasets."""
        base = self.data['factor'][['Ticker', 'Company_Name', 'Composite_Score', 'Rating',
                                     'FCF_Yield', 'Momentum_12_1', 'Return_12M', 'Return_1M',
                                     'Momentum_Status', 'Stability_Score', 'Asset_Growth',
                                     'Max_Drawdown', 'Current_Drawdown', 'Margin_Score',
                                     'Margin_Sentiment']].copy()
        
        # Merge health
        if not self.data['health'].empty:
            health_cols = ['Ticker', 'Health_Score', 'CCR_TTM', 'Sloan_Ratio', 'Health_Rating']
            health_cols = [c for c in health_cols if c in self.data['health'].columns]
            base = base.merge(self.data['health'][health_cols], on='Ticker', how='left')
        
        # Merge valuation
        if not self.data['valuation'].empty:
            val_cols = ['Ticker', 'Current_Price', 'Decision', 'Market_Regime',
                       'RS_Ratio', 'RS_Status', 'PE', 'PE_Percentile', 'PB', 'PB_Percentile']
            val_cols = [c for c in val_cols if c in self.data['valuation'].columns]
            base = base.merge(self.data['valuation'][val_cols], on='Ticker', how='left')
        
        # Merge structural
        if not self.data['structural'].empty:
            struct_cols = ['Ticker', 'Score', 'Result_Tag', 'GPM_Inflection', 'OPM_Inflection',
                          'Operating_Leverage', 'Rev_YoY', 'Rev_Acceleration', 'Rev_New_High']
            struct_cols = [c for c in struct_cols if c in self.data['structural'].columns]
            base = base.merge(self.data['structural'][struct_cols], on='Ticker', how='left')
        
        # Merge forensic
        if not self.data['inst_forensic'].empty:
            forensic_cols = ['Ticker', 'Forensic_Score', 'F_Score', 'Hollow_Ratio', 'ROIC']
            forensic_cols = [c for c in forensic_cols if c in self.data['inst_forensic'].columns]
            base = base.merge(self.data['inst_forensic'][forensic_cols], on='Ticker', how='left')
        
        # Merge hidden gems
        if not self.data['hidden_gems'].empty:
            gem_cols = ['Ticker', 'Gem_Score', 'Gem_Type', 'Rev_Acc', 'Chip_Trend',
                       'QFII_Net_4W', 'Fund_Net_4W', 'RS', 'PSR_Percentile']
            gem_cols = [c for c in gem_cols if c in self.data['hidden_gems'].columns]
            base = base.merge(self.data['hidden_gems'][gem_cols], on='Ticker', how='left')
        
        self.merged_df = base
        return base
    
    def find_alpha_stocks(self) -> pd.DataFrame:
        """
        策略一：Alpha Stock 強勢股
        ========================
        條件：
        1. 動能極強 (Momentum_12_1 > 30% 或 RS > 1.2)
        2. 品質過關 (Forensic >= 60, Sloan < 0.1)
        3. 結構改善 (GPM或OPM拐點, 或營收創高)
        4. 法人認同 (外資或投信買超)
        """
        print("\n" + "="*60)
        print("🔥 策略一：ALPHA STOCK 強勢股")
        print("   真的很強的公司 - 動能+品質+結構三強合一")
        print("="*60)
        
        df = self.merged_df.copy()
        
        # ========================================
        # 條件篩選
        # ========================================
        
        # 1. 動能條件 (至少滿足一項)
        mom_12_1 = self._safe_numeric(df, 'Momentum_12_1', 0)
        rs_ratio = self._safe_numeric(df, 'RS_Ratio', 1.0)
        ret_12m = self._safe_numeric(df, 'Return_12M', 0)
        
        momentum_pass = (mom_12_1 > 30) | (rs_ratio > 1.2) | (ret_12m > 50)
        
        # 2. 品質條件 (必須通過)
        forensic = self._safe_numeric(df, 'Forensic_Score', 60)
        sloan = self._safe_numeric(df, 'Sloan_Ratio', 0)
        f_score = self._safe_numeric(df, 'F_Score', 5)
        
        quality_pass = (forensic >= 55) & (sloan < 0.15) & (f_score >= 5)
        
        # 3. 結構改善 (至少滿足一項)
        gpm_inf = df.get('GPM_Inflection', pd.Series([False] * len(df))).fillna(False).astype(bool)
        opm_inf = df.get('OPM_Inflection', pd.Series([False] * len(df))).fillna(False).astype(bool)
        rev_high = df.get('Rev_New_High', pd.Series([False] * len(df))).fillna(False).astype(bool)
        rev_acc = self._safe_numeric(df, 'Rev_Acceleration', 0)
        
        structural_pass = gpm_inf | opm_inf | rev_high | (rev_acc > 50)
        
        # 4. 法人認同 (加分項)
        qfii = self._safe_numeric(df, 'QFII_Net_4W', 0)
        fund = self._safe_numeric(df, 'Fund_Net_4W', 0)
        
        inst_buying = (qfii > 0) | (fund > 0)
        
        # ========================================
        # 計算 Alpha Score
        # ========================================
        df['Alpha_Score'] = 0.0
        
        # 動能分數 (0-40)
        df['Alpha_Score'] += np.where(mom_12_1 > 100, 40,
                             np.where(mom_12_1 > 50, 35,
                             np.where(mom_12_1 > 30, 30,
                             np.where(mom_12_1 > 15, 20,
                             np.where(mom_12_1 > 5, 10, 0)))))
        
        # RS加成
        df['Alpha_Score'] += np.where(rs_ratio > 2.0, 15,
                             np.where(rs_ratio > 1.5, 12,
                             np.where(rs_ratio > 1.2, 10,
                             np.where(rs_ratio > 1.0, 5, 0))))
        
        # 品質分數 (0-25)
        df['Alpha_Score'] += np.where(forensic >= 80, 15,
                             np.where(forensic >= 70, 12,
                             np.where(forensic >= 60, 8, 0)))
        df['Alpha_Score'] += np.where(f_score >= 8, 10,
                             np.where(f_score >= 7, 7,
                             np.where(f_score >= 6, 5, 0)))
        
        # 結構分數 (0-20)
        df['Alpha_Score'] += np.where(gpm_inf & opm_inf, 20,
                             np.where(gpm_inf | opm_inf, 15,
                             np.where(rev_high, 10, 0)))
        
        # 法人加成 (0-15)
        df['Alpha_Score'] += np.where((qfii > 10000) & (fund > 0), 15,
                             np.where(qfii > 10000, 10,
                             np.where((qfii > 0) & (fund > 0), 8,
                             np.where(qfii > 0, 5, 0))))
        
        # 風險減分
        mdd = self._safe_numeric(df, 'Max_Drawdown', -30)
        df['Alpha_Score'] += np.where(mdd < -60, -10,
                             np.where(mdd < -50, -5, 0))
        
        # ========================================
        # 篩選 Alpha Stocks
        # ========================================
        # 必須通過：動能 + 品質
        # 加分：結構改善、法人買超
        
        alpha_candidates = df[momentum_pass & quality_pass].copy()
        
        # 按 Alpha Score 排序
        alpha_candidates = alpha_candidates.sort_values('Alpha_Score', ascending=False)
        
        # 加入策略標籤
        def get_alpha_tag(row):
            tags = []
            if row.get('Momentum_12_1', 0) > 100:
                tags.append("🚀爆發動能")
            elif row.get('Momentum_12_1', 0) > 50:
                tags.append("🔥強勢動能")
            elif row.get('Momentum_12_1', 0) > 30:
                tags.append("📈正向動能")
            
            if row.get('GPM_Inflection', False) and row.get('OPM_Inflection', False):
                tags.append("💎雙拐點")
            elif row.get('GPM_Inflection', False) or row.get('OPM_Inflection', False):
                tags.append("🔄拐點浮現")
            
            if row.get('QFII_Net_4W', 0) > 10000 and row.get('Fund_Net_4W', 0) > 0:
                tags.append("🏛️雙法人買超")
            elif row.get('QFII_Net_4W', 0) > 5000:
                tags.append("📊外資買超")
            
            if row.get('F_Score', 0) >= 8:
                tags.append("✅高F-Score")
            
            if row.get('Rev_New_High', False):
                tags.append("📈營收創高")
            
            return " | ".join(tags) if tags else "強勢股"
        
        alpha_candidates['Alpha_Tag'] = alpha_candidates.apply(get_alpha_tag, axis=1)
        alpha_candidates['Strategy'] = '🔥 Alpha Stock'
        
        return alpha_candidates.head(15)
    
    def find_early_bird_stocks(self) -> pd.DataFrame:
        """
        策略二：Early Bird 早鳥股
        ========================
        條件：
        1. 隱藏寶石特徵 (Gem_Score高 或 結構轉好)
        2. 法人尚未大量買進 (QFII買超不大 或 剛開始買)
        3. 估值不貴 (PE/PB Percentile < 60)
        4. 動能開始啟動 (Momentum > 0 但 < 50, 還沒漲太多)
        5. 品質尚可 (不是地雷)
        """
        print("\n" + "="*60)
        print("💎 策略二：EARLY BIRD 早鳥股")
        print("   在別人注意到之前先買好 - 低調潛力股")
        print("="*60)
        
        df = self.merged_df.copy()
        
        # ========================================
        # 條件篩選
        # ========================================
        
        # 1. 結構改善或隱藏寶石特徵
        gem_score = self._safe_numeric(df, 'Gem_Score', 0)
        gpm_inf = df.get('GPM_Inflection', pd.Series([False] * len(df))).fillna(False).astype(bool)
        opm_inf = df.get('OPM_Inflection', pd.Series([False] * len(df))).fillna(False).astype(bool)
        rev_acc = self._safe_numeric(df, 'Rev_Acceleration', 0)
        
        has_potential = (gem_score >= 60) | gpm_inf | opm_inf | (rev_acc > 30)
        
        # 2. 法人尚未大量買進 (早期訊號)
        qfii = self._safe_numeric(df, 'QFII_Net_4W', 0)
        fund = self._safe_numeric(df, 'Fund_Net_4W', 0)
        
        # 法人還沒注意 或 剛開始小買
        early_stage = (qfii < 20000) & (qfii > -10000)  # 還沒大買也沒大賣
        
        # 3. 估值不貴
        pe_pct = self._safe_numeric(df, 'PE_Percentile', 50)
        pb_pct = self._safe_numeric(df, 'PB_Percentile', 50)
        
        not_expensive = (pe_pct < 70) | (pb_pct < 70)
        
        # 4. 動能剛啟動 (還沒漲太多)
        mom_12_1 = self._safe_numeric(df, 'Momentum_12_1', 0)
        ret_12m = self._safe_numeric(df, 'Return_12M', 0)
        
        # 動能正向但還沒爆發 (這是早期訊號)
        early_momentum = (mom_12_1 > -10) & (mom_12_1 < 80)  # 還沒漲太多
        
        # 5. 品質不是地雷
        forensic = self._safe_numeric(df, 'Forensic_Score', 60)
        sloan = self._safe_numeric(df, 'Sloan_Ratio', 0)
        
        not_trap = (forensic >= 50) & (sloan < 0.15)
        
        # ========================================
        # 計算 Early Bird Score
        # ========================================
        df['EarlyBird_Score'] = 0.0
        
        # 結構改善分數 (重要！這是早期訊號) (0-35)
        df['EarlyBird_Score'] += np.where(gpm_inf & opm_inf, 35,
                                 np.where(gpm_inf | opm_inf, 25,
                                 np.where(rev_acc > 100, 20,
                                 np.where(rev_acc > 50, 15,
                                 np.where(rev_acc > 20, 10, 0)))))
        
        # 隱藏寶石加成 (0-20)
        df['EarlyBird_Score'] += np.where(gem_score >= 100, 20,
                                 np.where(gem_score >= 80, 15,
                                 np.where(gem_score >= 60, 10, 0)))
        
        # 估值便宜加成 (0-20)
        df['EarlyBird_Score'] += np.where(pe_pct < 30, 15,
                                 np.where(pe_pct < 50, 10,
                                 np.where(pe_pct < 70, 5, 0)))
        df['EarlyBird_Score'] += np.where(pb_pct < 30, 5,
                                 np.where(pb_pct < 50, 3, 0))
        
        # 法人剛開始買 (早期卡位優勢) (0-15)
        df['EarlyBird_Score'] += np.where((qfii > 0) & (qfii < 10000) & (fund > 0), 15,  # 雙法人剛開始買
                                 np.where((qfii > 0) & (qfii < 10000), 10,  # 外資剛開始買
                                 np.where((fund > 0) & (fund < 5000), 8,  # 投信剛開始買
                                 np.where(qfii == 0, 5, 0))))  # 還沒被注意
        
        # 動能剛啟動加成 (0-10)
        df['EarlyBird_Score'] += np.where((mom_12_1 > 10) & (mom_12_1 < 50), 10,  # 甜蜜區：剛啟動
                                 np.where((mom_12_1 > 0) & (mom_12_1 <= 10), 8,
                                 np.where((mom_12_1 > -5) & (mom_12_1 <= 0), 5, 0)))
        
        # 品質加成
        df['EarlyBird_Score'] += np.where(forensic >= 70, 5, 0)
        
        # ========================================
        # 篩選 Early Bird Stocks
        # ========================================
        early_candidates = df[has_potential & not_trap].copy()
        
        # 優先選擇估值不貴的
        early_candidates = early_candidates[not_expensive.loc[early_candidates.index]]
        
        # 按 Early Bird Score 排序
        early_candidates = early_candidates.sort_values('EarlyBird_Score', ascending=False)
        
        # 加入策略標籤
        def get_early_tag(row):
            tags = []
            
            if row.get('GPM_Inflection', False) and row.get('OPM_Inflection', False):
                tags.append("💎雙拐點浮現")
            elif row.get('GPM_Inflection', False):
                tags.append("🔄毛利拐點")
            elif row.get('OPM_Inflection', False):
                tags.append("🔄營益拐點")
            
            if row.get('Rev_Acceleration', 0) > 50:
                tags.append("📈營收加速")
            
            if row.get('Rev_New_High', False):
                tags.append("🏆營收創高")
            
            qfii = row.get('QFII_Net_4W', 0)
            fund = row.get('Fund_Net_4W', 0)
            if qfii > 0 and qfii < 10000:
                tags.append("👀外資剛注意")
            if fund > 0 and fund < 5000:
                tags.append("👀投信剛注意")
            if qfii <= 0 and fund <= 0:
                tags.append("🤫尚未被發現")
            
            pe_pct = row.get('PE_Percentile', 50)
            if pe_pct < 30:
                tags.append("💰估值偏低")
            elif pe_pct < 50:
                tags.append("💵估值合理")
            
            if row.get('Gem_Score', 0) >= 80:
                tags.append("💎隱藏寶石")
            
            return " | ".join(tags) if tags else "早期佈局"
        
        early_candidates['EarlyBird_Tag'] = early_candidates.apply(get_early_tag, axis=1)
        early_candidates['Strategy'] = '💎 Early Bird'
        
        return early_candidates.head(15)
    
    def find_contrarian_picks(self) -> pd.DataFrame:
        """
        策略三：Contrarian 逆向佈局
        ==========================
        條件：
        1. 股價大跌但基本面轉好 (Current_Drawdown 大但結構改善)
        2. 品質沒問題 (不是財務出問題才跌)
        3. 法人開始回補
        """
        print("\n" + "="*60)
        print("🎯 策略三：CONTRARIAN 逆向佈局")
        print("   跌深但基本面轉好 - 反彈潛力股")
        print("="*60)
        
        df = self.merged_df.copy()
        
        # 跌深
        cur_dd = self._safe_numeric(df, 'Current_Drawdown', 0)
        deep_drawdown = cur_dd < -25
        
        # 結構轉好
        gpm_inf = df.get('GPM_Inflection', pd.Series([False] * len(df))).fillna(False).astype(bool)
        opm_inf = df.get('OPM_Inflection', pd.Series([False] * len(df))).fillna(False).astype(bool)
        rev_acc = self._safe_numeric(df, 'Rev_Acceleration', 0)
        
        improving = gpm_inf | opm_inf | (rev_acc > 30)
        
        # 品質沒問題
        forensic = self._safe_numeric(df, 'Forensic_Score', 60)
        sloan = self._safe_numeric(df, 'Sloan_Ratio', 0)
        
        quality_ok = (forensic >= 55) & (sloan < 0.12)
        
        # 計算反彈分數
        df['Contrarian_Score'] = 0.0
        
        # 跌深加分 (跌越深反彈空間越大)
        df['Contrarian_Score'] += np.where(cur_dd < -50, 30,
                                  np.where(cur_dd < -40, 25,
                                  np.where(cur_dd < -30, 20,
                                  np.where(cur_dd < -20, 10, 0))))
        
        # 結構改善加分
        df['Contrarian_Score'] += np.where(gpm_inf & opm_inf, 30,
                                  np.where(gpm_inf | opm_inf, 20,
                                  np.where(rev_acc > 50, 15, 0)))
        
        # 品質加分
        df['Contrarian_Score'] += np.where(forensic >= 70, 15,
                                  np.where(forensic >= 60, 10, 0))
        
        # 法人開始買加分
        qfii = self._safe_numeric(df, 'QFII_Net_4W', 0)
        fund = self._safe_numeric(df, 'Fund_Net_4W', 0)
        df['Contrarian_Score'] += np.where((qfii > 0) | (fund > 0), 15, 0)
        
        # 估值便宜加分
        pe_pct = self._safe_numeric(df, 'PE_Percentile', 50)
        df['Contrarian_Score'] += np.where(pe_pct < 30, 10,
                                  np.where(pe_pct < 50, 5, 0))
        
        # 篩選
        contrarian = df[deep_drawdown & improving & quality_ok].copy()
        contrarian = contrarian.sort_values('Contrarian_Score', ascending=False)
        
        def get_contrarian_tag(row):
            tags = []
            dd = row.get('Current_Drawdown', 0)
            if dd < -50:
                tags.append(f"📉跌深{dd:.0f}%")
            elif dd < -30:
                tags.append(f"📉回檔{dd:.0f}%")
            
            if row.get('GPM_Inflection', False) or row.get('OPM_Inflection', False):
                tags.append("🔄結構轉好")
            
            if row.get('QFII_Net_4W', 0) > 0 or row.get('Fund_Net_4W', 0) > 0:
                tags.append("👀法人回補")
            
            return " | ".join(tags) if tags else "反彈潛力"
        
        contrarian['Contrarian_Tag'] = contrarian.apply(get_contrarian_tag, axis=1)
        contrarian['Strategy'] = '🎯 Contrarian'
        
        return contrarian.head(10)
    
    def print_results(self, alpha_df: pd.DataFrame, early_df: pd.DataFrame, contrarian_df: pd.DataFrame):
        """Print formatted results."""
        
        # ========================================
        # Alpha Stocks
        # ========================================
        print("\n")
        print("╔" + "═"*70 + "╗")
        print("║" + " "*20 + "🔥 ALPHA STOCKS 強勢股" + " "*27 + "║")
        print("║" + " "*15 + "真的很強 - 動能+品質+結構三強合一" + " "*18 + "║")
        print("╚" + "═"*70 + "╝")
        
        for i, (_, row) in enumerate(alpha_df.iterrows(), 1):
            ticker = row['Ticker']
            name = row['Company_Name']
            score = row['Alpha_Score']
            mom = row.get('Momentum_12_1', 0)
            ret = row.get('Return_12M', 0)
            tag = row.get('Alpha_Tag', '')
            
            print(f"\n#{i:2d} | {ticker:10s} | {name:10s} | Alpha分數: {score:.0f}")
            print(f"     動能12-1: {mom:+.1f}% | 年報酬: {ret:+.1f}%")
            print(f"     💡 {tag}")
        
        # ========================================
        # Early Bird Stocks
        # ========================================
        print("\n\n")
        print("╔" + "═"*70 + "╗")
        print("║" + " "*20 + "💎 EARLY BIRD 早鳥股" + " "*28 + "║")
        print("║" + " "*12 + "在別人注意到之前先買好 - 低調潛力股" + " "*19 + "║")
        print("╚" + "═"*70 + "╝")
        
        for i, (_, row) in enumerate(early_df.iterrows(), 1):
            ticker = row['Ticker']
            name = row['Company_Name']
            score = row['EarlyBird_Score']
            pe_pct = row.get('PE_Percentile', 0)
            tag = row.get('EarlyBird_Tag', '')
            
            print(f"\n#{i:2d} | {ticker:10s} | {name:10s} | 早鳥分數: {score:.0f}")
            if pd.notna(pe_pct) and pe_pct > 0:
                print(f"     PE百分位: {pe_pct:.0f}% (越低越便宜)")
            print(f"     💡 {tag}")
        
        # ========================================
        # Contrarian Picks
        # ========================================
        print("\n\n")
        print("╔" + "═"*70 + "╗")
        print("║" + " "*18 + "🎯 CONTRARIAN 逆向佈局" + " "*28 + "║")
        print("║" + " "*15 + "跌深但基本面轉好 - 反彈潛力股" + " "*22 + "║")
        print("╚" + "═"*70 + "╝")
        
        for i, (_, row) in enumerate(contrarian_df.iterrows(), 1):
            ticker = row['Ticker']
            name = row['Company_Name']
            score = row['Contrarian_Score']
            dd = row.get('Current_Drawdown', 0)
            tag = row.get('Contrarian_Tag', '')
            
            print(f"\n#{i:2d} | {ticker:10s} | {name:10s} | 反彈分數: {score:.0f}")
            print(f"     當前回檔: {dd:.1f}%")
            print(f"     💡 {tag}")
    
    def create_final_watchlist(self, alpha_df: pd.DataFrame, early_df: pd.DataFrame, 
                                contrarian_df: pd.DataFrame) -> pd.DataFrame:
        """Create a unified watchlist with risk-adjusted recommendations."""
        
        print("\n\n")
        print("╔" + "═"*70 + "╗")
        print("║" + " "*20 + "🎯 最終推薦清單 TOP 20" + " "*27 + "║")
        print("║" + " "*15 + "綜合三大策略的最佳選擇" + " "*28 + "║")
        print("╚" + "═"*70 + "╝")
        
        # 合併並去重
        alpha_top = alpha_df.head(10).copy()
        alpha_top['Final_Score'] = alpha_top['Alpha_Score'] * 1.2  # Alpha股加權
        alpha_top['Recommendation'] = '🔥 強勢追擊'
        
        early_top = early_df.head(8).copy()
        early_top['Final_Score'] = early_top['EarlyBird_Score'] * 1.1
        early_top['Recommendation'] = '💎 早期佈局'
        
        contrarian_top = contrarian_df.head(5).copy()
        contrarian_top['Final_Score'] = contrarian_top['Contrarian_Score'] * 1.0
        contrarian_top['Recommendation'] = '🎯 逆向抄底'
        
        # 合併
        all_picks = pd.concat([alpha_top, early_top, contrarian_top], ignore_index=True)
        
        # 去重 (保留分數最高的)
        all_picks = all_picks.sort_values('Final_Score', ascending=False)
        all_picks = all_picks.drop_duplicates(subset=['Ticker'], keep='first')
        
        # 取前20
        final_20 = all_picks.head(20).copy()
        final_20['Rank'] = range(1, len(final_20) + 1)
        
        # 印出結果
        print("\n")
        for _, row in final_20.iterrows():
            rank = row['Rank']
            ticker = row['Ticker']
            name = row['Company_Name']
            score = row['Final_Score']
            rec = row['Recommendation']
            strategy = row.get('Strategy', '')
            
            # 取得相關標籤
            tag = row.get('Alpha_Tag', '') or row.get('EarlyBird_Tag', '') or row.get('Contrarian_Tag', '')
            
            print(f"#{rank:2d} | {ticker:10s} | {name:10s} | 分數:{score:5.0f} | {rec}")
            print(f"     {tag}")
            print("-" * 72)
        
        return final_20
    
    def save_results(self, final_df: pd.DataFrame, alpha_df: pd.DataFrame, 
                     early_df: pd.DataFrame, contrarian_df: pd.DataFrame):
        """Save all results to CSV files."""
        
        # Save final top 20
        output_cols = ['Rank', 'Ticker', 'Company_Name', 'Final_Score', 'Recommendation', 
                      'Strategy', 'Momentum_12_1', 'Return_12M', 'Current_Drawdown',
                      'PE_Percentile', 'Forensic_Score', 'F_Score', 'QFII_Net_4W', 'Fund_Net_4W']
        output_cols = [c for c in output_cols if c in final_df.columns]
        
        final_path = self.data_dir / 'alpha_hunter_top20.csv'
        final_df[output_cols].to_csv(final_path, index=False, encoding='utf-8-sig')
        print(f"\n💾 最終清單已儲存: {final_path}")
        
        # Save individual strategies
        alpha_path = self.data_dir / 'alpha_stocks.csv'
        alpha_df.to_csv(alpha_path, index=False, encoding='utf-8-sig')
        print(f"💾 Alpha強勢股已儲存: {alpha_path}")
        
        early_path = self.data_dir / 'early_bird_stocks.csv'
        early_df.to_csv(early_path, index=False, encoding='utf-8-sig')
        print(f"💾 早鳥股已儲存: {early_path}")
        
        contrarian_path = self.data_dir / 'contrarian_stocks.csv'
        contrarian_df.to_csv(contrarian_path, index=False, encoding='utf-8-sig')
        print(f"💾 逆向佈局股已儲存: {contrarian_path}")
    
    def run(self):
        """Run the complete alpha hunting process."""
        print("\n")
        print("╔" + "═"*58 + "╗")
        print("║" + " "*15 + "ALPHA HUNTER v1.0" + " "*24 + "║")
        print("║" + " "*18 + "超額報酬獵手" + " "*26 + "║")
        print("╚" + "═"*58 + "╝")
        print(f"\n📅 分析時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Load and merge data
        self.load_all_data()
        self.merge_data()
        
        # Run three strategies
        alpha_stocks = self.find_alpha_stocks()
        early_birds = self.find_early_bird_stocks()
        contrarian = self.find_contrarian_picks()
        
        # Print results
        self.print_results(alpha_stocks, early_birds, contrarian)
        
        # Create final watchlist
        final_20 = self.create_final_watchlist(alpha_stocks, early_birds, contrarian)
        
        # Save results
        self.save_results(final_20, alpha_stocks, early_birds, contrarian)
        
        print("\n✅ 分析完成！")
        print("   🔥 Alpha強勢股 - 追漲策略")
        print("   💎 早鳥股 - 提前佈局")  
        print("   🎯 逆向股 - 抄底策略")
        
        return final_20


def main():
    hunter = AlphaHunter()
    hunter.run()


if __name__ == "__main__":
    main()

