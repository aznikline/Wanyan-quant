"""
test_paper_trader.py - Lv.3 模拟盘交易引擎验证
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datetime import date, datetime, timedelta
from paper_trader import (
    MockAccount, BrokerAdapter, PaperTrader,
    Order, OrderSide, OrderStatus, Position,
)
from realism import RealismConfig
from live_signal import TradeSignal


def test_mock_account_buy_sell():
    print("\n=== Test 1: MockAccount 买入卖出基础 ===")
    acc = MockAccount(initial_capital=100_000)

    # 买入 1000 股 @ 10 元
    o = acc.buy("000001.SZ", "平安银行", 10.0, 1000, today="2026-05-22")
    print(f"  买单: {o.status.value} 成交{o.filled_quantity}股@{o.filled_price:.4f} 成本{o.cost:.2f}")
    assert o.status == OrderStatus.FILLED
    assert o.filled_quantity == 1000

    pos = acc.get_position("000001.SZ")
    assert pos.quantity == 1000
    print(f"  持仓: {pos.quantity}股 均价{pos.avg_cost:.4f}")

    # T+1：当日卖不出
    o2 = acc.sell("000001.SZ", "平安银行", 11.0, 500, today="2026-05-22")
    print(f"  当日卖单: {o2.status.value} reason={o2.reason}")
    assert o2.status == OrderStatus.REJECTED

    # 次日可卖
    o3 = acc.sell("000001.SZ", "平安银行", 11.0, 500, today="2026-05-23")
    print(f"  次日卖单: {o3.status.value} 成交{o3.filled_quantity}股@{o3.filled_price:.4f}")
    assert o3.status == OrderStatus.FILLED
    assert o3.filled_quantity == 500

    print("  PASS")


def test_mock_account_insufficient_cash():
    print("\n=== Test 2: 资金不足自动减量 ===")
    acc = MockAccount(initial_capital=10_000)
    o = acc.buy("000001.SZ", "平安银行", 10.0, 5000, today="2026-05-22")
    print(f"  尝试买5000股需50000+成本，但只有10000")
    print(f"  实际成交: {o.filled_quantity}股 @{o.filled_price:.4f}")
    assert o.filled_quantity <= 1000
    assert o.filled_quantity > 0
    assert acc.cash >= 0
    print("  PASS")


def test_position_pnl():
    print("\n=== Test 3: 持仓盈亏更新 ===")
    acc = MockAccount(initial_capital=100_000)
    acc.buy("000001.SZ", "平安银行", 10.0, 1000, today="2026-05-22")
    acc.update_prices({"000001.SZ": 12.0})
    pos = acc.get_position("000001.SZ")
    print(f"  浮盈: {pos.unrealized_pnl:.2f} ({pos.unrealized_pnl_pct:.2f}%)")
    # 含滑点：买入约 10.01 元，现价 12 元，浮盈约 (12-10.01)*1000≈1990
    assert pos.unrealized_pnl > 1900
    print("  PASS")


def test_account_snapshot():
    print("\n=== Test 4: 账户快照 ===")
    acc = MockAccount(initial_capital=100_000)
    acc.buy("000001.SZ", "平安银行", 10.0, 1000, today="2026-05-22")
    acc.update_prices({"000001.SZ": 11.0})
    snap = acc.snapshot("2026-05-22")
    print(f"  总资产: {snap.total_assets:.2f}")
    print(f"  现金:  {snap.cash:.2f}")
    print(f"  市值:  {snap.market_value:.2f}")
    print(f"  日盈亏: {snap.daily_pnl:+.2f}")
    assert snap.total_assets > 100_000
    print("  PASS")


def test_broker_adapter_mock():
    print("\n=== Test 5: BrokerAdapter mock 模式 ===")
    broker = BrokerAdapter(mode="mock", initial_capital=100_000)
    o = broker.buy("000001.SZ", "平安银行", 10.0, 1000, today="2026-05-22")
    assert o.status == OrderStatus.FILLED
    assert broker.account.cash < 100_000
    print(f"  下单成功，剩余现金: {broker.account.cash:.2f}")
    print("  PASS")


def test_paper_trader_execute_signal():
    print("\n=== Test 6: PaperTrader 执行信号闭环 ===")
    broker = BrokerAdapter(mode="mock", initial_capital=100_000)
    trader = PaperTrader(broker, trade_dir="/tmp/paper_trades_test")

    # 信号：买入 50% 仓位
    sig = TradeSignal(
        symbol="000001.SZ", name="平安银行",
        date="2026-05-22", action="buy", position=0.5,
        price=10.0, strategy="测试", reason="MA金叉",
    )
    o = trader.execute_signal(sig, today="2026-05-22")
    print(f"  执行买入: status={o.status.value} qty={o.filled_quantity}")
    assert o.status == OrderStatus.FILLED

    # 卖出信号：清仓
    sig2 = TradeSignal(
        symbol="000001.SZ", name="平安银行",
        date="2026-05-23", action="sell", position=1.0,
        price=11.0, strategy="测试", reason="止盈",
    )
    o2 = trader.execute_signal(sig2, today="2026-05-23")
    print(f"  执行卖出: status={o2.status.value} qty={o2.filled_quantity}")
    assert o2.status == OrderStatus.FILLED

    # 保存日志
    path = trader.save_daily_log("2026-05-23")
    print(f"  日志保存: {path}")
    assert Path(path).exists()
    print("  PASS")


def test_full_simulation():
    print("\n=== Test 7: 完整一周模拟 ===")
    broker = BrokerAdapter(mode="mock", initial_capital=1_000_000)
    trader = PaperTrader(broker)

    # 模拟一周交易：买 → 持 → 加仓 → 减仓 → 清仓
    days = ["2026-05-18", "2026-05-19", "2026-05-20", "2026-05-21", "2026-05-22"]
    prices = [10.0, 10.5, 11.0, 11.5, 12.0]
    actions = ["buy", "hold", "buy", "sell", "sell"]
    positions = [0.3, 0, 0.3, 0.5, 1.0]

    for d, p, a, pos in zip(days, prices, actions, positions):
        sig = TradeSignal("000001.SZ", "平安银行", d, a, pos, p, "测试")
        trader.execute_signal(sig, today=d)
        broker.account.update_prices({"000001.SZ": p})
        broker.account.snapshot(d)

    print(broker.account.summary())
    final = broker.account.snapshot("2026-05-22")
    print(f"  一周总收益率: {(final.total_assets / 1_000_000 - 1) * 100:+.2f}%")
    print("  PASS")


if __name__ == "__main__":
    test_mock_account_buy_sell()
    test_mock_account_insufficient_cash()
    test_position_pnl()
    test_account_snapshot()
    test_broker_adapter_mock()
    test_paper_trader_execute_signal()
    test_full_simulation()
    print("\nLv.3 模拟盘交易引擎全部测试通过")
