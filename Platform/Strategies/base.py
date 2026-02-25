#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
📊 Strategy Base - 策略基礎類別
================================================================================

所有策略都必須繼承此類別，並實作 compute() 方法。

使用範例:
>>> from Platform.Strategies import Strategy
>>> from Platform.Factors import *
>>> 
>>> class MyStrategy(Strategy):
>>>     name = "動量策略"
>>>     params = {"lookback": 20, "top_n": 10}
>>>     
>>>     def compute(self, db):
>>>         close = db.get('close')
>>>         return zscore(ts_pct_change(close, self.params["lookback"]))

Author: Investment AI Platform
Version: 1.0
================================================================================
"""

import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import json
import warnings
warnings.filterwarnings('ignore')


class Strategy(ABC):
    """
    策略基礎類別
    
    所有自訂策略都必須繼承此類別並實作 compute() 方法。
    """
    
    # ═══════════════════════════════════════════════════════════════════════
    # 策略元資料 (子類別應覆寫)
    # ═══════════════════════════════════════════════════════════════════════
    
    name: str = "Unnamed Strategy"
    description: str = ""
    version: str = "1.0"
    author: str = "Anonymous"
    
    # 策略參數
    params: Dict[str, Any] = {}
    
    # 預設設定
    default_config = {
        "rebalance_freq": "weekly",      # daily, weekly, monthly
        "top_n": 10,                      # 持有股票數
        "max_weight": 0.15,               # 單一標的最大權重
        "equal_weight": True,            # True=等權重, False=按分數比例
        "transaction_cost": 0.001425,     # 手續費率
        "tax": 0.003,                     # 證交稅
        "slippage": 0.001,               # 滑價
    }
    
    # ═══════════════════════════════════════════════════════════════════════
    # 初始化
    # ═══════════════════════════════════════════════════════════════════════
    
    def __init__(self, **kwargs):
        """
        初始化策略
        
        Args:
            **kwargs: 覆寫預設參數
        """
        # 合併參數
        self.config = {**self.default_config, **kwargs}
        self.params = {**self.__class__.params, **kwargs.get('params', {})}
        
        # 狀態
        self._score: Optional[pd.DataFrame] = None
        self._signals: Optional[pd.DataFrame] = None
        self._db = None
        self._computed = False
    
    # ═══════════════════════════════════════════════════════════════════════
    # 核心方法 (必須實作)
    # ═══════════════════════════════════════════════════════════════════════
    
    @abstractmethod
    def compute(self, db) -> pd.DataFrame:
        """
        計算因子分數 (必須實作)
        
        Args:
            db: FieldDB 資料庫實例
        
        Returns:
            pd.DataFrame: 因子分數 (rows=日期, cols=股票)
                          分數越高表示越看好
        
        Example:
            def compute(self, db):
                close = db.get('close')
                return zscore(ts_pct_change(close, 20))
        """
        pass
    
    # ═══════════════════════════════════════════════════════════════════════
    # 選擇性覆寫方法
    # ═══════════════════════════════════════════════════════════════════════
    
    def filter_universe(self, db) -> pd.DataFrame:
        """
        篩選投資範圍 (選擇性覆寫)
        
        返回一個布林 DataFrame，True 表示該股票可投資
        
        Args:
            db: FieldDB 資料庫實例
        
        Returns:
            pd.DataFrame: 布林遮罩 (rows=日期, cols=股票)
        
        Example:
            def filter_universe(self, db):
                # 排除成交量過低的股票
                volume = db.get('volume')
                return volume > volume.quantile(0.1, axis=1)
        """
        # 預設: 所有股票都可投資
        close = db.get('close')
        return close.notna()
    
    def get_weights(self, score: pd.DataFrame) -> pd.DataFrame:
        """
        計算投資組合權重 (選擇性覆寫)
        
        equal_weight=True  → 等權重 (1/n)
        equal_weight=False → 按分數比例分配
        
        Args:
            score: 因子分數 DataFrame
        
        Returns:
            pd.DataFrame: 權重 (rows=日期, cols=股票)
        """
        top_n = self.config.get('top_n', 10)
        max_weight = self.config.get('max_weight', 0.15)
        equal_weight = self.config.get('equal_weight', True)
        
        ranks = score.rank(axis=1, ascending=False)
        selected = ranks <= top_n
        
        if equal_weight:
            weights = selected.astype(float)
        else:
            masked_score = score.where(selected, 0.0)
            row_min = masked_score.where(selected).min(axis=1)
            row_max = masked_score.where(selected).max(axis=1)
            row_range = (row_max - row_min).replace(0, 1)
            
            weights = masked_score.sub(row_min, axis=0).div(row_range, axis=0)
            weights = weights.where(selected, 0.0)
        
        # 正規化使權重總和 = 1
        row_sums = weights.sum(axis=1)
        weights = weights.div(row_sums.replace(0, 1), axis=0)
        
        # 限制最大權重
        weights = weights.clip(upper=max_weight)
        
        # 重新正規化
        row_sums = weights.sum(axis=1)
        weights = weights.div(row_sums.replace(0, 1), axis=0)
        
        return weights
    
    # ═══════════════════════════════════════════════════════════════════════
    # 執行方法
    # ═══════════════════════════════════════════════════════════════════════
    
    def run(self, db, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        執行策略計算
        
        Args:
            db: FieldDB 資料庫實例
            start_date: 開始日期 (可選)
            end_date: 結束日期 (可選)
        
        Returns:
            pd.DataFrame: 投資組合權重
        """
        self._db = db
        
        # 計算因子分數
        score = self.compute(db)
        
        # 篩選投資範圍
        universe = self.filter_universe(db)
        score = score.where(universe, np.nan)
        
        # 日期範圍
        if start_date:
            score = score[score.index >= start_date]
        if end_date:
            score = score[score.index <= end_date]
        
        self._score = score
        
        # 計算權重
        weights = self.get_weights(score)
        self._signals = weights
        self._computed = True
        
        return weights
    
    def get_latest_signals(self, db=None) -> pd.Series:
        """
        取得最新的交易信號
        
        Args:
            db: FieldDB 實例 (如果尚未計算)
        
        Returns:
            pd.Series: 最新權重 (index=股票代碼)
        """
        if not self._computed and db:
            self.run(db)
        
        if self._signals is None:
            raise ValueError("策略尚未執行，請先呼叫 run()")
        
        latest = self._signals.iloc[-1]
        return latest[latest > 0].sort_values(ascending=False)
    
    def get_latest_score(self, db=None) -> pd.Series:
        """
        取得最新的因子分數
        
        Args:
            db: FieldDB 實例 (如果尚未計算)
        
        Returns:
            pd.Series: 最新分數 (index=股票代碼)
        """
        if not self._computed and db:
            self.run(db)
        
        if self._score is None:
            raise ValueError("策略尚未執行，請先呼叫 run()")
        
        return self._score.iloc[-1].sort_values(ascending=False)
    
    # ═══════════════════════════════════════════════════════════════════════
    # 工具方法
    # ═══════════════════════════════════════════════════════════════════════
    
    def summary(self) -> Dict[str, Any]:
        """取得策略摘要"""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "params": self.params,
            "config": self.config,
        }
    
    def __repr__(self):
        return f"<Strategy: {self.name} v{self.version}>"
    
    def __str__(self):
        return f"{self.name}: {self.description}"


# ═══════════════════════════════════════════════════════════════════════════════
# 匯出
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = ['Strategy']


# ═══════════════════════════════════════════════════════════════════════════════
# 測試
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    from Platform.Core.build_field_database import FieldDB
    from Platform.Factors import *
    
    # 定義測試策略
    class MomentumStrategy(Strategy):
        name = "動量策略"
        description = "買入過去20天漲幅最大的股票"
        params = {"lookback": 20, "top_n": 10}
        
        def compute(self, db):
            close = db.get('close')
            momentum = ts_pct_change(close, self.params["lookback"])
            return zscore(momentum)
    
    print("=" * 70)
    print("📊 Strategy Base 測試")
    print("=" * 70)
    
    # 載入資料庫
    db = FieldDB()
    
    # 建立策略
    strategy = MomentumStrategy(top_n=5)
    print(f"\n策略: {strategy}")
    print(f"參數: {strategy.params}")
    print(f"設定: {strategy.config}")
    
    # 執行策略
    print("\n執行策略...")
    weights = strategy.run(db)
    
    print(f"\n權重矩陣 shape: {weights.shape}")
    print(f"最新權重:")
    latest = strategy.get_latest_signals()
    for ticker, weight in latest.items():
        print(f"   {ticker}: {weight*100:.1f}%")
    
    print(f"\n最新分數 (Top 10):")
    scores = strategy.get_latest_score()
    for ticker, score in scores.head(10).items():
        print(f"   {ticker}: {score:.3f}")
    
    print("\n" + "=" * 70)
    print("✅ Strategy Base 測試完成！")
    print("=" * 70)
