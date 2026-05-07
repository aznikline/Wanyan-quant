import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import BacktestConfig
from backtest_engine import BacktestEngine
from strategies import get_all_strategies, create_strategy
from data_loader import DataLoader

st.set_page_config(
  page_title=" - Rock Quant",
  page_icon="",
  layout="wide",
  initial_sidebar_state="expanded"
)

st.title(" ")
st.caption("")

# ========== ==========
st.warning(" ")

st.markdown("---")

# ========== ==========
with st.sidebar:
  st.header("")
  
  analysis_mode = st.radio(
    "",
    [" - ", " - ", ""],
    label_visibility="collapsed"
  )
  
  loader = DataLoader()
  preset_symbols = list(loader.preset_symbols.keys())
  
  col1, col2 = st.columns(2)
  with col1:
    start_date = st.date_input("", pd.to_datetime("2020-01-01"))
  with col2:
    end_date = st.date_input("", pd.to_datetime("2023-12-31"))
  
  initial_capital = st.number_input("", value=1000000, step=100000)

# ========== 1: - ==========
if analysis_mode == " - ":
  st.subheader(" ")
  
  col1, col2 = st.columns([1, 3])
  with col1:
    symbol_name = st.selectbox("", preset_symbols)
  
  with col2:
    # 4
    default_selected = ["", "MACD", "RSI", ""]
    default_selected = [s for s in default_selected if s in get_all_strategies()]
    
    selected_strategies = st.multiselect(
      "3-5",
      get_all_strategies(),
      default=default_selected
    )
  
  if st.button("", type="primary") and len(selected_strategies) > 0:
    symbol_code = loader.preset_symbols[symbol_name]
    data = loader.load_data(symbol_code, str(start_date), str(end_date))
    config = BacktestConfig(initial_capital=initial_capital)
    engine = BacktestEngine(config)
    
    results = {}
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, strategy_name in enumerate(selected_strategies):
      status_text.caption(f": {strategy_name} ({idx+1}/{len(selected_strategies)})")
      strategy = create_strategy(strategy_name)
      signals = strategy.generate_signals(data)
      result = engine.run(data, signals)
      results[strategy_name] = result
      progress_bar.progress((idx + 1) / len(selected_strategies))
    
    status_text.success(f" {len(selected_strategies)} ")
    st.session_state.multi_strategy_results = results
    st.session_state.multi_strategy_symbol = symbol_name
  
  # 
  if 'multi_strategy_results' in st.session_state:
    results = st.session_state.multi_strategy_results
    
    st.success(f" {len(results)} ")
    st.markdown("---")
    
    # 
    st.subheader(" ")
    
    fig = go.Figure()
    colors = px.colors.qualitative.Plotly
    
    for idx, (name, result) in enumerate(results.items()):
      normalized = result.equity_curve / initial_capital
      fig.add_trace(go.Scatter(
        x=normalized.index,
        y=normalized.values,
        name=name,
        line=dict(color=colors[idx % len(colors)], width=2)
      ))
    
    fig.update_layout(
      height=450,
      hovermode="x unified",
      yaxis_title="=1",
      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("---")
    
    # 
    st.subheader(" ")
    
    col1, col2 = st.columns([3, 1])
    with col1:
      sort_by = st.selectbox("", 
        ["", "", "%", "%", "%", "%", ""],
        index=0
      )
    
    comparison_data = []
    for name, result in results.items():
      perf = result.performance
      comparison_data.append({
        "": name,
        "%": round(perf[''], 2),
        "%": round(perf['(CAGR)'], 2),
        "%": round(perf[''], 2),
        "": round(perf[''], 2),
        "": round(perf[''], 2),
        "%": round(perf[''], 1),
        "": perf['']
      })
    
    df_comparison = pd.DataFrame(comparison_data)
    
    # 
    ascending = sort_by == "%"
    df_comparison = df_comparison.sort_values(by=sort_by, ascending=ascending)
    df_comparison = df_comparison.reset_index(drop=True)
    df_comparison.index = df_comparison.index + 1 # 1
    df_comparison.index.name = ""
    
    st.dataframe(df_comparison, use_container_width=True)
    
    # 
    st.markdown("---")
    st.subheader(" ")
    
    # 
    metrics = ["%", "", "", "%"]
    fig_radar = go.Figure()
    
    for idx, row in df_comparison.iterrows():
      normalized_values = []
      for m in metrics:
        min_val = df_comparison[m].min()
        max_val = df_comparison[m].max()
        if max_val == min_val:
          normalized_values.append(50)
        else:
          normalized_values.append((row[m] - min_val) / (max_val - min_val) * 100)
      
      fig_radar.add_trace(go.Scatterpolar(
        r=normalized_values,
        theta=["", "", "", ""],
        fill='toself',
        name=row[''],
        line=dict(color=colors[idx % len(colors)])
      ))
    
    fig_radar.update_layout(
      polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
      height=500
    )
    
    st.plotly_chart(fig_radar, use_container_width=True)

# ========== 2: - ==========
elif analysis_mode == " - ":
  st.subheader(" ")
  
  col1, col2 = st.columns([1, 3])
  with col1:
    strategy_name = st.selectbox("", get_all_strategies())
  
  with col2:
    selected_symbols = st.multiselect(
      "5-10",
      preset_symbols,
      default=preset_symbols[:5]
    )
  
  if st.button("", type="primary") and len(selected_symbols) > 0:
    with st.spinner(f" {len(selected_symbols)} ..."):
      config = BacktestConfig(initial_capital=initial_capital)
      engine = BacktestEngine(config)
      strategy = create_strategy(strategy_name)
      
      results = {}
      progress_bar = st.progress(0)
      
      for idx, symbol_name in enumerate(selected_symbols):
        symbol_code = loader.preset_symbols[symbol_name]
        data = loader.load_data(symbol_code, str(start_date), str(end_date))
        signals = strategy.generate_signals(data)
        result = engine.run(data, signals)
        results[symbol_name] = result
        progress_bar.progress((idx + 1) / len(selected_symbols))
      
      st.session_state.multi_symbol_results = results
      st.session_state.multi_symbol_strategy = strategy_name
  
  # 
  if 'multi_symbol_results' in st.session_state:
    results = st.session_state.multi_symbol_results
    
    st.success(f" {len(results)} ")
    st.markdown("---")
    
    # 
    st.subheader(" ")
    
    fig = go.Figure()
    colors = px.colors.qualitative.Set1
    
    for idx, (name, result) in enumerate(results.items()):
      normalized = result.equity_curve / initial_capital
      fig.add_trace(go.Scatter(
        x=normalized.index,
        y=normalized.values,
        name=name,
        line=dict(color=colors[idx % len(colors)], width=2)
      ))
    
    fig.update_layout(
      height=450,
      hovermode="x unified",
      yaxis_title="=1",
      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("---")
    
    # 
    st.subheader(" ")
    
    comparison_data = []
    for name, result in results.items():
      perf = result.performance
      comparison_data.append({
        "": name,
        "%": round(perf[''], 2),
        "%": round(perf['(CAGR)'], 2),
        "%": round(perf[''], 2),
        "": round(perf[''], 2),
        "": round(perf[''], 2),
        "%": round(perf[''], 1),
        "": perf['']
      })
    
    df_comparison = pd.DataFrame(comparison_data)
    st.dataframe(df_comparison, use_container_width=True, hide_index=True)
    
    # : vs 
    st.markdown("---")
    st.subheader(" -")
    
    fig_scatter = go.Figure()
    
    for idx, row in df_comparison.iterrows():
      fig_scatter.add_trace(go.Scatter(
        x=[row["%"]],
        y=[row["%"]],
        mode="markers+text",
        marker=dict(size=abs(row[""])*8+5, color=colors[idx % len(colors)], opacity=0.7),
        text=row[""],
        textposition="top center",
        name=row[""],
        hovertemplate=f"<b>{row['']}</b><br>: {row['%']:.1f}%<br>: {row['%']:.1f}%<br>: {row['']:.2f}"
      ))
    
    fig_scatter.update_layout(
      height=450,
      xaxis_title=" (%)",
      yaxis_title=" (%)",
      showlegend=False
    )
    
    st.plotly_chart(fig_scatter, use_container_width=True)

# ========== 3: ==========
else:
  st.subheader(" ")
  
  selected_strategies = st.multiselect(
    "3-8",
    get_all_strategies(),
    default=get_all_strategies()[:5]
  )
  
  symbol_name = st.selectbox("", preset_symbols)
  
  col1, col2 = st.columns(2)
  with col1:
    min_weight = st.slider("(%)", 0, 30, 5) / 100
  with col2:
    max_weight = st.slider("(%)", 10, 50, 30) / 100
  
  if st.button("", type="primary") and len(selected_strategies) >= 2:
    with st.spinner("..."):
      # 1. 
      symbol_code = loader.preset_symbols[symbol_name]
      data = loader.load_data(symbol_code, str(start_date), str(end_date))
      config = BacktestConfig(initial_capital=initial_capital)
      engine = BacktestEngine(config)
      
      strategy_equities = {}
      for strategy_name in selected_strategies:
        strategy = create_strategy(strategy_name)
        signals = strategy.generate_signals(data)
        result = engine.run(data, signals)
        strategy_equities[strategy_name] = result.equity_curve.pct_change().dropna()
      
      # 2. 
      returns_df = pd.DataFrame(strategy_equities)
      expected_returns = returns_df.mean() * 252
      cov_matrix = returns_df.cov() * 252
      
      # 3. 
      from scipy.optimize import minimize
      
      n_assets = len(selected_strategies)
      weights_init = np.array([1/n_assets] * n_assets)
      bounds = tuple((min_weight, max_weight) for _ in range(n_assets))
      constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
      
      def objective_sharpe(weights):
        port_return = np.sum(expected_returns * weights)
        port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        return -port_return / max(port_vol, 0.001)
      
      opt_result = minimize(objective_sharpe, weights_init, method='SLSQP', bounds=bounds, constraints=constraints)
      optimal_weights = opt_result.x
      
      # 4. 
      optimal_return = np.sum(expected_returns * optimal_weights)
      optimal_vol = np.sqrt(np.dot(optimal_weights.T, np.dot(cov_matrix, optimal_weights)))
      optimal_sharpe = optimal_return / max(optimal_vol, 0.001)
      
      # 
      equal_weights = weights_init
      equal_return = np.sum(expected_returns * equal_weights)
      equal_vol = np.sqrt(np.dot(equal_weights.T, np.dot(cov_matrix, equal_weights)))
      equal_sharpe = equal_return / max(equal_vol, 0.001)
      
      # 
      st.session_state.portfolio_result = {
        'strategies': selected_strategies,
        'optimal_weights': optimal_weights,
        'equal_weights': equal_weights,
        'optimal_return': optimal_return,
        'optimal_vol': optimal_vol,
        'optimal_sharpe': optimal_sharpe,
        'equal_return': equal_return,
        'equal_vol': equal_vol,
        'equal_sharpe': equal_sharpe,
        'returns_df': returns_df
      }
  
  # 
  if 'portfolio_result' in st.session_state:
    res = st.session_state.portfolio_result
    
    st.success("")
    st.markdown("---")
    
    # 
    st.subheader(" ")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
      weights_df = pd.DataFrame({
        '': res['strategies'],
        '%': (res['optimal_weights'] * 100).round(1)
      }).sort_values('%', ascending=False)
      
      fig_pie = go.Figure(data=[go.Pie(
        labels=weights_df[''],
        values=weights_df['%'],
        textinfo='label+percent',
        hole=0.4
      )])
      fig_pie.update_layout(height=400)
      st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
      st.dataframe(weights_df, use_container_width=True, hide_index=True)
      
      # 
      st.markdown("#### ")
      sharpe_gain = (res['optimal_sharpe'] - res['equal_sharpe']) / abs(res['equal_sharpe']) * 100
      
      col_a, col_b = st.columns(2)
      with col_a:
        st.metric("", f"{res['optimal_return']*100:.1f}%", 
             delta=f"{(res['optimal_return']-res['equal_return'])*100:+.1f}% vs ")
      with col_b:
        st.metric("", f"{res['optimal_sharpe']:.2f}",
             delta=f"{sharpe_gain:+.1f}% vs ")
    
    st.markdown("---")
    
    # 
    st.subheader(" ")
    
    corr_matrix = res['returns_df'].corr()
    
    fig_corr = go.Figure(data=go.Heatmap(
      z=corr_matrix.values,
      x=corr_matrix.columns,
      y=corr_matrix.index,
      colorscale='RdBu_r',
      zmid=0,
      zmin=-1,
      zmax=1,
      text=[[f"{v:.2f}" for v in row] for row in corr_matrix.values],
      texttemplate='%{text}',
      colorbar=dict(title="")
    ))
    
    fig_corr.update_layout(height=450)
    st.plotly_chart(fig_corr, use_container_width=True)
    
    st.info(" -11")

st.markdown("---")
st.caption("Rock Quant 2.0 - ")
