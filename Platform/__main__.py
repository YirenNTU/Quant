#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
📊 Investment AI Platform - 命令列介面
================================================================================

使用方式:
    python -m Platform --help
    python -m Platform list                    # 列出範例策略
    python -m Platform backtest momentum       # 回測動量策略
    python -m Platform allocate momentum       # 取得動量策略配置
    python -m Platform run my_strategy.py      # 執行自訂策略

================================================================================
"""

import sys
import argparse
from pathlib import Path

# 確保可以 import Platform
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    parser = argparse.ArgumentParser(
        description="📊 Investment AI Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  python -m Platform list
  python -m Platform backtest momentum --start 2024-01-01
  python -m Platform allocate combined --capital 1000000
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # list 命令
    list_parser = subparsers.add_parser('list', help='列出可用策略')
    
    # backtest 命令
    bt_parser = subparsers.add_parser('backtest', help='執行回測')
    bt_parser.add_argument('strategy', help='策略名稱 (momentum, value, combined)')
    bt_parser.add_argument('--start', default='2024-06-01', help='開始日期')
    bt_parser.add_argument('--end', default=None, help='結束日期')
    bt_parser.add_argument('--capital', type=float, default=1000000, help='初始資金')
    bt_parser.add_argument('--freq', default='weekly', help='調倉頻率')
    
    # allocate 命令
    alloc_parser = subparsers.add_parser('allocate', help='取得資產配置')
    alloc_parser.add_argument('strategy', help='策略名稱')
    alloc_parser.add_argument('--capital', type=float, default=1000000, help='可用資金')
    alloc_parser.add_argument('--positions', type=int, default=10, help='最大持倉數')
    alloc_parser.add_argument('--output', help='輸出 CSV 檔案')
    
    # run 命令
    run_parser = subparsers.add_parser('run', help='執行自訂策略')
    run_parser.add_argument('file', help='策略檔案路徑')
    run_parser.add_argument('--backtest', action='store_true', help='執行回測')
    run_parser.add_argument('--allocate', action='store_true', help='取得配置')
    run_parser.add_argument('--capital', type=float, default=1000000, help='資金')
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return
    
    # 執行命令
    if args.command == 'list':
        cmd_list()
    elif args.command == 'backtest':
        cmd_backtest(args)
    elif args.command == 'allocate':
        cmd_allocate(args)
    elif args.command == 'run':
        cmd_run(args)


def cmd_list():
    """列出可用策略"""
    from Platform.Strategies.examples import MomentumStrategy, ValueStrategy, CombinedStrategy
    
    strategies = [MomentumStrategy, ValueStrategy, CombinedStrategy]
    
    print("\n📋 可用策略:")
    print("-" * 60)
    for s in strategies:
        print(f"  • {s.__name__:<20} - {s.name}: {s.description}")
    print("-" * 60)
    print("\n使用 'python -m Platform backtest <策略名稱>' 執行回測")


def cmd_backtest(args):
    """執行回測"""
    from Platform import Backtester
    from Platform.Strategies.examples import MomentumStrategy, ValueStrategy, CombinedStrategy
    
    # 策略對應
    strategies = {
        'momentum': MomentumStrategy,
        'value': ValueStrategy,
        'combined': CombinedStrategy,
    }
    
    name = args.strategy.lower()
    if name not in strategies:
        print(f"❌ 找不到策略: {args.strategy}")
        print(f"   可用: {list(strategies.keys())}")
        return
    
    strategy = strategies[name]()
    
    print(f"\n🔄 執行回測: {strategy.name}")
    print(f"   期間: {args.start} ~ {args.end or '最新'}")
    print(f"   資金: ${args.capital:,.0f}")
    
    result = Backtester.run(
        strategy=strategy,
        start_date=args.start,
        end_date=args.end,
        initial_capital=args.capital,
        rebalance_freq=args.freq,
    )
    
    print(result.summary())


def cmd_allocate(args):
    """取得資產配置"""
    from Platform import get_allocation
    from Platform.Strategies.examples import MomentumStrategy, ValueStrategy, CombinedStrategy
    
    strategies = {
        'momentum': MomentumStrategy,
        'value': ValueStrategy,
        'combined': CombinedStrategy,
    }
    
    name = args.strategy.lower()
    if name not in strategies:
        print(f"❌ 找不到策略: {args.strategy}")
        return
    
    strategy = strategies[name]()
    
    allocation = get_allocation(
        strategy=strategy,
        capital=args.capital,
        max_positions=args.positions,
    )
    
    # AllocationResult 的 __str__ 已經會顯示公司名稱
    print(allocation)
    
    if args.output:
        allocation.to_csv(args.output)
        print(f"\n✅ 已儲存至: {args.output}")


def cmd_run(args):
    """執行自訂策略"""
    import importlib.util
    from Platform.Strategies.base import Strategy
    from Platform import Backtester, get_allocation
    
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"❌ 找不到檔案: {args.file}")
        return
    
    # 動態載入
    spec = importlib.util.spec_from_file_location("user_strategy", file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # 找策略類別
    strategy_class = None
    for name, obj in vars(module).items():
        if isinstance(obj, type) and issubclass(obj, Strategy) and obj is not Strategy:
            strategy_class = obj
            break
    
    if strategy_class is None:
        print(f"❌ 找不到策略類別，確認檔案中有繼承 Strategy 的類別")
        return
    
    strategy = strategy_class()
    print(f"\n📊 載入策略: {strategy.name}")
    
    if args.backtest:
        print("\n🔄 執行回測...")
        result = Backtester.run(strategy, start_date="2024-06-01")
        print(result.summary())
    
    if args.allocate:
        print("\n📈 取得配置...")
        allocation = get_allocation(strategy, capital=args.capital)
        print(allocation)


if __name__ == '__main__':
    main()
