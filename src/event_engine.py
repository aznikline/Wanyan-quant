"""
event_engine.py - Lv.D 事件驱动回测引擎
====================================================
对比向量化引擎：
- 向量化：快但无法处理动态信号（如止损触发后新仓位）
- 事件驱动：慢但可以模拟真实交易过程，支持高频策略、动态加减仓
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass, field
from enum import Enum

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from realism import RealismConfig, apply_slippage, calc_transaction_cost
from config import BacktestConfig


# ============================================================
# 事件类型
# ============================================================
class EventType(Enum):
    BAR = "bar"            # 新K线
    SIGNAL = "signal"      # 策略信号
    ORDER = "order"        # 订单
    FILL = "fill"          # 成交
    TIMER = "timer"        # 定时器（如尾盘清仓）


@dataclass
class Event:
    type: EventType
    timestamp: pd.Timestamp
    data: Dict = field(default_factory=dict)


@dataclass
class BarData:
    """单根 K 线"""
    symbol: str
    timestamp: pd.Timestamp
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class SignalData:
    symbol: str
    direction: int        # 1=long, -1=short, 0=flat
    target_position: float = 1.0
    price: float = 0.0
    reason: str = ""


@dataclass
class OrderData:
    symbol: str
    direction: int        # 1=buy, -1=sell
    quantity: int
    price: float
    order_type: str = "market"  # market / limit
    status: str = "pending"


@dataclass
class FillData:
    symbol: str
    direction: int
    quantity: int
    fill_price: float
    cost: float
    timestamp: pd.Timestamp


# ============================================================
# 投资组合
# ============================================================
class Portfolio:
    """事件驱动投资组合"""
    def __init__(self, initial_capital: float, realism: RealismConfig):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.realism = realism
        self.positions: Dict[str, Dict] = {}   # {symbol: {qty, avg_cost}}
        self.fills: List[FillData] = []
        self.equity_curve: List[Dict] = []

    def on_fill(self, fill: FillData):
        """成交回调"""
        sym = fill.symbol
        if sym not in self.positions:
            self.positions[sym] = {"qty": 0, "avg_cost": 0.0}

        pos = self.positions[sym]

        if fill.direction == 1:  # buy
            cost_total = fill.fill_price * fill.quantity + fill.cost
            self.cash -= cost_total
            new_qty = pos["qty"] + fill.quantity
            pos["avg_cost"] = (pos["avg_cost"] * pos["qty"] +
                              fill.fill_price * fill.quantity) / new_qty if new_qty > 0 else 0
            pos["qty"] = new_qty
        else:  # sell
            self.cash += fill.fill_price * fill.quantity - fill.cost
            pos["qty"] -= fill.quantity
            if pos["qty"] <= 0:
                pos["qty"] = 0
                pos["avg_cost"] = 0

        self.fills.append(fill)

    def get_position(self, symbol: str) -> int:
        return self.positions.get(symbol, {}).get("qty", 0)

    def get_equity(self, current_prices: Dict[str, float]) -> float:
        """当前总权益"""
        equity = self.cash
        for sym, pos in self.positions.items():
            price = current_prices.get(sym, pos["avg_cost"])
            equity += price * pos["qty"]
        return equity

    def snapshot(self, timestamp: pd.Timestamp, current_prices: Dict[str, float]):
        """记录权益快照"""
        equity = self.get_equity(current_prices)
        self.equity_curve.append({
            "timestamp": timestamp,
            "equity": equity,
            "cash": self.cash,
            "positions": dict(self.positions),
        })


# ============================================================
# 事件驱动引擎主体
# ============================================================
class EventDrivenEngine:
    """
    事件驱动回测引擎
    输入：data + strategy_func
    输出：equity_curve / fills / 绩效
    """
    def __init__(self,
                 config: BacktestConfig,
                 realism: RealismConfig = None):
        self.config = config
        self.realism = realism or RealismConfig(enable=True)
        self.portfolio = Portfolio(config.initial_capital, self.realism)
        self.event_queue: List[Event] = []
        self._t1_locked: Dict[str, Dict] = {}   # T+1 锁定记录

    def run(self,
            data: pd.DataFrame,
            strategy_func: Callable[[BarData, Portfolio], Optional[SignalData]]) -> Dict:
        """
        逐根 Bar 推进
        strategy_func: (bar, portfolio) → SignalData 或 None
        """
        for ts, row in data.iterrows():
            bar = BarData(
                symbol=self.config.symbol,
                timestamp=ts,
                open=row["open"], high=row["high"],
                low=row["low"], close=row["close"],
                volume=row.get("volume", 0),
            )

            # 1. 策略生成信号
            signal = strategy_func(bar, self.portfolio)

            # 2. 信号转订单
            if signal:
                orders = self._signal_to_orders(signal, bar)

                # 3. 订单成交
                for order in orders:
                    fill = self._execute_order(order, bar)
                    if fill:
                        self.portfolio.on_fill(fill)

            # 4. 释放 T+1 锁定（次日所有锁定释放）
            today_str = str(ts.date())
            for sym in list(self._t1_locked.keys()):
                for lock_date in list(self._t1_locked[sym].keys()):
                    if lock_date < today_str:
                        del self._t1_locked[sym][lock_date]

            # 5. 记录权益
            self.portfolio.snapshot(ts, {self.config.symbol: row["close"]})

        return self._summarize()

    def _signal_to_orders(self, signal: SignalData, bar: BarData) -> List[OrderData]:
        """信号转订单"""
        orders = []
        current_qty = self.portfolio.get_position(signal.symbol)
        # 目标股数：按总资产的 target_position 比例
        equity = self.portfolio.get_equity({signal.symbol: bar.close})
        target_value = equity * abs(signal.target_position) * (1 if signal.direction > 0 else 0)
        target_qty = int(target_value / bar.close) // 100 * 100 if bar.close > 0 else 0

        delta = target_qty - current_qty
        if delta > 0:
            orders.append(OrderData(
                symbol=signal.symbol, direction=1,
                quantity=delta, price=bar.close,
            ))
        elif delta < 0:
            # T+1 检查
            available = current_qty
            if self.realism.enable_t_plus_1:
                locked = sum(self._t1_locked.get(signal.symbol, {}).values())
                available = max(0, current_qty - locked)
            sell_qty = min(abs(delta), available)
            if sell_qty > 0:
                orders.append(OrderData(
                    symbol=signal.symbol, direction=-1,
                    quantity=sell_qty, price=bar.close,
                ))
        return orders

    def _execute_order(self, order: OrderData, bar: BarData) -> Optional[FillData]:
        """执行订单 → 成交"""
        # 涨跌停检查
        if self.realism.enable_price_limit:
            from realism import compute_limit_prices, is_limit_up, is_limit_down
            # 简化：用昨日收盘 = open（实际应传入）
            pre_close = bar.open
            upper = pre_close * (1 + self.realism.price_limit_pct)
            lower = pre_close * (1 - self.realism.price_limit_pct)
            if order.direction == 1 and bar.open >= upper - 0.005:
                return None  # 涨停买不到
            if order.direction == -1 and bar.open <= lower + 0.005:
                return None  # 跌停卖不掉

        # 滑点
        fill_price = apply_slippage(
            bar.open, order.direction, self.realism)

        # 资金检查
        amount = fill_price * order.quantity
        cost = calc_transaction_cost(
            amount, "buy" if order.direction == 1 else "sell",
            self.realism)["total"]

        if order.direction == 1 and amount + cost > self.portfolio.cash:
            # 减量
            max_qty = int(self.portfolio.cash / (fill_price * 1.005)) // 100 * 100
            if max_qty <= 0:
                return None
            order.quantity = max_qty
            amount = fill_price * order.quantity
            cost = calc_transaction_cost(amount, "buy", self.realism)["total"]

        # 记录 T+1 锁定
        if order.direction == 1 and self.realism.enable_t_plus_1:
            today_str = str(bar.timestamp.date())
            if order.symbol not in self._t1_locked:
                self._t1_locked[order.symbol] = {}
            self._t1_locked[order.symbol][today_str] = (
                self._t1_locked[order.symbol].get(today_str, 0) + order.quantity)

        return FillData(
            symbol=order.symbol,
            direction=order.direction,
            quantity=order.quantity,
            fill_price=fill_price,
            cost=cost,
            timestamp=bar.timestamp,
        )

    def _summarize(self) -> Dict:
        """生成绩效摘要"""
        eq_df = pd.DataFrame(self.portfolio.equity_curve).set_index("timestamp")
        final_equity = eq_df["equity"].iloc[-1] if not eq_df.empty else self.config.initial_capital
        total_return = final_equity / self.config.initial_capital - 1

        # 最大回撤
        rolling_max = eq_df["equity"].expanding().max()
        drawdown = (eq_df["equity"] - rolling_max) / rolling_max
        max_dd = drawdown.min() if not drawdown.empty else 0

        return {
            "equity_curve": eq_df["equity"],
            "drawdown_curve": drawdown,
            "fills": self.portfolio.fills,
            "performance": {
                "total_return": total_return * 100,
                "final_equity": final_equity,
                "max_drawdown": abs(max_dd) * 100,
                "total_trades": len(self.portfolio.fills),
            },
        }
