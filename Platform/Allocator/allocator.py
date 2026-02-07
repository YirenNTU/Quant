#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
📊 Allocator - 資產配置生成器
================================================================================

根據策略分數產生當下應該買的股票清單和配置建議。

使用範例:
>>> from Platform.Allocator import get_allocation
>>> 
>>> allocation = get_allocation(
>>>     strategy=MyStrategy(),
>>>     capital=1_000_000,
>>>     max_positions=10,
>>> )
>>> print(allocation)

Author: Investment AI Platform
Version: 1.0
================================================================================
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')


@dataclass
class AllocationResult:
    """資產配置結果"""
    
    strategy_name: str
    date: str
    capital: float
    allocations: pd.DataFrame  # 配置明細
    summary: Dict[str, Any]
    
    def __str__(self) -> str:
        """輸出配置表格"""
        text = f"""
================================================================================
📊 資產配置建議: {self.strategy_name}
================================================================================

📅 日期: {self.date}
💰 可用資金: ${self.capital:,.0f}
📈 持倉數量: {self.summary['n_positions']} 檔

┌{'─'*8}┬{'─'*12}┬{'─'*10}┬{'─'*12}┬{'─'*12}┬{'─'*10}┐
│{'股票':<6}│{'公司名稱':<10}│{'權重(%)':<8}│{'股價':<10}│{'金額':<10}│{'張數':<8}│
├{'─'*8}┼{'─'*12}┼{'─'*10}┼{'─'*12}┼{'─'*12}┼{'─'*10}┤"""
        
        for _, row in self.allocations.iterrows():
            ticker = str(row['ticker'])
            name = str(row.get('name', '-'))[:8]
            weight = row['weight'] * 100
            price = row['price']
            amount = row['amount']
            lots = row['lots']
            
            # 顯示張數（如果是零股則顯示小數）
            lots_display = f"{lots:.2f}" if lots < 1 else f"{lots:.0f}"
            text += f"\n│{ticker:<8}│{name:<12}│{weight:>8.1f}│{price:>10,.0f}│{amount:>10,.0f}│{lots_display:>8}│"
        
        text += f"""
└{'─'*8}┴{'─'*12}┴{'─'*10}┴{'─'*12}┴{'─'*12}┴{'─'*10}┘

💵 總配置金額: ${self.summary['total_allocated']:,.0f}
💰 剩餘現金:   ${self.summary['cash_remaining']:,.0f}
📊 配置比例:   {self.summary['allocation_pct']*100:.1f}%

================================================================================
"""
        return text
    
    def to_csv(self, path: str = None):
        """輸出 CSV"""
        if path is None:
            path = f"allocation_{self.date}.csv"
        self.allocations.to_csv(path, index=False, encoding='utf-8-sig')
        print(f"✅ 已儲存: {path}")


class Allocator:
    """資產配置器"""
    
    @staticmethod
    def get_allocation(
        strategy,
        capital: float = 1_000_000,
        max_positions: int = 10,
        max_weight: float = 0.15,
        min_weight: float = 0.03,
        lot_size: int = 1000,  # 一張 = 1000 股
        min_lots: int = 1,     # 最少買一張
        allow_fractional: bool = False,  # 是否允許零股交易
        db = None,
    ) -> AllocationResult:
        """
        取得資產配置建議
        
        Args:
            strategy: 策略實例
            capital: 可用資金
            max_positions: 最大持倉數
            max_weight: 單一標的最大權重
            min_weight: 單一標的最小權重
            lot_size: 每張股數 (預設 1000)
            min_lots: 最少張數 (預設 1)
            allow_fractional: 是否允許零股交易 (預設 False)
            db: FieldDB 實例
        
        Returns:
            AllocationResult: 配置結果
        """
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        
        from Platform.Core.build_field_database import FieldDB
        
        # 載入資料庫
        if db is None:
            db = FieldDB()
        
        # 執行策略取得分數
        strategy.run(db)
        scores = strategy.get_latest_score()
        
        # 取得最新價格
        close = db.get('close')
        latest_prices = close.iloc[-1]
        latest_date = str(close.index[-1])[:10]
        
        # 載入股票名稱
        ticker_info = db.tickers_info.get('names', {}) if hasattr(db, 'tickers_info') else {}
        
        # 篩選有效股票
        valid_tickers = scores.index.intersection(latest_prices.index)
        scores = scores[valid_tickers]
        prices = latest_prices[valid_tickers]
        
        # 移除無效值
        valid_mask = (~scores.isna()) & (~prices.isna()) & (prices > 0)
        scores = scores[valid_mask]
        prices = prices[valid_mask]
        
        # 排名取 top N
        top_n = min(max_positions, len(scores))
        
        if top_n == 0:
            print("⚠️ 沒有有效的股票分數，請檢查策略的 compute() 方法")
            print("   提示: 確認資料索引對齊，季報資料需要 reindex 到日報日期")
            return AllocationResult(
                strategy_name=strategy.name,
                date=latest_date,
                capital=capital,
                allocations=pd.DataFrame(),
                summary={'n_positions': 0, 'total_allocated': 0, 'cash_remaining': capital, 'allocation_pct': 0},
            )
        
        # 🆕 先對所有有效分數進行標準化（Z-score）
        score_mean = scores.mean()
        score_std = scores.std()
        if score_std > 0:
            standardized_scores = (scores - score_mean) / score_std
        else:
            standardized_scores = scores
        
        # 然後取 top N（使用標準化後的分數）
        top_scores_standardized = standardized_scores.nlargest(top_n)
        
        # 保存原始分數用於顯示（使用相同的 ticker index）
        top_scores_original = scores[top_scores_standardized.index]
        
        # 計算權重（使用標準化後的分數進行 min-max 正規化）
        score_min = top_scores_standardized.min()
        score_range = top_scores_standardized.max() - score_min
        if score_range > 0:
            weights = (top_scores_standardized - score_min) / score_range
        else:
            weights = pd.Series(1.0, index=top_scores_standardized.index)
        
        # 正規化
        weight_sum = weights.sum()
        if weight_sum > 0:
            weights = weights / weight_sum
        else:
            weights = pd.Series(1.0 / len(weights), index=weights.index)
        
        # 如果有太多股票權重過低，先篩選
        weights = weights[weights >= min_weight / 2]
        if len(weights) == 0:
            if len(top_scores_standardized) > 0:
                weights = pd.Series(1.0 / len(top_scores_standardized), index=top_scores_standardized.index)
            else:
                print("⚠️ 無法計算權重")
                return AllocationResult(
                    strategy_name=strategy.name,
                    date=latest_date,
                    capital=capital,
                    allocations=pd.DataFrame(),
                    summary={'n_positions': 0, 'total_allocated': 0, 'cash_remaining': capital, 'allocation_pct': 0},
                )
        
        # 限制權重範圍
        weights = weights.clip(lower=min_weight, upper=max_weight)
        weights = weights / weights.sum()
        
        # 計算配置
        allocations = []
        total_allocated = 0
        
        for ticker in weights.index:
            weight = weights[ticker]
            price = prices[ticker]
            target_amount = capital * weight
            
            if allow_fractional:
                # 🆕 允許零股：直接計算股數，不取整到整張
                shares = target_amount / price
                shares = max(shares, 0)  # 至少 0 股
                
                # 如果權重夠高但股數太少，至少買 1 股
                if shares < 1 and weight >= min_weight:
                    shares = 1
                
                if shares > 0:
                    actual_amount = shares * price
                    lots = shares / lot_size  # 換算成張數（可能小於 1）
                    
                    if total_allocated + actual_amount <= capital:
                        total_allocated += actual_amount
                        
                        allocations.append({
                            'ticker': ticker,
                            'name': ticker_info.get(ticker, '-'),
                            'score': top_scores_original[ticker],  # 使用原始分數顯示
                            'weight': actual_amount / capital,
                            'price': price,
                            'lots': lots,  # 可能是小數（如 0.5 張）
                            'shares': shares,  # 實際股數（可能是零股）
                            'amount': actual_amount,
                        })
            else:
                # 原有邏輯：只買整張
                # 計算張數 (取整)
                lots = int(target_amount / (price * lot_size))
                lots = max(lots, 0)  # 至少 0 張
                
                # 如果張數不足最小張數但權重夠高，至少買一張
                if lots == 0 and weight >= min_weight and (price * lot_size) <= target_amount * 1.5:
                    lots = min_lots
                
                if lots > 0:
                    shares = lots * lot_size
                    actual_amount = shares * price
                    
                    if total_allocated + actual_amount <= capital:
                        total_allocated += actual_amount
                        
                        allocations.append({
                            'ticker': ticker,
                            'name': ticker_info.get(ticker, '-'),
                            'score': top_scores_original[ticker],  # 使用原始分數顯示
                            'weight': actual_amount / capital,
                            'price': price,
                            'lots': lots,
                            'shares': shares,
                            'amount': actual_amount,
                        })
        
        # 建立 DataFrame
        alloc_df = pd.DataFrame(allocations)
        if len(alloc_df) > 0:
            alloc_df = alloc_df.sort_values('weight', ascending=False)
        
        # 摘要
        summary = {
            'n_positions': len(alloc_df),
            'total_allocated': total_allocated,
            'cash_remaining': capital - total_allocated,
            'allocation_pct': total_allocated / capital if capital > 0 else 0,
        }
        
        return AllocationResult(
            strategy_name=strategy.name,
            date=latest_date,
            capital=capital,
            allocations=alloc_df,
            summary=summary,
        )


def get_allocation(strategy, **kwargs) -> AllocationResult:
    """取得資產配置 (便利函數)"""
    return Allocator.get_allocation(strategy, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# 匯出
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = ['Allocator', 'AllocationResult', 'get_allocation']


# ═══════════════════════════════════════════════════════════════════════════════
# 測試
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    from Platform.Strategies.base import Strategy
    from Platform.Core.build_field_database import FieldDB
    from Platform.Factors import *
    
    # 定義測試策略
    class MomentumStrategy(Strategy):
        name = "動量策略"
        description = "買入過去20天漲幅最大的股票"
        params = {"lookback": 20}
        
        def compute(self, db):
            close = db.get('close')
            momentum = ts_pct_change(close, self.params["lookback"])
            return zscore(momentum)
    
    print("=" * 70)
    print("📊 Allocator 資產配置器測試")
    print("=" * 70)
    
    # 取得配置
    strategy = MomentumStrategy()
    allocation = get_allocation(
        strategy=strategy,
        capital=1_000_000,
        max_positions=10,
    )
    
    print(allocation)
