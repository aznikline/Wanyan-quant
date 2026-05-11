"""
Rock Quant 因子库 - 标准化统一接口
所有量价因子统一实现，支持自动注册、参数验证、向量化计算
"""
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Callable, Type


class FactorRegistry:
    """因子注册器 - 全局单例管理所有因子"""
    _registry: Dict[str, Type['BaseFactor']] = {}
    
    @classmethod
    def register(cls, factor_name: str) -> Callable:
        """装饰器：注册因子类"""
        def wrapper(factor_cls: Type['BaseFactor']) -> Type['BaseFactor']:
            cls._registry[factor_name] = factor_cls
            return factor_cls
        return wrapper
    
    @classmethod
    def get_factor(cls, factor_name: str) -> Type['BaseFactor']:
        """获取因子类"""
        return cls._registry.get(factor_name)
    
    @classmethod
    def list_factors(cls) -> List[str]:
        """列出所有已注册的因子"""
        return list(cls._registry.keys())
    
    @classmethod
    def get_all_factors(cls) -> Dict[str, Type['BaseFactor']]:
        """获取所有因子类"""
        return cls._registry.copy()


class BaseFactor(ABC):
    """因子基类 - 所有自定义因子继承此类"""
    
    name: str = "base_factor"
    description: str = "基础因子类"
    factor_type: str = "trend"  # trend, volatility, momentum, volume
    
    @abstractmethod
    def calculate(self, data: pd.DataFrame, **params) -> pd.Series:
        """
        向量化计算因子值
        Args:
            data: 行情数据，包含 open, high, low, close, volume
            **params: 因子参数
        Returns:
            因子值序列
        """
        pass
    
    @abstractmethod
    def get_params_schema(self) -> Dict[str, Any]:
        """
        返回参数字典定义
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
    
    @classmethod
    def get_factor_info(cls) -> Dict[str, Any]:
        """获取因子信息"""
        return {
            "name": cls.name,
            "description": cls.description,
            "type": cls.factor_type,
            "params_schema": cls.get_params_schema(cls)
        }


# ============= 趋势类因子 =============

@FactorRegistry.register("ma")
class MovingAverageFactor(BaseFactor):
    """移动平均线因子"""
    name = "ma"
    description = "简单移动平均线，经典趋势跟踪指标"
    factor_type = "trend"
    
    def calculate(self, data: pd.DataFrame, period: int = 20) -> pd.Series:
        return data['close'].rolling(period).mean()
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {
            "period": {
                "type": "int",
                "default": 20,
                "min": 1,
                "max": 250,
                "description": "均线周期"
            }
        }


@FactorRegistry.register("ema")
class EMAFactor(BaseFactor):
    """指数移动平均线因子"""
    name = "ema"
    description = "指数移动平均线，最近价格权重更高"
    factor_type = "trend"
    
    def calculate(self, data: pd.DataFrame, period: int = 20) -> pd.Series:
        return data['close'].ewm(span=period, adjust=False).mean()
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {
            "period": {
                "type": "int",
                "default": 20,
                "min": 1,
                "max": 250,
                "description": "均线周期"
            }
        }


@FactorRegistry.register("macd")
class MACDFactor(BaseFactor):
    """MACD因子"""
    name = "macd"
    description = "MACD指标，捕捉趋势变化和动量"
    factor_type = "trend"
    
    def calculate(self, data: pd.DataFrame, fast: int = 12, 
                  slow: int = 26, signal: int = 9) -> pd.Series:
        ema_fast = data['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = data['close'].ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        return macd_line - signal_line  # MACD柱
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {
            "fast": {
                "type": "int",
                "default": 12,
                "min": 2,
                "max": 100,
                "description": "快线周期"
            },
            "slow": {
                "type": "int",
                "default": 26,
                "min": 5,
                "max": 200,
                "description": "慢线周期"
            },
            "signal": {
                "type": "int",
                "default": 9,
                "min": 2,
                "max": 50,
                "description": "信号线周期"
            }
        }


# ============= 波动率类因子 =============

@FactorRegistry.register("bollinger_width")
class BollingerWidthFactor(BaseFactor):
    """布林带宽度因子 - 衡量市场波动率"""
    name = "bollinger_width"
    description = "布林带宽度，衡量波动率水平"
    factor_type = "volatility"
    
    def calculate(self, data: pd.DataFrame, period: int = 20, 
                  std_dev: float = 2.0) -> pd.Series:
        sma = data['close'].rolling(period).mean()
        std = data['close'].rolling(period).std()
        upper = sma + std_dev * std
        lower = sma - std_dev * std
        return (upper - lower) / sma
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {
            "period": {
                "type": "int",
                "default": 20,
                "min": 5,
                "max": 100,
                "description": "计算周期"
            },
            "std_dev": {
                "type": "float",
                "default": 2.0,
                "min": 0.5,
                "max": 5.0,
                "description": "标准差倍数"
            }
        }


@FactorRegistry.register("volatility")
class VolatilityFactor(BaseFactor):
    """波动率因子"""
    name = "volatility"
    description = "历史波动率，年化标准差"
    factor_type = "volatility"
    
    def calculate(self, data: pd.DataFrame, period: int = 20) -> pd.Series:
        returns = data['close'].pct_change()
        return returns.rolling(period).std() * np.sqrt(252)
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {
            "period": {
                "type": "int",
                "default": 20,
                "min": 5,
                "max": 250,
                "description": "波动率计算周期"
            }
        }


@FactorRegistry.register("atr")
class ATRFactor(BaseFactor):
    """ATR因子 - 平均真实波幅"""
    name = "atr"
    description = "平均真实波幅，衡量价格波动范围"
    factor_type = "volatility"
    
    def calculate(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        high_low = data['high'] - data['low']
        high_close = np.abs(data['high'] - data['close'].shift())
        low_close = np.abs(data['low'] - data['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return true_range.rolling(period).mean()
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {
            "period": {
                "type": "int",
                "default": 14,
                "min": 5,
                "max": 100,
                "description": "ATR周期"
            }
        }


# ============= 动量类因子 =============

@FactorRegistry.register("rsi")
class RSIFactor(BaseFactor):
    """RSI因子"""
    name = "rsi"
    description = "相对强弱指数，衡量超买超卖"
    factor_type = "momentum"
    
    def calculate(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        delta = data['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {
            "period": {
                "type": "int",
                "default": 14,
                "min": 2,
                "max": 100,
                "description": "RSI计算周期"
            }
        }


@FactorRegistry.register("momentum")
class MomentumFactor(BaseFactor):
    """动量因子"""
    name = "momentum"
    description = "价格动量，N周期收益率"
    factor_type = "momentum"
    
    def calculate(self, data: pd.DataFrame, period: int = 20) -> pd.Series:
        return data['close'].pct_change(period)
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {
            "period": {
                "type": "int",
                "default": 20,
                "min": 1,
                "max": 250,
                "description": "动量计算周期"
            }
        }


@FactorRegistry.register("cci")
class CCIFactor(BaseFactor):
    """CCI因子 - 顺势指标"""
    name = "cci"
    description = "顺势指标，衡量价格偏离统计平均的程度"
    factor_type = "momentum"
    
    def calculate(self, data: pd.DataFrame, period: int = 20) -> pd.Series:
        tp = (data['high'] + data['low'] + data['close']) / 3
        sma_tp = tp.rolling(period).mean()
        mad = tp.rolling(period).apply(lambda x: np.mean(np.abs(x - x.mean())))
        return (tp - sma_tp) / (0.015 * mad)
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {
            "period": {
                "type": "int",
                "default": 20,
                "min": 5,
                "max": 100,
                "description": "CCI计算周期"
            }
        }


@FactorRegistry.register("kdj_k")
class KDJFactor(BaseFactor):
    """KDJ的K值因子"""
    name = "kdj_k"
    description = "随机指标K值，衡量超买超卖"
    factor_type = "momentum"
    
    def calculate(self, data: pd.DataFrame, period: int = 9, 
                  smooth_k: int = 3, smooth_d: int = 3) -> pd.Series:
        low_min = data['low'].rolling(period).min()
        high_max = data['high'].rolling(period).max()
        
        rsv = (data['close'] - low_min) / (high_max - low_min) * 100
        rsv = rsv.fillna(50)
        
        k = rsv.rolling(smooth_k).mean()
        return k
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {
            "period": {
                "type": "int",
                "default": 9,
                "min": 2,
                "max": 50,
                "description": "RSV计算周期"
            },
            "smooth_k": {
                "type": "int",
                "default": 3,
                "min": 2,
                "max": 20,
                "description": "K值平滑周期"
            }
        }


# ============= 成交量类因子 =============

@FactorRegistry.register("obv")
class OBVFactor(BaseFactor):
    """OBV能量潮因子"""
    name = "obv"
    description = "能量潮指标，成交量配合价格的累积量"
    factor_type = "volume"
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        volume = data['volume']
        direction = np.sign(data['close'].diff())
        direction.iloc[0] = 0
        return (direction * volume).cumsum()
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {}


@FactorRegistry.register("volume_ma")
class VolumeMAFactor(BaseFactor):
    """成交量均线因子"""
    name = "volume_ma"
    description = "成交量均线，衡量量能变化"
    factor_type = "volume"
    
    def calculate(self, data: pd.DataFrame, period: int = 20) -> pd.Series:
        return data['volume'].rolling(period).mean()
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {
            "period": {
                "type": "int",
                "default": 20,
                "min": 2,
                "max": 250,
                "description": "成交量均线周期"
            }
        }


@FactorRegistry.register("volume_ratio")
class VolumeRatioFactor(BaseFactor):
    """量比因子"""
    name = "volume_ratio"
    description = "量比，当前成交量与平均成交量的比值"
    factor_type = "volume"
    
    def calculate(self, data: pd.DataFrame, period: int = 20) -> pd.Series:
        vol_ma = data['volume'].rolling(period).mean()
        return data['volume'] / vol_ma
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {
            "period": {
                "type": "int",
                "default": 20,
                "min": 2,
                "max": 250,
                "description": "成交量均线周期"
            }
        }


@FactorRegistry.register("price_volume_divergence")
class PriceVolumeDivergence(BaseFactor):
    """量价背离因子"""
    name = "price_volume_divergence"
    description = "量价背离检测，价格与成交量趋势的一致性"
    factor_type = "volume"
    
    def calculate(self, data: pd.DataFrame, period: int = 10) -> pd.Series:
        price_trend = data['close'].diff(period)
        volume_trend = data['volume'].diff(period)
        # 背离：价格上涨但成交量下降，或价格下跌但成交量上升
        divergence = np.where(
            (price_trend > 0) & (volume_trend < 0), -1,
            np.where(
                (price_trend < 0) & (volume_trend > 0), 1,
                0
            )
        )
        return pd.Series(divergence, index=data.index)
    
    def get_params_schema(self) -> Dict[str, Any]:
        return {
            "period": {
                "type": "int",
                "default": 10,
                "min": 2,
                "max": 60,
                "description": "背离检测周期"
            }
        }


# ============= 工具函数 =============

def calculate_factor(factor_name: str, data: pd.DataFrame, **params) -> pd.Series:
    """
    便捷函数：计算指定因子的值
    
    Args:
        factor_name: 因子名称
        data: 行情数据
        **params: 因子参数
    
    Returns:
        因子值序列
    """
    factor_cls = FactorRegistry.get_factor(factor_name)
    if factor_cls is None:
        raise ValueError(f"Factor '{factor_name}' not found. Available factors: {FactorRegistry.list_factors()}")
    
    factor = factor_cls()
    return factor.calculate(data, **params)


def get_factor_info(factor_name: str) -> Dict[str, Any]:
    """获取因子信息"""
    factor_cls = FactorRegistry.get_factor(factor_name)
    if factor_cls is None:
        raise ValueError(f"Factor '{factor_name}' not found")
    return factor_cls.get_factor_info()


def list_factors_by_type() -> Dict[str, List[str]]:
    """按类型列出所有因子"""
    result = {}
    for name, factor_cls in FactorRegistry.get_all_factors().items():
        factor_type = factor_cls.factor_type
        if factor_type not in result:
            result[factor_type] = []
        result[factor_type].append(name)
    return result


# 导出因子列表
FACTOR_LIST = FactorRegistry.list_factors()
FACTORS_BY_TYPE = list_factors_by_type()
