"""
xtquant_adapter.py - Lv.A QMT/MiniQMT 真实交易适配器
====================================================
功能：
1. 封装 xtdata（行情）+ xttrader（交易），统一接口给 BrokerAdapter 用
2. 本地无 QMT 环境时自动降级为 MockQMT，所有调用走本地模拟
3. 真实环境只需 pip install xtquant + 启动 MiniQMT 客户端即可生效

使用方法（真实环境）：
    adapter = XtQuantAdapter(
        account_id="您的资金账号",
        client_path=r"C:\\国信MiniQMT\\bin.x64\\XtMiniQmt.exe",
        session_id=66666,
    )
    adapter.connect()
    adapter.buy("000001.SZ", 12.34, 100)
"""
import sys
from pathlib import Path
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

# 延迟导入 xtquant
def _import_xtquant():
    try:
        from xtquant import xtdata, xttrader
        from xtquant.xttype import StockAccount
        return xtdata, xttrader, StockAccount
    except ImportError:
        return None, None, None


@dataclass
class QmtOrder:
    """QMT 订单标准格式"""
    order_id: str
    symbol: str       # 600519.SH 格式
    price: float
    quantity: int
    direction: str    # 'buy' or 'sell'
    price_type: str = "limit"   # limit / market
    status: str = "pending"
    filled_quantity: int = 0
    filled_price: float = 0.0
    reject_reason: str = ""


# ============================================================
# 真实 QMT 适配器
# ============================================================
class XtQuantAdapter:
    """
    MiniQMT 真实交易适配器
    本地无 xtquant 库时自动降级为 MockQMT
    """

    def __init__(self,
                 account_id: str = "",
                 client_path: str = "",
                 session_id: int = 66666,
                 account_type: str = "STOCK",
                 mock_mode: bool = False):
        self.account_id = account_id
        self.client_path = client_path
        self.session_id = session_id
        self.account_type = account_type
        self.mock_mode = mock_mode

        self._xtdata = None
        self._xttrader = None
        self._account = None
        self._trader = None
        self._connected = False

        # 检查 xtquant 是否可用
        xtdata, xttrader, _StockAccount = _import_xtquant()
        if not xtdata or mock_mode:
            self.mock_mode = True
            print("[XtQuant] xtquant 未安装或 mock_mode=True，使用本地 mock")
        else:
            self._xtdata = xtdata
            self._xttrader = xttrader
            self._StockAccount = _StockAccount

    def connect(self) -> bool:
        """连接 MiniQMT 客户端"""
        if self.mock_mode:
            self._connected = True
            return True

        try:
            # 创建账户对象
            self._account = self._StockAccount(self.account_id, self.account_type)
            # 创建 trader
            self._trader = self._xttrader.XtQuantTrader(
                self.client_path, self.session_id)
            self._trader.start()
            ok = self._trader.connect()
            if ok < 0:
                raise RuntimeError(f"连接失败 code={ok}")
            sub = self._trader.subscribe(self._account)
            if sub < 0:
                raise RuntimeError(f"订阅失败 code={sub}")
            self._connected = True
            return True
        except Exception as e:
            print(f"[XtQuant] 连接失败: {e}, 降级为 mock 模式")
            self.mock_mode = True
            self._connected = True
            return False

    def _to_qmt_symbol(self, symbol: str) -> str:
        """000001.SZ → 000001.SZ（QMT 格式相同）"""
        return symbol

    def buy(self, symbol: str, price: float, quantity: int,
            price_type: str = "limit") -> QmtOrder:
        """限价买入"""
        if not self._connected:
            self.connect()

        order = QmtOrder(
            order_id=f"QMT-{datetime.now().strftime('%H%M%S%f')}",
            symbol=symbol, price=price, quantity=quantity,
            direction="buy", price_type=price_type,
        )

        if self.mock_mode:
            # mock 直接全部成交
            order.status = "filled"
            order.filled_quantity = quantity
            order.filled_price = price
            return order

        # 真实下单
        try:
            from xtquant import xtconstant
            price_type_map = {
                "limit": xtconstant.FIX_PRICE,
                "market": xtconstant.MARKET_SH_CONVERT_5_CANCEL,
            }
            seq = self._trader.order_stock(
                self._account, symbol, xtconstant.STOCK_BUY,
                quantity, price_type_map[price_type], price,
                "wanyan", order.order_id, "wanyan-quant")
            if seq < 0:
                order.status = "rejected"
                order.reject_reason = f"order_stock 返回 {seq}"
            else:
                order.order_id = str(seq)
                order.status = "submitted"
            return order
        except Exception as e:
            order.status = "rejected"
            order.reject_reason = str(e)
            return order

    def sell(self, symbol: str, price: float, quantity: int,
             price_type: str = "limit") -> QmtOrder:
        """限价卖出"""
        if not self._connected:
            self.connect()

        order = QmtOrder(
            order_id=f"QMT-{datetime.now().strftime('%H%M%S%f')}",
            symbol=symbol, price=price, quantity=quantity,
            direction="sell", price_type=price_type,
        )

        if self.mock_mode:
            order.status = "filled"
            order.filled_quantity = quantity
            order.filled_price = price
            return order

        try:
            from xtquant import xtconstant
            price_type_map = {
                "limit": xtconstant.FIX_PRICE,
                "market": xtconstant.MARKET_SH_CONVERT_5_CANCEL,
            }
            seq = self._trader.order_stock(
                self._account, symbol, xtconstant.STOCK_SELL,
                quantity, price_type_map[price_type], price,
                "wanyan", order.order_id, "wanyan-quant")
            if seq < 0:
                order.status = "rejected"
                order.reject_reason = f"order_stock 返回 {seq}"
            else:
                order.order_id = str(seq)
                order.status = "submitted"
            return order
        except Exception as e:
            order.status = "rejected"
            order.reject_reason = str(e)
            return order

    def query_asset(self) -> Dict:
        """查询资金"""
        if self.mock_mode:
            return {
                "cash": 1_000_000.0,
                "market_value": 0.0,
                "total_assets": 1_000_000.0,
                "frozen_cash": 0.0,
            }
        try:
            asset = self._trader.query_stock_asset(self._account)
            return {
                "cash": asset.cash,
                "market_value": asset.market_value,
                "total_assets": asset.total_asset,
                "frozen_cash": asset.frozen_cash,
            }
        except Exception as e:
            return {"error": str(e)}

    def query_positions(self) -> List[Dict]:
        """查询持仓"""
        if self.mock_mode:
            return []
        try:
            positions = self._trader.query_stock_positions(self._account)
            return [{
                "symbol": p.stock_code,
                "volume": p.volume,
                "can_use_volume": p.can_use_volume,
                "avg_price": p.avg_price,
                "market_value": p.market_value,
            } for p in positions]
        except Exception as e:
            return [{"error": str(e)}]

    def get_latest_quote(self, symbol: str) -> Dict:
        """获取最新行情"""
        if self.mock_mode:
            import random
            return {"last": round(10 + random.random() * 5, 2), "volume": 100000}
        try:
            data = self._xtdata.get_full_tick([symbol])
            if symbol in data:
                t = data[symbol]
                return {"last": t["lastPrice"], "volume": t["volume"]}
            return {}
        except Exception as e:
            return {"error": str(e)}

    def disconnect(self):
        """断开连接"""
        if not self.mock_mode and self._trader:
            try:
                self._trader.stop()
            except Exception:
                pass
        self._connected = False


# ============================================================
# 集成到现有 BrokerAdapter
# ============================================================
def integrate_with_broker_adapter():
    """
    在 src/paper_trader.py 的 BrokerAdapter._setup_qmt 中接入：
        from xtquant_adapter import XtQuantAdapter
        self._qmt = XtQuantAdapter(
            account_id=kwargs["account_id"],
            client_path=kwargs["client_path"],
        )
        self._qmt.connect()
    """
    pass
