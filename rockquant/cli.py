#!/usr/bin/env python3
"""
Rock Quant CLI - 命令行量化回测工具

Usage:
    rockquant run <strategy> [options]
    rockquant analyze <strategy> [options]
    rockquant report <strategy> [options]
    rockquant list
    rockquant factors
    rockquant --help

Examples:
    rockquant run 双均线策略 --symbol 000001.SZ --start 20230101 --end 20240101
    rockquant analyze 双均线策略 --short-period 10 --long-period 30
    rockquant report RSI超买超卖策略 --output report.pdf
    rockquant list
"""

import argparse
import sys
import os
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np

from src.config import BacktestConfig
from src.backtest_engine import BacktestEngine
from src.strategies import create_strategy, get_all_strategies, get_strategy_info
from src.performance import PerformanceCalculator
from src.ai_analyzer import AIStrategyAnalyzer
from src.factors import list_factors_by_type


def load_test_data(days=500):
    """生成测试数据"""
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now() - pd.Timedelta(days=days), periods=days, freq='D')
    base_price = 100 + np.cumsum(np.random.randn(days) * 0.5)
    
    return pd.DataFrame({
        'open': base_price * (1 + np.random.randn(days) * 0.005),
        'high': base_price * (1 + np.abs(np.random.randn(days)) * 0.02),
        'low': base_price * (1 - np.abs(np.random.randn(days)) * 0.02),
        'close': base_price,
        'volume': np.random.randint(1000000, 10000000, days)
    }, index=dates)


def cmd_run(args):
    """运行回测命令"""
    print(f"\n{'='*60}")
    print(f"  Rock Quant v2.6 - 策略回测")
    print(f"{'='*60}\n")
    
    # 解析策略参数
    strategy_params = {}
    for k, v in vars(args).items():
        if k.startswith('param_') and v is not None:
            param_name = k[6:].replace('_', '-')
            strategy_params[param_name] = v
    
    print(f"策略: {args.strategy}")
    print(f"参数: {strategy_params if strategy_params else '默认'}")
    print()
    
    # 创建策略
    strategy = create_strategy(args.strategy, **strategy_params)
    
    # 加载数据
    df = load_test_data()
    print(f"数据范围: {df.index[0].strftime('%Y-%m-%d')} 至 {df.index[-1].strftime('%Y-%m-%d')}")
    print(f"数据点数: {len(df)} 天")
    print()
    
    # 生成信号
    signals = strategy.generate_signals(df)
    
    # 运行回测
    config = BacktestConfig(initial_capital=getattr(args, 'capital', 100000), position_size=getattr(args, 'position', 0.8))
    engine = BacktestEngine(config)
    result = engine.run(df, signals)
    
    # 计算绩效
    perf = PerformanceCalculator.calculate_all(result.equity_curve, result.trades, config.initial_capital)
    
    # 输出结果
    print(f"{'='*40}")
    print(f"  回测结果")
    print(f"{'='*40}")
    print(f"初始资金: {config.initial_capital:,.0f}")
    print(f"最终净值: {result.equity_curve.iloc[-1]:,.0f}")
    print(f"总收益率: {perf['总收益率']:+.2%}")
    print(f"年化收益: {perf['年化收益率(CAGR)']:+.2%}")
    print(f"夏普比率: {perf['夏普比率']:.2f}")
    print(f"最大回撤: {perf['最大回撤']:.2%}")
    print(f"胜率: {perf['胜率']:.1%}")
    print(f"盈亏比: {perf['盈亏比']:.2f}")
    print(f"交易次数: {perf['总交易次数']}")
    print()
    
    return result, perf


def cmd_analyze(args):
    """AI分析命令"""
    result, perf = cmd_run(args)
    
    print(f"\n{'='*60}")
    print(f"  AI 深度分析")
    print(f"{'='*60}\n")
    
    # 运行AI分析
    analyzer = AIStrategyAnalyzer()
    analysis = analyzer.analyze(result.equity_curve, result.trades, perf, args.strategy, 'TEST')
    
    print(f"【综合评级】 {analysis.score.grade} 级")
    print(f"【综合评分】 {analysis.score.overall_score:.1f}/100")
    print()
    print(f"【5维度评分】")
    print(f"  收益能力: {analysis.score.return_score:.0f}/40")
    print(f"  风险控制: {analysis.score.risk_score:.0f}/20")
    print(f"  风险调整收益: {analysis.score.risk_adjusted_score:.0f}/15")
    print(f"  稳定性: {analysis.score.consistency_score:.0f}/10")
    print(f"  交易质量: {analysis.score.trading_quality_score:.0f}/15")
    print()
    
    print(f"【收益归因】")
    attribution_items = [
        ('趋势捕捉', analysis.attribution.trend_capture, '策略识别和捕捉趋势行情的能力'),
        ('波动择时', analysis.attribution.volatility_timing, '利用市场波动获取收益的能力'),
        ('均值回归', analysis.attribution.mean_reversion, '逆向交易和均值回归能力'),
        ('仓位管理', analysis.attribution.position_sizing, '仓位大小调整对收益的贡献'),
        ('运气成分', analysis.attribution.luck_factor, '运气因素对总收益的贡献比例'),
    ]
    total = sum(v for _, v, _ in attribution_items) or 1
    for name, value, interpretation in attribution_items:
        ratio = value / total
        print(f"  {name}: {ratio:.1%} - {interpretation}")
    print()
    
    print(f"【专家辩论】")
    agent_names = {
        'CONSERVATIVE': '风控专家',
        'AGGRESSIVE': '交易专家', 
        'STATISTICIAN': '统计专家',
        'BEHAVIORAL': '行为金融专家'
    }
    for debate in analysis.debate_results:
        role_str = str(debate.role).split('.')[-1] if hasattr(debate.role, 'value') or '.' in str(debate.role) else str(debate.role)
        name = agent_names.get(role_str, role_str)
        confidence = debate.confidence if debate.confidence <= 1 else debate.confidence / 100
        print(f"  {name}: {debate.recommendation} (置信度: {confidence:.0%})")
    print()
    print(f"【综合结论】")
    lines = analysis.final_conclusion.strip().split('\n')
    for line in lines[:3]:  # 只显示前3行
        print(f"  {line.strip()}")
    print()


def cmd_list(args):
    """列出所有策略"""
    print(f"\n{'='*60}")
    print(f"  Rock Quant v2.6 - 可用策略列表")
    print(f"{'='*60}\n")
    
    strategies = get_all_strategies()
    for i, strategy in enumerate(strategies, 1):
        info = get_strategy_info(strategy)
        print(f"{i:2d}. {strategy}")
        print(f"     {info['description']}")
        params = info['params_schema']
        if params:
            param_str = ', '.join([f"{k}={v['default']}" for k, v in params.items()])
            print(f"     参数: {param_str}")
        print()
    
    print(f"总计: {len(strategies)} 个策略\n")


def cmd_factors(args):
    """列出所有因子"""
    print(f"\n{'='*60}")
    print(f"  Rock Quant v2.6 - 量价因子库")
    print(f"{'='*60}\n")
    
    factor_types = ['趋势类', '震荡类', '成交量类', '波动率类']
    total = 0
    
    for factor_type in factor_types:
        factors = list_factors_by_type(factor_type)
        total += len(factors)
        print(f"【{factor_type}】({len(factors)}个)")
        for factor in factors:
            print(f"  - {factor}")
        print()
    
    print(f"总计: {total} 个因子\n")


def main():
    parser = argparse.ArgumentParser(
        prog='rockquant',
        description='Rock Quant CLI - 顽岩量化命令行回测工具 v2.6',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # run 命令
    run_parser = subparsers.add_parser('run', help='运行策略回测')
    run_parser.add_argument('strategy', help='策略名称')
    run_parser.add_argument('--symbol', default='000001.SZ', help='标的代码')
    run_parser.add_argument('--start', help='开始日期 YYYYMMDD')
    run_parser.add_argument('--end', help='结束日期 YYYYMMDD')
    run_parser.add_argument('--capital', type=float, default=100000, help='初始资金')
    run_parser.add_argument('--position', type=float, default=0.8, help='仓位比例')
    run_parser.add_argument('--param-short-period', type=int, help='短期均线周期')
    run_parser.add_argument('--param-long-period', type=int, help='长期均线周期')
    run_parser.add_argument('--param-period', type=int, help='通用周期参数')
    
    # analyze 命令
    analyze_parser = subparsers.add_parser('analyze', help='AI深度分析策略')
    analyze_parser.add_argument('strategy', help='策略名称')
    analyze_parser.add_argument('--symbol', default='000001.SZ', help='标的代码')
    analyze_parser.add_argument('--capital', type=float, default=100000, help='初始资金')
    
    # report 命令
    report_parser = subparsers.add_parser('report', help='生成PDF报告')
    report_parser.add_argument('strategy', help='策略名称')
    report_parser.add_argument('--output', default='report.pdf', help='输出文件')
    
    # list 命令
    subparsers.add_parser('list', help='列出所有可用策略')
    
    # factors 命令
    subparsers.add_parser('factors', help='列出所有量价因子')
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return
    
    commands = {
        'run': cmd_run,
        'analyze': cmd_analyze,
        'list': cmd_list,
        'factors': cmd_factors,
    }
    
    if args.command in commands:
        try:
            commands[args.command](args)
        except Exception as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    main()
