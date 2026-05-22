"""
market_intel.py - Lv.C 市场情报数据（涨停板/龙虎榜/北向/财联社）
====================================================
封装 akshare 高价值接口，提供干净的 DataFrame 输出
本地无 akshare 或网络不通时返回空 DataFrame，不抛异常
"""
import pandas as pd
import numpy as np
from typing import Optional, List
from datetime import datetime, timedelta


def _import_ak():
    try:
        import akshare as ak
        return ak
    except ImportError:
        return None


# ============================================================
# 涨停板池
# ============================================================
def get_zt_pool(date: str = "") -> pd.DataFrame:
    """
    获取指定日期的涨停板池
    date: YYYYMMDD 格式，默认今天
    返回字段: 代码/名称/涨停价/涨停时间/封板资金/连板数/换手率/流通市值
    """
    ak = _import_ak()
    if not ak:
        return pd.DataFrame()
    if not date:
        date = datetime.now().strftime("%Y%m%d")
    try:
        df = ak.stock_zt_pool_em(date=date)
        return df
    except Exception as e:
        print(f"[market_intel] 涨停池拉取失败: {e}")
        return pd.DataFrame()


def get_zt_pool_strong(date: str = "") -> pd.DataFrame:
    """强势股池"""
    ak = _import_ak()
    if not ak:
        return pd.DataFrame()
    if not date:
        date = datetime.now().strftime("%Y%m%d")
    try:
        return ak.stock_zt_pool_strong_em(date=date)
    except Exception as e:
        print(f"[market_intel] 强势股池失败: {e}")
        return pd.DataFrame()


def get_zt_pool_zbgc(date: str = "") -> pd.DataFrame:
    """炸板池"""
    ak = _import_ak()
    if not ak:
        return pd.DataFrame()
    if not date:
        date = datetime.now().strftime("%Y%m%d")
    try:
        return ak.stock_zt_pool_zbgc_em(date=date)
    except Exception as e:
        print(f"[market_intel] 炸板池失败: {e}")
        return pd.DataFrame()


# ============================================================
# 龙虎榜
# ============================================================
def get_dragon_table(start_date: str = "", end_date: str = "") -> pd.DataFrame:
    """
    龙虎榜详情
    返回字段: 代码/名称/涨跌幅/解读/收盘价/成交额/净买额/上榜原因
    """
    ak = _import_ak()
    if not ak:
        return pd.DataFrame()
    if not start_date:
        start_date = datetime.now().strftime("%Y%m%d")
    if not end_date:
        end_date = start_date
    try:
        return ak.stock_lhb_detail_em(start_date=start_date, end_date=end_date)
    except Exception as e:
        print(f"[market_intel] 龙虎榜失败: {e}")
        return pd.DataFrame()


# ============================================================
# 北向资金
# ============================================================
def get_north_flow_today() -> pd.DataFrame:
    """北向资金当日实时净流入"""
    ak = _import_ak()
    if not ak:
        return pd.DataFrame()
    # akshare 多个接口名充后恢复，全试一遍
    candidates = [
        "stock_hsgt_fund_flow_summary_em",
        "stock_hsgt_north_net_flow_in_em",
        "stock_em_hsgt_north_net_flow_in",
    ]
    for fname in candidates:
        if hasattr(ak, fname):
            try:
                return getattr(ak, fname)()
            except Exception:
                continue
    return pd.DataFrame()


def get_north_top10() -> pd.DataFrame:
    """北向资金 TOP10 净买入个股"""
    ak = _import_ak()
    if not ak:
        return pd.DataFrame()
    try:
        return ak.stock_hsgt_hold_stock_em(market="北向", indicator="今日排行")
    except Exception as e:
        print(f"[market_intel] 北向TOP10失败: {e}")
        return pd.DataFrame()


# ============================================================
# 板块涨跌
# ============================================================
def get_industry_board() -> pd.DataFrame:
    """行业板块实时涨跌"""
    ak = _import_ak()
    if not ak:
        return pd.DataFrame()
    try:
        return ak.stock_board_industry_name_em()
    except Exception as e:
        print(f"[market_intel] 行业板块失败: {e}")
        return pd.DataFrame()


def get_concept_board() -> pd.DataFrame:
    """概念板块实时涨跌"""
    ak = _import_ak()
    if not ak:
        return pd.DataFrame()
    try:
        return ak.stock_board_concept_name_em()
    except Exception as e:
        print(f"[market_intel] 概念板块失败: {e}")
        return pd.DataFrame()


# ============================================================
# 财联社快讯
# ============================================================
def get_news_telegraph(limit: int = 50) -> pd.DataFrame:
    """财联社电报"""
    ak = _import_ak()
    if not ak:
        return pd.DataFrame()
    try:
        df = ak.stock_info_global_cls()
        return df.head(limit)
    except Exception as e:
        print(f"[market_intel] 财联社快讯失败: {e}")
        return pd.DataFrame()


# ============================================================
# 综合市场情绪指标
# ============================================================
def get_market_sentiment(date: str = "") -> dict:
    """
    综合市场情绪：涨停数/跌停数/连板数/北向净流入
    """
    if not date:
        date = datetime.now().strftime("%Y%m%d")

    zt = get_zt_pool(date)
    north = get_north_flow_today()

    sentiment = {
        "date": date,
        "zt_count": len(zt) if not zt.empty else 0,
        "lianban_count": 0,
        "north_net_flow": 0.0,
    }

    # 连板数（连板>=2）
    if not zt.empty and "连板数" in zt.columns:
        sentiment["lianban_count"] = int((zt["连板数"] >= 2).sum())

    # 北向当日净流入
    if not north.empty and "value" in north.columns:
        sentiment["north_net_flow"] = float(north["value"].iloc[-1]) if len(north) > 0 else 0.0

    # 情绪评级
    score = 0
    if sentiment["zt_count"] > 50: score += 1
    if sentiment["lianban_count"] > 15: score += 1
    if sentiment["north_net_flow"] > 30: score += 1
    if sentiment["zt_count"] < 20: score -= 1
    if sentiment["lianban_count"] < 5: score -= 1
    if sentiment["north_net_flow"] < -30: score -= 1

    if score >= 2: sentiment["mood"] = "🔥 强势"
    elif score >= 1: sentiment["mood"] = "📈 偏强"
    elif score >= -1: sentiment["mood"] = "😐 中性"
    elif score >= -2: sentiment["mood"] = "📉 偏弱"
    else: sentiment["mood"] = "❄️ 弱势"

    sentiment["score"] = score
    return sentiment
