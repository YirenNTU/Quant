#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
📊 Backtester - 回測引擎
================================================================================

執行策略歷史回測，計算績效指標。

使用範例:
>>> from Platform.Backtest import Backtester
>>> from Platform.Strategies.examples.momentum import MomentumStrategy
>>> 
>>> result = Backtester.run(
>>>     strategy=MomentumStrategy(),
>>>     start_date="2024-01-01",
>>>     end_date="2025-12-31",
>>> )
>>> print(result.summary())

Author: Investment AI Platform
Version: 1.0
================================================================================
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Union, Type
from datetime import datetime, timedelta
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')


@dataclass
class BacktestResult:
    """回測結果"""
    
    # 基本資訊
    strategy_name: str
    start_date: str
    end_date: str
    initial_capital: float
    
    # 時間序列
    portfolio_value: pd.Series      # 組合淨值
    daily_returns: pd.Series        # 日報酬
    positions: pd.DataFrame         # 每日持倉
    weights: pd.DataFrame           # 每日權重
    trades: pd.DataFrame            # 交易紀錄
    
    # 績效指標
    metrics: Dict[str, float]
    
    def summary(self) -> str:
        """輸出績效摘要"""
        m = self.metrics
        
        text = f"""
================================================================================
📊 回測報告: {self.strategy_name}
================================================================================

📅 回測期間: {self.start_date} ~ {self.end_date}
💰 初始資金: ${self.initial_capital:,.0f}
💵 最終淨值: ${m['final_value']:,.0f}

📈 績效指標:
   • 總報酬率:     {m['total_return']*100:>8.2f}%
   • 年化報酬率:   {m['annual_return']*100:>8.2f}%
   • 年化波動率:   {m['annual_volatility']*100:>8.2f}%
   • 夏普比率:     {m['sharpe_ratio']:>8.2f}
   • 索提諾比率:   {m['sortino_ratio']:>8.2f}
   • Calmar 比率: {m['calmar_ratio']:>8.2f}

📉 風險指標:
   • 最大回撤:     {m['max_drawdown']*100:>8.2f}%
   • 最長回撤天數: {m['max_drawdown_days']:>8.0f} 天
   • 勝率:         {m['win_rate']*100:>8.2f}%
   • 盈虧比:       {m['profit_loss_ratio']:>8.2f}

📊 交易統計:
   • 總交易次數:   {m['total_trades']:>8.0f}
   • 週轉率(年化): {m['annual_turnover']*100:>8.2f}%
   • 平均持倉數:   {m['avg_positions']:>8.1f}

================================================================================
"""
        return text
    
    def plot(self, save_path: str = None, show: bool = True):
        """
        繪製績效圖 (需要 matplotlib)
        
        Args:
            save_path: 若提供路徑，則儲存圖片 (如 'performance.png')
            show: 是否顯示圖片 (預設 True)
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            
            # 設定中文字體
            plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Microsoft JhengHei', 'SimHei', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            
            fig, axes = plt.subplots(3, 1, figsize=(14, 10))
            
            # 顏色設定
            primary_color = '#2E86AB'
            positive_color = '#28A745'
            negative_color = '#DC3545'
            
            # ─────────────────────────────────────────────────────────────
            # 1. 淨值曲線
            # ─────────────────────────────────────────────────────────────
            ax1 = axes[0]
            
            # 繪製淨值曲線
            ax1.plot(self.portfolio_value.index, self.portfolio_value.values, 
                    linewidth=2, color=primary_color, label='Portfolio Value')
            
            # 繪製起始資金水平線
            ax1.axhline(y=self.initial_capital, color='gray', linestyle='--', 
                       alpha=0.5, label=f'Initial Capital (${self.initial_capital:,.0f})')
            
            # 標註最終淨值
            final_val = self.portfolio_value.iloc[-1]
            total_ret = (final_val / self.initial_capital - 1) * 100
            ax1.annotate(f'${final_val:,.0f}\n({total_ret:+.1f}%)', 
                        xy=(self.portfolio_value.index[-1], final_val),
                        xytext=(10, 0), textcoords='offset points',
                        fontsize=10, fontweight='bold',
                        color=positive_color if total_ret >= 0 else negative_color)
            
            ax1.set_title(f'📊 {self.strategy_name} - 淨值曲線 (Portfolio Value)', fontsize=14, fontweight='bold')
            ax1.set_ylabel('淨值 ($)', fontsize=11)
            ax1.legend(loc='upper left')
            ax1.grid(True, alpha=0.3)
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
            
            # 填充盈利/虧損區域
            ax1.fill_between(self.portfolio_value.index, 
                            self.initial_capital, 
                            self.portfolio_value.values,
                            where=self.portfolio_value.values >= self.initial_capital,
                            color=positive_color, alpha=0.1)
            ax1.fill_between(self.portfolio_value.index, 
                            self.initial_capital, 
                            self.portfolio_value.values,
                            where=self.portfolio_value.values < self.initial_capital,
                            color=negative_color, alpha=0.1)
            
            # ─────────────────────────────────────────────────────────────
            # 2. 回撤曲線
            # ─────────────────────────────────────────────────────────────
            ax2 = axes[1]
            drawdown = (self.portfolio_value / self.portfolio_value.cummax() - 1) * 100
            
            ax2.plot(drawdown.index, drawdown.values, linewidth=1, color=negative_color)
            ax2.fill_between(drawdown.index, drawdown.values, 0, color=negative_color, alpha=0.3)
            
            # 標註最大回撤
            max_dd = drawdown.min()
            max_dd_date = drawdown.idxmin()
            ax2.annotate(f'Max DD: {max_dd:.1f}%', 
                        xy=(max_dd_date, max_dd),
                        xytext=(10, -15), textcoords='offset points',
                        fontsize=10, fontweight='bold', color=negative_color,
                        arrowprops=dict(arrowstyle='->', color=negative_color))
            
            ax2.set_title('📉 回撤曲線 (Drawdown)', fontsize=14, fontweight='bold')
            ax2.set_ylabel('回撤 (%)', fontsize=11)
            ax2.grid(True, alpha=0.3)
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
            
            # ─────────────────────────────────────────────────────────────
            # 3. 月報酬柱狀圖
            # ─────────────────────────────────────────────────────────────
            ax3 = axes[2]
            monthly_returns = self.daily_returns.resample('ME').apply(lambda x: (1+x).prod() - 1) * 100
            
            colors = [positive_color if x >= 0 else negative_color for x in monthly_returns]
            bars = ax3.bar(range(len(monthly_returns)), monthly_returns.values, color=colors, alpha=0.8)
            
            # 設定 x 軸標籤
            tick_labels = [d.strftime('%Y-%m') for d in monthly_returns.index]
            ax3.set_xticks(range(len(monthly_returns)))
            ax3.set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=8)
            
            ax3.axhline(y=0, color='black', linewidth=0.5)
            ax3.set_title('📊 月報酬率 (Monthly Returns)', fontsize=14, fontweight='bold')
            ax3.set_ylabel('報酬率 (%)', fontsize=11)
            ax3.grid(True, alpha=0.3, axis='y')
            
            # 標註最佳和最差月份
            if len(monthly_returns) > 0:
                best_month = monthly_returns.idxmax()
                worst_month = monthly_returns.idxmin()
                best_idx = list(monthly_returns.index).index(best_month)
                worst_idx = list(monthly_returns.index).index(worst_month)
                
                ax3.annotate(f'Best: {monthly_returns.max():.1f}%', 
                            xy=(best_idx, monthly_returns.max()),
                            xytext=(0, 5), textcoords='offset points',
                            fontsize=8, ha='center', color=positive_color)
                ax3.annotate(f'Worst: {monthly_returns.min():.1f}%', 
                            xy=(worst_idx, monthly_returns.min()),
                            xytext=(0, -12), textcoords='offset points',
                            fontsize=8, ha='center', color=negative_color)
            
            plt.tight_layout()
            
            # 儲存圖片
            if save_path:
                plt.savefig(save_path, dpi=150, bbox_inches='tight', 
                           facecolor='white', edgecolor='none')
                print(f"✅ 績效圖已儲存至: {save_path}")
            
            # 顯示圖片
            if show:
                plt.show()
            else:
                plt.close()
            
        except ImportError:
            print("❌ 需要安裝 matplotlib 才能繪圖")
            print("   執行: pip install matplotlib")


class Backtester:
    """回測引擎"""
    
    @staticmethod
    def run(
        strategy,
        start_date: str = None,
        end_date: str = None,
        initial_capital: float = 1_000_000,
        rebalance_freq: str = "weekly",
        transaction_cost: float = 0.001425,
        tax: float = 0.003,
        slippage: float = 0.001,
        benchmark: str = None,
        db = None,
    ) -> BacktestResult:
        """
        執行回測
        
        Args:
            strategy: 策略實例
            start_date: 開始日期 (預設: 資料最早日期)
            end_date: 結束日期 (預設: 資料最新日期)
            initial_capital: 初始資金
            rebalance_freq: 調倉頻率 (daily, weekly, monthly)
            transaction_cost: 手續費率
            tax: 證交稅率 (賣出時)
            slippage: 滑價
            benchmark: 基準指數代碼 (可選)
            db: FieldDB 實例 (可選，不傳會自動載入)
        
        Returns:
            BacktestResult: 回測結果
        """
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        
        from Platform.Core.build_field_database import FieldDB
        
        # 載入資料庫
        if db is None:
            db = FieldDB()
        
        # 取得價格資料
        close = db.get('close')
        
        # 設定日期範圍
        if start_date is None:
            start_date = str(close.index.min())[:10]
        if end_date is None:
            end_date = str(close.index.max())[:10]
        
        # 執行策略
        weights = strategy.run(db, start_date, end_date)
        
        # 過濾日期
        close = close[(close.index >= start_date) & (close.index <= end_date)]
        weights = weights[(weights.index >= start_date) & (weights.index <= end_date)]
        
        # 對齊
        common_dates = close.index.intersection(weights.index)
        common_cols = close.columns.intersection(weights.columns)
        close = close.loc[common_dates, common_cols]
        weights = weights.loc[common_dates, common_cols]
        
        # 計算每日報酬
        daily_returns = close.pct_change()
        
        # 決定調倉日
        rebalance_dates = Backtester._get_rebalance_dates(
            weights.index, rebalance_freq
        )
        
        # 模擬交易
        portfolio_value, positions, trades_list = Backtester._simulate(
            weights=weights,
            close=close,
            daily_returns=daily_returns,
            rebalance_dates=rebalance_dates,
            initial_capital=initial_capital,
            transaction_cost=transaction_cost,
            tax=tax,
            slippage=slippage,
        )
        
        # 計算績效指標
        portfolio_returns = portfolio_value.pct_change().dropna()
        metrics = Backtester._calculate_metrics(
            portfolio_value=portfolio_value,
            portfolio_returns=portfolio_returns,
            initial_capital=initial_capital,
            weights=weights,
            trades=trades_list,
        )
        
        # 建立交易紀錄 DataFrame
        if trades_list:
            trades_df = pd.DataFrame(trades_list)
        else:
            trades_df = pd.DataFrame(columns=['date', 'ticker', 'action', 'shares', 'price', 'value', 'cost'])
        
        return BacktestResult(
            strategy_name=strategy.name,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            portfolio_value=portfolio_value,
            daily_returns=portfolio_returns,
            positions=positions,
            weights=weights,
            trades=trades_df,
            metrics=metrics,
        )
    
    @staticmethod
    def _get_rebalance_dates(dates: pd.DatetimeIndex, freq: str) -> set:
        """取得調倉日期"""
        if freq == "daily":
            return set(dates)
        elif freq == "weekly":
            # 每週五調倉
            return set(dates[dates.dayofweek == 4])
        elif freq == "monthly":
            # 每月最後一個交易日
            return set(dates.to_series().groupby(dates.to_period('M')).last())
        else:
            return set(dates)
    
    @staticmethod
    def _simulate(
        weights: pd.DataFrame,
        close: pd.DataFrame,
        daily_returns: pd.DataFrame,
        rebalance_dates: set,
        initial_capital: float,
        transaction_cost: float,
        tax: float,
        slippage: float,
    ) -> tuple:
        """模擬交易"""
        
        dates = weights.index
        tickers = weights.columns
        
        # 初始化
        cash = initial_capital
        holdings = pd.Series(0.0, index=tickers)  # 持股數量
        portfolio_values = []
        positions_list = []
        trades = []
        
        current_weights = pd.Series(0.0, index=tickers)
        
        for date in dates:
            price = close.loc[date]
            target_weights = weights.loc[date].fillna(0)
            
            # 計算當前持倉價值
            holdings_value = (holdings * price).fillna(0)
            total_value = cash + holdings_value.sum()
            
            # 是否調倉日
            if date in rebalance_dates:
                # 目標持倉
                target_value = target_weights * total_value
                target_shares = (target_value / price).fillna(0)
                
                # 計算交易
                trade_shares = target_shares - holdings
                
                for ticker in tickers:
                    if abs(trade_shares[ticker]) > 0.01:
                        shares = trade_shares[ticker]
                        p = price[ticker]
                        
                        if pd.isna(p) or p <= 0:
                            continue
                        
                        # 買入
                        if shares > 0:
                            cost = shares * p * (1 + slippage)
                            fee = cost * transaction_cost
                            total_cost = cost + fee
                            
                            if total_cost <= cash:
                                cash -= total_cost
                                holdings[ticker] += shares
                                
                                trades.append({
                                    'date': date,
                                    'ticker': ticker,
                                    'action': 'BUY',
                                    'shares': shares,
                                    'price': p,
                                    'value': cost,
                                    'cost': fee,
                                })
                        
                        # 賣出
                        elif shares < 0:
                            sell_shares = min(abs(shares), holdings[ticker])
                            if sell_shares > 0:
                                proceeds = sell_shares * p * (1 - slippage)
                                fee = proceeds * transaction_cost
                                tax_cost = proceeds * tax
                                net_proceeds = proceeds - fee - tax_cost
                                
                                cash += net_proceeds
                                holdings[ticker] -= sell_shares
                                
                                trades.append({
                                    'date': date,
                                    'ticker': ticker,
                                    'action': 'SELL',
                                    'shares': -sell_shares,
                                    'price': p,
                                    'value': proceeds,
                                    'cost': fee + tax_cost,
                                })
            
            # 更新持倉價值
            holdings_value = (holdings * price).fillna(0)
            total_value = cash + holdings_value.sum()
            
            portfolio_values.append(total_value)
            positions_list.append(holdings.copy())
        
        portfolio_value = pd.Series(portfolio_values, index=dates)
        positions = pd.DataFrame(positions_list, index=dates)
        
        return portfolio_value, positions, trades
    
    @staticmethod
    def _calculate_metrics(
        portfolio_value: pd.Series,
        portfolio_returns: pd.Series,
        initial_capital: float,
        weights: pd.DataFrame,
        trades: list,
    ) -> Dict[str, float]:
        """計算績效指標"""
        
        # 基本指標
        final_value = portfolio_value.iloc[-1]
        total_return = final_value / initial_capital - 1
        
        # 年化
        n_days = len(portfolio_value)
        n_years = n_days / 252
        annual_return = (1 + total_return) ** (1 / n_years) - 1 if n_years > 0 else 0
        
        # 波動率
        daily_std = portfolio_returns.std()
        annual_volatility = daily_std * np.sqrt(252)
        
        # 夏普比率 (假設無風險利率 2%)
        risk_free_rate = 0.02
        excess_return = annual_return - risk_free_rate
        sharpe_ratio = excess_return / annual_volatility if annual_volatility > 0 else 0
        
        # 索提諾比率
        downside_returns = portfolio_returns[portfolio_returns < 0]
        downside_std = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
        sortino_ratio = excess_return / downside_std if downside_std > 0 else 0
        
        # 最大回撤
        cummax = portfolio_value.cummax()
        drawdown = portfolio_value / cummax - 1
        max_drawdown = drawdown.min()
        
        # 最長回撤天數
        is_dd = portfolio_value < cummax
        dd_groups = (is_dd != is_dd.shift()).cumsum()
        dd_lengths = is_dd.groupby(dd_groups).sum()
        max_drawdown_days = dd_lengths.max() if len(dd_lengths) > 0 else 0
        
        # Calmar 比率
        calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown < 0 else 0
        
        # 勝率
        winning_days = (portfolio_returns > 0).sum()
        total_days = len(portfolio_returns)
        win_rate = winning_days / total_days if total_days > 0 else 0
        
        # 盈虧比
        avg_win = portfolio_returns[portfolio_returns > 0].mean() if winning_days > 0 else 0
        avg_loss = abs(portfolio_returns[portfolio_returns < 0].mean()) if (total_days - winning_days) > 0 else 1
        profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0
        
        # 交易統計
        total_trades = len(trades)
        
        # 週轉率
        weight_changes = weights.diff().abs().sum(axis=1).sum()
        annual_turnover = weight_changes / n_years if n_years > 0 else 0
        
        # 平均持倉數
        avg_positions = (weights > 0).sum(axis=1).mean()
        
        return {
            'final_value': final_value,
            'total_return': total_return,
            'annual_return': annual_return,
            'annual_volatility': annual_volatility,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'max_drawdown': max_drawdown,
            'max_drawdown_days': max_drawdown_days,
            'win_rate': win_rate,
            'profit_loss_ratio': profit_loss_ratio,
            'total_trades': total_trades,
            'annual_turnover': annual_turnover,
            'avg_positions': avg_positions,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# 匯出
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = ['Backtester', 'BacktestResult']


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
    print("📊 Backtester 回測引擎測試")
    print("=" * 70)
    
    # 執行回測
    strategy = MomentumStrategy(top_n=10)
    
    result = Backtester.run(
        strategy=strategy,
        start_date="2024-06-01",
        end_date="2025-12-31",
        initial_capital=1_000_000,
        rebalance_freq="weekly",
    )
    
    print(result.summary())
    
    print("\n📋 最近5筆交易:")
    print(result.trades.tail())
