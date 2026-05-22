"""
alpha158.py - Lv.B Qlib Alpha158 因子库精简实现
====================================================
从 60 个最常用因子开始，覆盖 K线、波动率、量价、技术指标四大类。
全部纯 pandas 实现，无需 Qlib 依赖。
"""
import pandas as pd
import numpy as np
from typing import Dict, Callable


# ============================================================
# K 线形态因子（KBAR）
# ============================================================
def kmid(df: pd.DataFrame) -> pd.Series:
    """K线中位价（高低中点）"""
    return (df["close"] - df["open"]) / df["open"]


def klen(df: pd.DataFrame) -> pd.Series:
    """K线长度"""
    return (df["high"] - df["low"]) / df["open"]


def kmid2(df: pd.DataFrame) -> pd.Series:
    """实体占比"""
    return (df["close"] - df["open"]) / (df["high"] - df["low"] + 1e-12)


def kup(df: pd.DataFrame) -> pd.Series:
    """上影线"""
    return (df["high"] - np.maximum(df["open"], df["close"])) / df["open"]


def kup2(df: pd.DataFrame) -> pd.Series:
    """上影线/总长度"""
    return (df["high"] - np.maximum(df["open"], df["close"])) / (df["high"] - df["low"] + 1e-12)


def klow(df: pd.DataFrame) -> pd.Series:
    """下影线"""
    return (np.minimum(df["open"], df["close"]) - df["low"]) / df["open"]


def klow2(df: pd.DataFrame) -> pd.Series:
    """下影线/总长度"""
    return (np.minimum(df["open"], df["close"]) - df["low"]) / (df["high"] - df["low"] + 1e-12)


def ksft(df: pd.DataFrame) -> pd.Series:
    """开收盘相对中位"""
    return (2 * df["close"] - df["high"] - df["low"]) / df["open"]


# ============================================================
# 滚动因子（ROC/MA/STD/VOLATILITY）
# ============================================================
def make_roc(window: int) -> Callable:
    """N日收益率"""
    def f(df: pd.DataFrame) -> pd.Series:
        return df["close"] / df["close"].shift(window) - 1
    f.__name__ = f"roc{window}"
    return f


def make_ma(window: int) -> Callable:
    """N日均线偏离度"""
    def f(df: pd.DataFrame) -> pd.Series:
        return df["close"] / df["close"].rolling(window).mean() - 1
    f.__name__ = f"ma{window}"
    return f


def make_std(window: int) -> Callable:
    """N日波动率"""
    def f(df: pd.DataFrame) -> pd.Series:
        return df["close"].pct_change().rolling(window).std()
    f.__name__ = f"std{window}"
    return f


def make_max(window: int) -> Callable:
    """N日最高偏离"""
    def f(df: pd.DataFrame) -> pd.Series:
        return df["high"].rolling(window).max() / df["close"] - 1
    f.__name__ = f"max{window}"
    return f


def make_min(window: int) -> Callable:
    """N日最低偏离"""
    def f(df: pd.DataFrame) -> pd.Series:
        return df["low"].rolling(window).min() / df["close"] - 1
    f.__name__ = f"min{window}"
    return f


def make_qtlu(window: int) -> Callable:
    """N日 80% 分位"""
    def f(df: pd.DataFrame) -> pd.Series:
        return df["close"].rolling(window).quantile(0.8) / df["close"] - 1
    f.__name__ = f"qtlu{window}"
    return f


def make_qtld(window: int) -> Callable:
    """N日 20% 分位"""
    def f(df: pd.DataFrame) -> pd.Series:
        return df["close"].rolling(window).quantile(0.2) / df["close"] - 1
    f.__name__ = f"qtld{window}"
    return f


def make_rank(window: int) -> Callable:
    """N日价格排名"""
    def f(df: pd.DataFrame) -> pd.Series:
        return df["close"].rolling(window).rank(pct=True)
    f.__name__ = f"rank{window}"
    return f


def make_imax(window: int) -> Callable:
    """N日内最高价位置"""
    def f(df: pd.DataFrame) -> pd.Series:
        return df["high"].rolling(window).apply(lambda x: np.argmax(x), raw=True) / window
    f.__name__ = f"imax{window}"
    return f


def make_imin(window: int) -> Callable:
    """N日内最低价位置"""
    def f(df: pd.DataFrame) -> pd.Series:
        return df["low"].rolling(window).apply(lambda x: np.argmin(x), raw=True) / window
    f.__name__ = f"imin{window}"
    return f


# ============================================================
# 量价相关因子（VOL/CORR）
# ============================================================
def make_vma(window: int) -> Callable:
    """N日成交量均线偏离"""
    def f(df: pd.DataFrame) -> pd.Series:
        return df["volume"] / df["volume"].rolling(window).mean() - 1
    f.__name__ = f"vma{window}"
    return f


def make_vstd(window: int) -> Callable:
    """N日成交量波动"""
    def f(df: pd.DataFrame) -> pd.Series:
        return df["volume"].pct_change().rolling(window).std()
    f.__name__ = f"vstd{window}"
    return f


def make_wvma(window: int) -> Callable:
    """N日量价加权动量"""
    def f(df: pd.DataFrame) -> pd.Series:
        ret = df["close"].pct_change()
        return (ret * df["volume"]).rolling(window).sum() / df["volume"].rolling(window).sum()
    f.__name__ = f"wvma{window}"
    return f


def make_corr(window: int) -> Callable:
    """N日量价相关系数"""
    def f(df: pd.DataFrame) -> pd.Series:
        return df["close"].rolling(window).corr(df["volume"])
    f.__name__ = f"corr{window}"
    return f


def make_cord(window: int) -> Callable:
    """N日价差与量比相关"""
    def f(df: pd.DataFrame) -> pd.Series:
        return df["close"].pct_change().rolling(window).corr(
            df["volume"].pct_change())
    f.__name__ = f"cord{window}"
    return f


# ============================================================
# 因子注册表
# ============================================================
def get_alpha158_factors() -> Dict[str, Callable]:
    """
    返回 60+ Alpha158 因子的字典
    key: 因子名, value: 因子计算函数
    """
    factors = {
        # K线形态（8个）
        "kmid": kmid, "klen": klen, "kmid2": kmid2,
        "kup": kup, "kup2": kup2,
        "klow": klow, "klow2": klow2, "ksft": ksft,
    }

    # 多窗口滚动因子
    for w in [5, 10, 20, 30, 60]:
        factors[f"roc{w}"] = make_roc(w)
        factors[f"ma{w}"] = make_ma(w)
        factors[f"std{w}"] = make_std(w)
        factors[f"max{w}"] = make_max(w)
        factors[f"min{w}"] = make_min(w)
        factors[f"qtlu{w}"] = make_qtlu(w)
        factors[f"qtld{w}"] = make_qtld(w)
        factors[f"rank{w}"] = make_rank(w)
        factors[f"imax{w}"] = make_imax(w)
        factors[f"imin{w}"] = make_imin(w)
        factors[f"vma{w}"] = make_vma(w)
        factors[f"vstd{w}"] = make_vstd(w)
        factors[f"wvma{w}"] = make_wvma(w)
        factors[f"corr{w}"] = make_corr(w)
        factors[f"cord{w}"] = make_cord(w)

    return factors


def compute_all_factors(df: pd.DataFrame, exclude_inf_nan: bool = True) -> pd.DataFrame:
    """
    一次性计算所有 Alpha158 因子
    返回 DataFrame，index 与原始 df 一致，columns 为各因子名
    """
    factors = get_alpha158_factors()
    result = {}
    for name, f in factors.items():
        try:
            s = f(df)
            if exclude_inf_nan:
                s = s.replace([np.inf, -np.inf], np.nan)
            result[name] = s
        except Exception as e:
            result[name] = pd.Series(np.nan, index=df.index)
    return pd.DataFrame(result, index=df.index)


def factor_summary(factor_df: pd.DataFrame) -> pd.DataFrame:
    """因子统计摘要"""
    return pd.DataFrame({
        "valid_count": factor_df.notna().sum(),
        "mean": factor_df.mean(),
        "std": factor_df.std(),
        "min": factor_df.min(),
        "max": factor_df.max(),
    })


# ============================================================
# 因子有效性快速评估（IC 分析）
# ============================================================
def compute_ic(factor_df: pd.DataFrame, returns: pd.Series,
               method: str = "spearman") -> pd.Series:
    """
    计算每个因子与未来收益的 Information Coefficient
    returns 应该是未来 N 日收益（如 close.pct_change(5).shift(-5)）
    """
    ic = {}
    for col in factor_df.columns:
        valid = factor_df[col].notna() & returns.notna()
        if valid.sum() < 30:
            ic[col] = np.nan
            continue
        ic[col] = factor_df.loc[valid, col].corr(returns.loc[valid], method=method)
    return pd.Series(ic).sort_values(ascending=False)
