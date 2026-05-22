"""
pages/11_市场情报.py - Lv.C 市场情报中心
涨停板/龙虎榜/北向资金/板块/财联社
"""
import streamlit as st
import pandas as pd
from pathlib import Path
import sys
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from market_intel import (
    get_zt_pool, get_zt_pool_strong, get_zt_pool_zbgc,
    get_dragon_table, get_north_flow_today, get_north_top10,
    get_industry_board, get_concept_board,
    get_news_telegraph, get_market_sentiment,
)

st.set_page_config(page_title="市场情报 - Rock Quant", layout="wide")
st.title("市场情报中心")
st.caption("涨停板·龙虎榜·北向资金·板块·快讯")

# 情绪指标
st.subheader("市场情绪")
sentiment = get_market_sentiment()
c1, c2, c3, c4 = st.columns(4)
c1.metric("情绪", sentiment["mood"], f"score {sentiment['score']:+d}")
c2.metric("涨停数", sentiment["zt_count"])
c3.metric("连板数", sentiment["lianban_count"])
c4.metric("北向(亿)", f"{sentiment['north_net_flow']:.1f}")

# 标签页
tabs = st.tabs(["涨停板", "强势股", "炸板", "龙虎榜", "北向", "板块", "财联社"])

with tabs[0]:
    df = get_zt_pool()
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("无数据（网络不通或非交易日）")

with tabs[1]:
    df = get_zt_pool_strong()
    st.dataframe(df, use_container_width=True, hide_index=True) if not df.empty else st.info("无数据")

with tabs[2]:
    df = get_zt_pool_zbgc()
    st.dataframe(df, use_container_width=True, hide_index=True) if not df.empty else st.info("无数据")

with tabs[3]:
    df = get_dragon_table()
    st.dataframe(df, use_container_width=True, hide_index=True) if not df.empty else st.info("无数据")

with tabs[4]:
    st.markdown("### 当日实时净流入")
    df = get_north_flow_today()
    st.dataframe(df.tail(20), use_container_width=True, hide_index=True) if not df.empty else st.info("无数据")
    st.markdown("### 北向TOP10持仓")
    df2 = get_north_top10()
    st.dataframe(df2, use_container_width=True, hide_index=True) if not df2.empty else st.info("无数据")

with tabs[5]:
    st.markdown("### 行业板块")
    df = get_industry_board()
    st.dataframe(df, use_container_width=True, hide_index=True) if not df.empty else st.info("无数据")
    st.markdown("### 概念板块")
    df2 = get_concept_board()
    st.dataframe(df2, use_container_width=True, hide_index=True) if not df2.empty else st.info("无数据")

with tabs[6]:
    df = get_news_telegraph(50)
    st.dataframe(df, use_container_width=True, hide_index=True) if not df.empty else st.info("无数据")

st.markdown("---")
st.caption("Rock Quant 2.9 - 市场情报中心")
