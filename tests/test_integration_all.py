"""
test_integration_all.py - Lv.A-D 全套集成测试
验证 XtQuant / Alpha158 / MarketIntel / EventDriven 四大新功能
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd
import numpy as np

# ============================================================
# Lv.A: XtQuant 适配器
# ============================================================
def test_xtquant_adapter():
    print("\n=== Lv.A Test: XtQuant 适配器（mock模式）===")
    from xtquant_adapter import XtQuantAdapter

    adapter = XtQuantAdapter(mock_mode=True)
    assert adapter.connect() == True
    print("  连接 OK（mock 模式自动降级）")

    # 买入
    order = adapter.buy("000001.SZ", 12.34, 1000)
    print(f"  买单: {order.status} qty={order.filled_quantity} price={order.filled_price}")
    assert order.status == "filled"

    # 卖出
    order2 = adapter.sell("000001.SZ", 13.00, 500)
    print(f"  卖单: {order2.status} qty={order2.filled_quantity}")
    assert order2.status == "filled"

    # 查询
    asset = adapter.query_asset()
    print(f"  资金: 总{asset['total_assets']:.0f} 现金{asset['cash']:.0f}")
    print("  PASS")


# ============================================================
# Lv.B: Alpha158 因子库
# ============================================================
def test_alpha158():
    print("\n=== Lv.B Test: Alpha158 因子库 ===")
    from alpha158 import get_alpha158_factors, compute_all_factors, compute_ic

    # 造数据
    np.random.seed(42)
    n = 250
    dates = pd.bdate_range("2024-01-01", periods=n)
    close = 100 * np.cumprod(1 + np.random.normal(0.001, 0.02, n))
    df = pd.DataFrame({
        "open": close * (1 + np.random.normal(0, 0.003, n)),
        "high": close * 1.02,
        "low": close * 0.98,
        "close": close,
        "volume": np.random.randint(1e6, 5e6, n),
    }, index=dates)

    # 因子数量
    factors = get_alpha158_factors()
    print(f"  注册因子数: {len(factors)}")
    assert len(factors) >= 60

    # 计算
    factor_df = compute_all_factors(df)
    print(f"  因子矩阵: {factor_df.shape}")
    assert factor_df.shape[1] >= 60

    # IC 评估
    future_return = df["close"].pct_change(5).shift(-5)
    ic = compute_ic(factor_df, future_return)
    print(f"  Top 5 因子 IC:")
    for name, val in ic.head().items():
        print(f"    {name}: {val:.4f}")

    print("  PASS")


# ============================================================
# Lv.C: 市场情报模块
# ============================================================
def test_market_intel():
    print("\n=== Lv.C Test: 市场情报（mock，无网络降级）===")
    from market_intel import (
        get_zt_pool, get_dragon_table, get_north_flow_today,
        get_market_sentiment,
    )

    # 这些在沙箱内会因网络失败返回空 DataFrame
    zt = get_zt_pool()
    print(f"  涨停池: {len(zt)} 条（无网络时为0属正常）")

    sentiment = get_market_sentiment()
    print(f"  情绪: {sentiment.get('mood')} score={sentiment.get('score')}")
    print(f"  涨停={sentiment['zt_count']} 连板={sentiment['lianban_count']} 北向={sentiment['north_net_flow']:.0f}亿")

    # 接口不抛异常即通过
    assert "mood" in sentiment
    print("  PASS")


# ============================================================
# Lv.D: 事件驱动引擎
# ============================================================
def test_event_engine():
    print("\n=== Lv.D Test: 事件驱动引擎 ===")
    from event_engine import EventDrivenEngine, SignalData, BarData
    from config import BacktestConfig
    from realism import RealismConfig

    # 造数据
    np.random.seed(7)
    n = 100
    dates = pd.bdate_range("2024-01-01", periods=n)
    close = 100 * np.cumprod(1 + np.random.normal(0.001, 0.02, n))
    df = pd.DataFrame({
        "open": close * (1 + np.random.normal(0, 0.003, n)),
        "high": close * 1.02,
        "low": close * 0.98,
        "close": close,
        "volume": np.random.randint(1e6, 5e6, n),
    }, index=dates)

    # 策略：均线金叉买，死叉卖
    state = {"ma_short": [], "ma_long": []}

    def strategy(bar: BarData, portfolio) -> SignalData:
        state["ma_short"].append(bar.close)
        state["ma_long"].append(bar.close)
        if len(state["ma_short"]) < 20:
            return None
        s = np.mean(state["ma_short"][-5:])
        l = np.mean(state["ma_long"][-20:])
        if s > l:
            return SignalData(symbol="TEST", direction=1, target_position=1.0, price=bar.close)
        else:
            return SignalData(symbol="TEST", direction=0, target_position=0, price=bar.close)

    cfg = BacktestConfig(
        symbol="TEST", start_date="2024-01-01", end_date="2024-12-31",
        initial_capital=1_000_000, commission_rate=0, slippage_rate=0,
    )
    engine = EventDrivenEngine(cfg, realism=RealismConfig(enable=True))
    result = engine.run(df, strategy)

    perf = result["performance"]
    print(f"  总收益: {perf['total_return']:+.2f}%")
    print(f"  最大回撤: {perf['max_drawdown']:.2f}%")
    print(f"  成交数: {perf['total_trades']}")
    print(f"  最终权益: {perf['final_equity']:,.2f}")

    assert perf["total_trades"] > 0
    print("  PASS")


# ============================================================
# 综合集成：用 Alpha158 因子 + 事件驱动引擎 + XtQuant 模拟执行
# ============================================================
def test_full_integration():
    print("\n=== 综合集成: Alpha158→信号→事件驱动→XtQuant ===")
    from alpha158 import get_alpha158_factors
    from event_engine import EventDrivenEngine, SignalData, BarData
    from xtquant_adapter import XtQuantAdapter
    from config import BacktestConfig
    from realism import RealismConfig

    np.random.seed(11)
    n = 120
    dates = pd.bdate_range("2024-01-01", periods=n)
    close = 50 * np.cumprod(1 + np.random.normal(0.002, 0.018, n))
    df = pd.DataFrame({
        "open": close * (1 + np.random.normal(0, 0.003, n)),
        "high": close * 1.02,
        "low": close * 0.98,
        "close": close,
        "volume": np.random.randint(1e6, 5e6, n),
    }, index=dates)

    # 用 alpha158 的 roc20 + ma20 组合作为信号
    from alpha158 import make_roc, make_ma
    roc20 = make_roc(20)(df)
    ma20 = make_ma(20)(df)

    def strategy(bar: BarData, portfolio) -> SignalData:
        idx = df.index.get_loc(bar.timestamp)
        if idx < 20:
            return None
        r = roc20.iloc[idx]
        m = ma20.iloc[idx]
        if pd.notna(r) and pd.notna(m) and r > 0 and m > 0:
            return SignalData("TEST", 1, 1.0, bar.close)
        else:
            return SignalData("TEST", 0, 0, bar.close)

    cfg = BacktestConfig(symbol="TEST", initial_capital=1_000_000,
                          commission_rate=0, slippage_rate=0)
    engine = EventDrivenEngine(cfg, RealismConfig(enable=True))
    result = engine.run(df, strategy)
    print(f"  Alpha158-driven 策略收益: {result['performance']['total_return']:+.2f}%")

    # 把最后一个信号送到 XtQuant 适配器
    adapter = XtQuantAdapter(mock_mode=True)
    adapter.connect()
    final_signal = strategy(BarData("TEST", df.index[-1], df["open"].iloc[-1],
                                     df["high"].iloc[-1], df["low"].iloc[-1],
                                     df["close"].iloc[-1], df["volume"].iloc[-1]), None)
    if final_signal and final_signal.direction == 1:
        order = adapter.buy("000001.SZ", df["close"].iloc[-1], 1000)
        print(f"  实盘信号已送出: {order.status}")

    print("  PASS")


if __name__ == "__main__":
    test_xtquant_adapter()
    test_alpha158()
    test_market_intel()
    test_event_engine()
    test_full_integration()
    print("\nLv.A-D 全套集成测试通过")
