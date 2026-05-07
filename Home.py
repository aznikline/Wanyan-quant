import streamlit as st
import pandas as pd

st.set_page_config(
  page_title="Rock Quant 2.0 - ",
  page_icon="",
  layout="wide",
  initial_sidebar_state="expanded"
)

st.title(" Rock Quant 2.0")
st.markdown("## ")
st.markdown("---")

# ========== 
with st.sidebar:
  st.success(" ")
  st.markdown("---")
  st.markdown("### ")
  st.markdown("- ****")
  st.markdown("- ****")
  st.markdown("- ****20")

# ========== 
st.markdown("###  - ")

col1, col2, col3, col4 = st.columns(4)

quick_presets = [
  {
    "name": "",
    "symbol": "300",
    "desc": "",
    "page": "",
    "strategy": ""
  },
  {
    "name": "RSI",
    "symbol": "300",
    "desc": "",
    "page": "",
    "strategy": "RSI"
  },
  {
    "name": "4PK",
    "symbol": "300",
    "desc": "",
    "page": "",
    "mode": ""
  },
  {
    "name": "",
    "symbol": "300",
    "desc": "",
    "page": "",
    "mode": ""
  }
]

for idx, preset in enumerate(quick_presets):
  with [col1, col2, col3, col4][idx]:
    st.markdown(f"**{preset['name']}**")
    st.caption(f"{preset['symbol']} | {preset['desc']}")
    if st.button(f"→ {preset['page']}", key=f"quick_{idx}", use_container_width=True):
      if preset['page'] == "":
        st.session_state.quick_strategy = preset.get('strategy')
        st.session_state.quick_symbol = preset.get('symbol')
        st.switch_page("pages/01_.py")
      else:
        st.switch_page("pages/02_.py")

st.markdown("---")

# ========== 
st.markdown("### ")

col1, col2, col3 = st.columns(3)

with col1:
  st.markdown("#### ")
  st.caption("")
  st.markdown("- 20")
  st.markdown("- ")
  st.markdown("- ")
  st.markdown("- ")
  st.markdown("- ")
  if st.button(" →", use_container_width=True, type="primary"):
    st.switch_page("pages/01_.py")

with col2:
  st.markdown("#### ")
  st.caption("")
  st.markdown("- ")
  st.markdown("- ")
  st.markdown("- ")
  st.markdown("- ")
  if st.button(" →", use_container_width=True, type="primary"):
    st.switch_page("pages/02_.py")

with col3:
  st.markdown("#### ")
  st.caption("20")
  st.markdown("- 7")
  st.markdown("- A")
  st.markdown("- ")
  st.markdown("- ")
  if st.button(" →", use_container_width=True, type="primary"):
    st.switch_page("pages/03_.py")

st.markdown("---")

# ========== 
st.markdown("### 20")

strategy_categories = {
  " 6": ["", "MACD", "DMA", 
              "TRIX", "", ""],
  " 7": ["RSI", "KDJ", "CCI",
              "WR", "MOM", "ROC", "BIAS"],
  " 2": ["", ""],
  " 4": ["", "OBV", "VR", "EMV"],
  " 1": ["DMI"],
}

for category, strategies in strategy_categories.items():
  with st.expander(category, expanded=False):
    cols = st.columns(3)
    for idx, s in enumerate(strategies):
      cols[idx % 3].markdown(f"- {s}")

st.markdown("---")

# ========== 
st.markdown("### ")

selection_data = [
  {"": "", "": "DMI", "": "RSIKDJWRBIAS", "": ""},
  {"": "", "": "", "": "", "": ""},
  {"": "", "": "RSIKDJWRBIAS", "": "", "": ""},
  {"": "", "": "", "": "", "": ""},
  {"": "V", "": "BIASROCOBV", "": "", "": ""},
  {"": "", "": "ADXADX>25ADX<20", "": "", "": ""},
]

df_selection = pd.DataFrame(selection_data)
st.table(df_selection)

st.markdown("---")

# ========== 
st.markdown("### 4")

col1, col2, col3, col4 = st.columns(4)

with col1:
  st.markdown("#### L1 ")
  st.caption("")
  st.markdown("- ")
  st.markdown("- ")
  st.success("")

with col2:
  st.markdown("#### L2 ")
  st.caption("")
  st.markdown("- ")
  st.markdown("- ")
  st.info("")

with col3:
  st.markdown("#### L3 ")
  st.caption("")
  st.markdown("- ")
  st.markdown("- ")
  st.warning("")

with col4:
  st.markdown("#### L4 ")
  st.caption("")
  st.markdown("- ")
  st.markdown("- ")
  st.error("")

st.markdown("---")

# ========== 
st.markdown("### ")

progress_data = [
  {"": "20", "": 100, "": " "},
  {"": "", "": 100, "": " "},
  {"": "", "": 100, "": " "},
  {"": "", "": 100, "": " "},
  {"": "", "": 100, "": " "},
  {"": "", "": 100, "": " "},
  {"": "/", "": 100, "": " "},
  {"": "", "": 100, "": " "},
  {"": "", "": 100, "": " "},
  {"": "PDF", "": 0, "": " "},
  {"": "", "": 0, "": " "},
]

for item in progress_data:
  col1, col2, col3 = st.columns([3, 5, 2])
  with col1:
    st.markdown(f"{item['']} {item['']}")
  with col2:
    st.progress(item[''] / 100)
  with col3:
    st.markdown(f"{item['']}%")

st.markdown("---")
st.caption("Rock Quant 2.2.0 - | | PDF | A")
