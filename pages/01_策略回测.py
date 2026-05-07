import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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

# ========== - ==========
loader = DataLoader()
preset_symbols = list(loader.preset_symbols.keys())
all_strategies = get_all_strategies()

st.title(" ")
st.caption("")

# ========== ==========
col_data1, col_data2 = st.columns([3, 1])
with col_data1:
  data_sources = [
    ("", "simulated"),
    ("Akshare ", "akshare"),
    ("Tushare ", "tushare"),
  ]
  source_labels = [s[0] for s in data_sources]
  source_codes = [s[1] for s in data_sources]
  
  default_source_idx = source_codes.index(st.session_state.get('data_source', 'simulated')) if st.session_state.get('data_source', 'simulated') in source_codes else 0
  selected_source_label = st.selectbox("", source_labels, index=default_source_idx, key="data_source_select")
  selected_source = source_codes[source_labels.index(selected_source_label)]
  st.session_state['data_source'] = selected_source
  
  # Tushare Token
  if selected_source == 'tushare':
    tushare_token = st.text_input("Tushare Token", type="password", 
                   value=st.session_state.get('tushare_token', ''),
                   help=" Tushare Token https://tushare.pro/user/token ")
    st.session_state['tushare_token'] = tushare_token
    loader.set_tushare_token(tushare_token)
  
  loader.set_data_source(selected_source)
  
  # 
  available, msg = loader.check_data_source_available(selected_source)
  if not available:
    st.warning(f" {msg}")
  elif selected_source == 'simulated':
    st.info("ℹ Akshare Tushare")
  else:
    st.success(f" {selected_source_label}")
  
  st.markdown("---")

st.markdown("---")

# ========== ==========
# 
default_strategy = 0
default_symbol = 0
auto_run = False

if 'quick_strategy' in st.session_state and st.session_state.quick_strategy in all_strategies:
  default_strategy = all_strategies.index(st.session_state.quick_strategy)
  auto_run = True # 
  
if 'quick_symbol' in st.session_state and st.session_state.quick_symbol in preset_symbols:
  default_symbol = preset_symbols.index(st.session_state.quick_symbol)

# ========== ==========
with st.sidebar:
  st.header("")
  
  strategy_name = st.selectbox("", all_strategies, index=default_strategy, key="strategy_name")
  symbol_name = st.selectbox("", preset_symbols, index=default_symbol, key="symbol_name")
  
  col1, col2 = st.columns(2)
  with col1:
    start_date = st.date_input("", pd.to_datetime("2020-01-01"), key="start_date")
  with col2:
    end_date = st.date_input("", pd.to_datetime("2023-12-31"), key="end_date")
  
  st.subheader("")
  initial_capital = st.number_input("", value=1000000, step=100000, key="initial_capital")
  
  # - session_state
  st.subheader("")
  strategy = create_strategy(strategy_name)
  param_schema = strategy.get_params_schema()
  
  for param_name, param_config in param_schema.items():
    param_type = param_config.get('type', 'int')
    param_default = param_config.get('default', 20)
    param_min = param_config.get('min', 1)
    param_max = param_config.get('max', 200)
    
    key = f"param_{strategy_name}_{param_name}"
    
    if param_type == 'int':
      st.session_state[key] = st.slider(
        param_name, 
        min_value=param_min, 
        max_value=param_max, 
        value=param_default,
        key=key
      )
    elif param_type == 'float':
      st.session_state[key] = st.slider(
        param_name, 
        min_value=float(param_min), 
        max_value=float(param_max), 
        value=float(param_default),
        key=key
      )

# ========== ==========
#  flag
run_triggered = st.button(" ", type="primary") or (auto_run and 'last_result' not in st.session_state and 'auto_run_done' not in st.session_state)

if run_triggered:
  try:
    with st.spinner("..."):
      # 
      if auto_run:
        st.session_state['auto_run_done'] = True
        # 
        if 'quick_strategy' in st.session_state:
          del st.session_state['quick_strategy']
      
      symbol_code = loader.preset_symbols[symbol_name]
      try:
        data = loader.load_data(symbol_code, str(start_date), str(end_date), data_source=selected_source)
      except Exception as e:
        st.error(f": {str(e)}")
        if selected_source == 'akshare':
          st.info("Akshare ")
        st.stop()
      
      if len(data) < 30:
        st.warning(" 30")
      
      config = BacktestConfig(initial_capital=initial_capital)
      engine = BacktestEngine(config)
      
      # strategysession_state
      strategy = create_strategy(strategy_name)
      for param_name in param_schema.keys():
        key = f"param_{strategy_name}_{param_name}"
        if key in st.session_state:
          setattr(strategy, param_name, st.session_state[key])
      
      signals = strategy.generate_signals(data)
      result = engine.run(data, signals)
      perf = result.performance
      
      # session_state
      st.session_state.last_result = result
      st.session_state.last_perf = perf
      st.session_state.last_strategy = strategy_name
      st.session_state.last_symbol = symbol_name
      st.session_state.start_date = start_date
      st.session_state.end_date = end_date
      st.session_state.initial_capital = initial_capital
      
  except Exception as e:
    st.error(f" : {str(e)}")
    st.caption("")

# ========== ==========
if 'last_result' in st.session_state:
  result = st.session_state.last_result
  perf = st.session_state.last_perf
  current_strategy = st.session_state.last_strategy
  current_symbol = st.session_state.last_symbol
  
  st.success(f" - {current_strategy} @ {current_symbol}")
  
  # ========== PDF ==========
  col1, col2 = st.columns([3, 1])
  with col2:
    if st.button(" PDF", type="secondary", use_container_width=True):
      with st.spinner("PDF..."):
        try:
          from pdf_generator import PDFReportGenerator
          
          pdf_gen = PDFReportGenerator()
          missing = pdf_gen.check_dependencies()
          if missing:
            st.error(f": {', '.join(missing)}")
            st.code(f"pip install {' '.join(missing)}", language="bash")
          else:
            pdf_buffer = pdf_gen.generate_report(
              result=result,
              strategy_name=current_strategy,
              symbol_name=current_symbol,
              start_date=str(st.session_state.start_date),
              end_date=str(st.session_state.end_date),
              initial_capital=st.session_state.initial_capital,
              perf=perf
            )
            
            # 
            filename = f"{current_strategy}_{current_symbol}_{st.session_state.start_date}_{st.session_state.end_date}_.pdf"
            filename = filename.replace(' ', '_').replace('/', '')
            
            st.success(" PDF")
            
            # 
            st.download_button(
              label=" PDF",
              data=pdf_buffer,
              file_name=filename,
              mime="application/pdf",
              type="primary",
              use_container_width=True
            )
        except Exception as e:
          st.error(f": {str(e)}")
          st.caption("")
  
  st.markdown("---")
  
  # ========== 1. ==========
  st.subheader(" ")
  
  col1, col2, col3, col4 = st.columns(4)
  with col1:
    st.metric("", f"{perf['']:.2f}%")
    st.metric("", f"{perf['(CAGR)']:.2f}%")
  with col2:
    st.metric("", f"{perf['']:.2f}%", delta_color="inverse")
    st.metric("", f"{perf['']:.2f}")
  with col3:
    st.metric("", f"{perf['']:.2f}")
    st.metric("", f"{perf['']:.2f}")
  with col4:
    st.metric("", perf[''])
    st.metric("", f"{perf['']:.1f}%")
  
  st.markdown("---")
  
  # ========== 2. ==========
  st.subheader(" ")
  
  fig_equity = go.Figure()
  fig_equity.add_trace(go.Scatter(
    x=result.equity_curve.index, 
    y=result.equity_curve.values, 
    name="", 
    line=dict(color="#1f77b4", width=2)
  ))
  
  # 
  fig_equity.add_trace(go.Scatter(
    x=result.drawdown_curve.index,
    y=result.drawdown_curve.values * 100,
    name="(%)",
    line=dict(color="#ff7f0e", width=1),
    yaxis="y2"
  ))
  
  fig_equity.update_layout(
    height=450,
    hovermode="x unified",
    yaxis_title="",
    yaxis2=dict(title="(%)", overlaying="y", side="right", range=[-100, 0]),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
  )
  
  st.plotly_chart(fig_equity, use_container_width=True)
  st.markdown("---")
  
  # ========== 3. ==========
  st.subheader(" ")
  
  equity_daily = result.equity_curve
  monthly_equity = equity_daily.resample('M').last()
  monthly_returns = monthly_equity.pct_change().dropna() * 100
  
  monthly_data = []
  for date, ret in monthly_returns.items():
    monthly_data.append({
      'year': date.year,
      'month': date.month,
      'return': round(ret, 2)
    })
  
  df_monthly = pd.DataFrame(monthly_data)
  pivot_data = df_monthly.pivot(index='year', columns='month', values='return')
  pivot_data.columns = ['1','2','3','4','5','6','7','8','9','10','11','12']
  
  fig_heatmap = go.Figure(data=go.Heatmap(
    z=pivot_data.values,
    x=pivot_data.columns,
    y=pivot_data.index.astype(str),
    colorscale='RdYlGn',
    zmid=0,
    text=[[f"{v:.2f}%" for v in row] for row in pivot_data.values],
    texttemplate='%{text}',
    showscale=True,
    colorbar=dict(title="%")
  ))
  
  fig_heatmap.update_layout(height=300)
  st.plotly_chart(fig_heatmap, use_container_width=True)
  
  # 
  col1, col2, col3 = st.columns(3)
  with col1:
    best_month = df_monthly.loc[df_monthly['return'].idxmax()]
    st.metric("", f"{best_month['return']:.2f}%", 
         f"{int(best_month['year'])}{int(best_month['month'])}")
  with col2:
    worst_month = df_monthly.loc[df_monthly['return'].idxmin()]
    st.metric("", f"{worst_month['return']:.2f}%",
         f"{int(worst_month['year'])}{int(worst_month['month'])}", delta_color="inverse")
  with col3:
    positive_months = len(df_monthly[df_monthly['return'] > 0])
    total_months = len(df_monthly)
    st.metric("", f"{positive_months/total_months*100:.1f}%",
         f"{positive_months}/{total_months}")
  
  st.markdown("---")
  
  # ========== 4. 
  with st.expander(" - "):
    st.caption("")
    
    strategy = create_strategy(current_strategy)
    default_params = strategy.get_params_schema()
    
    if len(default_params) >= 1:
      # 
      param_names = list(default_params.keys())
      scan_param = st.selectbox("", param_names)
      
      # 
      p_config = default_params[scan_param]
      p_min = p_config.get('min', 5)
      p_max = p_config.get('max', 200)
      p_default = p_config.get('default', 20)
      
      col1, col2 = st.columns(2)
      with col1:
        scan_start = st.number_input("", value=p_min, min_value=p_min, max_value=p_max)
      with col2:
        scan_end = st.number_input("", value=min(p_max, p_max), min_value=p_min, max_value=p_max)
      
      scan_step = st.slider("", 2, 20, 5)
      
      if st.button("", type="primary"):
        with st.spinner(f" {scan_param} ..."):
          # 
          scan_values = list(range(int(scan_start), int(scan_end) + 1, scan_step))
          
          # session_state
          scan_symbol = st.session_state.get('last_symbol', symbol_name)
          symbol_code = loader.preset_symbols[scan_symbol]
          s_date = st.session_state.get('start_date', start_date)
          e_date = st.session_state.get('end_date', end_date)
          capital = st.session_state.get('initial_capital', initial_capital)
          
          data = loader.load_data(symbol_code, str(s_date), str(e_date))
          config = BacktestConfig(initial_capital=capital)
          engine = BacktestEngine(config)
          
          # 
          scan_results = []
          
          for val in scan_values:
            test_strategy = create_strategy(current_strategy)
            setattr(test_strategy, scan_param, val)
            signals = test_strategy.generate_signals(data)
            result = engine.run(data, signals)
            perf = result.performance
            
            scan_results.append({
              '': val,
              '%': round(perf[''], 2),
              '%': round(perf['(CAGR)'], 2),
              '%': round(perf[''], 2),
              '': round(perf[''], 2),
              '': round(perf[''], 2),
              '%': round(perf[''], 1),
              '': perf['']
            })
          
          df_scan = pd.DataFrame(scan_results)
          
          # 
          col1, col2 = st.columns([1, 1])
          
          with col1:
            st.markdown("#### ")
            fig_sharpe = go.Figure()
            fig_sharpe.add_trace(go.Scatter(
              x=df_scan[''],
              y=df_scan[''],
              mode='lines+markers+text',
              text=df_scan[''].round(2),
              textposition='top center',
              line=dict(color='#2ecc71', width=3),
              marker=dict(size=10)
            ))
            # 
            best_s = df_scan.loc[df_scan[''].idxmax()]
            fig_sharpe.add_annotation(
              x=best_s[''], y=best_s[''],
              text=f": {best_s['']:.2f}",
              showarrow=True, arrowhead=1, ax=0, ay=-40
            )
            fig_sharpe.update_layout(height=350, yaxis_title='', xaxis_title=scan_param)
            st.plotly_chart(fig_sharpe, use_container_width=True)
          
          with col2:
            st.markdown("#### ")
            fig_calmar = go.Figure()
            fig_calmar.add_trace(go.Scatter(
              x=df_scan[''],
              y=df_scan[''],
              mode='lines+markers+text',
              text=df_scan[''].round(2),
              textposition='top center',
              line=dict(color='#3498db', width=3),
              marker=dict(size=10)
            ))
            # 
            best_c = df_scan.loc[df_scan[''].idxmax()]
            fig_calmar.add_annotation(
              x=best_c[''], y=best_c[''],
              text=f": {best_c['']:.2f}",
              showarrow=True, arrowhead=1, ax=0, ay=-40
            )
            fig_calmar.update_layout(height=350, yaxis_title='', xaxis_title=scan_param)
            st.plotly_chart(fig_calmar, use_container_width=True)
          
          # 
          st.markdown("#### -")
          fig_scatter = go.Figure()
          for _, row in df_scan.iterrows():
            fig_scatter.add_trace(go.Scatter(
              x=[row['%']],
              y=[row['%']],
              mode='markers+text',
              marker=dict(size=abs(row[''])*5+8, color='RoyalBlue'),
              text=str(row['']),
              textposition='top center',
              name=f"={row['']}",
              hovertemplate=f"={row['']}<br>={row['%']:.1f}%<br>={row['%']:.1f}%<br>={row['']:.2f}"
            ))
          
          fig_scatter.update_layout(
            height=400,
            xaxis_title=' (%)',
            yaxis_title=' (%)',
            showlegend=False
          )
          st.plotly_chart(fig_scatter, use_container_width=True)
          
          # 
          st.markdown("#### ")
          st.dataframe(df_scan, use_container_width=True, hide_index=True)
          
          # 
          best_sharpe = df_scan.loc[df_scan[''].idxmax()]
          best_calmar = df_scan.loc[df_scan[''].idxmax()]
          best_return = df_scan.loc[df_scan['%'].idxmax()]
          
          col1, col2, col3 = st.columns(3)
          with col1:
            st.success(f" : {scan_param}={best_sharpe['']}")
            st.caption(f" {best_sharpe['']:.2f} | {best_sharpe['%']:.1f}%")
          with col2:
            st.success(f" : {scan_param}={best_calmar['']}")
            st.caption(f" {best_calmar['']:.2f} | {best_calmar['%']:.1f}%")
          with col3:
            st.success(f" : {scan_param}={best_return['']}")
            st.caption(f" {best_return['%']:.1f}% | {best_return['%']:.1f}%")
    else:
      st.info("")
  
  st.markdown("---")
  
  # ========== 5. ==========
  st.subheader(" ")
  
  trades = result.trades
  if len(trades) > 0:
    col1, col2 = st.columns([1, 1])
    
    with col1:
      # 
      fig_hist = go.Figure()
      wins = trades[trades['return_pct'] > 0]['return_pct']
      losses = trades[trades['return_pct'] < 0]['return_pct']
      
      fig_hist.add_trace(go.Histogram(
        x=wins, name='', marker_color='#2ecc71', opacity=0.7, nbinsx=20
      ))
      fig_hist.add_trace(go.Histogram(
        x=losses, name='', marker_color='#e74c3c', opacity=0.7, nbinsx=20
      ))
      
      fig_hist.update_layout(
        title='',
        height=350,
        xaxis_title='%',
        yaxis_title='',
        barmode='overlay',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
      )
      
      st.plotly_chart(fig_hist, use_container_width=True)
    
    with col2:
      # 
      st.markdown("#### ")
      
      avg_win = wins.mean() if len(wins) > 0 else 0
      avg_loss = losses.mean() if len(losses) > 0 else 0
      
      stats_data = [
        ["", f"{avg_win:.2f}%"],
        ["", f"{avg_loss:.2f}%"],
        ["", f"{abs(avg_win/avg_loss) if avg_loss != 0 else 0:.2f}"],
        ["", f"{trades['return_pct'].max():.2f}%"],
        ["", f"{trades['return_pct'].min():.2f}%"],
        ["", len(wins)],
        ["", len(losses)],
      ]
      
      df_stats = pd.DataFrame(stats_data, columns=["", ""])
      st.dataframe(df_stats, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # ========== 6. ==========
    with st.expander(""):
      trades_display = trades.copy()
      trades_display['entry_date'] = pd.to_datetime(trades_display['entry_date']).dt.strftime('%Y-%m-%d')
      trades_display['exit_date'] = pd.to_datetime(trades_display['exit_date']).dt.strftime('%Y-%m-%d')
      trades_display = trades_display[['entry_date', 'exit_date', 'entry_price', 'exit_price', 'position', 'return_pct', 'pnl']]
      trades_display.columns = ['', '', '', '', '', '%', '']
      st.dataframe(trades_display, use_container_width=True)

else:
  # 
  st.info(" ")
  
  # 
  st.markdown("### ")
  col1, col2, col3 = st.columns(3)
  with col1:
    st.markdown("****")
    st.caption("")
  with col2:
    st.markdown("****")
    st.caption("")
  with col3:
    st.markdown("****")
    st.caption("")
  
  # 
  st.markdown("---")
  st.markdown("### ")
  col_a, col_b, col_c = st.columns(3)
  with col_a:
    st.caption("****")
    st.markdown("30")
  with col_b:
    st.caption("****")
    st.markdown("")
  with col_c:
    st.caption("****")
    st.markdown("")

st.markdown("---")
st.caption("Rock Quant 2.0 - ")
