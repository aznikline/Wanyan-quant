import streamlit as st
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from strategy_docs import get_all_strategy_docs

st.set_page_config(
  page_title=" - Rock Quant",
  page_icon="",
  layout="wide",
  initial_sidebar_state="expanded"
)

st.title(" ")
st.caption("20")

# ========== ==========
st.info(" A2010-2023300")

st.markdown("---")

# ========== ==========
with st.sidebar:
  st.header("")
  
  strategy_docs = get_all_strategy_docs()
  
  # 
  categories = {}
  for name, doc in strategy_docs.items():
    cat = doc.get('category', '')
    if cat not in categories:
      categories[cat] = []
    categories[cat].append(name)
  
  # 
  selected_category = st.selectbox("", list(categories.keys()))
  
  # 
  strategy_list = categories[selected_category]
  selected_strategy = st.selectbox("", strategy_list)
  
  st.markdown("---")
  st.caption(f" {len(strategy_docs)} ")

# ========== ==========
if selected_strategy:
  doc = strategy_docs[selected_strategy]
  
  # 
  col1, col2 = st.columns([3, 1])
  with col1:
    st.subheader(f" {selected_strategy}")
    st.caption(doc.get('english_name', ''))
  
  with col2:
    st.markdown(f"****: {doc.get('inventor', 'N/A')}")
    st.markdown(f"****: {doc.get('year', 'N/A')}")
  
  st.markdown("---")
  
  # 
  st.markdown("### ")
  st.write(doc.get('principle', ''))
  
  st.markdown("---")
  
  # 
  st.markdown("### ")
  formulas = doc.get('formulas', [])
  if formulas:
    for idx, formula in enumerate(formulas):
      st.markdown(f"**{idx+1}. {formula['name']}**")
      st.latex(formula['formula'])
      st.caption(formula['description'])
      if idx < len(formulas) - 1:
        st.markdown("")
  else:
    st.info("")
  
  st.markdown("---")
  
  # 
  st.markdown("### ")
  
  params = doc.get('parameters', [])
  if params:
    params_data = []
    for p in params:
      params_data.append({
        "": p.get('name', ''),
        "": p.get('classic_value', ''),
        "A": p.get('cn_best_value', ''),
        "": p.get('description', '')
      })
    
    df_params = pd.DataFrame(params_data)
    st.dataframe(df_params, use_container_width=True, hide_index=True)
  else:
    st.info("")
  
  st.markdown("---")
  
  # 
  col1, col2 = st.columns(2)
  
  with col1:
    st.markdown("### ")
    for s in doc.get('suitable_scenarios', []):
      st.markdown(f"- {s}")
  
  with col2:
    st.markdown("### ")
    for s in doc.get('bad_scenarios', []):
      st.markdown(f"- {s}")
  
  st.markdown("---")
  
  # 
  col1, col2 = st.columns(2)
  
  with col1:
    st.markdown("### ")
    for exp in doc.get('real_trading_tips', []):
      st.markdown(f"- {exp}")
  
  with col2:
    st.markdown("### ")
    for trap in doc.get('common_pitfalls', []):
      st.markdown(f"- {trap}")
  
  st.markdown("---")
  
  # 
  st.markdown("### ")
  for improve in doc.get('improvement_directions', []):
    st.markdown(f"- {improve}")
  
  st.markdown("---")
  
  # A
  st.markdown("### A")
  summary = doc.get('cn_summary', '')
  if summary:
    st.success(summary)
  else:
    st.info("A")
  
  st.markdown("---")
  
  # 
  with st.expander(" "):
    selection_data = [
      {"": "", "": "", "": "RSIKDJBIAS"},
      {"": "", "": "", "": ""},
      {"": "", "": "RSIKDJWRBIAS", "": ""},
      {"": "", "": "", "": ""},
      {"": "V", "": "BIASROCOBV", "": ""},
    ]
    
    df_selection = pd.DataFrame(selection_data)
    st.table(df_selection)

else:
  # 
  st.info(" ")
  
  # 
  st.markdown("### ")
  
  overview_data = []
  for name, doc in strategy_docs.items():
    overview_data.append({
      "": name,
      "": doc.get('category', ''),
      "": doc.get('inventor', 'N/A'),
      "": doc.get('brief', '')[:50] + "..."
    })
  
  df_overview = pd.DataFrame(overview_data)
  st.dataframe(df_overview, use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("Rock Quant 2.0 - | A2010-2023")
