"""
動量策略 - Momentum Strategy

買入過去 N 天漲幅最大的股票
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from Platform.Strategies import Strategy
from Platform.Factors import *


class MomentumStrategy(Strategy):
    """動量策略"""
    
    name = "動量策略"
    description = "買入過去20天漲幅最大的股票"
    version = "1.0"
    author = "Platform"
    
    params = {
        "lookback": 20,      # 動量計算週期
        "top_n": 10,         # 持有股票數
    }
    
    def compute(self, db):
        close = db.get('close')
        
        # 計算動量 (N 日報酬率)
        momentum = ts_pct_change(close, self.params["lookback"])
        
        # Z-score 標準化
        return zscore(momentum)
    
    def filter_universe(self, db):
        """排除成交量過低的股票"""
        volume = db.get('volume')
        close = db.get('close')
        
        # 日成交金額 > 1000 萬
        daily_amount = close * volume
        min_amount = 10_000_000
        
        return ts_mean(daily_amount, 20) > min_amount


if __name__ == '__main__':
    from Platform import quick_test
    quick_test(MomentumStrategy)
