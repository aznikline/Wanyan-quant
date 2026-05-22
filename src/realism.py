"""
realism.py - 回测真实性补齐模块（Lv.1）
================================================
功能：
1. 滑点模型（固定滑点 / 比例滑点 / 波动率滑点）
2. 交易成本（佣金双向 + 印花税仅卖出 + 过户费）
3. 涨跌停过滤（涨停不买、跌停不卖；ST 板可配 5%）
4. T+1 限制（当日买入次日才能卖出）
5. 真实性配置 RealismConfig + 单元函数，便于 backtest_engine 注入
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict


# ============================================================
# 配置
# ============================================================
@dataclass
class RealismConfig:
    """真实性配置（A股默认参数）"""

    # ---- 开关 ----
    enable: bool = True                # 一键开关：False 则等同理想回测
    enable_slippage: bool = True
    enable_cost: bool = True
    enable_price_limit: bool = True    # 涨跌停过滤
    enable_t_plus_1: bool = True       # T+1 限制

    # ---- 滑点 ----
    slippage_mode: str = "ratio"       # 'ratio'(比例) | 'fixed'(固定tick) | 'vol'(波动率)
    slippage_ratio: float = 0.001      # 比例滑点（千一）
    slippage_fixed: float = 0.01       # 固定滑点（元/股）
    slippage_vol_mult: float = 0.5     # 波动率滑点系数（= 当日ATR的倍数）

    # ---- 交易成本（A股标准）----
    commission_rate: float = 0.00025   # 佣金率 万二点五（双向）
    commission_min: float = 5.0        # 单笔最低佣金 5 元
    stamp_tax_rate: float = 0.001      # 印花税 千一（仅卖出）
    transfer_fee_rate: float = 0.00001 # 过户费 万分之 0.1（沪市，统一计）

    # ---- 涨跌停 ----
    price_limit_pct: float = 0.10      # 普通股 10%
    st_price_limit_pct: float = 0.05   # ST 股 5%
    is_st: bool = False                # 当前标的是否 ST

    # ---- T+1 ----
    t_plus: int = 1                    # 0=T+0(港美), 1=T+1(A股)


# ============================================================
# 涨跌停判定
# ============================================================
def compute_limit_prices(data: pd.DataFrame, cfg: RealismConfig) -> pd.DataFrame:
    """
    根据昨收价计算每日涨停价、跌停价。
    返回包含 'pre_close', 'upper_limit', 'lower_limit' 列的 DataFrame。
    """
    out = data.copy()
    if "pre_close" not in out.columns:
        out["pre_close"] = out["close"].shift(1)

    pct = cfg.st_price_limit_pct if cfg.is_st else cfg.price_limit_pct
    # A 股涨跌停价四舍五入到分
    out["upper_limit"] = (out["pre_close"] * (1 + pct)).round(2)
    out["lower_limit"] = (out["pre_close"] * (1 - pct)).round(2)
    return out


def is_limit_up(row: pd.Series, tol: float = 0.005) -> bool:
    """开盘即一字涨停（无法买入）：开盘 >= 涨停价 - 容差"""
    if pd.isna(row.get("upper_limit")):
        return False
    return row["open"] >= row["upper_limit"] - tol


def is_limit_down(row: pd.Series, tol: float = 0.005) -> bool:
    """开盘即一字跌停（无法卖出）：开盘 <= 跌停价 + 容差"""
    if pd.isna(row.get("lower_limit")):
        return False
    return row["open"] <= row["lower_limit"] + tol


def filter_signals_by_price_limit(signals: pd.Series,
                                   data: pd.DataFrame,
                                   cfg: RealismConfig) -> Tuple[pd.Series, Dict[str, int]]:
    """
    应用涨跌停过滤：
    - 当日涨停：买入信号(>0 且仓位向上)被阻断
    - 当日跌停：卖出信号(<0 或仓位向下)被阻断
    返回过滤后的 signals 和统计 dict
    """
    if not cfg.enable or not cfg.enable_price_limit:
        return signals, {"blocked_buy": 0, "blocked_sell": 0}

    data_lim = compute_limit_prices(data, cfg)
    signals = signals.reindex(data_lim.index).fillna(0).copy()

    blocked_buy = 0
    blocked_sell = 0
    prev_sig = 0.0
    out = signals.copy()

    for dt in signals.index:
        row = data_lim.loc[dt]
        cur_sig = signals.loc[dt]
        delta = cur_sig - prev_sig

        if delta > 0 and is_limit_up(row):       # 想加仓但涨停
            out.loc[dt] = prev_sig
            blocked_buy += 1
        elif delta < 0 and is_limit_down(row):   # 想减仓但跌停
            out.loc[dt] = prev_sig
            blocked_sell += 1
        else:
            prev_sig = cur_sig
            continue
        prev_sig = out.loc[dt]

    return out, {"blocked_buy": blocked_buy, "blocked_sell": blocked_sell}


# ============================================================
# T+1 限制
# ============================================================
def apply_t_plus_1(signals: pd.Series, cfg: RealismConfig) -> Tuple[pd.Series, int]:
    """
    T+1：当日买入的仓位次日才能卖。
    实现方法：跟踪每日新增多头仓位，禁止当日减仓低于"昨日已有仓位"。
    返回 (新 signals, blocked_count)
    """
    if not cfg.enable or not cfg.enable_t_plus_1 or cfg.t_plus == 0:
        return signals, 0

    out = signals.copy().astype(float)
    blocked = 0
    yesterday_locked = 0.0   # 昨日（含之前）可卖的多头仓位
    today_new_long = 0.0     # 今日新增的多头（T+1 锁定，明日释放）

    prev_pos = 0.0
    first = True
    for dt in out.index:
        # 跨日：把昨日新增释放为可卖（首日不释放）
        if not first:
            yesterday_locked += today_new_long
            today_new_long = 0.0
        first = False

        cur = float(out.loc[dt])
        delta = cur - prev_pos
        if delta > 1e-9:
            # 加仓 → 新仓位本日锁定
            today_new_long += delta
            prev_pos = cur
        elif delta < -1e-9:
            # 减仓 → 只能动 yesterday_locked
            sellable = yesterday_locked
            want_sell = -delta
            if want_sell > sellable + 1e-9:
                # 卖不动这么多，限制本日仓位
                allowed_pos = prev_pos - sellable
                out.loc[dt] = allowed_pos
                yesterday_locked = 0.0
                blocked += 1
                prev_pos = allowed_pos
            else:
                yesterday_locked -= want_sell
                prev_pos = cur
        else:
            prev_pos = cur

    return out, blocked


# ============================================================
# 滑点 & 成交价
# ============================================================
def apply_slippage(price: float, direction: int, cfg: RealismConfig,
                    atr: Optional[float] = None) -> float:
    """
    direction: +1=买入(滑高), -1=卖出(滑低)
    """
    if not cfg.enable or not cfg.enable_slippage:
        return price

    if cfg.slippage_mode == "ratio":
        slip = price * cfg.slippage_ratio
    elif cfg.slippage_mode == "fixed":
        slip = cfg.slippage_fixed
    elif cfg.slippage_mode == "vol":
        slip = (atr or 0.0) * cfg.slippage_vol_mult
    else:
        slip = price * cfg.slippage_ratio

    return round(price + direction * slip, 4)


# ============================================================
# 交易成本
# ============================================================
def calc_transaction_cost(amount: float, side: str, cfg: RealismConfig) -> Dict[str, float]:
    """
    amount: 成交金额（正数）
    side: 'buy' or 'sell'
    返回明细 dict 与总成本
    """
    if not cfg.enable or not cfg.enable_cost:
        return {"commission": 0, "stamp_tax": 0, "transfer_fee": 0, "total": 0}

    commission = max(amount * cfg.commission_rate, cfg.commission_min)
    transfer_fee = amount * cfg.transfer_fee_rate
    stamp_tax = amount * cfg.stamp_tax_rate if side == "sell" else 0.0
    total = commission + transfer_fee + stamp_tax
    return {
        "commission": round(commission, 4),
        "stamp_tax": round(stamp_tax, 4),
        "transfer_fee": round(transfer_fee, 4),
        "total": round(total, 4),
    }


def calc_cost_rate(side: str, cfg: RealismConfig) -> float:
    """
    返回交易成本的"比率"形式，方便接入向量化引擎。
    （忽略最低佣金 5 元的影响，适合资金量较大时；UI 可提醒小资金误差）
    """
    if not cfg.enable or not cfg.enable_cost:
        return 0.0
    rate = cfg.commission_rate + cfg.transfer_fee_rate
    if side == "sell":
        rate += cfg.stamp_tax_rate
    return rate


# ============================================================
# 统一入口：给 BacktestEngine 调用
# ============================================================
def preprocess_signals(signals: pd.Series,
                        data: pd.DataFrame,
                        cfg: RealismConfig) -> Tuple[pd.Series, Dict[str, int]]:
    """
    顺序：先涨跌停过滤 → 再 T+1 限制。
    返回最终可执行的 signals 与统计信息。
    """
    stats = {"blocked_buy": 0, "blocked_sell": 0, "blocked_t1": 0}
    if not cfg.enable:
        return signals, stats

    s1, lim_stat = filter_signals_by_price_limit(signals, data, cfg)
    stats.update(lim_stat)

    s2, t1_blocked = apply_t_plus_1(s1, cfg)
    stats["blocked_t1"] = t1_blocked
    return s2, stats
