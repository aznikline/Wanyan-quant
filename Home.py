import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import sys
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent / "src"))

st.set_page_config(
    page_title="Rock Quant 2.4 - 顽岩量价模型",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Rock Quant 2.4")
st.markdown("## 顽岩量价模型量化回测平台")
st.markdown("---")

# ========== 配置 - 标的列表 ==========
PRESET_SYMBOLS = [
    {"name": "沪深300", "code": "000300.SH", "tag": "推荐"},
    {"name": "中证500", "code": "000905.SH", "tag": ""},
    {"name": "创业板指", "code": "399006.SZ", "tag": ""},
    {"name": "上证指数", "code": "000001.SH", "tag": ""},
    {"name": "贵州茅台", "code": "600519.SH", "tag": ""},
    {"name": "宁德时代", "code": "300750.SZ", "tag": ""},
    {"name": "比亚迪", "code": "002594.SZ", "tag": ""},
]

# ========== 配置 - 策略场景分组 ==========
STRATEGY_SCENARIOS = {
    "稳健型": {
        "strategies": ["双均线策略", "布林带突破策略"],
        "description": "低回撤，适合新手和定投",
        "color": "green"
    },
    "趋势型": {
        "strategies": ["MACD策略", "DMA平均线差策略", "TRIX三重指数策略"],
        "description": "高收益，适合趋势行情",
        "color": "blue"
    },
    "震荡型": {
        "strategies": ["RSI超买超卖策略", "KDJ随机指标策略", "CCI顺势指标策略"],
        "description": "波段操作，适合震荡市场",
        "color": "orange"
    },
    "量价型": {
        "strategies": ["OBV能量潮策略", "VR容量比率策略", "成交量突破策略"],
        "description": "量价配合，捕捉资金动向",
        "color": "purple"
    }
}

# ========== 侧边栏引导 ==========
with st.sidebar:
    st.markdown("---")
    st.markdown("### 快速导航")
    st.markdown("- **策略回测**：单策略深度回测与绩效分析")
    st.markdown("- **批量分析**：多策略对比、多标的回测、组合优化")
    st.markdown("- **策略百科**：20个策略完整文档与实盘经验")
    st.markdown("---")
    st.caption("v2.4.0 | 体验优化版")

# ========== 3步快速开始区 ==========
st.markdown("### 🚀 3步完成第一次回测")

# 第1步：选择标的
st.markdown("#### 第1步：选择标的")
col1, col2, col3, col4 = st.columns(4)
symbols_col = [col1, col2, col3, col4]

if 'selected_symbol' not in st.session_state:
    st.session_state.selected_symbol = "沪深300"

for idx, symbol in enumerate(PRESET_SYMBOLS[:4]):
    with symbols_col[idx]:
        is_selected = st.session_state.selected_symbol == symbol['name']
        btn_type = "primary" if is_selected else "secondary"
        if st.button(f"{symbol['name']}\n{symbol['tag']}", key=f"sym_{idx}", use_container_width=True, type=btn_type):
            st.session_state.selected_symbol = symbol['name']
            st.rerun()

col1, col2, col3 = st.columns(3)
for idx, symbol in enumerate(PRESET_SYMBOLS[4:]):
    with [col1, col2, col3][idx]:
        is_selected = st.session_state.selected_symbol == symbol['name']
        btn_type = "primary" if is_selected else "secondary"
        if st.button(f"{symbol['name']}", key=f"sym_more_{idx}", use_container_width=True, type=btn_type):
            st.session_state.selected_symbol = symbol['name']
            st.rerun()

st.caption(f"已选择：{st.session_state.selected_symbol}")
st.markdown("---")

# 第2步：选择策略
st.markdown("#### 第2步：选择策略")

if 'selected_strategy' not in st.session_state:
    st.session_state.selected_strategy = "双均线策略"

col1, col2 = st.columns(2)
with col1:
    # 场景选择
    scene_list = list(STRATEGY_SCENARIOS.keys())
    if 'selected_scene' not in st.session_state:
        st.session_state.selected_scene = "稳健型"

    for idx, (scene, config) in enumerate(STRATEGY_SCENARIOS.items()):
        is_selected = st.session_state.selected_scene == scene
        btn_type = "primary" if is_selected else "secondary"
        if st.button(f"{scene}\n{config['description']}", key=f"scene_{idx}", use_container_width=True, type=btn_type):
            st.session_state.selected_scene = scene
            # 自动选中该场景第一个策略
            first_strategy = config['strategies'][0]
            st.session_state.selected_strategy = first_strategy
            st.rerun()

with col2:
    # 该场景下的策略列表
    current_scene_config = STRATEGY_SCENARIOS[st.session_state.selected_scene]
    st.markdown(f"**{st.session_state.selected_scene}** 策略列表：")
    for idx, strategy_name in enumerate(current_scene_config['strategies']):
        is_selected = st.session_state.selected_strategy == strategy_name
        btn_type = "primary" if is_selected else "secondary"
        if st.button(strategy_name, key=f"strat_{idx}", use_container_width=True, type=btn_type):
            st.session_state.selected_strategy = strategy_name
            st.rerun()

st.caption(f"已选择策略：{st.session_state.selected_strategy}")
st.markdown("---")

# 第3步：选择时间范围
st.markdown("#### 第3步：选择时间范围")
col1, col2, col3, col4 = st.columns(4)

end_date_default = datetime.now().strftime("%Y-%m-%d")
start_date_default = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

if 'start_date' not in st.session_state:
    st.session_state.start_date = start_date_default
if 'end_date' not in st.session_state:
    st.session_state.end_date = end_date_default

with col1:
    if st.button("近1年", use_container_width=True):
        st.session_state.start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        st.session_state.end_date = end_date_default
        st.rerun()

with col2:
    if st.button("近3年", use_container_width=True):
        st.session_state.start_date = (datetime.now() - timedelta(days=1095)).strftime("%Y-%m-%d")
        st.session_state.end_date = end_date_default
        st.rerun()

with col3:
    if st.button("近5年", use_container_width=True):
        st.session_state.start_date = (datetime.now() - timedelta(days=1825)).strftime("%Y-%m-%d")
        st.session_state.end_date = end_date_default
        st.rerun()

with col4:
    if st.button("2015年至今", use_container_width=True):
        st.session_state.start_date = "2015-01-01"
        st.session_state.end_date = end_date_default
        st.rerun()

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("开始日期", value=datetime.strptime(st.session_state.start_date, "%Y-%m-%d"))
with col2:
    end_date = st.date_input("结束日期", value=datetime.strptime(st.session_state.end_date, "%Y-%m-%d"))

st.session_state.start_date = start_date.strftime("%Y-%m-%d")
st.session_state.end_date = end_date.strftime("%Y-%m-%d")

st.markdown("---")

# 开始回测按钮
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("开始回测", use_container_width=True, type="primary"):
        # 保存参数到session state，跳转到回测页面
        st.session_state.quick_start_mode = True
        st.session_state.quick_symbol = st.session_state.selected_symbol
        st.session_state.quick_strategy = st.session_state.selected_strategy
        st.session_state.quick_start_date = st.session_state.start_date
        st.session_state.quick_end_date = st.session_state.end_date
        st.switch_page("pages/01_策略回测.py")

st.markdown("---")

# ========== 功能入口区 ==========
st.markdown("### 🔧 更多功能")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("#### 策略回测")
    st.caption("单策略完整回测分析")
    st.markdown("- 20个主流量价策略")
    st.markdown("- 完整绩效指标计算")
    st.markdown("- 参数敏感性扫描")
    if st.button("进入策略回测 →", key="entry_backtest", use_container_width=True):
        st.switch_page("pages/01_策略回测.py")

with col2:
    st.markdown("#### 批量分析")
    st.caption("多维度批量计算与对比")
    st.markdown("- 同一标的多策略对比")
    st.markdown("- 同一策略多标的回测")
    st.markdown("- 策略组合权重优化")
    if st.button("进入批量分析 →", key="entry_batch", use_container_width=True):
        st.switch_page("pages/02_批量分析.py")

with col3:
    st.markdown("#### 策略百科")
    st.caption("20个策略深度知识库")
    st.markdown("- 每个策略7维度详解")
    st.markdown("- A股实盘参数建议")
    st.markdown("- 常见陷阱与避坑指南")
    if st.button("进入策略百科 →", key="entry_wiki", use_container_width=True):
        st.switch_page("pages/03_策略百科.py")

st.markdown("---")

# ========== 策略选型参考 ==========
st.markdown("### 📋 策略选型参考矩阵")

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
st.caption("Rock Quant 2.4.0 - 顽岩量价模型 | 完整开源 | 所有回测结果基于A股历史数据")
