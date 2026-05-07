import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Rock Quant 2.0 - 顽岩量价模型",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📈 Rock Quant 2.0")
st.markdown("## 顽岩量价模型量化回测平台")
st.markdown("---")

# ========== 侧边栏引导
with st.sidebar:
    st.success("👈 选择上方页面进入对应功能")
    st.markdown("---")
    st.markdown("### 快速导航")
    st.markdown("- **策略回测**：单策略深度回测与绩效分析")
    st.markdown("- **批量分析**：多策略对比、多标的回测、组合优化")
    st.markdown("- **策略百科**：20个策略完整文档与实盘经验")

# ========== 🔥 快速开始区
st.markdown("### ⚡ 快速开始 - 一键回测")

col1, col2, col3, col4 = st.columns(4)

quick_presets = [
    {
        "name": "双均线策略",
        "symbol": "沪深300",
        "desc": "经典趋势跟踪",
        "page": "策略回测",
        "strategy": "双均线策略"
    },
    {
        "name": "RSI策略",
        "symbol": "沪深300",
        "desc": "震荡反转神器",
        "page": "策略回测",
        "strategy": "RSI超买超卖策略"
    },
    {
        "name": "4大策略PK",
        "symbol": "沪深300",
        "desc": "多策略横向对比",
        "page": "批量分析",
        "mode": "多策略对比"
    },
    {
        "name": "策略组合优化",
        "symbol": "沪深300",
        "desc": "马科维茨权重计算",
        "page": "批量分析",
        "mode": "组合优化"
    }
]

for idx, preset in enumerate(quick_presets):
    with [col1, col2, col3, col4][idx]:
        st.markdown(f"**{preset['name']}**")
        st.caption(f"{preset['symbol']} | {preset['desc']}")
        if st.button(f"→ 直接{preset['page']}", key=f"quick_{idx}", use_container_width=True):
            if preset['page'] == "策略回测":
                st.session_state.quick_strategy = preset.get('strategy')
                st.session_state.quick_symbol = preset.get('symbol')
                st.switch_page("pages/01_策略回测.py")
            else:
                st.switch_page("pages/02_批量分析.py")

st.markdown("---")

# ========== 功能卡片
st.markdown("### 🎯 核心功能")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("#### 📈 策略回测")
    st.caption("单策略完整回测分析")
    st.markdown("- 20个主流量价策略")
    st.markdown("- 完整绩效指标计算")
    st.markdown("- 月度收益热力图")
    st.markdown("- 交易盈亏分布分析")
    st.markdown("- 参数敏感性扫描")
    if st.button("进入策略回测 →", use_container_width=True, type="primary"):
        st.switch_page("pages/01_策略回测.py")

with col2:
    st.markdown("#### 🎯 批量分析")
    st.caption("多维度批量计算与对比")
    st.markdown("- 同一标的多策略对比")
    st.markdown("- 同一策略多标的回测")
    st.markdown("- 策略组合权重优化")
    st.markdown("- 相关性矩阵分析")
    if st.button("进入批量分析 →", use_container_width=True, type="primary"):
        st.switch_page("pages/02_批量分析.py")

with col3:
    st.markdown("#### 📚 策略百科")
    st.caption("20个策略深度知识库")
    st.markdown("- 每个策略7维度详解")
    st.markdown("- A股实盘参数建议")
    st.markdown("- 适用与失效场景")
    st.markdown("- 常见陷阱与避坑指南")
    if st.button("进入策略百科 →", use_container_width=True, type="primary"):
        st.switch_page("pages/03_策略百科.py")

st.markdown("---")

# ========== 统计卡片
st.markdown("### 📊 内置策略库（20个）")

strategy_categories = {
    "📈 趋势跟踪类（6个）": ["双均线策略", "MACD策略", "DMA平均线差策略", 
                           "TRIX三重指数策略", "均线多头发散策略", "唐奇安通道突破策略"],
    "📊 震荡反转类（7个）": ["RSI超买超卖策略", "KDJ随机指标策略", "CCI顺势指标策略",
                           "WR威廉指标策略", "MOM动量线策略", "ROC变动率策略", "BIAS乖离率策略"],
    "📌 通道突破类（2个）": ["布林带突破策略", "肯特纳通道突破策略"],
    "📉 量价配合类（4个）": ["成交量突破策略", "OBV能量潮策略", "VR容量比率策略", "EMV简易波动策略"],
    "🎯 趋势强弱类（1个）": ["DMI趋向指标策略"],
}

for category, strategies in strategy_categories.items():
    with st.expander(category, expanded=False):
        cols = st.columns(3)
        for idx, s in enumerate(strategies):
            cols[idx % 3].markdown(f"- {s}")

st.markdown("---")

# ========== 策略选型矩阵
st.markdown("### 💡 策略选型参考矩阵")

selection_data = [
    {"市场状态": "明确单边上涨趋势", "首选策略": "唐奇安通道、双均线、DMI", "禁用策略": "RSI、KDJ、WR、BIAS", "核心逻辑": "趋势策略让利润奔跑，震荡策略会反复卖飞"},
    {"市场状态": "明确单边下跌趋势", "首选策略": "空仓或唐奇安做空", "禁用策略": "所有抄底类震荡策略", "核心逻辑": "下跌趋势中任何反弹都是逃命机会，不要抄底"},
    {"市场状态": "区间震荡行情", "首选策略": "RSI、KDJ、WR、BIAS、布林带", "禁用策略": "所有趋势突破类策略", "核心逻辑": "震荡市高抛低吸，突破策略来回打脸"},
    {"市场状态": "横盘末期即将突破", "首选策略": "布林带突破、肯特纳通道、成交量突破", "禁用策略": "不要提前赌方向，等突破确认", "核心逻辑": "布林带收窄是突破的最强信号之一"},
    {"市场状态": "V型反转极端行情", "首选策略": "BIAS、ROC、OBV背离", "禁用策略": "所有滞后的趋势类策略", "核心逻辑": "极端乖离率是唯一靠谱的反转信号"},
    {"市场状态": "不知道什么行情", "首选策略": "先看ADX值，ADX>25用趋势，ADX<20用震荡", "禁用策略": "不要上来就随便用一个策略", "核心逻辑": "先判断有没有趋势，再选策略，这是专业和散户的区别"},
]

df_selection = pd.DataFrame(selection_data)
st.table(df_selection)

st.markdown("---")

# ========== 使用层次引导
st.markdown("### 🎯 4层使用深度指南")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("#### L1 入门层")
    st.caption("新手用户，刚接触量化")
    st.markdown("- 策略百科 学习原理")
    st.markdown("- 快速开始 一键体验")
    st.success("目标：建立正确的策略认知")

with col2:
    st.markdown("#### L2 进阶层")
    st.caption("有一定经验，想优化")
    st.markdown("- 策略回测 深度分析")
    st.markdown("- 参数扫描 找到最优值")
    st.info("目标：找到适合自己的参数")

with col3:
    st.markdown("#### L3 专业层")
    st.caption("专业交易者，稳定盈利")
    st.markdown("- 多策略对比 筛选优胜")
    st.markdown("- 组合优化 分散风险")
    st.warning("目标：构建稳定的多策略系统")

with col4:
    st.markdown("#### L4 专家层")
    st.caption("量化开发者，自研策略")
    st.markdown("- 修改策略源码")
    st.markdown("- 开发自定义因子")
    st.error("目标：开发自己的独家策略")

st.markdown("---")

# ========== 产品路线图
st.markdown("### 📖 产品路线图")

progress_data = [
    {"功能模块": "20个主流量价策略库", "进度": 100, "状态": "✅ 已完成"},
    {"功能模块": "完整绩效指标计算", "进度": 100, "状态": "✅ 已完成"},
    {"功能模块": "策略深度百科知识库", "进度": 100, "状态": "✅ 已完成"},
    {"功能模块": "策略选型矩阵指南", "进度": 100, "状态": "✅ 已完成"},
    {"功能模块": "多策略对比分析", "进度": 100, "状态": "✅ 已完成"},
    {"功能模块": "参数敏感性扫描", "进度": 100, "状态": "✅ 已完成"},
    {"功能模块": "月度热力图/盈亏分布", "进度": 100, "状态": "✅ 已完成"},
    {"功能模块": "多标的批量回测", "进度": 100, "状态": "✅ 已完成"},
    {"功能模块": "策略组合优化", "进度": 100, "状态": "✅ 已完成"},
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
st.caption("Rock Quant 2.2.0 - 顽岩量价模型 | 完整开源 | 支持专业PDF报告导出 | 所有回测结果基于A股历史数据")
