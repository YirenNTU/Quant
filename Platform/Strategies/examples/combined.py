"""
綜合策略 - Combined Strategy

結合動量、價值、成交量、籌碼多因子
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from Platform.Strategies import Strategy
from Platform.Factors import *


class CombinedStrategy(Strategy):
    """綜合策略"""
    
    name = "綜合策略"
    description = "結合動量、價值、成交量、籌碼的多因子策略"
    version = "1.0"
    author = "Platform"
    
    params = {
        "momentum_weight": 0.30,    # 動量權重
        "value_weight": 0.25,       # 價值權重
        "volume_weight": 0.20,      # 成交量權重
        "chip_weight": 0.25,        # 籌碼權重
        "top_n": 10,
    }
    
    def compute(self, db):
        # === 動量因子 ===
        close = db.get('close')
        mom_20 = ts_pct_change(close, 20)
        momentum_score = zscore(mom_20)
        
        # === 價值因子 ===
        pe = db.get('pe').ffill()
        pb = db.get('pb').ffill()
        value_score = zscore(-pe) * 0.5 + zscore(-pb) * 0.5
        
        # === 成交量因子 ===
        volume = db.get('volume')
        # 價量背離: 價格創新高但成交量萎縮 (不好)
        # 我們要的是: 價格上漲且成交量放大
        price_rank = ts_rank(close, 20)
        vol_rank = ts_rank(volume, 20)
        volume_score = zscore(price_rank + vol_rank)
        
        # === 籌碼因子 ===
        try:
            qfii_net = db.get('qfii_net').reindex(close.index).ffill()
            fund_net = db.get('fund_net').reindex(close.index).ffill()
            # 法人買超
            chip_score = zscore(qfii_net) * 0.6 + zscore(fund_net) * 0.4
        except:
            # 如果籌碼資料不足，使用動量替代
            chip_score = momentum_score * 0
        
        # === 組合 ===
        score = (self.params["momentum_weight"] * momentum_score +
                 self.params["value_weight"] * value_score +
                 self.params["volume_weight"] * volume_score +
                 self.params["chip_weight"] * chip_score)
        
        return score
    
    def filter_universe(self, db):
        """排除成交量過低的股票"""
        volume = db.get('volume')
        close = db.get('close')
        
        daily_amount = close * volume
        return ts_mean(daily_amount, 20) > 5_000_000


if __name__ == '__main__':
    from Platform import quick_test
    quick_test(CombinedStrategy)
