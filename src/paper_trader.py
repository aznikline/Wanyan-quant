"""
paper_trader.py - Lv.3 模拟盘交易引擎
====================================================
功能：
1. MockAccount：本地模拟账户（持仓/资金/成交/冻结）
2. PaperTrader：信号→下单→账户管理 全闭环
3. BrokerAdapter：抽象桥接层，mock / easytrader / qmt 三种模式
4. 交易日志与绩效追踪
"""
import pandas as pd
import numpy as np
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json

import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).parent))

from realism import RealismConfig, calc_transaction_cost, apply_slippage


# ============================================================
# 数据结构
# ============================================================
class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    """订单"""
    order_id: str
    symbol: str
    name: str
    side: OrderSide
    price: float
    quantity: int
    status: OrderStatus = OrderStatus.PENDING
    filled_price: float = 0.0
    filled_quantity: int = 0
    filled_time: str = ""
    cost: float = 0.0
    reason: str = ""


@dataclass
class Position:
    """持仓"""
    symbol: str
    name: str
    quantity: int = 0
    avg_cost: float = 0.0      # 持仓均价
    current_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    available: int = 0         # 可卖数量（T+1后）


@dataclass
class AccountSnapshot:
    """账户快照"""
    date: str
    total_assets: float
    cash: float
    market_value: float
    unrealized_pnl: float
    positions: Dict[str, Position] = field(default_factory=dict)
    daily_pnl: float = 0.0
    daily_return_pct: float = 0.0


# ============================================================
# MockAccount - 本地模拟账户
# ============================================================
class MockAccount:
    """本地模拟账户，完整模拟 A 股交易规则"""

    def __init__(self, initial_capital: float = 1_000_000,
                 realism_config: RealismConfig = None):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.realism = realism_config or RealismConfig(enable=True)
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.snapshots: Dict[str, AccountSnapshot] = {}
        self._order_counter = 0
        # T+1 锁定记录：{symbol: {date_str: quantity}}
        self._t1_lock: Dict[str, Dict[str, int]] = {}

    def _next_order_id(self) -> str:
        self._order_counter += 1
        return f"ORD-{self._order_counter:06d}"

    def get_position(self, symbol: str) -> Position:
        return self.positions.get(symbol, Position(symbol=symbol, name=symbol))

    def get_available_quantity(self, symbol: str, today: str = "") -> int:
        """可卖数量 = 总持仓 - T+1 锁定"""
        pos = self.positions.get(symbol)
        if not pos:
            return 0
        locked = 0
        if self.realism.enable_t_plus_1 and symbol in self._t1_lock:
            for lock_date, qty in self._t1_lock[symbol].items():
                if lock_date >= today:  # 今天买的还不能卖
                    locked += qty
        return max(0, pos.quantity - locked)

    def buy(self, symbol: str, name: str, price: float, quantity: int,
            today: str = "") -> Order:
        """买入"""
        order = Order(
            order_id=self._next_order_id(),
            symbol=symbol, name=name,
            side=OrderSide.BUY,
            price=price, quantity=quantity,
        )

        # 滑点
        filled_price = price
        if self.realism.enable and self.realism.enable_slippage:
            filled_price = apply_slippage(price, 1, self.realism)

        # 成本
        amount = filled_price * quantity
        cost_detail = calc_transaction_cost(amount, "buy", self.realism)
        total_cost = amount + cost_detail["total"]

        # 检查资金
        if total_cost > self.cash:
            # 减少数量
            max_qty = int(self.cash / (filled_price * (1 + self.realism.commission_rate + self.realism.transfer_fee_rate + 0.001)))
            max_qty = max(max_qty // 100 * 100, 0)  # A 股 100 股整数倍
            if max_qty == 0:
                order.status = OrderStatus.REJECTED
                order.reason = f"资金不足: 需{total_cost:.0f} 可用{self.cash:.0f}"
                self.orders.append(order)
                return order
            quantity = max_qty
            amount = filled_price * quantity
            cost_detail = calc_transaction_cost(amount, "buy", self.realism)
            total_cost = amount + cost_detail["total"]

        # A 股 100 股整数倍
        quantity = quantity // 100 * 100
        if quantity <= 0:
            order.status = OrderStatus.REJECTED
            order.reason = "买入数量不足100股"
            self.orders.append(order)
            return order

        # 扣资金
        self.cash -= total_cost

        # 更新持仓
        if symbol in self.positions:
            pos = self.positions[symbol]
            total_qty = pos.quantity + quantity
            pos.avg_cost = (pos.avg_cost * pos.quantity + filled_price * quantity) / total_qty
            pos.quantity = total_qty
        else:
            self.positions[symbol] = Position(
                symbol=symbol, name=name,
                quantity=quantity, avg_cost=filled_price,
                current_price=filled_price,
                market_value=filled_price * quantity,
            )

        # T+1 锁定
        if self.realism.enable_t_plus_1:
            if symbol not in self._t1_lock:
                self._t1_lock[symbol] = {}
            self._t1_lock[symbol][today] = self._t1_lock[symbol].get(today, 0) + quantity

        order.status = OrderStatus.FILLED
        order.filled_price = filled_price
        order.filled_quantity = quantity
        order.filled_time = today
        order.cost = cost_detail["total"]
        self.orders.append(order)
        return order

    def sell(self, symbol: str, name: str, price: float, quantity: int,
             today: str = "") -> Order:
        """卖出"""
        order = Order(
            order_id=self._next_order_id(),
            symbol=symbol, name=name,
            side=OrderSide.SELL,
            price=price, quantity=quantity,
        )

        pos = self.positions.get(symbol)
        if not pos or pos.quantity <= 0:
            order.status = OrderStatus.REJECTED
            order.reason = f"无持仓: {symbol}"
            self.orders.append(order)
            return order

        # 可卖数量
        available = self.get_available_quantity(symbol, today)
        quantity = min(quantity, available, pos.quantity)
        quantity = quantity // 100 * 100
        if quantity <= 0:
            order.status = OrderStatus.REJECTED
            order.reason = f"可卖为0（T+1锁定）: {symbol}"
            self.orders.append(order)
            return order

        # 滑点
        filled_price = price
        if self.realism.enable and self.realism.enable_slippage:
            filled_price = apply_slippage(price, -1, self.realism)

        # 收入
        amount = filled_price * quantity
        cost_detail = calc_transaction_cost(amount, "sell", self.realism)
        net_income = amount - cost_detail["total"]

        # 加资金
        self.cash += net_income

        # 更新持仓
        pos.quantity -= quantity
        if pos.quantity <= 0:
            del self.positions[symbol]

        order.status = OrderStatus.FILLED
        order.filled_price = filled_price
        order.filled_quantity = quantity
        order.filled_time = today
        order.cost = cost_detail["total"]
        self.orders.append(order)
        return order

    def update_prices(self, prices: Dict[str, float]):
        """更新持仓市值"""
        for symbol, price in prices.items():
            if symbol in self.positions:
                pos = self.positions[symbol]
                pos.current_price = price
                pos.market_value = price * pos.quantity
                pos.unrealized_pnl = (price - pos.avg_cost) * pos.quantity
                pos.unrealized_pnl_pct = (price / pos.avg_cost - 1) * 100 if pos.avg_cost > 0 else 0

    def snapshot(self, today: str) -> AccountSnapshot:
        """账户快照"""
        market_value = sum(p.market_value for p in self.positions.values())
        unrealized_pnl = sum(p.unrealized_pnl for p in self.positions.values())
        total = self.cash + market_value

        prev_total = self.initial_capital
        if self.snapshots:
            last_date = max(self.snapshots.keys())
            prev_total = self.snapshots[last_date].total_assets

        snap = AccountSnapshot(
            date=today,
            total_assets=total,
            cash=self.cash,
            market_value=market_value,
            unrealized_pnl=unrealized_pnl,
            positions={k: v for k, v in self.positions.items()},
            daily_pnl=total - prev_total,
            daily_return_pct=(total / prev_total - 1) * 100 if prev_total > 0 else 0,
        )
        self.snapshots[today] = snap
        return snap

    def release_t1_locks(self, today: str):
        """释放 T+1 锁定（昨日及更早的可卖）"""
        # 在实际调用中，today 之后的 lock 不再限制
        pass  # get_available_quantity 已通过日期判断实现

    def summary(self) -> str:
        """账户摘要"""
        market_value = sum(p.market_value for p in self.positions.values())
        total = self.cash + market_value
        pnl = total - self.initial_capital
        pnl_pct = pnl / self.initial_capital * 100

        lines = [
            f"========== 模拟账户 ==========",
            f"初始资金: {self.initial_capital:>12,.0f}",
            f"可用现金: {self.cash:>12,.2f}",
            f"持仓市值: {market_value:>12,.2f}",
            f"总资产:   {total:>12,.2f}",
            f"总盈亏:   {pnl:>+12,.2f} ({pnl_pct:>+.2f}%)",
            f"持仓数:   {len(self.positions)}",
            f"成交笔数: {len([o for o in self.orders if o.status == OrderStatus.FILLED])}",
        ]

        if self.positions:
            lines.append("-" * 40)
            lines.append("持仓明细:")
            for sym, pos in self.positions.items():
                lines.append(
                    f"  {pos.name}({sym}): {pos.quantity}股 "
                    f"均价{pos.avg_cost:.2f} 现价{pos.current_price:.2f} "
                    f"浮盈{pos.unrealized_pnl:+,.2f}({pos.unrealized_pnl_pct:+.2f}%)"
                )

        lines.append("=" * 40)
        return "\n".join(lines)


# ============================================================
# BrokerAdapter - 券商桥接抽象层
# ============================================================
class BrokerMode(Enum):
    MOCK = "mock"           # 本地模拟
    EASYTRADER = "easytrader"  # 同花顺/通达信
    QMT = "qmt"             # MiniQMT


class BrokerAdapter:
    """
    券商适配器：统一接口，mock 可直接跑，easytrader/qmt 在本地客户端环境使用。
    """

    def __init__(self, mode: str = "mock", **kwargs):
        self.mode = BrokerMode(mode)
        self._broker = None

        if self.mode == BrokerMode.MOCK:
            self._account = MockAccount(
                initial_capital=kwargs.get("initial_capital", 1_000_000),
                realism_config=kwargs.get("realism_config", RealismConfig(enable=True)),
            )
        elif self.mode == BrokerMode.EASYTRADER:
            self._setup_easytrader(kwargs)
        elif self.mode == BrokerMode.QMT:
            self._setup_qmt(kwargs)

    def _setup_easytrader(self, kwargs):
        """初始化 easytrader（需要本地客户端运行）"""
        try:
            import easytrader
            client = kwargs.get("client", "ths")  # ths=同花顺, yjb=佣金宝
            self._broker = easytrader.use(client)
            if "exe_path" in kwargs:
                self._broker.connect(kwargs["exe_path"])
        except ImportError:
            raise ImportError("easytrader 未安装: pip install easytrader")

    def _setup_qmt(self, kwargs):
        """初始化 MiniQMT"""
        # QMT 需要本地运行 xtquant
        try:
            from xtquant import xttrader
            # 具体初始化留给用户
        except ImportError:
            raise ImportError("xtquant 未安装，请参考迅投 QMT 文档")

    @property
    def account(self) -> MockAccount:
        if self.mode != BrokerMode.MOCK:
            raise RuntimeError("仅 mock 模式可访问 MockAccount")
        return self._account

    def buy(self, symbol: str, name: str, price: float, quantity: int,
            today: str = "") -> Order:
        if self.mode == BrokerMode.MOCK:
            return self._account.buy(symbol, name, price, quantity, today)
        elif self.mode == BrokerMode.EASYTRADER:
            return self._easytrader_buy(symbol, price, quantity)
        elif self.mode == BrokerMode.QMT:
            return self._qmt_buy(symbol, price, quantity)

    def sell(self, symbol: str, name: str, price: float, quantity: int,
             today: str = "") -> Order:
        if self.mode == BrokerMode.MOCK:
            return self._account.sell(symbol, name, price, quantity, today)
        elif self.mode == BrokerMode.EASYTRADER:
            return self._easytrader_sell(symbol, price, quantity)
        elif self.mode == BrokerMode.QMT:
            return self._qmt_sell(symbol, price, quantity)

    def _easytrader_buy(self, symbol, price, quantity):
        self._broker.buy(security=symbol, price=price, amount=quantity)
        return Order("LIVE", symbol, symbol, OrderSide.BUY, price, quantity, OrderStatus.FILLED)

    def _easytrader_sell(self, symbol, price, quantity):
        self._broker.sell(security=symbol, price=price, amount=quantity)
        return Order("LIVE", symbol, symbol, OrderSide.SELL, price, quantity, OrderStatus.FILLED)

    def _qmt_buy(self, symbol, price, quantity):
        # TODO: xtquant 下单接口
        return Order("LIVE", symbol, symbol, OrderSide.BUY, price, quantity, OrderStatus.PENDING)

    def _qmt_sell(self, symbol, price, quantity):
        return Order("LIVE", symbol, symbol, OrderSide.SELL, price, quantity, OrderStatus.PENDING)


# ============================================================
# PaperTrader - 模拟盘主控
# ============================================================
class PaperTrader:
    """
    模拟盘交易主控：
    信号 → 订单 → 成交 → 账户 → 日志 → 绩效
    """

    def __init__(self, broker: BrokerAdapter, trade_dir: str = "paper_trades"):
        self.broker = broker
        self.trade_dir = Path(trade_dir)
        self.trade_dir.mkdir(parents=True, exist_ok=True)
        self.trade_log: List[Dict] = []

    def execute_signal(self, signal, today: str = "") -> Optional[Order]:
        """执行一个 TradeSignal"""
        if not today:
            today = datetime.now().strftime("%Y-%m-%d")

        symbol = signal.symbol
        name = signal.name
        price = signal.price
        action = signal.action
        position_target = signal.position

        if action == "hold":
            return None

        if self.broker.mode == BrokerMode.MOCK:
            account = self.broker.account

            if action == "buy":
                # 计算目标仓位对应的股数
                target_value = account.cash * position_target
                quantity = int(target_value / price) if price > 0 else 0
                quantity = quantity // 100 * 100
                order = self.broker.buy(symbol, name, price, quantity, today)

            elif action == "sell":
                pos = account.get_position(symbol)
                if pos.quantity > 0:
                    sell_qty = int(pos.quantity * position_target)
                    sell_qty = sell_qty // 100 * 100
                    order = self.broker.sell(symbol, name, price, sell_qty, today)
                else:
                    order = None
            else:
                order = None

            if order and order.status == OrderStatus.FILLED:
                self.trade_log.append({
                    "date": today,
                    "symbol": symbol,
                    "name": name,
                    "action": action,
                    "price": order.filled_price,
                    "quantity": order.filled_quantity,
                    "cost": order.cost,
                    "reason": signal.reason,
                })

            return order

        # easytrader / qmt 模式
        if action == "buy":
            target_value = 100000 * position_target  # 简化
            quantity = int(target_value / price) // 100 * 100
            return self.broker.buy(symbol, name, price, quantity, today)
        elif action == "sell":
            return self.broker.sell(symbol, name, price, 100, today)  # 简化
        return None

    def save_daily_log(self, today: str = ""):
        """保存当日交易日志"""
        if not today:
            today = datetime.now().strftime("%Y-%m-%d")

        log_path = self.trade_dir / f"{today}.json"
        data = {
            "date": today,
            "trades": self.trade_log,
        }

        if self.broker.mode == BrokerMode.MOCK:
            snap = self.broker.account.snapshot(today)
            data["account"] = {
                "total_assets": snap.total_assets,
                "cash": snap.cash,
                "market_value": snap.market_value,
                "daily_pnl": snap.daily_pnl,
                "daily_return_pct": snap.daily_return_pct,
            }

        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return str(log_path)
