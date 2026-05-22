"""
test_live_signal.py - Lv.2 实时信号引擎验证
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from live_signal import (
    TradeSignal,
    SignalReport,
    check_data_freshness,
    fetch_latest_data,
    generate_signals,
    generate_multi_signals,
    push_to_file,
    push_to_console,
)
from realism import RealismConfig


def make_data(days=120, last_date=None):
    if last_date is None:
        last_date = datetime.now().date()
    dates = pd.bdate_range(end=last_date, periods=days)
    np.random.seed(7)
    close = 50 * np.cumprod(1 + np.random.normal(0.001, 0.015, days))
    df = pd.DataFrame({
        "open": close * (1 + np.random.normal(0, 0.003, days)),
        "high": close * 1.01,
        "low": close * 0.99,
        "close": close,
        "volume": np.random.randint(1e6, 5e6, days),
    }, index=dates)
    df["open"] = df["open"].clip(df["low"], df["high"])
    return df


def test_data_freshness():
    print("\n=== Test 1: 数据新鲜度判断 ===")
    fresh = make_data(last_date=datetime.now().date())
    stale = make_data(last_date=datetime.now().date() - timedelta(days=10))
    empty = pd.DataFrame()

    assert check_data_freshness(fresh) == "fresh"
    assert check_data_freshness(stale) == "stale"
    assert check_data_freshness(empty) == "no_data"
    print("  fresh / stale / no_data 三种状态判断正确")
    print("  PASS")


def test_signal_dataclass():
    print("\n=== Test 2: TradeSignal & SignalReport 格式化 ===")
    sig = TradeSignal(
        symbol="000001.SZ", name="平安银行",
        date="2026-05-22", action="buy", position=0.5,
        price=12.34, strategy="双均线策略", confidence=0.8,
        reason="MA5上穿MA20"
    )
    text = sig.to_text()
    assert "平安银行" in text and "BUY" in text and "12.34" in text
    print(f"  信号文本: {text}")

    report = SignalReport(date="2026-05-22", data_source="akshare", strategy="双均线")
    report.signals = [sig]
    s = report.summary()
    assert "Rock Quant" in s and "买入信号" in s
    print("  报告格式化正常")
    print("  PASS")


def test_generate_signals_with_simulated():
    print("\n=== Test 3: 模拟数据生成信号（完整闭环）===")
    report = generate_signals(
        symbol="000001.SZ",
        symbol_name="平安银行",
        strategy_name="双均线策略",
        data_source="simulated",
        realism_config=RealismConfig(enable=True),
    )
    print(f"  数据新鲜度: {report.data_freshness}")
    print(f"  信号数: {len(report.signals)}")
    if report.signals:
        print(f"  最新信号: {report.signals[0].to_text()}")
    assert report.error == "", f"应无报错，实际: {report.error}"
    assert len(report.signals) >= 1
    print("  PASS")


def test_multi_symbols():
    print("\n=== Test 4: 批量信号生成 ===")
    watchlist = {
        "000001.SZ": "平安银行",
        "600000.SH": "浦发银行",
        "000300.SH": "沪深300",
    }
    report = generate_multi_signals(
        watchlist,
        strategy_name="双均线策略",
        data_source="simulated",
    )
    print(f"  总信号数: {len(report.signals)}")
    for s in report.signals:
        print(f"    {s.to_text()}")
    assert len(report.signals) == 3
    print("  PASS")


def test_push_to_file():
    print("\n=== Test 5: 信号推送到文件 ===")
    sig = TradeSignal("000001.SZ", "平安银行", "2026-05-22", "buy", 0.5, 12.34, "双均线")
    report = SignalReport(date="2026-05-22", signals=[sig], strategy="双均线", data_source="simulated")
    out_path = "/tmp/wanyan_test_signal.txt"
    path = push_to_file(report, out_path)
    assert Path(path).exists()
    content = Path(path).read_text()
    assert "平安银行" in content
    print(f"  写入文件: {path}")
    print(f"  内容预览:\n{content[:200]}...")
    print("  PASS")


def test_full_workflow():
    print("\n=== Test 6: 完整工作流演示 ===")
    watchlist = {
        "000001.SZ": "平安银行",
        "600519.SH": "贵州茅台",
        "000300.SH": "沪深300",
    }
    report = generate_multi_signals(
        watchlist,
        strategy_name="MACD策略",
        data_source="simulated",
        realism_config=RealismConfig(enable=True),
    )
    push_to_console(report)
    print("  PASS")


if __name__ == "__main__":
    test_data_freshness()
    test_signal_dataclass()
    test_generate_signals_with_simulated()
    test_multi_symbols()
    test_push_to_file()
    test_full_workflow()
    print("\nLv.2 实时信号引擎全部测试通过")
