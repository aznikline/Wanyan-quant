"""
策略工厂 - 可视化自定义策略编辑器
用户通过选择条件组合，无需写代码即可创建自己的量化策略
"""

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from strategies import BaseStrategy

st.set_page_config(
    page_title="策略工厂 - Rock Quant",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title(" 策略工厂")
st.caption("可视化自定义策略编辑器 - 无需写代码，拖拽组合条件")

st.markdown("---")

# ========== 初始化 ==========
if 'custom_strategies' not in st.session_state:
    st.session_state.custom_strategies = {}

if 'conditions' not in st.session_state:
    st.session_state.conditions = [
        {'type': 'crossover', 'indicator': 'MA', 'param': 5, 'compare': 'MA', 'compare_param': 20}
    ]

# ========== 可用指标列表 ==========
INDICATORS = {
    "MA": {"name": "移动平均线", "params": ["period"], "default": 20},
    "MACD": {"name": "MACD", "params": ["fast", "slow", "signal"], "default": [12, 26, 9]},
    "RSI": {"name": "RSI相对强弱", "params": ["period"], "default": 14},
    "BOLL": {"name": "布林带", "params": ["period", "std"], "default": [20, 2]},
    "VOLUME": {"name": "成交量", "params": ["ma_period"], "default": 20},
}

COMPARATORS = {
    "crossover": "上穿",
    "crossdown": "下穿",
    "above": "大于",
    "below": "小于",
}

# ========== 条件构建器 ==========
st.subheader(" 策略构建器")

with st.expander("买入条件", expanded=True):
    st.markdown("**当满足以下条件时，买入开仓：**")
    
    for i, cond in enumerate(st.session_state.conditions):
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        
        with col1:
            indicator = st.selectbox(
                f"指标 {i+1}",
                list(INDICATORS.keys()),
                format_func=lambda x: INDICATORS[x]["name"],
                key=f"indicator_{i}"
            )
            
        with col2:
            comparator = st.selectbox(
                f"比较 {i+1}",
                list(COMPARATORS.keys()),
                format_func=lambda x: COMPARATORS[x],
                key=f"comparator_{i}"
            )
            
        with col3:
            compare_with = st.selectbox(
                f"对比 {i+1}",
                ["另一指标", "固定数值"],
                key=f"compare_{i}"
            )
            
        with col4:
            if st.button("", key=f"del_{i}") and len(st.session_state.conditions) > 1:
                st.session_state.conditions.pop(i)
                st.rerun()
    
    if st.button("+ 添加条件", type="secondary"):
        st.session_state.conditions.append(
            {'type': 'crossover', 'indicator': 'MA', 'param': 5, 'compare': 'MA', 'compare_param': 20}
        )
        st.rerun()

with st.expander("卖出条件"):
    st.markdown("**当满足以下条件时，卖出平仓：**")
    st.info("卖出条件开发中...")

st.markdown("---")

# ========== 预览区 ==========
st.subheader(" 策略预览")

# 生成策略代码预览
st.markdown("**生成的策略代码：**")

strategy_code = '''
class CustomStrategy(BaseStrategy):
    """用户自定义策略"""
    
    def __init__(self):
        super().__init__()
        self.strategy_name = "自定义策略"
'''

# 添加参数
for i, cond in enumerate(st.session_state.conditions):
    strategy_code += f'''
        self.param_{i+1}_indicator = {cond.get('indicator', 'MA')}
        self.param_{i+1}_comparator = {cond.get('comparator', 'crossover')}
'''

strategy_code += '''
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """生成交易信号"""
        signals = pd.Series(0, index=data.index)
        
        # 计算技术指标
        ma5 = data['close'].rolling(5).mean()
        ma20 = data['close'].rolling(20).mean()
        
        # 生成信号
        crossover = (ma5 > ma20) & (ma5.shift(1) <= ma20.shift(1))
        signals[crossover] = 1
        
        return signals
'''

st.code(strategy_code, language="python")

st.markdown("---")

# ========== 保存策略 ==========
st.subheader(" 保存策略")

col1, col2 = st.columns(2)
with col1:
    strategy_name = st.text_input("策略名称", placeholder="例如：我的均线策略")
    
with col2:
    strategy_desc = st.text_input("策略描述", placeholder="简要描述策略逻辑")

if st.button("保存策略到策略库", type="primary", use_container_width=True):
    if not strategy_name:
        st.error("请输入策略名称")
    else:
        # 保存策略
        st.session_state.custom_strategies[strategy_name] = {
            'name': strategy_name,
            'desc': strategy_desc,
            'conditions': st.session_state.conditions.copy(),
            'created_at': pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
        }
        st.success(f" 策略「{strategy_name}」已保存！")
        st.balloons()

# ========== 已保存策略列表 ==========
if st.session_state.custom_strategies:
    st.markdown("---")
    st.subheader(" 我的策略")
    
    for name, strategy in st.session_state.custom_strategies.items():
        with st.expander(f"{name} - {strategy['desc'] or '暂无描述'}"):
            st.write(f"创建时间：{strategy['created_at']}")
            st.write(f"条件数量：{len(strategy['conditions'])}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("应用此策略", key=f"use_{name}"):
                    st.info("策略应用功能开发中...")
            with col2:
                if st.button("删除策略", key=f"del_strat_{name}", type="secondary"):
                    del st.session_state.custom_strategies[name]
                    st.rerun()

st.markdown("---")
st.info(" 提示：策略工厂正在开发中，目前支持预览策略代码生成逻辑，完整的自定义策略回测功能即将上线！")
