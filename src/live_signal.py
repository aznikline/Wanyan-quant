"""
live_signal.py - Lv.2 实时信号引擎
====================================================
功能：
1. 从 AKShare / Tushare / 本地缓存 增量拉取最新行情
2. 对最新行情跑策略 → 输出今日交易信号
3. 信号格式化 & 推送（飞书 / 文件 / 控制台）
4. 盘后定时任务入口
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field

import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).parent))

from data_loader import DataLoader, DataSource
from realism import RealismConfig, preprocess_signals
from config import BacktestConfig, RiskControlConfig, PositionConfig
from backtest_engine import BacktestEngine


# ============================================================
# 信号数据结构
# ============================================================
@dataclass
class TradeSignal:
    """单只标的的交易信号"""
    symbol: str
    name: str
    date: str                  # 信号日期 YYYY-MM-DD
    action: str                # 'buy' | 'sell' | 'hold'
    position: float            # 建议仓位 0.0~1.0
    price: float               # 当前收盘价
    strategy: str              # 策略名
    confidence: float = 0.0    # 信号置信度 0~1
    reason: str = ""           # 信号理由
    realism_enabled: bool = True

    def to_text(self) -> str:
        flag = "+" if self.action == "buy" else ("-" if self.action == "sell" else "=")
        return (
            f"[{self.date}] {self.name}({self.symbol}) {flag} "
            f"{self.action.upper()} 仓位{self.position:.0%} "
            f"价格{self.price:.2f} | {self.strategy}"
            + (f" | 真实模式" if self.realism_enabled else "")
            + (f" | {self.reason}" if self.reason else "")
        )


@dataclass
class SignalReport:
    """每日信号汇总报告"""
    date: str
    signals: List[TradeSignal] = field(default_factory=list)
    data_freshness: str = "unknown"   # 'fresh' | 'stale' | 'no_data'
    data_source: str = ""
    strategy: str = ""
    error: str = ""

    def summary(self) -> str:
        lines = [
            f"========== Rock Quant 每日信号 ==========",
            f"日期: {self.date}",
            f"数据源: {self.data_source}",
            f"数据新鲜度: {self.data_freshness}",
            f"策略: {self.strategy}",
            f"信号数: {len(self.signals)}",
            "-" * 40,
        ]
        buy_signals = [s for s in self.signals if s.action == "buy"]
        sell_signals = [s for s in self.signals if s.action == "sell"]
        hold_signals = [s for s in self.signals if s.action == "hold"]

        if buy_signals:
            lines.append(">>> 买入信号 <<<")
            for s in buy_signals:
                lines.append(f"  {s.to_text()}")
        if sell_signals:
            lines.append(">>> 卖出信号 <<<")
            for s in sell_signals:
                lines.append(f"  {s.to_text()}")
        if hold_signals:
            lines.append(f"  持仓观望: {len(hold_signals)} 只")

        if self.error:
            lines.append(f"[ERROR] {self.error}")

        lines.append("=" * 40)
        return "\n".join(lines)


# ============================================================
# 数据新鲜度检测
# ============================================================
def check_data_freshness(data: pd.DataFrame, max_stale_days: int = 2) -> str:
    """
    判断数据是否最新。
    返回 'fresh' | 'stale' | 'no_data'
    """
    if data is None or len(data) == 0:
        return "no_data"

    last_date = data.index[-1]
    if isinstance(last_date, pd.Timestamp):
        last_date = last_date.to_pydatetime().date()

    today = datetime.now().date()
    # 如果今天是周末，允许周五的数据
    weekday = today.weekday()
    if weekday == 5:   # 周六 → 允许周四
        threshold = today - timedelta(days=2)
    elif weekday == 6: # 周日 → 允许周五
        threshold = today - timedelta(days=2)
    else:
        threshold = today - timedelta(days=max_stale_days)

    if last_date >= threshold:
        return "fresh"
    return "stale"


# ============================================================
# 增量数据拉取
# ============================================================
def fetch_latest_data(
    symbol: str,
    start_date: str = "",
    end_date: str = "",
    data_source: str = "akshare",
    cache_dir: str = "data",
) -> pd.DataFrame:
    """
    拉取最新行情数据（增量：优先读缓存，再从数据源补齐）
    """
    loader = DataLoader(cache_dir=cache_dir, data_source=data_source)
    today = datetime.now().strftime("%Y-%m-%d")
    if not end_date:
        end_date = today
    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

    try:
        data = loader.load_data(symbol, start_date, end_date, use_cache=True)
        return data
    except Exception as e:
        # 降级：尝试模拟数据
        try:
            loader.set_data_source(DataSource.SIMULATED)
            return loader.load_data(symbol, start_date, end_date)
        except Exception:
            return pd.DataFrame()


# ============================================================
# 实时信号生成
# ============================================================
def generate_signals(
    symbol: str,
    symbol_name: str,
    strategy_name: str,
    strategy_params: Dict = None,
    data_source: str = "akshare",
    realism_config: RealismConfig = None,
    cache_dir: str = "data",
) -> SignalReport:
    """
    对单只标的生成今日交易信号。
    完整流程：拉数据 → 跑策略 → 过滤真实性 → 输出信号
    """
    today = datetime.now().strftime("%Y-%m-%d")
    report = SignalReport(date=today, data_source=data_source, strategy=strategy_name)

    # 1. 拉数据
    try:
        data = fetch_latest_data(symbol, data_source=data_source, cache_dir=cache_dir)
    except Exception as e:
        report.error = f"数据拉取失败: {e}"
        return report

    if data.empty:
        report.data_freshness = "no_data"
        report.error = "无数据"
        return report

    report.data_freshness = check_data_freshness(data)

    # 2. 创建策略 & 生成信号
    try:
        from strategies import create_strategy
        strategy = create_strategy(strategy_name)
        if strategy_params:
            for k, v in strategy_params.items():
                if hasattr(strategy, k):
                    setattr(strategy, k, v)
        signals = strategy.generate_signals(data)
    except Exception as e:
        report.error = f"策略执行失败: {e}"
        return report

    # 3. 真实性过滤
    r_cfg = realism_config or RealismConfig(enable=True)
    if r_cfg.enable:
        signals, _ = preprocess_signals(signals, data, r_cfg)

    # 4. 解析最后一个信号 → TradeSignal
    if len(signals) == 0:
        return report

    last_pos = float(signals.iloc[-1])
    prev_pos = float(signals.iloc[-2]) if len(signals) > 1 else 0.0
    last_price = float(data["close"].iloc[-1])
    last_date_str = str(data.index[-1].date()) if hasattr(data.index[-1], "date") else str(data.index[-1])

    # 判断动作
    if last_pos > 0.01 and prev_pos < 0.01:
        action = "buy"
    elif last_pos < -0.01 and prev_pos > -0.01:
        action = "sell"
    elif abs(last_pos) < 0.01 and abs(prev_pos) > 0.01:
        action = "sell"   # 平仓视作卖出
    else:
        action = "hold"

    # 置信度：用仓位变化幅度近似
    confidence = min(abs(last_pos - prev_pos), 1.0)

    sig = TradeSignal(
        symbol=symbol,
        name=symbol_name,
        date=last_date_str,
        action=action,
        position=abs(last_pos),
        price=last_price,
        strategy=strategy_name,
        confidence=confidence,
        realism_enabled=r_cfg.enable,
    )
    report.signals = [sig]
    return report


def generate_multi_signals(
    watchlist: Dict[str, str],        # {symbol: name}
    strategy_name: str,
    strategy_params: Dict = None,
    data_source: str = "akshare",
    realism_config: RealismConfig = None,
) -> SignalReport:
    """
    批量信号生成：对多只标的跑同一策略
    """
    today = datetime.now().strftime("%Y-%m-%d")
    all_report = SignalReport(date=today, data_source=data_source, strategy=strategy_name)

    for symbol, name in watchlist.items():
        try:
            r = generate_signals(symbol, name, strategy_name, strategy_params,
                                 data_source, realism_config)
            all_report.signals.extend(r.signals)
            if r.data_freshness == "stale":
                all_report.data_freshness = "stale"
            elif r.data_freshness == "fresh" and all_report.data_freshness != "stale":
                all_report.data_freshness = "fresh"
        except Exception as e:
            all_report.signals.append(TradeSignal(
                symbol=symbol, name=name, date=today,
                action="hold", position=0, price=0,
                strategy=strategy_name, reason=f"异常: {e}"
            ))

    return all_report


# ============================================================
# 推送通道
# ============================================================
def push_to_file(report: SignalReport, filepath: str = "signals/latest.txt") -> str:
    """信号写入文件"""
    p = Path(filepath)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(report.summary())
    return str(p)


def push_to_console(report: SignalReport):
    """信号打印到控制台"""
    print(report.summary())


# ============================================================
# CLI 入口（供 cron 或手动调用）
# ============================================================
def main():
    """每日信号生成入口"""
    import argparse
    parser = argparse.ArgumentParser(description="Rock Quant 每日信号生成")
    parser.add_argument("--symbols", nargs="+", default=["000001.SZ"], help="标的代码列表")
    parser.add_argument("--names", nargs="+", default=["平安银行"], help="标的名称列表")
    parser.add_argument("--strategy", default="双均线策略", help="策略名")
    parser.add_argument("--source", default="akshare", help="数据源: akshare/tushare/simulated")
    parser.add_argument("--output", default="signals/latest.txt", help="输出文件路径")
    args = parser.parse_args()

    watchlist = dict(zip(args.symbols, args.names))
    report = generate_multi_signals(watchlist, args.strategy, data_source=args.source)
    push_to_console(report)
    path = push_to_file(report, args.output)
    print(f"\n信号已写入: {path}")


if __name__ == "__main__":
    main()
