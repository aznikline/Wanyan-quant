import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import BacktestConfig
from backtest_engine import BacktestEngine
from strategies import get_all_strategies, create_strategy
from data_loader import DataLoader

st.set_page_config(
    page_title="Rock Quant 2.0 - 顽岩风格量价模型",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📈 Rock Quant 2.0")
st.markdown("## 顽岩风格量价模型量化回测平台")
st.markdown("---")

st.sidebar.success("👈 选择左侧页面进入对应功能")

# 统计卡片
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("内置策略数量", "20个", delta="覆盖5大类")
with col2:
    st.metric("绩效指标", "20+", delta="全量化")
with col3:
    st.metric("可视化图表", "8种", delta="交互式")
with col4:
    st.metric("使用深度", "4层", delta="入门到专家")

st.markdown("---")

st.subheader("🚀 快速开始")

tab1, tab2, tab3, tab4 = st.tabs(["📚 策略百科", "⚡ 一键回测", "🎯 使用指南", "📖 产品路线图"])

with tab1:
    st.markdown("### 策略库概览")
    
    strategy_categories = {
        "趋势跟踪类 (6个)": ["双均线策略", "MACD策略", "DMA平均线差策略", "TRIX三重指数策略", "均线多头发散策略", "唐奇安通道突破策略"],
        "震荡反转类 (7个)": ["RSI超买超卖策略", "KDJ随机指标策略", "CCI顺势指标策略", "WR威廉指标策略", "MOM动量线策略", "ROC变动率策略", "BIAS乖离率策略"],
        "通道突破类 (2个)": ["布林带突破策略", "肯特纳通道突破策略"],
        "量价配合类 (4个)": ["成交量突破策略", "OBV能量潮策略", "VR容量比率策略", "EMV简易波动策略"],
        "趋势强弱类 (1个)": ["DMI趋向指标策略"],
    }
    
    for category, strategies in strategy_categories.items():
        with st.expander(category):
            for s in strategies:
                st.markdown(f"- {s}")

with tab2:
    st.markdown("### 一键快速回测")
    
    col1, col2 = st.columns(2)
    with col1:
        strategy_name = st.selectbox("选择策略", get_all_strategies())
    with col2:
        loader = DataLoader()
        preset_symbols = list(loader.preset_symbols.keys())
        symbol_name = st.selectbox("选择标的", preset_symbols)
    
    if st.button("🚀 开始回测", type="primary"):
        with st.spinner("正在回测..."):
            symbol_code = loader.preset_symbols[symbol_name]
            data = loader.load_data(symbol_code, "2020-01-01", "2023-12-31")
            config = BacktestConfig(initial_capital=1000000)
            engine = BacktestEngine(config)
            strategy = create_strategy(strategy_name)
            signals = strategy.generate_signals(data)
            result = engine.run(data, signals)
            perf = result.performance
            
            st.success("回测完成!")
            
            st.markdown("#### 核心绩效指标")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("总收益率", f"{perf['总收益率']:.2f}%")
                st.metric("年化收益率", f"{perf['年化收益率(CAGR)']:.2f}%")
            with col2:
                st.metric("夏普比率", f"{perf['夏普比率']:.2f}")
                st.metric("卡玛比率", f"{perf['卡玛比率']:.2f}")
            with col3:
                st.metric("最大回撤", f"{perf['最大回撤']:.2f}%")
                st.metric("索提诺比率", f"{perf['索提诺比率']:.2f}")
            with col4:
                st.metric("交易次数", perf['总交易次数'])
                st.metric("胜率", f"{perf['胜率']:.1f}%")
            
            st.markdown("#### 净值曲线")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=result.equity_curve.index, y=result.equity_curve.values, name="策略净值", line=dict(color="#1f77b4", width=2)))
            fig.update_layout(height=400, hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.markdown("### 🎯 使用指南")
    
    st.markdown("#### L1 入门层 - 新手用户")
    st.markdown("- 左侧 策略中心 浏览所有策略的原理说明")
    st.markdown("- 一键回测 快速了解策略表现")
    
    st.markdown("#### L2 进阶层 - 进阶用户")
    st.markdown("- 多策略对比 同时对比多个策略的表现")
    st.markdown("- 参数敏感性分析 找到最优参数区间")
    
    st.markdown("#### L3 专业层 - 专业用户 (开发中)")
    st.markdown("- 策略组合优化 多策略组合回测")
    st.markdown("- 风控参数叠加测试")
    
    st.markdown("#### L4 专家层 - 量化开发者 (开发中)")
    st.markdown("- 自定义策略开发")
    st.markdown("- 自定义指标编写")

with tab4:
    st.markdown("### 📖 产品路线图")
    
    progress_data = [
        {"功能模块": "20个主流量价策略库", "进度": 100, "状态": "✅ 已完成"},
        {"功能模块": "完整绩效指标计算", "进度": 100, "状态": "✅ 已完成"},
        {"功能模块": "策略中心分类展示", "进度": 100, "状态": "✅ 已完成"},
        {"功能模块": "多策略对比分析", "进度": 100, "状态": "✅ 已完成"},
        {"功能模块": "参数敏感性扫描", "进度": 100, "状态": "✅ 已完成"},
        {"功能模块": "月度热力图/盈亏分布", "进度": 50, "状态": "🚧 开发中"},
        {"功能模块": "多标的批量回测", "进度": 30, "状态": "📋 规划中"},
        {"功能模块": "策略组合优化", "进度": 20, "状态": "📋 规划中"},
        {"功能模块": "PDF报告导出", "进度": 0, "状态": "📋 规划中"},
        {"功能模块": "自定义策略编辑器", "进度": 0, "状态": "📋 规划中"},
    ]
    
    for item in progress_data:
        col1, col2, col3 = st.columns([3, 5, 2])
        with col1:
            st.markdown(f"{item['状态']} {item['功能模块']}")
        with col2:
            st.progress(item['进度'] / 100)
        with col3:
            st.markdown(f"{item['进度']}%")

st.markdown("---")
st.caption("Rock Quant 2.0 - 顽岩风格量价模型 | 完整开源")
