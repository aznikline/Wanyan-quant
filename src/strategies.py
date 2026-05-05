import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseStrategy(ABC):
    """策略基类 - 所有自定义策略继承此类"""
    
    name: str = "base_strategy"
    description: str = "基础策略类"
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        生成交易信号
        返回: 1=开多, -1=开空, 0=平仓
        """
        pass
    
    @abstractmethod
    def get_params_schema(self) -> Dict[str, Any]:
        """
        返回参数字典定义，用于前端自动生成控件
        格式: {
            "param_name": {
                "type": "int|float|str",
                "default": value,
                "min": min_value,
                "max": max_value,
                "description": "参数说明"
            }
        }
        """
        pass
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """参数合法性校验"""
        schema = self.get_params_schema()
        for name, value in params.items():
            if name not in schema:
                continue
            param_info = schema[name]
            if 'min' in param_info and value < param_info['min']:
                return False
            if 'max' in param_info and value > param_info['max']:
                return False
        return True


class DualMAStrategy(BaseStrategy):
    """双均线策略 - 金叉买入，死叉卖出"""
    
    name = "dual_ma"
    description = "经典双均线策略，短期均线上穿长期均线买入，下穿卖出"
    
    def __init__(self, short_period: int = 5, long_period: int = 20):
        self.short_period = short_period
        self.long_period = long_period
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data['close']
        ma_short = close.rolling(self.short_period).mean()
        ma_long = close.rolling(self.long_period).mean()
        
        # 金叉死叉判断
        golden_cross = (ma_short > ma_long) & (ma_short.shift(1) <= ma_long.shift(1))
        death_cross = (ma_short < ma_long) & (ma_short.shift(1) >= ma_long.shift(1))
        
        # 生成信号
        signals = pd.Series(0, index=data.index)
        signals[golden_cross] = 1
        signals[death_cross] = -1
        
        # 持有状态
        signals = signals.replace(0, np.nan).ffill().fillna(0)
        return signals
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {
            "short_period": {
                "type": "int",
                "default": 5,
                "min": 1,
                "max": 60,
                "description": "短期均线周期"
            },
            "long_period": {
                "type": "int",
                "default": 20,
                "min": 5,
                "max": 250,
                "description": "长期均线周期"
            }
        }


class MACDStrategy(BaseStrategy):
    """MACD策略"""
    
    name = "macd"
    description = "MACD指标策略，金叉买入，死叉卖出，配合顶背离底背离"
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data['close']
        ema_fast = close.ewm(span=self.fast_period).mean()
        ema_slow = close.ewm(span=self.slow_period).mean()
        macd = ema_fast - ema_slow
        signal = macd.ewm(span=self.signal_period).mean()
        
        golden_cross = (macd > signal) & (macd.shift(1) <= signal.shift(1))
        death_cross = (macd < signal) & (macd.shift(1) >= signal.shift(1))
        
        signals = pd.Series(0, index=data.index)
        signals[golden_cross] = 1
        signals[death_cross] = -1
        
        signals = signals.replace(0, np.nan).ffill().fillna(0)
        return signals
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {
            "fast_period": {"type": "int", "default": 12, "min": 5, "max": 30, "description": "快线周期"},
            "slow_period": {"type": "int", "default": 26, "min": 20, "max": 60, "description": "慢线周期"},
            "signal_period": {"type": "int", "default": 9, "min": 3, "max": 20, "description": "信号线周期"}
        }


class RSIStrategy(BaseStrategy):
    """RSI超买超卖策略"""
    
    name = "rsi"
    description = "RSI相对强弱指标策略，超卖区间买入，超买区间卖出"
    
    def __init__(self, period: int = 14, overbought: int = 70, oversold: int = 30):
        self.period = period
        self.overbought = overbought
        self.oversold = oversold
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data['close']
        delta = close.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(self.period).mean()
        avg_loss = loss.rolling(self.period).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        buy_signal = (rsi < self.oversold) & (rsi.shift(1) >= self.oversold)
        sell_signal = (rsi > self.overbought) & (rsi.shift(1) <= self.overbought)
        
        signals = pd.Series(0, index=data.index)
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        signals = signals.replace(0, np.nan).ffill().fillna(0)
        return signals
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {
            "period": {"type": "int", "default": 14, "min": 5, "max": 30, "description": "RSI周期"},
            "overbought": {"type": "int", "default": 70, "min": 60, "max": 90, "description": "超买阈值"},
            "oversold": {"type": "int", "default": 30, "min": 10, "max": 40, "description": "超卖阈值"}
        }


class BollingerStrategy(BaseStrategy):
    """布林带突破策略"""
    
    name = "bollinger"
    description = "布林带突破策略，突破上轨买入，跌破下轨卖出"
    
    def __init__(self, period: int = 20, std_dev: float = 2.0):
        self.period = period
        self.std_dev = std_dev
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data['close']
        mid = close.rolling(self.period).mean()
        std = close.rolling(self.period).std()
        upper = mid + self.std_dev * std
        lower = mid - self.std_dev * std
        
        break_upper = (close > upper) & (close.shift(1) <= upper.shift(1))
        break_lower = (close < lower) & (close.shift(1) >= lower.shift(1))
        
        signals = pd.Series(0, index=data.index)
        signals[break_upper] = 1
        signals[break_lower] = -1
        
        signals = signals.replace(0, np.nan).ffill().fillna(0)
        return signals
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {
            "period": {"type": "int", "default": 20, "min": 10, "max": 60, "description": "布林带周期"},
            "std_dev": {"type": "float", "default": 2.0, "min": 1.0, "max": 4.0, "description": "标准差倍数"}
        }


# 策略注册中心
STRATEGY_REGISTRY = {
    "双均线策略": DualMAStrategy,
    "MACD策略": MACDStrategy,
    "RSI超买超卖策略": RSIStrategy,
    "布林带突破策略": BollingerStrategy,
}


def get_all_strategies() -> List[str]:
    """获取所有可用策略名称"""
    return list(STRATEGY_REGISTRY.keys())


def create_strategy(name: str, **params) -> BaseStrategy:
    """创建策略实例"""
    if name not in STRATEGY_REGISTRY:
        raise ValueError(f"未知策略: {name}，可用策略: {list(STRATEGY_REGISTRY.keys())}")
    return STRATEGY_REGISTRY[name](**params)
