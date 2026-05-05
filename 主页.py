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
    page_title="Rock Quant 2.0 - 顽岩量价模型",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📈 Rock Quant 2.0")
st.markdown("## 顽岩量价模型量化回测平台")
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

tab1, tab2, tab3, tab4 = st.tabs(["📚 策略百科", "⚡ 一键回测", "🎯 策略选型矩阵", "📖 产品路线图"])

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
    st.markdown("### 🎯 策略选型矩阵 - 什么行情用什么策略")
    
    selection_data = [
        {"市场状态": "明确单边上涨趋势", "首选策略": "唐奇安通道、双均线、DMI", "禁用策略": "RSI、KDJ、WR、BIAS", "核心逻辑": "趋势策略让利润奔跑，震荡策略会反复卖飞"},
        {"市场状态": "明确单边下跌趋势", "首选策略": "空仓或唐奇安做空", "禁用策略": "所有抄底类震荡策略", "核心逻辑": "下跌趋势中任何反弹都是逃命机会，不要抄底"},
        {"市场状态": "区间震荡行情", "首选策略": "RSI、KDJ、WR、BIAS、布林带", "禁用策略": "所有趋势突破类策略", "核心逻辑": "震荡市高抛低吸，突破策略来回打脸"},
        {"市场状态": "横盘末期即将突破", "首选策略": "布林带突破、肯特纳通道、成交量突破", "禁用策略": "不要提前赌方向，等突破确认", "核心逻辑": "布林带收窄是突破的最强信号之一"},
        {"市场状态": "V型反转极端行情", "首选策略": "BIAS、ROC、OBV背离", "禁用策略": "所有滞后的趋势类策略", "核心逻辑": "极端乖离率是唯一靠谱的反转信号"},
        {"市场状态": "不知道什么行情", "首选策略": "先看ADX值，ADX>25用趋势，ADX<20用震荡", "禁用策略": "不要上来就随便用一个策略", "核心逻辑": "先判断有没有趋势，再选策略，这是专业和散户的区别"},
    ]
    
    df = pd.DataFrame(selection_data)
    st.table(df)
    
    st.markdown("---")
    
    st.markdown("### 💡 使用深度分层指南")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("#### L1 入门层")
        st.caption("新手用户，刚接触量化")
        st.markdown("- 策略中心 浏览所有策略的原理说明")
        st.markdown("- 一键回测 快速了解策略表现")
        st.markdown("- 学习 优缺点和适用场景")
        st.success("目标：建立正确的策略认知，不迷信单一策略")
    with col2:
        st.markdown("#### L2 进阶层")
        st.caption("有一定经验，想优化")
        st.markdown("- 多策略对比 横向对比优劣")
        st.markdown("- 参数敏感性分析 找到最优区间")
        st.markdown("- 学习 实盘经验和常见陷阱")
        st.info("目标：找到适合自己风险偏好的策略和参数")
    with col3:
        st.markdown("#### L3 专业层")
        st.caption("专业交易者，想稳定盈利")
        st.markdown("- 策略组合优化 多策略分散")
        st.markdown("- 风控参数叠加 控制回撤")
        st.markdown("- 动态仓位管理 凯利公式")
        st.warning("目标：构建稳定盈利的多策略系统")
    with col4:
        st.markdown("#### L4 专家层")
        st.caption("量化开发者，自研策略")
        st.markdown("- 自定义策略开发")
        st.markdown("- 自定义因子编写")
        st.markdown("- 策略源码级优化")
        st.error("目标：开发自己的独家策略")
    
    st.markdown("---")
    
    st.markdown("### 📚 学习路径推荐")
    st.markdown("1. 先把策略中心所有策略的深度百科过一遍，建立完整认知")
    st.markdown("2. 用多策略对比，看看同一行情下不同策略的表现差异")
    st.markdown("3. 用参数敏感性分析，理解每个参数对策略收益风险的影响")
    st.markdown("4. 最重要：理解每个策略的适用和失效场景，不要在错误的行情用错误的策略")

with tab4:
    st.markdown("### 📖 产品路线图")
    
    progress_data = [
        {"功能模块": "20个主流量价策略库", "进度": 100, "状态": "✅ 已完成"},
        {"功能模块": "完整绩效指标计算", "进度": 100, "状态": "✅ 已完成"},
        {"功能模块": "策略深度百科知识库", "进度": 100, "状态": "✅ 已完成"},
        {"功能模块": "策略选型矩阵指南", "进度": 100, "状态": "✅ 已完成"},
        {"功能模块": "多策略对比分析", "进度": 100, "状态": "✅ 已完成"},
        {"功能模块": "参数敏感性扫描", "进度": 100, "状态": "✅ 已完成"},
        {"功能模块": "回测结果专业解读", "进度": 100, "状态": "✅ 已完成"},
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
st.caption("Rock Quant 2.0 - 顽岩量价模型 | 完整开源")
