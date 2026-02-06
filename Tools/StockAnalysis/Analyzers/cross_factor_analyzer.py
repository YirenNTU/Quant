#!/usr/bin/env python3
"""
Cross-Factor Analyzer v1.0
==========================
Comprehensive cross-analysis across 9 factor reports to identify top investment opportunities.

Strategy Profile: "Aggressive with Defense"
- Higher risk tolerance for better payoff
- Defensive guardrails to avoid value traps and financial fraud
- Emphasis on momentum + quality + structural improvement

Author: Investment AI System
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


class CrossFactorAnalyzer:
    """Cross-analyze multiple factor reports to find optimal investment candidates."""
    
    def __init__(self, data_dir: str = None):
        """Initialize the analyzer with data directory."""
        if data_dir is None:
            # 從 Analyzers/cross_factor_analyzer.py 往上4層到達專案根目錄
            self.data_dir = Path(__file__).parent.parent.parent.parent / "Stock_Pool"
        else:
            self.data_dir = Path(data_dir)
        
        # File mappings
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
        """Load all 9 CSV files into memory."""
        print("=" * 60)
        print("📊 Loading all factor reports...")
        print("=" * 60)
        
        for key, filename in self.file_map.items():
            filepath = self.data_dir / filename
            if filepath.exists():
                df = pd.read_csv(filepath)
                self.data[key] = df
                print(f"  ✅ {key}: {len(df)} records from {filename}")
            else:
                print(f"  ⚠️ {key}: File not found - {filename}")
                self.data[key] = pd.DataFrame()
        
        print()
        return self.data
    
    def _safe_numeric(self, df: pd.DataFrame, col: str, default: float = 0) -> pd.Series:
        """Safely convert column to numeric."""
        if col not in df.columns:
            return pd.Series([default] * len(df), index=df.index)
        return pd.to_numeric(df[col], errors='coerce').fillna(default)
    
    def merge_all_data(self) -> pd.DataFrame:
        """Merge all datasets on Ticker for cross-analysis."""
        print("🔗 Merging datasets for cross-analysis...")
        
        # Start with factor analysis as base (most comprehensive)
        if self.data['factor'].empty:
            print("  ❌ Error: Factor analysis data is empty!")
            return pd.DataFrame()
        
        base = self.data['factor'][['Ticker', 'Company_Name', 'Composite_Score', 'Rating',
                                     'FCF_Yield', 'Momentum_12_1', 'Return_12M', 'Return_1M',
                                     'Momentum_Status', 'Stability_Score', 'Asset_Growth',
                                     'Max_Drawdown', 'Current_Drawdown', 'Margin_Score',
                                     'Margin_Sentiment']].copy()
        
        # Merge health check data
        if not self.data['health'].empty:
            health_cols = ['Ticker', 'Health_Score', 'CCR_TTM', 'FCF_Status', 
                          'Sloan_Ratio', 'Sloan_Status', 'Inv_Risk', 'Health_Rating']
            health_cols = [c for c in health_cols if c in self.data['health'].columns]
            base = base.merge(self.data['health'][health_cols], on='Ticker', how='left', suffixes=('', '_health'))
        
        # Merge valuation data
        if not self.data['valuation'].empty:
            val_cols = ['Ticker', 'Current_Price', 'Decision', 'Market_Regime',
                       'RS_Ratio', 'RS_Status', 'PE', 'PE_Percentile', 'PB', 'PB_Percentile']
            val_cols = [c for c in val_cols if c in self.data['valuation'].columns]
            base = base.merge(self.data['valuation'][val_cols], on='Ticker', how='left', suffixes=('', '_val'))
        
        # Merge structural change data
        if not self.data['structural'].empty:
            struct_cols = ['Ticker', 'Score', 'Result_Tag', 'Latest_GPM', 'GPM_Inflection',
                          'Latest_OPM', 'OPM_Inflection', 'Operating_Leverage', 
                          'Rev_YoY', 'Rev_Acceleration', 'Rev_New_High']
            struct_cols = [c for c in struct_cols if c in self.data['structural'].columns]
            base = base.merge(self.data['structural'][struct_cols], on='Ticker', how='left', suffixes=('', '_struct'))
        
        # Merge institutional forensic data
        if not self.data['inst_forensic'].empty:
            forensic_cols = ['Ticker', 'Forensic_Score', 'Forensic_Verdict', 'F_Score', 
                            'Hollow_Ratio', 'ROIC', 'Quality_Warning']
            forensic_cols = [c for c in forensic_cols if c in self.data['inst_forensic'].columns]
            base = base.merge(self.data['inst_forensic'][forensic_cols], on='Ticker', how='left', suffixes=('', '_forensic'))
        
        # Merge hidden gems data (for chip flow info)
        if not self.data['hidden_gems'].empty:
            gem_cols = ['Ticker', 'Gem_Score', 'Gem_Type', 'Rev_Acc', 'Chip_Trend',
                       'QFII_Net_4W', 'Fund_Net_4W', 'RS', 'PSR', 'PSR_Percentile']
            gem_cols = [c for c in gem_cols if c in self.data['hidden_gems'].columns]
            base = base.merge(self.data['hidden_gems'][gem_cols], on='Ticker', how='left', suffixes=('', '_gem'))
        
        self.merged_df = base
        print(f"  ✅ Merged dataset: {len(base)} stocks with {len(base.columns)} factors")
        print()
        
        return self.merged_df
    
    def calculate_cross_scores(self) -> pd.DataFrame:
        """Calculate cross-factor composite scores with aggressive-defensive balance."""
        print("📈 Calculating cross-factor scores...")
        print("   Strategy: Aggressive with Defense")
        print()
        
        df = self.merged_df.copy()
        
        # ========================================
        # 1. MOMENTUM SCORE (30% weight) - Aggressive
        # ========================================
        momentum_score = pd.Series(0.0, index=df.index)
        
        # 12-1 Momentum (higher is better)
        mom_12_1 = self._safe_numeric(df, 'Momentum_12_1', 0)
        momentum_score += np.where(mom_12_1 > 50, 30,
                          np.where(mom_12_1 > 30, 25,
                          np.where(mom_12_1 > 15, 20,
                          np.where(mom_12_1 > 5, 15,
                          np.where(mom_12_1 > 0, 10, 0)))))
        
        # RS Ratio (relative strength)
        rs_ratio = self._safe_numeric(df, 'RS_Ratio', 1.0)
        momentum_score += np.where(rs_ratio > 1.5, 20,
                          np.where(rs_ratio > 1.2, 15,
                          np.where(rs_ratio > 1.0, 10,
                          np.where(rs_ratio > 0.8, 5, 0))))
        
        # Return 12M bonus
        ret_12m = self._safe_numeric(df, 'Return_12M', 0)
        momentum_score += np.where(ret_12m > 100, 15,
                          np.where(ret_12m > 50, 12,
                          np.where(ret_12m > 30, 10,
                          np.where(ret_12m > 15, 7, 0))))
        
        # Recent momentum (Return 1M)
        ret_1m = self._safe_numeric(df, 'Return_1M', 0)
        momentum_score += np.where(ret_1m > 20, 10,
                          np.where(ret_1m > 10, 8,
                          np.where(ret_1m > 5, 5,
                          np.where(ret_1m > 0, 3, 0))))
        
        # Normalize to 0-100
        momentum_score = (momentum_score / momentum_score.max() * 100).fillna(0)
        
        # ========================================
        # 2. QUALITY SCORE (25% weight) - Defensive
        # ========================================
        quality_score = pd.Series(50.0, index=df.index)  # Base score
        
        # Forensic Score (higher is better)
        forensic = self._safe_numeric(df, 'Forensic_Score', 60)
        quality_score += np.where(forensic >= 80, 20,
                         np.where(forensic >= 70, 15,
                         np.where(forensic >= 60, 10,
                         np.where(forensic >= 50, 0, -20))))
        
        # F-Score (Piotroski)
        f_score = self._safe_numeric(df, 'F_Score', 5)
        quality_score += np.where(f_score >= 8, 15,
                         np.where(f_score >= 7, 10,
                         np.where(f_score >= 6, 5,
                         np.where(f_score >= 5, 0, -10))))
        
        # Sloan Ratio (lower is better - accruals quality)
        sloan = self._safe_numeric(df, 'Sloan_Ratio', 0)
        quality_score += np.where(sloan < -0.05, 15,  # Very good cash flow
                         np.where(sloan < 0, 10,
                         np.where(sloan < 0.05, 5,
                         np.where(sloan < 0.1, 0, -15))))
        
        # ROIC bonus
        roic = self._safe_numeric(df, 'ROIC', 0)
        quality_score += np.where(roic > 15, 10,
                         np.where(roic > 10, 7,
                         np.where(roic > 5, 5, 0)))
        
        # Hollow Ratio penalty (high = earnings from non-operating)
        hollow = self._safe_numeric(df, 'Hollow_Ratio', 0)
        quality_score += np.where(hollow > 50, -15,
                         np.where(hollow > 30, -10,
                         np.where(hollow > 20, -5, 0)))
        
        # Normalize to 0-100
        quality_score = quality_score.clip(0, 100)
        
        # ========================================
        # 3. STRUCTURAL CHANGE SCORE (20% weight) - Growth
        # ========================================
        structural_score = pd.Series(30.0, index=df.index)  # Base score
        
        # GPM Inflection point
        gpm_inflection = df.get('GPM_Inflection', pd.Series([False] * len(df)))
        gpm_inflection = gpm_inflection.fillna(False).astype(bool)
        structural_score += np.where(gpm_inflection, 20, 0)
        
        # OPM Inflection point
        opm_inflection = df.get('OPM_Inflection', pd.Series([False] * len(df)))
        opm_inflection = opm_inflection.fillna(False).astype(bool)
        structural_score += np.where(opm_inflection, 15, 0)
        
        # Revenue Acceleration
        rev_acc = self._safe_numeric(df, 'Rev_Acceleration', 0)
        structural_score += np.where(rev_acc > 100, 15,
                            np.where(rev_acc > 50, 12,
                            np.where(rev_acc > 20, 8,
                            np.where(rev_acc > 0, 5, 0))))
        
        # Revenue New High
        rev_high = df.get('Rev_New_High', pd.Series([False] * len(df)))
        rev_high = rev_high.fillna(False).astype(bool)
        structural_score += np.where(rev_high, 10, 0)
        
        # Operating Leverage (positive = good)
        ol = self._safe_numeric(df, 'Operating_Leverage', 0)
        structural_score += np.where(ol > 0.5, 10,
                            np.where(ol > 0.2, 7,
                            np.where(ol > 0, 5, 0)))
        
        # Normalize to 0-100
        structural_score = (structural_score / structural_score.max() * 100).fillna(0)
        
        # ========================================
        # 4. VALUATION SCORE (15% weight) - Value
        # ========================================
        valuation_score = pd.Series(50.0, index=df.index)  # Base
        
        # PE Percentile (lower = cheaper)
        pe_pct = self._safe_numeric(df, 'PE_Percentile', 50)
        valuation_score += np.where(pe_pct < 20, 20,
                           np.where(pe_pct < 35, 15,
                           np.where(pe_pct < 50, 10,
                           np.where(pe_pct < 70, 5,
                           np.where(pe_pct < 85, 0, -10)))))
        
        # PB Percentile
        pb_pct = self._safe_numeric(df, 'PB_Percentile', 50)
        valuation_score += np.where(pb_pct < 20, 15,
                           np.where(pb_pct < 35, 10,
                           np.where(pb_pct < 50, 7,
                           np.where(pb_pct < 70, 3, 0))))
        
        # PSR Percentile (if available)
        psr_pct = self._safe_numeric(df, 'PSR_Percentile', 50)
        valuation_score += np.where(psr_pct < 30, 10,
                           np.where(psr_pct < 50, 7,
                           np.where(psr_pct < 70, 3, 0)))
        
        # Normalize to 0-100
        valuation_score = valuation_score.clip(0, 100)
        
        # ========================================
        # 5. CHIP/SENTIMENT SCORE (10% weight)
        # ========================================
        chip_score = pd.Series(50.0, index=df.index)
        
        # QFII Net buying
        qfii = self._safe_numeric(df, 'QFII_Net_4W', 0)
        chip_score += np.where(qfii > 10000, 15,
                     np.where(qfii > 5000, 12,
                     np.where(qfii > 1000, 8,
                     np.where(qfii > 0, 5,
                     np.where(qfii < -5000, -10, 0)))))
        
        # Fund Net buying
        fund = self._safe_numeric(df, 'Fund_Net_4W', 0)
        chip_score += np.where(fund > 5000, 12,
                     np.where(fund > 2000, 10,
                     np.where(fund > 500, 7,
                     np.where(fund > 0, 4, 0))))
        
        # Margin Score (existing)
        margin = self._safe_numeric(df, 'Margin_Score', 50)
        chip_score += np.where(margin >= 70, 10,
                     np.where(margin >= 60, 7,
                     np.where(margin >= 50, 5, 0)))
        
        # Normalize
        chip_score = chip_score.clip(0, 100)
        
        # ========================================
        # 6. RISK SCORE (Penalty) - Defensive
        # ========================================
        risk_penalty = pd.Series(0.0, index=df.index)
        
        # Max Drawdown penalty
        mdd = self._safe_numeric(df, 'Max_Drawdown', -30)
        risk_penalty += np.where(mdd < -60, -15,
                        np.where(mdd < -50, -10,
                        np.where(mdd < -40, -5, 0)))
        
        # Current Drawdown penalty (if in deep drawdown)
        cur_dd = self._safe_numeric(df, 'Current_Drawdown', 0)
        risk_penalty += np.where(cur_dd < -50, -15,
                        np.where(cur_dd < -40, -10,
                        np.where(cur_dd < -30, -5, 0)))
        
        # Quality Warning penalty
        quality_warn = df.get('Quality_Warning', pd.Series([False] * len(df)))
        quality_warn = quality_warn.fillna(False).astype(bool)
        risk_penalty += np.where(quality_warn, -10, 0)
        
        # ========================================
        # FINAL COMPOSITE SCORE
        # ========================================
        # Weights: Momentum 30%, Quality 25%, Structural 20%, Valuation 15%, Chip 10%
        df['Momentum_Cross_Score'] = momentum_score
        df['Quality_Cross_Score'] = quality_score
        df['Structural_Cross_Score'] = structural_score
        df['Valuation_Cross_Score'] = valuation_score
        df['Chip_Cross_Score'] = chip_score
        df['Risk_Penalty'] = risk_penalty
        
        df['Cross_Composite_Score'] = (
            momentum_score * 0.30 +
            quality_score * 0.25 +
            structural_score * 0.20 +
            valuation_score * 0.15 +
            chip_score * 0.10 +
            risk_penalty
        )
        
        # ========================================
        # BONUS: Hidden Gems Multiplier
        # ========================================
        gem_score = self._safe_numeric(df, 'Gem_Score', 0)
        df['Hidden_Gem_Bonus'] = np.where(gem_score >= 100, 10,
                                 np.where(gem_score >= 80, 7,
                                 np.where(gem_score >= 60, 5, 0)))
        
        df['Cross_Composite_Score'] += df['Hidden_Gem_Bonus']
        
        self.merged_df = df
        print(f"  ✅ Calculated composite scores for {len(df)} stocks")
        print()
        
        return df
    
    def apply_defensive_filters(self) -> pd.DataFrame:
        """Apply defensive filters to avoid value traps and fraud."""
        print("🛡️ Applying defensive filters...")
        
        df = self.merged_df.copy()
        initial_count = len(df)
        
        # Filter 1: Remove stocks with very low composite score (data issues)
        composite = self._safe_numeric(df, 'Composite_Score', 0)
        df = df[composite > 20]
        print(f"  📋 After data quality filter: {len(df)} stocks")
        
        # Filter 2: Remove extreme forensic red flags (but be lenient for aggressive stance)
        forensic = self._safe_numeric(df, 'Forensic_Score', 60)
        df = df[forensic >= 40]  # Only remove severe cases
        print(f"  📋 After forensic filter: {len(df)} stocks")
        
        # Filter 3: Remove extremely poor Sloan ratio (earnings manipulation)
        sloan = self._safe_numeric(df, 'Sloan_Ratio', 0)
        df = df[sloan < 0.25]  # Very lenient
        print(f"  📋 After accruals filter: {len(df)} stocks")
        
        print(f"  ✅ Defensive filters: {initial_count} → {len(df)} stocks")
        print()
        
        self.merged_df = df
        return df
    
    def generate_top_picks(self, top_n: int = 20) -> pd.DataFrame:
        """Generate top N stock picks with detailed analysis."""
        print(f"🏆 Generating Top {top_n} Stock Picks...")
        print("=" * 60)
        
        df = self.merged_df.copy()
        
        # Sort by Cross Composite Score
        df = df.sort_values('Cross_Composite_Score', ascending=False)
        
        # Select top N
        top_picks = df.head(top_n).copy()
        
        # Add ranking
        top_picks['Rank'] = range(1, len(top_picks) + 1)
        
        # Create investment thesis
        def create_thesis(row):
            thesis_parts = []
            
            # Momentum thesis
            mom = row.get('Momentum_12_1', 0)
            if pd.notna(mom) and mom > 30:
                thesis_parts.append("🚀強勢動能")
            elif pd.notna(mom) and mom > 15:
                thesis_parts.append("📈正向動能")
            
            # Structural thesis
            gpm_inf = row.get('GPM_Inflection', False)
            opm_inf = row.get('OPM_Inflection', False)
            if gpm_inf and opm_inf:
                thesis_parts.append("💎雙拐點")
            elif gpm_inf or opm_inf:
                thesis_parts.append("🔄結構改善")
            
            # Chip thesis
            qfii = row.get('QFII_Net_4W', 0)
            fund = row.get('Fund_Net_4W', 0)
            if pd.notna(qfii) and qfii > 5000 and pd.notna(fund) and fund > 0:
                thesis_parts.append("🔥外資+投信買超")
            elif pd.notna(qfii) and qfii > 5000:
                thesis_parts.append("📊外資買超")
            
            # Quality thesis
            f_score = row.get('F_Score', 0)
            if pd.notna(f_score) and f_score >= 8:
                thesis_parts.append("✅高F-Score")
            
            # Gem thesis
            gem_score = row.get('Gem_Score', 0)
            if pd.notna(gem_score) and gem_score >= 100:
                thesis_parts.append("💎隱藏寶石")
            
            return " | ".join(thesis_parts) if thesis_parts else "基本面穩健"
        
        top_picks['Investment_Thesis'] = top_picks.apply(create_thesis, axis=1)
        
        # Determine risk level
        def assess_risk(row):
            mdd = row.get('Max_Drawdown', -30)
            sloan = row.get('Sloan_Ratio', 0)
            forensic = row.get('Forensic_Score', 60)
            
            risk_score = 0
            if pd.notna(mdd) and mdd < -50:
                risk_score += 2
            if pd.notna(sloan) and sloan > 0.1:
                risk_score += 1
            if pd.notna(forensic) and forensic < 60:
                risk_score += 1
            
            if risk_score >= 3:
                return "⚠️ 高風險"
            elif risk_score >= 2:
                return "⚡ 中高風險"
            elif risk_score >= 1:
                return "📊 中等風險"
            else:
                return "✅ 低風險"
        
        top_picks['Risk_Level'] = top_picks.apply(assess_risk, axis=1)
        
        return top_picks
    
    def print_results(self, top_picks: pd.DataFrame):
        """Print formatted results."""
        print()
        print("=" * 80)
        print("🎯 TOP 20 CROSS-FACTOR STOCK PICKS")
        print("   Strategy: Aggressive with Defense | Higher Risk Tolerance for Better Payoff")
        print("=" * 80)
        print()
        
        for _, row in top_picks.iterrows():
            rank = row['Rank']
            ticker = row['Ticker']
            name = row['Company_Name']
            score = row['Cross_Composite_Score']
            rating = row.get('Rating', 'N/A')
            thesis = row['Investment_Thesis']
            risk = row['Risk_Level']
            
            # Component scores
            mom_score = row.get('Momentum_Cross_Score', 0)
            qual_score = row.get('Quality_Cross_Score', 0)
            struct_score = row.get('Structural_Cross_Score', 0)
            val_score = row.get('Valuation_Cross_Score', 0)
            
            print(f"#{rank:2d} | {ticker:10s} | {name:12s} | 綜合分數: {score:.1f}")
            print(f"     📊 動能:{mom_score:.0f} | 品質:{qual_score:.0f} | 結構:{struct_score:.0f} | 估值:{val_score:.0f}")
            print(f"     💡 {thesis}")
            print(f"     {risk} | 原始評級: {rating}")
            print("-" * 80)
        
        print()
    
    def save_results(self, top_picks: pd.DataFrame, output_dir: str = None):
        """Save results to CSV."""
        if output_dir is None:
            output_dir = self.data_dir
        
        output_path = Path(output_dir) / 'cross_factor_top20.csv'
        
        # Select columns for output
        output_cols = [
            'Rank', 'Ticker', 'Company_Name', 'Cross_Composite_Score',
            'Momentum_Cross_Score', 'Quality_Cross_Score', 'Structural_Cross_Score',
            'Valuation_Cross_Score', 'Chip_Cross_Score', 'Risk_Penalty',
            'Investment_Thesis', 'Risk_Level',
            'Rating', 'Momentum_12_1', 'Return_12M', 'RS_Ratio',
            'Forensic_Score', 'F_Score', 'Sloan_Ratio', 'ROIC',
            'PE_Percentile', 'PB_Percentile', 'Max_Drawdown', 'Current_Drawdown',
            'Gem_Score', 'QFII_Net_4W', 'Fund_Net_4W'
        ]
        
        # Only include columns that exist
        output_cols = [c for c in output_cols if c in top_picks.columns]
        
        top_picks[output_cols].to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"💾 Results saved to: {output_path}")
        
        # Also save full merged data
        full_output_path = Path(output_dir) / 'cross_factor_full_analysis.csv'
        self.merged_df.to_csv(full_output_path, index=False, encoding='utf-8-sig')
        print(f"💾 Full analysis saved to: {full_output_path}")
        
        return output_path
    
    def generate_summary_stats(self, top_picks: pd.DataFrame):
        """Generate summary statistics for the top picks."""
        print()
        print("=" * 60)
        print("📊 SUMMARY STATISTICS")
        print("=" * 60)
        
        # Risk distribution
        risk_dist = top_picks['Risk_Level'].value_counts()
        print("\n🎯 Risk Distribution:")
        for risk, count in risk_dist.items():
            print(f"   {risk}: {count} stocks")
        
        # Sector-like analysis (based on original rating)
        if 'Rating' in top_picks.columns:
            rating_dist = top_picks['Rating'].value_counts()
            print("\n📈 Original Rating Distribution:")
            for rating, count in rating_dist.items():
                if pd.notna(rating):
                    print(f"   {rating}: {count} stocks")
        
        # Average scores
        print("\n📊 Average Component Scores:")
        print(f"   Momentum Score:   {top_picks['Momentum_Cross_Score'].mean():.1f}")
        print(f"   Quality Score:    {top_picks['Quality_Cross_Score'].mean():.1f}")
        print(f"   Structural Score: {top_picks['Structural_Cross_Score'].mean():.1f}")
        print(f"   Valuation Score:  {top_picks['Valuation_Cross_Score'].mean():.1f}")
        print(f"   Composite Score:  {top_picks['Cross_Composite_Score'].mean():.1f}")
        
        # Key highlights
        print("\n🌟 Key Highlights:")
        
        # Highest momentum
        if 'Momentum_12_1' in top_picks.columns:
            best_mom = top_picks.nlargest(3, 'Momentum_12_1')[['Ticker', 'Company_Name', 'Momentum_12_1']]
            print("\n   Top Momentum:")
            for _, r in best_mom.iterrows():
                print(f"     {r['Ticker']} ({r['Company_Name']}): {r['Momentum_12_1']:.1f}%")
        
        # Best quality
        if 'Forensic_Score' in top_picks.columns:
            best_qual = top_picks.nlargest(3, 'Forensic_Score')[['Ticker', 'Company_Name', 'Forensic_Score']]
            print("\n   Top Quality (Forensic):")
            for _, r in best_qual.iterrows():
                if pd.notna(r['Forensic_Score']):
                    print(f"     {r['Ticker']} ({r['Company_Name']}): {r['Forensic_Score']:.0f}")
        
        # Hidden gems
        if 'Gem_Score' in top_picks.columns:
            gems = top_picks[top_picks['Gem_Score'] >= 80][['Ticker', 'Company_Name', 'Gem_Score']]
            if len(gems) > 0:
                print("\n   💎 Hidden Gems Included:")
                for _, r in gems.iterrows():
                    print(f"     {r['Ticker']} ({r['Company_Name']}): Gem Score {r['Gem_Score']:.0f}")
        
        print()
    
    def run_full_analysis(self, top_n: int = 20):
        """Run the complete cross-factor analysis pipeline."""
        print()
        print("╔" + "═" * 58 + "╗")
        print("║" + " " * 15 + "CROSS-FACTOR ANALYZER v1.0" + " " * 17 + "║")
        print("║" + " " * 10 + "Aggressive with Defense Strategy" + " " * 15 + "║")
        print("╚" + "═" * 58 + "╝")
        print()
        print(f"📅 Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Step 1: Load data
        self.load_all_data()
        
        # Step 2: Merge data
        self.merge_all_data()
        
        if self.merged_df is None or len(self.merged_df) == 0:
            print("❌ Error: No data to analyze!")
            return None
        
        # Step 3: Calculate cross-factor scores
        self.calculate_cross_scores()
        
        # Step 4: Apply defensive filters
        self.apply_defensive_filters()
        
        # Step 5: Generate top picks
        top_picks = self.generate_top_picks(top_n)
        
        # Step 6: Print results
        self.print_results(top_picks)
        
        # Step 7: Summary stats
        self.generate_summary_stats(top_picks)
        
        # Step 8: Save results
        self.save_results(top_picks)
        
        return top_picks


def main():
    """Main entry point."""
    analyzer = CrossFactorAnalyzer()
    top_picks = analyzer.run_full_analysis(top_n=20)
    
    if top_picks is not None:
        print()
        print("✅ Analysis complete!")
        print("   Check 'cross_factor_top20.csv' for detailed results.")
        print()


if __name__ == "__main__":
    main()

