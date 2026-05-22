"""
pages/10_因子库.py - Lv.B Alpha158 因子分析中心
"""
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from alpha158 import get_alpha158_factors, compute_all_factors, factor_summary, compute_ic
from data_loader import DataLoader

st.set_page_config(page_title="因子库 - Rock Quant", layout="wide")
st.title("Alpha158 因子库")
st.caption("Qlib 精简版，83 个量价/技术因子")

with st.sidebar:
    st.header("数据配置")
    loader = DataLoader()
    symbol_name = st.selectbox("标的", list(loader.preset_symbols.keys()))
    start_date = st.date_input("开始日期", pd.to_datetime("2023-01-01"))
    end_date = st.date_input("结束日期", pd.to_datetime("2024-12-31"))
    source = st.selectbox("数据源", ["simulated", "akshare", "tushare"])
    forward_days = st.slider("IC 未来收益天数", 1, 20, 5)
    run = st.button("计算因子", type="primary")

if run:
    symbol_code = loader.preset_symbols[symbol_name]
    with st.spinner("加载数据..."):
        try:
            data = loader.load_data(symbol_code, str(start_date), str(end_date), data_source=source)
        except Exception as e:
            st.error(f"数据加载失败: {e}")
            st.stop()
        st.success(f"数据加载完成: {len(data)} 行")

    with st.spinner("计算 83 个因子..."):
        factor_df = compute_all_factors(data)

    # 因子统计
    st.subheader("因子统计")
    summary = factor_summary(factor_df)
    st.dataframe(summary.head(20), use_container_width=True)

    # IC 评估
    st.subheader(f"因子有效性（未来 {forward_days} 日收益 IC）")
    future_ret = data["close"].pct_change(forward_days).shift(-forward_days)
    ic = compute_ic(factor_df, future_ret).dropna()

    top_n = 20
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"### Top {top_n} 正向因子")
        top_pos = ic.head(top_n).to_frame("IC")
        st.dataframe(top_pos.style.format({"IC": "{:.4f}"}))

    with col2:
        st.markdown(f"### Top {top_n} 负向因子")
        top_neg = ic.tail(top_n).sort_values().to_frame("IC")
        st.dataframe(top_neg.style.format({"IC": "{:.4f}"}))

    # 因子原始数据
    with st.expander("因子原始数据（最后20行）", expanded=False):
        st.dataframe(factor_df.tail(20), use_container_width=True)

    # 单因子曲线
    st.subheader("单因子时序")
    factor_name = st.selectbox("选择因子", factor_df.columns.tolist())
    if factor_name:
        import plotly.express as px
        chart_df = pd.DataFrame({
            "日期": factor_df.index,
            factor_name: factor_df[factor_name],
        })
        fig = px.line(chart_df, x="日期", y=factor_name, title=f"{factor_name} 时序")
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.caption("Rock Quant 2.9 - Alpha158 因子库")
