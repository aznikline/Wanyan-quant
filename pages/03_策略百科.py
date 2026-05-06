import streamlit as st
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from strategy_docs import get_all_strategy_docs

st.set_page_config(
    page_title="策略百科 - Rock Quant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📚 策略深度百科")
st.caption("20个主流量价策略的完整文档、参数建议、实盘经验与避坑指南")
st.markdown("---")

# ========== 侧边栏导航 ==========
with st.sidebar:
    st.header("策略分类")
    
    strategy_docs = get_all_strategy_docs()
    
    # 按分类分组
    categories = {}
    for name, doc in strategy_docs.items():
        cat = doc.get('category', '其他')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(name)
    
    # 选择分类
    selected_category = st.selectbox("选择策略分类", list(categories.keys()))
    
    # 选择具体策略
    strategy_list = categories[selected_category]
    selected_strategy = st.selectbox("选择策略", strategy_list)
    
    st.markdown("---")
    st.caption(f"共 {len(strategy_docs)} 个策略文档")

# ========== 展示策略详情 ==========
if selected_strategy:
    doc = strategy_docs[selected_strategy]
    
    # 头部信息
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(f"📍 {selected_strategy}")
        st.caption(doc.get('english_name', ''))
    
    with col2:
        st.markdown(f"**发明者**: {doc.get('inventor', 'N/A')}")
        st.markdown(f"**发明年份**: {doc.get('year', 'N/A')}")
    
    st.markdown("---")
    
    # 核心原理
    st.markdown("### 🎯 核心原理")
    st.write(doc.get('principle', ''))
    
    st.markdown("---")
    
    # 计算公式
    st.markdown("### 📐 计算公式")
    formulas = doc.get('formulas', [])
    if formulas:
        for idx, formula in enumerate(formulas):
            st.markdown(f"**{idx+1}. {formula['name']}**")
            st.latex(formula['formula'])
            st.caption(formula['description'])
            if idx < len(formulas) - 1:
                st.markdown("")
    else:
        st.info("暂无公式说明")
    
    st.markdown("---")
    
    # 核心参数
    st.markdown("### ⚙️ 核心参数")
    
    params = doc.get('parameters', [])
    if params:
        params_data = []
        for p in params:
            params_data.append({
                "参数名称": p.get('name', ''),
                "经典推荐值": p.get('classic_value', ''),
                "A股实测最优值": p.get('cn_best_value', ''),
                "参数说明": p.get('description', '')
            })
        
        df_params = pd.DataFrame(params_data)
        st.dataframe(df_params, use_container_width=True, hide_index=True)
    else:
        st.info("暂无参数说明")
    
    st.markdown("---")
    
    # 适用与失效场景
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### ✅ 适用场景")
        for s in doc.get('suitable_scenarios', []):
            st.markdown(f"- {s}")
    
    with col2:
        st.markdown("### ❌ 失效场景")
        for s in doc.get('bad_scenarios', []):
            st.markdown(f"- {s}")
    
    st.markdown("---")
    
    # 实盘经验与常见陷阱
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 💡 实盘经验")
        for exp in doc.get('real_trading_tips', []):
            st.markdown(f"- {exp}")
    
    with col2:
        st.markdown("### ⚠️ 常见陷阱")
        for trap in doc.get('common_pitfalls', []):
            st.markdown(f"- {trap}")
    
    st.markdown("---")
    
    # 改进方向
    st.markdown("### 🚀 改进方向")
    for improve in doc.get('improvement_directions', []):
        st.markdown(f"- {improve}")
    
    st.markdown("---")
    
    # A股实盘总结
    st.markdown("### 📊 A股实盘总结")
    summary = doc.get('cn_summary', '')
    if summary:
        st.success(summary)
    else:
        st.info("暂无A股实盘总结")
    
    st.markdown("---")
    
    # 策略选型矩阵
    with st.expander("📋 策略选型参考矩阵"):
        selection_data = [
            {"市场状态": "明确单边上涨趋势", "首选策略": "趋势突破类（唐奇安、双均线）", "禁用策略": "RSI、KDJ、BIAS等震荡类"},
            {"市场状态": "明确单边下跌趋势", "首选策略": "空仓或趋势做空", "禁用策略": "所有抄底类震荡策略"},
            {"市场状态": "区间震荡行情", "首选策略": "RSI、KDJ、WR、BIAS、布林带", "禁用策略": "所有趋势突破类策略"},
            {"市场状态": "横盘末期即将突破", "首选策略": "布林带突破、肯特纳通道、成交量突破", "禁用策略": "不要提前赌方向，等突破确认"},
            {"市场状态": "V型反转极端行情", "首选策略": "BIAS乖离率、ROC速率、OBV背离", "禁用策略": "所有滞后的趋势类策略"},
        ]
        
        df_selection = pd.DataFrame(selection_data)
        st.table(df_selection)

else:
    # 未选择策略时显示概览
    st.info("👈 请在左侧选择要查看的策略文档")
    
    # 展示所有策略概览
    st.markdown("### 📋 策略库概览")
    
    overview_data = []
    for name, doc in strategy_docs.items():
        overview_data.append({
            "策略名称": name,
            "分类": doc.get('category', '其他'),
            "发明者": doc.get('inventor', 'N/A'),
            "核心逻辑": doc.get('brief', '')[:50] + "..."
        })
    
    df_overview = pd.DataFrame(overview_data)
    st.dataframe(df_overview, use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("Rock Quant 2.0 - 顽岩量价模型 | 所有策略文档基于A股2010-2023年实盘回测总结")
