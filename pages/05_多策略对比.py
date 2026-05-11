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
    page_title="多策略对比 - Rock Quant",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 全局初始化
loader = DataLoader()
preset_symbols = list(loader.preset_symbols.keys())
all_strategies = get_all_strategies()

st.title("多策略对比分析")
st.markdown("同时回测多个策略，横向对比绩效表现，找出最适合当前市场环境的策略组合")

# ========== 侧边栏参数配置 ==========
with st.sidebar:
    st.header("对比参数")
    
    symbol_name = st.selectbox("选择标的", preset_symbols, index=0, key="compare_symbol")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("开始日期", pd.to_datetime("2020-01-01"), key="compare_start")
    with col2:
        end_date = st.date_input("结束日期", pd.to_datetime("2023-12-31"), key="compare_end")
    
    initial_capital = st.number_input("初始资金", value=1000000, step=100000, key="compare_capital")
    
    st.subheader("选择对比策略")
    st.caption("至少选择2个策略进行对比")
    
    selected_strategies = []
    for strategy in all_strategies:
        if st.checkbox(strategy, value=strategy in ["双均线策略", "MACD策略", "RSI超买超卖策略"], key=f"compare_{strategy}"):
            selected_strategies.append(strategy)
    
    st.markdown("---")
    run_compare = st.button(" 开始对比分析", type="primary", use_container_width=True)

# ========== 执行对比 ==========
if run_compare and len(selected_strategies) >= 2:
    
    symbol_code = loader.preset_symbols[symbol_name]
    
    with st.spinner(f"正在回测 {len(selected_strategies)} 个策略，预计需要 {len(selected_strategies) * 0.5:.1f} 秒..."):
        # 加载数据
        data = loader.load_data(symbol_code, str(start_date), str(end_date))
        
        # 存储所有策略结果
        results = {}
        perf_records = []
        
        config = BacktestConfig(initial_capital=initial_capital)
        engine = BacktestEngine(config)
        
        progress_bar = st.progress(0)
        for idx, strategy_name in enumerate(selected_strategies):
            strategy = create_strategy(strategy_name)
            signals = strategy.generate_signals(data)
            result = engine.run(data, signals)
            results[strategy_name] = result
            
            perf = result.performance
            perf_records.append({
                "策略名称": strategy_name,
                "年化收益率%": round(perf['年化收益率(CAGR)'], 2),
                "最大回撤%": round(perf['最大回撤'], 2),
                "夏普比率": round(perf['夏普比率'], 2),
                "胜率%": round(perf['胜率'], 2),
                "盈亏比": round(perf['盈亏比'], 2),
                "总交易次数": perf['总交易次数'],
                "累计净值": round(perf['累计净值'], 3),
                "卡玛比率": round(perf['卡玛比率'], 2),
                "年化波动率%": round(perf['年化波动率'], 2)
            })
            
            progress_bar.progress((idx + 1) / len(selected_strategies))
        
        progress_bar.empty()
        st.success(f" {len(selected_strategies)} 个策略回测完成！")

    # ========== 展示对比结果 ==========
    
    # 1. 综合绩效对比表格
    st.subheader("综合绩效对比")
    
    perf_df = pd.DataFrame(perf_records)
    
    # 添加性能排名标记
    def highlight_best(s):
        if s.name == "最大回撤%" or s.name == "年化波动率%":
            # 越小越好
            best_val = s.min()
            return ['background-color: #d4edda' if v == best_val else '' for v in s]
        else:
            # 越大越好
            best_val = s.max()
            return ['background-color: #d4edda' if v == best_val else '' for v in s]
    
    perf_df_styled = perf_df.style.apply(highlight_best, subset=["年化收益率%", "最大回撤%", "夏普比率", "胜率%", "盈亏比", "卡玛比率", "年化波动率%"])
    st.dataframe(perf_df_styled, use_container_width=True, hide_index=True)
    
    # 2. 净值曲线对比
    st.subheader("净值曲线对比")
    
    fig = go.Figure()
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']
    
    for idx, (name, result) in enumerate(results.items()):
        fig.add_trace(go.Scatter(
            x=result.equity_curve.index,
            y=result.equity_curve.values,
            name=name,
            line=dict(width=2, color=colors[idx % len(colors)])
        ))
    
    # 添加基准线（初始资金）
    fig.add_hline(y=initial_capital, line_dash="dash", line_color="gray", opacity=0.5, name="初始资金")
    
    fig.update_layout(
        height=500,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=30, b=30, l=30, r=30)
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # 3. 回撤曲线对比
    st.subheader("回撤曲线对比")
    
    fig2 = go.Figure()
    for idx, (name, result) in enumerate(results.items()):
        drawdown = -result.drawdown_curve.values
        fig2.add_trace(go.Scatter(
            x=result.drawdown_curve.index,
            y=drawdown,
            name=name,
            line=dict(width=2, color=colors[idx % len(colors)]),
            fill='tozeroy'
        ))
    
    fig2.update_layout(
        height=400,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis_title="回撤深度 (%)",
        margin=dict(t=30, b=30, l=30, r=30)
    )
    st.plotly_chart(fig2, use_container_width=True)
    
    # 4. 核心指标雷达图
    st.subheader("策略能力雷达图")
    
    # 选择关键指标并归一化
    radar_metrics = ["年化收益率%", "胜率%", "夏普比率", "盈亏比", "卡玛比率"]
    inverted_metrics = ["最大回撤%", "年化波动率%"]
    
    # 计算归一化值（0-100分）
    radar_data = []
    for record in perf_records:
        normalized = {}
        for metric in radar_metrics + inverted_metrics:
            values = [r[metric] for r in perf_records]
            min_v, max_v = min(values), max(values)
            if max_v == min_v:
                normalized[metric] = 50
            else:
                if metric in inverted_metrics:
                    # 越小越好，反向归一化
                    normalized[metric] = 100 - (record[metric] - min_v) / (max_v - min_v) * 100
                else:
                    # 越大越好，正向归一化
                    normalized[metric] = (record[metric] - min_v) / (max_v - min_v) * 100
        radar_data.append(normalized)
    
    fig3 = go.Figure()
    
    for idx, record in enumerate(perf_records):
        fig3.add_trace(go.Scatterpolar(
            r=[radar_data[idx][m] for m in ["年化收益率%", "胜率%", "夏普比率", "盈亏比", "最大回撤%", "卡玛比率"]],
            theta=["收益能力", "选股胜率", "风险调整", "盈亏弹性", "回撤控制", "收益/风险"],
            fill='toself',
            name=record["策略名称"],
            line=dict(color=colors[idx % len(colors)]),
            opacity=0.7
        ))
    
    fig3.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100])
        ),
        height=500,
        showlegend=True,
        margin=dict(t=30, b=30, l=30, r=30)
    )
    st.plotly_chart(fig3, use_container_width=True)
    
    # 5. 月度收益热力图对比
    st.subheader("月度收益对比")
    
    # 计算所有策略的月度收益
    monthly_data = {}
    for name, result in results.items():
        equity = result.equity_curve
        monthly_returns = equity.resample('ME').last().pct_change().dropna() * 100
        monthly_data[name] = monthly_returns
    
    # 展示前5个策略的月度热力图
    display_count = min(5, len(selected_strategies))
    cols = st.columns(display_count)
    
    for col_idx, strategy_name in enumerate(selected_strategies[:display_count]):
        with cols[col_idx]:
            st.markdown(f"**{strategy_name}**")
            returns = monthly_data[strategy_name]
            
            # 转换为年月矩阵
            heatmap_data = []
            years = sorted(set(returns.index.year))
            months = list(range(1, 13))
            
            for year in years:
                row = []
                for month in months:
                    mask = (returns.index.year == year) & (returns.index.month == month)
                    if mask.any():
                        row.append(round(returns[mask].iloc[0], 1))
                    else:
                        row.append(None)
                heatmap_data.append(row)
            
            fig4 = go.Figure(data=go.Heatmap(
                z=heatmap_data,
                x=["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"],
                y=[str(y) for y in years],
                colorscale='RdYlGn',
                zmid=0,
                showscale=False,
                text=heatmap_data,
                texttemplate="%{text}%",
                textfont={"size": 10}
            ))
            
            fig4.update_layout(height=200, margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig4, use_container_width=True)
    
    # 6. 交易统计对比
    st.subheader("交易统计对比")
    
    col1, col2, col3, col4 = st.columns(4)
    
    metrics = [
        ("总交易次数", "总交易次数"),
        ("胜率%", "胜率"),
        ("盈亏比", "盈亏比"),
        ("盈利因子", "盈利因子")
    ]
    
    for col, (label, key) in zip([col1, col2, col3, col4], metrics):
        with col:
            st.markdown(f"**{label}**")
            data = {r["策略名称"]: r[key] for r in perf_records}
            df = pd.DataFrame({"策略": list(data.keys()), label: list(data.values())})
            st.dataframe(df, use_container_width=True, hide_index=True)

elif run_compare and len(selected_strategies) < 2:
    st.warning("请至少选择2个策略进行对比分析")

else:
    # 默认展示说明
    st.info("👈 请在左侧选择对比策略和参数配置，然后点击「开始对比分析」")
    
    st.markdown("""
    ### 功能说明
    
    **多策略对比分析可以帮助您：**
    - 横向对比不同策略在同一时间段的表现
    - 找出适应当前市场环境的最优策略
    - 分析策略的互补性，用于构建策略组合
    - 直观对比风险收益特征
    
    **推荐对比维度：**
    - 双均线 vs MACD：趋势类策略对比
    - RSI vs 布林带：震荡类策略对比
    - 趋势类 vs 震荡类：不同市场适应性对比
    """)
