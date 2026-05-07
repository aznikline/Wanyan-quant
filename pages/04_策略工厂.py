"""
 - 

"""

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from strategies import BaseStrategy

st.set_page_config(
  page_title=" - Rock Quant",
  page_icon="",
  layout="wide",
  initial_sidebar_state="expanded"
)

st.title(" ")
st.caption(" - ")

st.markdown("---")

# ========== ==========
if 'custom_strategies' not in st.session_state:
  st.session_state.custom_strategies = {}

if 'conditions' not in st.session_state:
  st.session_state.conditions = [
    {'type': 'crossover', 'indicator': 'MA', 'param': 5, 'compare': 'MA', 'compare_param': 20}
  ]

# ========== ==========
INDICATORS = {
  "MA": {"name": "", "params": ["period"], "default": 20},
  "MACD": {"name": "MACD", "params": ["fast", "slow", "signal"], "default": [12, 26, 9]},
  "RSI": {"name": "RSI", "params": ["period"], "default": 14},
  "BOLL": {"name": "", "params": ["period", "std"], "default": [20, 2]},
  "VOLUME": {"name": "", "params": ["ma_period"], "default": 20},
}

COMPARATORS = {
  "crossover": "",
  "crossdown": "",
  "above": "",
  "below": "",
}

# ========== ==========
st.subheader(" ")

with st.expander("", expanded=True):
  st.markdown("****")
  
  for i, cond in enumerate(st.session_state.conditions):
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    
    with col1:
      indicator = st.selectbox(
        f" {i+1}",
        list(INDICATORS.keys()),
        format_func=lambda x: INDICATORS[x]["name"],
        key=f"indicator_{i}"
      )
      
    with col2:
      comparator = st.selectbox(
        f" {i+1}",
        list(COMPARATORS.keys()),
        format_func=lambda x: COMPARATORS[x],
        key=f"comparator_{i}"
      )
      
    with col3:
      compare_with = st.selectbox(
        f" {i+1}",
        ["", ""],
        key=f"compare_{i}"
      )
      
    with col4:
      if st.button("", key=f"del_{i}") and len(st.session_state.conditions) > 1:
        st.session_state.conditions.pop(i)
        st.rerun()
  
  if st.button("+ ", type="secondary"):
    st.session_state.conditions.append(
      {'type': 'crossover', 'indicator': 'MA', 'param': 5, 'compare': 'MA', 'compare_param': 20}
    )
    st.rerun()

with st.expander(""):
  st.markdown("****")
  st.info("...")

st.markdown("---")

# ========== ==========
st.subheader(" ")

# 
st.markdown("****")

strategy_code = '''
class CustomStrategy(BaseStrategy):
  """"""
  
  def __init__(self):
    super().__init__()
    self.strategy_name = ""
'''

# 
for i, cond in enumerate(st.session_state.conditions):
  strategy_code += f'''
    self.param_{i+1}_indicator = {cond.get('indicator', 'MA')}
    self.param_{i+1}_comparator = {cond.get('comparator', 'crossover')}
'''

strategy_code += '''
  def generate_signals(self, data: pd.DataFrame) -> pd.Series:
    """"""
    signals = pd.Series(0, index=data.index)
    
    # 
    ma5 = data['close'].rolling(5).mean()
    ma20 = data['close'].rolling(20).mean()
    
    # 
    crossover = (ma5 > ma20) & (ma5.shift(1) <= ma20.shift(1))
    signals[crossover] = 1
    
    return signals
'''

st.code(strategy_code, language="python")

st.markdown("---")

# ========== ==========
st.subheader(" ")

col1, col2 = st.columns(2)
with col1:
  strategy_name = st.text_input("", placeholder="")
  
with col2:
  strategy_desc = st.text_input("", placeholder="")

if st.button("", type="primary", use_container_width=True):
  if not strategy_name:
    st.error("")
  else:
    # 
    st.session_state.custom_strategies[strategy_name] = {
      'name': strategy_name,
      'desc': strategy_desc,
      'conditions': st.session_state.conditions.copy(),
      'created_at': pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
    }
    st.success(f" {strategy_name}")
    st.balloons()

# ========== ==========
if st.session_state.custom_strategies:
  st.markdown("---")
  st.subheader(" ")
  
  for name, strategy in st.session_state.custom_strategies.items():
    with st.expander(f"{name} - {strategy['desc'] or ''}"):
      st.write(f"{strategy['created_at']}")
      st.write(f"{len(strategy['conditions'])}")
      
      col1, col2 = st.columns(2)
      with col1:
        if st.button("", key=f"use_{name}"):
          st.info("...")
      with col2:
        if st.button("", key=f"del_strat_{name}", type="secondary"):
          del st.session_state.custom_strategies[name]
          st.rerun()

st.markdown("---")
st.info(" ")
