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


class KDJStrategy(BaseStrategy):
    """KDJ随机指标策略"""
    
    name = "kdj"
    description = "KDJ金叉买入，死叉卖出，超买超卖区域过滤"
    
    def __init__(self, n: int = 9, m1: int = 3, m2: int = 3, overbought: int = 80, oversold: int = 20):
        self.n = n
        self.m1 = m1
        self.m2 = m2
        self.overbought = overbought
        self.oversold = oversold
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        low_list = data['low'].rolling(self.n, min_periods=1).min()
        high_list = data['high'].rolling(self.n, min_periods=1).max()
        rsv = (data['close'] - low_list) / (high_list - low_list) * 100
        rsv = rsv.fillna(50)
        
        k = rsv.ewm(com=self.m1-1, adjust=False).mean()
        d = k.ewm(com=self.m2-1, adjust=False).mean()
        
        golden_cross = (k > d) & (k.shift(1) <= d.shift(1)) & (k < self.overbought)
        death_cross = (k < d) & (k.shift(1) >= d.shift(1)) & (k > self.oversold)
        
        signals = pd.Series(0, index=data.index)
        signals[golden_cross] = 1
        signals[death_cross] = -1
        
        signals = signals.replace(0, np.nan).ffill().fillna(0)
        return signals
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {
            "n": {"type": "int", "default": 9, "min": 5, "max": 30, "description": "RSV周期"},
            "m1": {"type": "int", "default": 3, "min": 2, "max": 10, "description": "K值平滑"},
            "m2": {"type": "int", "default": 3, "min": 2, "max": 10, "description": "D值平滑"},
            "overbought": {"type": "int", "default": 80, "min": 70, "max": 90, "description": "超买阈值"},
            "oversold": {"type": "int", "default": 20, "min": 10, "max": 40, "description": "超卖阈值"}
        }


class CCIStrategy(BaseStrategy):
    """CCI顺势指标策略"""
    
    name = "cci"
    description = "CCI突破+100买入，跌破-100卖出，抓趋势启动点"
    
    def __init__(self, period: int = 14, upper: int = 100, lower: int = -100):
        self.period = period
        self.upper = upper
        self.lower = lower
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        tp = (data['high'] + data['low'] + data['close']) / 3
        ma = tp.rolling(self.period).mean()
        md = tp.rolling(self.period).apply(lambda x: np.mean(np.abs(x - np.mean(x))))
        cci = (tp - ma) / (0.015 * md)
        
        break_upper = (cci > self.upper) & (cci.shift(1) <= self.upper)
        break_lower = (cci < self.lower) & (cci.shift(1) >= self.lower)
        
        signals = pd.Series(0, index=data.index)
        signals[break_upper] = 1
        signals[break_lower] = -1
        
        signals = signals.replace(0, np.nan).ffill().fillna(0)
        return signals
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {
            "period": {"type": "int", "default": 14, "min": 5, "max": 60, "description": "CCI周期"},
            "upper": {"type": "int", "default": 100, "min": 50, "max": 200, "description": "上轨阈值"},
            "lower": {"type": "int", "default": -100, "min": -200, "max": -50, "description": "下轨阈值"}
        }


class VolumeBreakoutStrategy(BaseStrategy):
    """成交量突破策略"""
    
    name = "volume_breakout"
    description = "放量突破买入，缩量跌破均线卖出，量价配合验证"
    
    def __init__(self, volume_period: int = 20, price_period: int = 20, volume_multiplier: float = 2.0):
        self.volume_period = volume_period
        self.price_period = price_period
        self.volume_multiplier = volume_multiplier
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data['close']
        volume = data['volume']
        
        ma_volume = volume.rolling(self.volume_period).mean()
        ma_price = close.rolling(self.price_period).mean()
        
        # 放量突破：成交量放大N倍 + 价格突破均线
        volume_breakout = volume > self.volume_multiplier * ma_volume
        price_breakout = (close > ma_price) & (close.shift(1) <= ma_price.shift(1))
        buy_signal = volume_breakout & price_breakout
        
        # 跌破均线卖出
        price_breakdown = (close < ma_price) & (close.shift(1) >= ma_price.shift(1))
        
        signals = pd.Series(0, index=data.index)
        signals[buy_signal] = 1
        signals[price_breakdown] = -1
        
        signals = signals.replace(0, np.nan).ffill().fillna(0)
        return signals
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {
            "volume_period": {"type": "int", "default": 20, "min": 5, "max": 60, "description": "成交量均线周期"},
            "price_period": {"type": "int", "default": 20, "min": 5, "max": 60, "description": "价格均线周期"},
            "volume_multiplier": {"type": "float", "default": 2.0, "min": 1.2, "max": 5.0, "description": "放量倍数"}
        }


class DMIStrategy(BaseStrategy):
    """DMI趋向指标策略"""
    
    name = "dmi"
    description = "+DI上穿-DI买入，下穿卖出，ADX过滤趋势强度"
    
    def __init__(self, period: int = 14, adx_threshold: int = 25):
        self.period = period
        self.adx_threshold = adx_threshold
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        high = data['high']
        low = data['low']
        close = data['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(self.period).mean()
        
        plus_dm = high.diff()
        minus_dm = low.diff() * -1
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        plus_dm_smooth = plus_dm.rolling(self.period).mean()
        minus_dm_smooth = minus_dm.rolling(self.period).mean()
        
        plus_di = 100 * plus_dm_smooth / atr
        minus_di = 100 * minus_dm_smooth / atr
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 0.001)
        adx = dx.rolling(self.period).mean()
        
        golden_cross = (plus_di > minus_di) & (plus_di.shift(1) <= minus_di.shift(1)) & (adx > self.adx_threshold)
        death_cross = (plus_di < minus_di) & (plus_di.shift(1) >= minus_di.shift(1))
        
        signals = pd.Series(0, index=data.index)
        signals[golden_cross] = 1
        signals[death_cross] = -1
        
        signals = signals.replace(0, np.nan).ffill().fillna(0)
        return signals
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {
            "period": {"type": "int", "default": 14, "min": 5, "max": 30, "description": "DMI周期"},
            "adx_threshold": {"type": "int", "default": 25, "min": 15, "max": 40, "description": "ADX趋势强度阈值"}
        }


class DMAStrategy(BaseStrategy):
    """DMA平均线差策略"""
    
    name = "dma"
    description = "DMA上穿AMA买入，下穿卖出，提前于均线发出信号"
    
    def __init__(self, fast_period: int = 10, slow_period: int = 50, ama_period: int = 10):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.ama_period = ama_period
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data['close']
        ema_fast = close.ewm(span=self.fast_period).mean()
        ema_slow = close.ewm(span=self.slow_period).mean()
        dma = ema_fast - ema_slow
        ama = dma.ewm(span=self.ama_period).mean()
        
        golden_cross = (dma > ama) & (dma.shift(1) <= ama.shift(1))
        death_cross = (dma < ama) & (dma.shift(1) >= ama.shift(1))
        
        signals = pd.Series(0, index=data.index)
        signals[golden_cross] = 1
        signals[death_cross] = -1
        
        signals = signals.replace(0, np.nan).ffill().fillna(0)
        return signals
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {
            "fast_period": {"type": "int", "default": 10, "min": 5, "max": 30, "description": "快线周期"},
            "slow_period": {"type": "int", "default": 50, "min": 20, "max": 120, "description": "慢线周期"},
            "ama_period": {"type": "int", "default": 10, "min": 5, "max": 30, "description": "AMA周期"}
        }


class TRIXStrategy(BaseStrategy):
    """TRIX三重指数平滑策略"""
    
    name = "trix"
    description = "TRIX金叉买入，死叉卖出，三重平滑过滤杂波，长线趋势"
    
    def __init__(self, period: int = 12, signal_period: int = 9):
        self.period = period
        self.signal_period = signal_period
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data['close']
        ema1 = close.ewm(span=self.period).mean()
        ema2 = ema1.ewm(span=self.period).mean()
        ema3 = ema2.ewm(span=self.period).mean()
        trix = (ema3 - ema3.shift(1)) / ema3.shift(1) * 100
        trix_signal = trix.ewm(span=self.signal_period).mean()
        
        golden_cross = (trix > trix_signal) & (trix.shift(1) <= trix_signal.shift(1))
        death_cross = (trix < trix_signal) & (trix.shift(1) >= trix_signal.shift(1))
        
        signals = pd.Series(0, index=data.index)
        signals[golden_cross] = 1
        signals[death_cross] = -1
        
        signals = signals.replace(0, np.nan).ffill().fillna(0)
        return signals
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {
            "period": {"type": "int", "default": 12, "min": 6, "max": 30, "description": "TRIX周期"},
            "signal_period": {"type": "int", "default": 9, "min": 3, "max": 20, "description": "信号线周期"}
        }


class MultiMAStrategy(BaseStrategy):
    """均线多头发散策略"""
    
    name = "multi_ma"
    description = "5/10/20/60均线多头发散买入，空头排列卖出，大趋势确认"
    
    def __init__(self):
        pass
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data['close']
        ma5 = close.rolling(5).mean()
        ma10 = close.rolling(10).mean()
        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()
        
        # 多头排列确认
        long_condition = (ma5 > ma10) & (ma10 > ma20) & (ma20 > ma60)
        short_condition = (ma5 < ma10) & (ma10 < ma20) & (ma20 < ma60)
        
        signals = pd.Series(0, index=data.index)
        signals[long_condition & ~long_condition.shift(1).fillna(False)] = 1
        signals[short_condition & ~short_condition.shift(1).fillna(False)] = -1
        
        signals = signals.replace(0, np.nan).ffill().fillna(0)
        return signals
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {}


class DonchianStrategy(BaseStrategy):
    """唐奇安通道突破策略"""
    
    name = "donchian"
    description = "突破N日最高点买入，跌破N日最低点卖出，海龟交易法则核心"
    
    def __init__(self, period: int = 20):
        self.period = period
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        high = data['high']
        low = data['low']
        
        upper = high.rolling(self.period).max().shift(1)  # 前N日最高点
        lower = low.rolling(self.period).min().shift(1)  # 前N日最低点
        
        break_upper = data['close'] > upper
        break_lower = data['close'] < lower
        
        signals = pd.Series(0, index=data.index)
        signals[break_upper] = 1
        signals[break_lower] = -1
        
        signals = signals.replace(0, np.nan).ffill().fillna(0)
        return signals
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {
            "period": {"type": "int", "default": 20, "min": 10, "max": 120, "description": "唐奇安通道周期"}
        }


class WRStrategy(BaseStrategy):
    """WR威廉指标策略"""
    
    name = "wr"
    description = "WR高于80超卖买入，低于20超买卖出，极短线震荡"
    
    def __init__(self, period: int = 14, overbought: int = 20, oversold: int = 80):
        self.period = period
        self.overbought = overbought
        self.oversold = oversold
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        high = data['high']
        low = data['low']
        close = data['close']
        
        hhv = high.rolling(self.period).max()
        llv = low.rolling(self.period).min()
        wr = (hhv - close) / (hhv - llv + 0.001) * 100
        
        buy_signal = (wr > self.oversold) & (wr.shift(1) <= self.oversold)
        sell_signal = (wr < self.overbought) & (wr.shift(1) >= self.overbought)
        
        signals = pd.Series(0, index=data.index)
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        signals = signals.replace(0, np.nan).ffill().fillna(0)
        return signals
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {
            "period": {"type": "int", "default": 14, "min": 5, "max": 30, "description": "WR周期"},
            "overbought": {"type": "int", "default": 20, "min": 10, "max": 40, "description": "超买阈值"},
            "oversold": {"type": "int", "default": 80, "min": 60, "max": 90, "description": "超卖阈值"}
        }


class MOMStrategy(BaseStrategy):
    """MOM动量线策略"""
    
    name = "mom"
    description = "MOM由负转正买入，由正转负卖出，动量拐点识别"
    
    def __init__(self, period: int = 10):
        self.period = period
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data['close']
        mom = close - close.shift(self.period)
        
        buy_signal = (mom > 0) & (mom.shift(1) <= 0)
        sell_signal = (mom < 0) & (mom.shift(1) >= 0)
        
        signals = pd.Series(0, index=data.index)
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        signals = signals.replace(0, np.nan).ffill().fillna(0)
        return signals
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {
            "period": {"type": "int", "default": 10, "min": 5, "max": 60, "description": "动量周期"}
        }


class ROCStrategy(BaseStrategy):
    """ROC变动率策略"""
    
    name = "roc"
    description = "ROC上穿零轴买入，下穿零轴卖出，极端值反转"
    
    def __init__(self, period: int = 12, extreme_threshold: float = 10.0):
        self.period = period
        self.extreme_threshold = extreme_threshold
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data['close']
        roc = (close - close.shift(self.period)) / close.shift(self.period) * 100
        
        buy_signal = (roc > 0) & (roc.shift(1) <= 0)
        sell_signal = (roc < 0) & (roc.shift(1) >= 0)
        
        # 极端值反转
        extreme_buy = (roc < -self.extreme_threshold) & (roc.shift(1) >= -self.extreme_threshold)
        extreme_sell = (roc > self.extreme_threshold) & (roc.shift(1) <= self.extreme_threshold)
        
        signals = pd.Series(0, index=data.index)
        signals[buy_signal | extreme_buy] = 1
        signals[sell_signal | extreme_sell] = -1
        
        signals = signals.replace(0, np.nan).ffill().fillna(0)
        return signals
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {
            "period": {"type": "int", "default": 12, "min": 5, "max": 60, "description": "ROC周期"},
            "extreme_threshold": {"type": "float", "default": 10.0, "min": 3.0, "max": 30.0, "description": "极端值阈值%"}
        }


class BIASStrategy(BaseStrategy):
    """BIAS乖离率策略"""
    
    name = "bias"
    description = "负乖离达到阈值买入，正乖离达到阈值卖出，均值回归"
    
    def __init__(self, period: int = 20, buy_threshold: float = -5.0, sell_threshold: float = 8.0):
        self.period = period
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data['close']
        ma = close.rolling(self.period).mean()
        bias = (close - ma) / ma * 100
        
        buy_signal = (bias < self.buy_threshold) & (bias.shift(1) >= self.buy_threshold)
        sell_signal = (bias > self.sell_threshold) & (bias.shift(1) <= self.sell_threshold)
        
        signals = pd.Series(0, index=data.index)
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        signals = signals.replace(0, np.nan).ffill().fillna(0)
        return signals
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {
            "period": {"type": "int", "default": 20, "min": 5, "max": 60, "description": "均线周期"},
            "buy_threshold": {"type": "float", "default": -5.0, "min": -15.0, "max": -1.0, "description": "买入乖离率%"},
            "sell_threshold": {"type": "float", "default": 8.0, "min": 3.0, "max": 20.0, "description": "卖出乖离率%"}
        }


class KeltnerStrategy(BaseStrategy):
    """肯特纳通道突破策略"""
    
    name = "keltner"
    description = "收盘价突破上轨买入，跌破下轨卖出，ATR计算通道，假信号更少"
    
    def __init__(self, period: int = 20, atr_period: int = 10, multiplier: float = 2.0):
        self.period = period
        self.atr_period = atr_period
        self.multiplier = multiplier
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data['close']
        high = data['high']
        low = data['low']
        
        mid = close.ewm(span=self.period).mean()
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(self.atr_period).mean()
        
        upper = mid + self.multiplier * atr
        lower = mid - self.multiplier * atr
        
        break_upper = (close > upper) & (close.shift(1) <= upper.shift(1))
        break_lower = (close < lower) & (close.shift(1) >= lower.shift(1))
        
        signals = pd.Series(0, index=data.index)
        signals[break_upper] = 1
        signals[break_lower] = -1
        
        signals = signals.replace(0, np.nan).ffill().fillna(0)
        return signals
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {
            "period": {"type": "int", "default": 20, "min": 10, "max": 60, "description": "中轨周期"},
            "atr_period": {"type": "int", "default": 10, "min": 5, "max": 30, "description": "ATR周期"},
            "multiplier": {"type": "float", "default": 2.0, "min": 1.0, "max": 4.0, "description": "通道倍数"}
        }


class OBVStrategy(BaseStrategy):
    """OBV能量潮策略"""
    
    name = "obv"
    description = "OBV创新高价格没新高=底背离买入，顶背离卖出"
    
    def __init__(self, period: int = 20):
        self.period = period
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data['close']
        volume = data['volume']
        
        # 计算OBV
        obv = pd.Series(0.0, index=data.index)
        for i in range(1, len(data)):
            if close.iloc[i] > close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
            elif close.iloc[i] < close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]
        
        # OBV均线
        obv_ma = obv.rolling(self.period).mean()
        
        # OBV突破均线买入
        buy_signal = (obv > obv_ma) & (obv.shift(1) <= obv_ma.shift(1))
        sell_signal = (obv < obv_ma) & (obv.shift(1) >= obv_ma.shift(1))
        
        signals = pd.Series(0, index=data.index)
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        signals = signals.replace(0, np.nan).ffill().fillna(0)
        return signals
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {
            "period": {"type": "int", "default": 20, "min": 10, "max": 60, "description": "OBV均线周期"}
        }


class VRStrategy(BaseStrategy):
    """VR容量比率策略"""
    
    name = "vr"
    description = "VR低于40极度缩量买入，高于350极度放量卖出，市场热度识别"
    
    def __init__(self, period: int = 26, buy_threshold: float = 40.0, sell_threshold: float = 350.0):
        self.period = period
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data['close']
        volume = data['volume']
        
        up_volume = pd.Series(0.0, index=data.index)
        down_volume = pd.Series(0.0, index=data.index)
        flat_volume = pd.Series(0.0, index=data.index)
        
        for i in range(1, len(data)):
            if close.iloc[i] > close.iloc[i-1]:
                up_volume.iloc[i] = volume.iloc[i]
            elif close.iloc[i] < close.iloc[i-1]:
                down_volume.iloc[i] = volume.iloc[i]
            else:
                flat_volume.iloc[i] = volume.iloc[i]
        
        up_sum = up_volume.rolling(self.period).sum()
        down_sum = down_volume.rolling(self.period).sum()
        flat_sum = flat_volume.rolling(self.period).sum()
        
        vr = (up_sum + 0.5 * flat_sum) / (down_sum + 0.5 * flat_sum + 0.001) * 100
        
        buy_signal = (vr < self.buy_threshold) & (vr.shift(1) >= self.buy_threshold)
        sell_signal = (vr > self.sell_threshold) & (vr.shift(1) <= self.sell_threshold)
        
        signals = pd.Series(0, index=data.index)
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        signals = signals.replace(0, np.nan).ffill().fillna(0)
        return signals
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {
            "period": {"type": "int", "default": 26, "min": 10, "max": 60, "description": "VR周期"},
            "buy_threshold": {"type": "float", "default": 40.0, "min": 20.0, "max": 100.0, "description": "买入阈值"},
            "sell_threshold": {"type": "float", "default": 350.0, "min": 200.0, "max": 600.0, "description": "卖出阈值"}
        }


class EMVStrategy(BaseStrategy):
    """EMV简易波动策略"""
    
    name = "emv"
    description = "EMV由负转正买入，由正转负卖出，缩量上涨确认"
    
    def __init__(self, period: int = 14):
        self.period = period
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        high = data['high']
        low = data['low']
        volume = data['volume']
        
        mid = (high + low) / 2
        mid_change = mid - mid.shift(1)
        
        tr = high - low
        vol_ratio = volume / tr  # 单位价格变动的成交量
        
        em = mid_change * (1 - volume / volume.rolling(self.period).max())  # 缩量加权
        emv = em.rolling(self.period).mean()
        
        buy_signal = (emv > 0) & (emv.shift(1) <= 0)
        sell_signal = (emv < 0) & (emv.shift(1) >= 0)
        
        signals = pd.Series(0, index=data.index)
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        signals = signals.replace(0, np.nan).ffill().fillna(0)
        return signals
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {
            "period": {"type": "int", "default": 14, "min": 5, "max": 30, "description": "EMV周期"}
        }


# 策略注册中心
STRATEGY_REGISTRY = {
    # 趋势跟踪类 6个
    "双均线策略": DualMAStrategy,
    "MACD策略": MACDStrategy,
    "DMA平均线差策略": DMAStrategy,
    "TRIX三重指数策略": TRIXStrategy,
    "均线多头发散策略": MultiMAStrategy,
    "唐奇安通道突破策略": DonchianStrategy,
    
    # 震荡反转类 7个
    "RSI超买超卖策略": RSIStrategy,
    "KDJ随机指标策略": KDJStrategy,
    "CCI顺势指标策略": CCIStrategy,
    "WR威廉指标策略": WRStrategy,
    "MOM动量线策略": MOMStrategy,
    "ROC变动率策略": ROCStrategy,
    "BIAS乖离率策略": BIASStrategy,
    
    # 通道突破类 3个
    "布林带突破策略": BollingerStrategy,
    "肯特纳通道突破策略": KeltnerStrategy,
    
    # 量价配合类 4个
    "成交量突破策略": VolumeBreakoutStrategy,
    "OBV能量潮策略": OBVStrategy,
    "VR容量比率策略": VRStrategy,
    "EMV简易波动策略": EMVStrategy,
    
    # 趋势强弱类 2个
    "DMI趋向指标策略": DMIStrategy,
}


def get_all_strategies() -> List[str]:
    """获取所有可用策略名称"""
    return list(STRATEGY_REGISTRY.keys())


def create_strategy(name: str, **params) -> BaseStrategy:
    """创建策略实例"""
    if name not in STRATEGY_REGISTRY:
        raise ValueError(f"未知策略: {name}，可用策略: {list(STRATEGY_REGISTRY.keys())}")
    return STRATEGY_REGISTRY[name](**params)


def get_strategy_info(name: str) -> Dict[str, Any]:
    """获取策略详细信息"""
    if name not in STRATEGY_REGISTRY:
        raise ValueError(f"未知策略: {name}，可用策略: {list(STRATEGY_REGISTRY.keys())}")
    cls = STRATEGY_REGISTRY[name]
    return {
        "name": cls.name,
        "description": cls.description,
        "params_schema": cls.get_params_schema(cls)
    }


# 兼容旧版变量名
STRATEGY_CLASSES = list(STRATEGY_REGISTRY.values())
