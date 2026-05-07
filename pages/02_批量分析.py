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
    page_title="批量分析 - Rock Quant",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title(" 批量分析")
st.caption("多策略对比、多标的批量回测、策略组合优化")

# ========== 模拟数据警告 ==========
st.warning(" 当前使用模拟数据进行演示，回测结果仅供参考，不构成投资建议。")

st.markdown("---")

# ========== 侧边栏参数 ==========
with st.sidebar:
    st.header("分析模式")
    
    analysis_mode = st.radio(
        "选择分析模式",
        ["同一标的 - 多策略对比", "同一策略 - 多标的对比", "策略组合优化"],
        label_visibility="collapsed"
    )
    
    loader = DataLoader()
    preset_symbols = list(loader.preset_symbols.keys())
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("开始日期", pd.to_datetime("2020-01-01"))
    with col2:
        end_date = st.date_input("结束日期", pd.to_datetime("2023-12-31"))
    
    initial_capital = st.number_input("初始资金", value=1000000, step=100000)

# ========== 模式1: 同一标的 - 多策略对比 ==========
if analysis_mode == "同一标的 - 多策略对比":
    st.subheader(" 多策略对比分析")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        symbol_name = st.selectbox("选择标的", preset_symbols)
    
    with col2:
        # 预选最常用的4个策略
        default_selected = ["双均线策略", "MACD策略", "RSI超买超卖策略", "布林带突破策略"]
        default_selected = [s for s in default_selected if s in get_all_strategies()]
        
        selected_strategies = st.multiselect(
            "选择要对比的策略（建议3-5个）",
            get_all_strategies(),
            default=default_selected
        )
    
    if st.button("开始批量对比", type="primary") and len(selected_strategies) > 0:
        symbol_code = loader.preset_symbols[symbol_name]
        data = loader.load_data(symbol_code, str(start_date), str(end_date))
        config = BacktestConfig(initial_capital=initial_capital)
        engine = BacktestEngine(config)
        
        results = {}
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, strategy_name in enumerate(selected_strategies):
            status_text.caption(f"正在回测: {strategy_name} ({idx+1}/{len(selected_strategies)})")
            strategy = create_strategy(strategy_name)
            signals = strategy.generate_signals(data)
            result = engine.run(data, signals)
            results[strategy_name] = result
            progress_bar.progress((idx + 1) / len(selected_strategies))
        
        status_text.success(f" {len(selected_strategies)} 个策略回测全部完成！")
        st.session_state.multi_strategy_results = results
        st.session_state.multi_strategy_symbol = symbol_name
    
    # 展示结果
    if 'multi_strategy_results' in st.session_state:
        results = st.session_state.multi_strategy_results
        
        st.success(f"回测完成，共 {len(results)} 个策略")
        st.markdown("---")
        
        # 净值曲线对比
        st.subheader(" 净值曲线对比")
        
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
            yaxis_title="净值（标准化，初始=1）",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("---")
        
        # 绩效对比表格
        st.subheader(" 绩效对比排名")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            sort_by = st.selectbox("排序方式", 
                ["夏普比率", "卡玛比率", "年化收益率%", "总收益率%", "最大回撤%", "胜率%", "交易次数"],
                index=0
            )
        
        comparison_data = []
        for name, result in results.items():
            perf = result.performance
            comparison_data.append({
                "策略名称": name,
                "总收益率%": round(perf['总收益率'], 2),
                "年化收益率%": round(perf['年化收益率(CAGR)'], 2),
                "最大回撤%": round(perf['最大回撤'], 2),
                "夏普比率": round(perf['夏普比率'], 2),
                "卡玛比率": round(perf['卡玛比率'], 2),
                "胜率%": round(perf['胜率'], 1),
                "交易次数": perf['总交易次数']
            })
        
        df_comparison = pd.DataFrame(comparison_data)
        
        # 排序
        ascending = sort_by == "最大回撤%"
        df_comparison = df_comparison.sort_values(by=sort_by, ascending=ascending)
        df_comparison = df_comparison.reset_index(drop=True)
        df_comparison.index = df_comparison.index + 1  # 排名从1开始
        df_comparison.index.name = "排名"
        
        st.dataframe(df_comparison, use_container_width=True)
        
        # 雷达图
        st.markdown("---")
        st.subheader(" 多维度能力对比")
        
        # 归一化数据用于雷达图
        metrics = ["年化收益率%", "夏普比率", "卡玛比率", "胜率%"]
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
                theta=["收益", "夏普", "卡玛", "胜率"],
                fill='toself',
                name=row['策略名称'],
                line=dict(color=colors[idx % len(colors)])
            ))
        
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            height=500
        )
        
        st.plotly_chart(fig_radar, use_container_width=True)

# ========== 模式2: 同一策略 - 多标的对比 ==========
elif analysis_mode == "同一策略 - 多标的对比":
    st.subheader(" 多标的批量回测")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        strategy_name = st.selectbox("选择策略", get_all_strategies())
    
    with col2:
        selected_symbols = st.multiselect(
            "选择要回测的标的（建议5-10个）",
            preset_symbols,
            default=preset_symbols[:5]
        )
    
    if st.button("开始批量回测", type="primary") and len(selected_symbols) > 0:
        with st.spinner(f"正在回测 {len(selected_symbols)} 个标的..."):
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
    
    # 展示结果
    if 'multi_symbol_results' in st.session_state:
        results = st.session_state.multi_symbol_results
        
        st.success(f"回测完成，共 {len(results)} 个标的")
        st.markdown("---")
        
        # 净值曲线对比
        st.subheader(" 净值曲线对比")
        
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
            yaxis_title="净值（标准化，初始=1）",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("---")
        
        # 绩效排名表格
        st.subheader(" 标的绩效排名")
        
        comparison_data = []
        for name, result in results.items():
            perf = result.performance
            comparison_data.append({
                "标的名称": name,
                "总收益率%": round(perf['总收益率'], 2),
                "年化收益率%": round(perf['年化收益率(CAGR)'], 2),
                "最大回撤%": round(perf['最大回撤'], 2),
                "夏普比率": round(perf['夏普比率'], 2),
                "卡玛比率": round(perf['卡玛比率'], 2),
                "胜率%": round(perf['胜率'], 1),
                "交易次数": perf['总交易次数']
            })
        
        df_comparison = pd.DataFrame(comparison_data)
        st.dataframe(df_comparison, use_container_width=True, hide_index=True)
        
        # 散点图: 收益 vs 回撤
        st.markdown("---")
        st.subheader(" 收益-风险散点图")
        
        fig_scatter = go.Figure()
        
        for idx, row in df_comparison.iterrows():
            fig_scatter.add_trace(go.Scatter(
                x=[row["最大回撤%"]],
                y=[row["年化收益率%"]],
                mode="markers+text",
                marker=dict(size=abs(row["夏普比率"])*8+5, color=colors[idx % len(colors)], opacity=0.7),
                text=row["标的名称"],
                textposition="top center",
                name=row["标的名称"],
                hovertemplate=f"<b>{row['标的名称']}</b><br>年化: {row['年化收益率%']:.1f}%<br>回撤: {row['最大回撤%']:.1f}%<br>夏普: {row['夏普比率']:.2f}"
            ))
        
        fig_scatter.update_layout(
            height=450,
            xaxis_title="最大回撤 (%)",
            yaxis_title="年化收益率 (%)",
            showlegend=False
        )
        
        st.plotly_chart(fig_scatter, use_container_width=True)

# ========== 模式3: 策略组合优化 ==========
else:
    st.subheader("⚖️ 策略组合优化（马科维茨）")
    
    selected_strategies = st.multiselect(
        "选择加入组合的策略（建议3-8个）",
        get_all_strategies(),
        default=get_all_strategies()[:5]
    )
    
    symbol_name = st.selectbox("选择回测标的（用于计算相关性）", preset_symbols)
    
    col1, col2 = st.columns(2)
    with col1:
        min_weight = st.slider("单策略最小权重(%)", 0, 30, 5) / 100
    with col2:
        max_weight = st.slider("单策略最大权重(%)", 10, 50, 30) / 100
    
    if st.button("开始组合优化计算", type="primary") and len(selected_strategies) >= 2:
        with st.spinner("正在计算最优权重..."):
            # 1. 先回测所有策略得到净值曲线
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
            
            # 2. 计算收益率和协方差矩阵
            returns_df = pd.DataFrame(strategy_equities)
            expected_returns = returns_df.mean() * 252
            cov_matrix = returns_df.cov() * 252
            
            # 3. 马科维茨优化（最大化夏普）
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
            
            # 4. 计算组合表现
            optimal_return = np.sum(expected_returns * optimal_weights)
            optimal_vol = np.sqrt(np.dot(optimal_weights.T, np.dot(cov_matrix, optimal_weights)))
            optimal_sharpe = optimal_return / max(optimal_vol, 0.001)
            
            # 等权基准
            equal_weights = weights_init
            equal_return = np.sum(expected_returns * equal_weights)
            equal_vol = np.sqrt(np.dot(equal_weights.T, np.dot(cov_matrix, equal_weights)))
            equal_sharpe = equal_return / max(equal_vol, 0.001)
            
            # 保存结果
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
    
    # 展示结果
    if 'portfolio_result' in st.session_state:
        res = st.session_state.portfolio_result
        
        st.success("组合优化计算完成")
        st.markdown("---")
        
        # 权重饼图
        st.subheader("⚖️ 最优权重分配")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            weights_df = pd.DataFrame({
                '策略': res['strategies'],
                '权重%': (res['optimal_weights'] * 100).round(1)
            }).sort_values('权重%', ascending=False)
            
            fig_pie = go.Figure(data=[go.Pie(
                labels=weights_df['策略'],
                values=weights_df['权重%'],
                textinfo='label+percent',
                hole=0.4
            )])
            fig_pie.update_layout(height=400)
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            st.dataframe(weights_df, use_container_width=True, hide_index=True)
            
            # 改进效果
            st.markdown("####  优化效果")
            sharpe_gain = (res['optimal_sharpe'] - res['equal_sharpe']) / abs(res['equal_sharpe']) * 100
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("组合年化收益", f"{res['optimal_return']*100:.1f}%", 
                         delta=f"{(res['optimal_return']-res['equal_return'])*100:+.1f}% vs 等权")
            with col_b:
                st.metric("组合夏普比率", f"{res['optimal_sharpe']:.2f}",
                         delta=f"{sharpe_gain:+.1f}% vs 等权")
        
        st.markdown("---")
        
        # 相关性矩阵
        st.subheader("🔗 策略相关性矩阵")
        
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
            colorbar=dict(title="相关系数")
        ))
        
        fig_corr.update_layout(height=450)
        st.plotly_chart(fig_corr, use_container_width=True)
        
        st.info(" 相关系数越接近-1，策略之间的对冲效果越好；越接近1，策略越同质化，分散效果越差")

st.markdown("---")
st.caption("Rock Quant 2.0 - 顽岩量价模型")
