#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
📊 Strategy Manager - 策略管理後台
================================================================================

管理、載入、執行多個策略，並提供比較功能。

使用範例:
>>> from Platform.Strategies import StrategyManager
>>> 
>>> manager = StrategyManager()
>>> manager.load_strategies("Platform/Strategies/user_strategies/")
>>> 
>>> # 執行所有策略回測
>>> results = manager.backtest_all()
>>> print(manager.compare(results))

Author: Investment AI Platform
Version: 1.0
================================================================================
"""

import os
import sys
import importlib.util
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List, Type
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 路徑設定
SCRIPT_DIR = Path(__file__).parent
PLATFORM_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = PLATFORM_DIR.parent


class StrategyManager:
    """策略管理後台"""
    
    def __init__(self, db=None):
        """
        初始化策略管理器
        
        Args:
            db: FieldDB 實例 (可選)
        """
        self.strategies: Dict[str, Any] = {}
        self.results: Dict[str, Any] = {}
        self._db = db
    
    @property
    def db(self):
        """延遲載入資料庫"""
        if self._db is None:
            sys.path.insert(0, str(PROJECT_ROOT))
            from Platform.Core.build_field_database import FieldDB
            self._db = FieldDB()
        return self._db
    
    def register(self, strategy_class: Type, name: str = None):
        """
        註冊策略類別
        
        Args:
            strategy_class: 策略類別
            name: 策略名稱 (可選，預設使用類別名稱)
        """
        if name is None:
            name = strategy_class.__name__
        
        self.strategies[name] = strategy_class
        print(f"✅ 已註冊策略: {name}")
    
    def load_strategies(self, directory: str):
        """
        從目錄載入所有策略
        
        Args:
            directory: 策略目錄路徑
        """
        dir_path = Path(directory)
        if not dir_path.exists():
            print(f"⚠️ 目錄不存在: {directory}")
            return
        
        # 載入所有 .py 檔案
        for file_path in dir_path.glob("*.py"):
            if file_path.name.startswith("_"):
                continue
            
            try:
                self._load_strategy_file(file_path)
            except Exception as e:
                print(f"⚠️ 載入失敗 {file_path.name}: {e}")
    
    def _load_strategy_file(self, file_path: Path):
        """載入單一策略檔案"""
        # 動態載入模組
        spec = importlib.util.spec_from_file_location(
            file_path.stem, file_path
        )
        module = importlib.util.module_from_spec(spec)
        
        # 確保能 import Platform
        sys.path.insert(0, str(PROJECT_ROOT))
        
        spec.loader.exec_module(module)
        
        # 找出所有策略類別
        from Platform.Strategies.base import Strategy
        
        for name, obj in vars(module).items():
            if (isinstance(obj, type) and 
                issubclass(obj, Strategy) and 
                obj is not Strategy):
                self.register(obj, name)
    
    def list_strategies(self) -> List[str]:
        """列出所有已註冊策略"""
        return list(self.strategies.keys())
    
    def get_strategy(self, name: str):
        """取得策略實例"""
        if name not in self.strategies:
            raise ValueError(f"找不到策略: {name}")
        return self.strategies[name]()
    
    def run(self, name: str, **kwargs) -> pd.DataFrame:
        """
        執行單一策略
        
        Args:
            name: 策略名稱
            **kwargs: 策略參數
        
        Returns:
            權重 DataFrame
        """
        strategy = self.get_strategy(name)
        for k, v in kwargs.items():
            if k in strategy.params:
                strategy.params[k] = v
            elif k in strategy.config:
                strategy.config[k] = v
        
        return strategy.run(self.db)
    
    def backtest(self, name: str, **kwargs):
        """
        執行單一策略回測
        
        Args:
            name: 策略名稱
            **kwargs: 回測參數
        
        Returns:
            BacktestResult
        """
        from Platform.Backtest import Backtester
        
        strategy = self.get_strategy(name)
        result = Backtester.run(strategy, db=self.db, **kwargs)
        self.results[name] = result
        return result
    
    def backtest_all(self, **kwargs) -> Dict[str, Any]:
        """
        執行所有策略回測
        
        Args:
            **kwargs: 回測參數
        
        Returns:
            Dict[策略名稱, BacktestResult]
        """
        results = {}
        
        for name in self.strategies.keys():
            print(f"🔄 回測中: {name}...")
            try:
                result = self.backtest(name, **kwargs)
                results[name] = result
                print(f"   ✅ {name}: 年化報酬 {result.metrics['annual_return']*100:.1f}%")
            except Exception as e:
                print(f"   ❌ {name}: {e}")
        
        return results
    
    def compare(self, results: Dict[str, Any] = None) -> pd.DataFrame:
        """
        比較多個策略績效
        
        Args:
            results: 回測結果字典 (預設使用 self.results)
        
        Returns:
            比較表格 DataFrame
        """
        if results is None:
            results = self.results
        
        if not results:
            print("⚠️ 沒有回測結果可比較")
            return pd.DataFrame()
        
        comparison = []
        
        for name, result in results.items():
            m = result.metrics
            comparison.append({
                '策略': name,
                '總報酬%': m['total_return'] * 100,
                '年化報酬%': m['annual_return'] * 100,
                '年化波動%': m['annual_volatility'] * 100,
                '夏普比率': m['sharpe_ratio'],
                '最大回撤%': m['max_drawdown'] * 100,
                'Calmar': m['calmar_ratio'],
                '勝率%': m['win_rate'] * 100,
            })
        
        df = pd.DataFrame(comparison)
        df = df.sort_values('夏普比率', ascending=False)
        df = df.round(2)
        
        return df
    
    def get_allocation(self, name: str, capital: float = 1_000_000, **kwargs):
        """
        取得策略的資產配置
        
        Args:
            name: 策略名稱
            capital: 可用資金
            **kwargs: 配置參數
        
        Returns:
            AllocationResult
        """
        from Platform.Allocator import get_allocation
        
        strategy = self.get_strategy(name)
        return get_allocation(strategy, capital=capital, db=self.db, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# 匯出
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = ['StrategyManager']


# ═══════════════════════════════════════════════════════════════════════════════
# 測試
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    sys.path.insert(0, str(PROJECT_ROOT))
    
    from Platform.Strategies.base import Strategy
    from Platform.Factors import *
    
    # 定義幾個測試策略
    class MomentumStrategy(Strategy):
        name = "動量策略"
        description = "買入過去20天漲幅最大的股票"
        params = {"lookback": 20}
        
        def compute(self, db):
            close = db.get('close')
            return zscore(ts_pct_change(close, self.params["lookback"]))
    
    class ValueStrategy(Strategy):
        name = "價值策略"
        description = "買入低本益比股票"
        params = {}
        
        def compute(self, db):
            pe = db.get('pe')
            # PE 越低分數越高
            return zscore(-pe.ffill())
    
    class CombinedStrategy(Strategy):
        name = "綜合策略"
        description = "動量 + 價值 + 成交量"
        params = {"mom_weight": 0.4, "val_weight": 0.3, "vol_weight": 0.3}
        
        def compute(self, db):
            close = db.get('close')
            pe = db.get('pe')
            volume = db.get('volume')
            
            mom = zscore(ts_pct_change(close, 20))
            val = zscore(-pe.ffill())
            vol = zscore(ts_rank(volume, 20))
            
            return (self.params["mom_weight"] * mom +
                    self.params["val_weight"] * val +
                    self.params["vol_weight"] * vol)
    
    print("=" * 70)
    print("📊 Strategy Manager 測試")
    print("=" * 70)
    
    # 建立管理器
    manager = StrategyManager()
    
    # 註冊策略
    manager.register(MomentumStrategy)
    manager.register(ValueStrategy)
    manager.register(CombinedStrategy)
    
    print(f"\n已註冊策略: {manager.list_strategies()}")
    
    # 執行回測
    print("\n🔄 執行回測...")
    results = manager.backtest_all(
        start_date="2024-06-01",
        end_date="2025-12-31",
    )
    
    # 比較結果
    print("\n📊 策略比較:")
    print(manager.compare())
    
    # 取得最佳策略的配置
    print("\n📈 最佳策略配置:")
    best = manager.compare().iloc[0]['策略']
    allocation = manager.get_allocation(best, capital=1_000_000)
    print(allocation)
