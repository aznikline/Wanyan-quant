import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from pathlib import Path
import sys
from scipy.optimize import minimize

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import BacktestConfig
from backtest_engine import BacktestEngine
from strategies import get_all_strategies, create_strategy
from data_loader import DataLoader

st.set_page_config(
    page_title="策略组合优化 - Rock Quant 2.0",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("⚖️ 策略组合优化")
st.markdown("基于马科维茨现代投资组合理论，优化多策略资金分配，实现风险分散与收益增强")
st.markdown("---")

# 侧边栏参数
st.sidebar.header("回测参数")

loader = DataLoader()
preset_symbols = list(loader.preset_symbols.keys())
symbol_name = st.sidebar.selectbox("选择标的", preset_symbols)

col1, col2 = st.sidebar.columns(2)
with col1:
    start_date = st.date_input("开始日期", pd.to_datetime("2020-01-01"))
with col2:
    end_date = st.date_input("结束日期", pd.to_datetime("2023-12-31"))

initial_capital = st.sidebar.number_input("初始资金", value=1000000, step=100000)

# 策略选择
all_strategies = get_all_strategies()
selected_strategies = st.sidebar.multiselect(
    "选择策略加入组合（建议3-8个）",
    all_strategies,
    default=all_strategies[:5]
)

# 优化目标
optimization_target = st.sidebar.selectbox(
    "优化目标",
    ["最大化夏普比率", "最大化收益率", "最小化波动率", "最大化卡玛比率", "最小化最大回撤"],
    index=0
)

# 约束条件
st.sidebar.markdown("### 权重约束")
min_weight = st.sidebar.slider("单策略最小权重(%)", 0, 50, 5) / 100
max_weight = st.sidebar.slider("单策略最大权重(%)", 10, 100, 40) / 100

if st.sidebar.button("🚀 开始组合优化", type="primary"):
    if len(selected_strategies) < 2:
        st.error("请至少选择2个策略进行组合优化")
    else:
        with st.spinner("正在计算各策略回测结果并进行组合优化..."):
            # ========== 第一步：计算所有策略的净值曲线 ==========
            symbol_code = loader.preset_symbols[symbol_name]
            data = loader.load_data(symbol_code, str(start_date), str(end_date))
            
            strategy_results = {}
            progress_bar = st.progress(0)
            
            for idx, strategy_name in enumerate(selected_strategies):
                config = BacktestConfig(initial_capital=initial_capital)
                engine = BacktestEngine(config)
                strategy = create_strategy(strategy_name)
                signals = strategy.generate_signals(data)
                result = engine.run(data, signals)
                
                strategy_results[strategy_name] = {
                    'equity': result.equity_curve,
                    'performance': result.performance,
                    'returns': result.equity_curve.pct_change().dropna()
                }
                
                progress_bar.progress((idx + 1) / len(selected_strategies))
            
            st.success(f"完成 {len(selected_strategies)} 个策略的基础回测计算")
            
            # ========== 第二步：构建收益率矩阵 ==========
            all_returns = pd.DataFrame({
                name: res['returns'] for name, res in strategy_results.items()
            }).dropna()
            
            # 计算协方差矩阵
            cov_matrix = all_returns.cov() * 252  # 年化协方差
            expected_returns = all_returns.mean() * 252  # 年化预期收益
            
            st.markdown("---")
            
            # ========== 第三步：马科维茨优化 ==========
            st.markdown("## 🎯 马科维茨有效前沿")
            
            n_assets = len(selected_strategies)
            weights_init = np.array([1/n_assets] * n_assets)
            bounds = tuple((min_weight, max_weight) for _ in range(n_assets))
            constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
            
            # 定义目标函数
            def objective_sharpe(weights):
                port_return = np.sum(expected_returns * weights)
                port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
                return -port_return / max(port_vol, 0.001)  # 负号因为minimize
            
            def objective_return(weights):
                return -np.sum(expected_returns * weights)
            
            def objective_vol(weights):
                return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            
            def objective_calmar(weights):
                port_return = np.sum(expected_returns * weights)
                # 计算组合回撤
                combined_equity = sum(
                    strategy_results[name]['equity'] * weights[i] 
                    for i, name in enumerate(selected_strategies)
                )
                rolling_max = combined_equity.expanding().max()
                drawdown = (combined_equity - rolling_max) / rolling_max
                max_dd = abs(drawdown.min())
                return -port_return / max(max_dd, 0.001)
            
            # 根据选择的目标执行优化
            if optimization_target == "最大化夏普比率":
                result = minimize(objective_sharpe, weights_init, method='SLSQP', bounds=bounds, constraints=constraints)
            elif optimization_target == "最大化收益率":
                result = minimize(objective_return, weights_init, method='SLSQP', bounds=bounds, constraints=constraints)
            elif optimization_target == "最小化波动率":
                result = minimize(objective_vol, weights_init, method='SLSQP', bounds=bounds, constraints=constraints)
            elif optimization_target == "最大化卡玛比率":
                result = minimize(objective_calmar, weights_init, method='SLSQP', bounds=bounds, constraints=constraints)
            else:  # 最小化最大回撤
                result = minimize(objective_calmar, weights_init, method='SLSQP', bounds=bounds, constraints=constraints)
            
            optimal_weights = result.x
            
            # ========== 第四步：绘制有效前沿 ==========
            # 蒙特卡洛模拟生成有效前沿
            n_portfolios = 2000
            results = np.zeros((3, n_portfolios))
            weight_array = []
            
            for i in range(n_portfolios):
                weights = np.random.dirichlet([1]*n_assets)  # 保证和为1
                weight_array.append(weights)
                
                port_return = np.sum(expected_returns * weights)
                port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
                port_sharpe = port_return / max(port_vol, 0.001)
                
                results[0,i] = port_return
                results[1,i] = port_vol
                results[2,i] = port_sharpe
            
            # 计算最优组合的表现
            optimal_return = np.sum(expected_returns * optimal_weights)
            optimal_vol = np.sqrt(np.dot(optimal_weights.T, np.dot(cov_matrix, optimal_weights)))
            optimal_sharpe = optimal_return / max(optimal_vol, 0.001)
            
            # 等权组合作为基准
            equal_weights = np.array([1/n_assets] * n_assets)
            equal_return = np.sum(expected_returns * equal_weights)
            equal_vol = np.sqrt(np.dot(equal_weights.T, np.dot(cov_matrix, equal_weights)))
            equal_sharpe = equal_return / max(equal_vol, 0.001)
            
            # 绘制有效前沿散点图
            fig_efficient = go.Figure()
            
            # 蒙特卡洛模拟点
            fig_efficient.add_trace(go.Scatter(
                x=results[1,:] * 100,
                y=results[0,:] * 100,
                mode='markers',
                marker=dict(
                    color=results[2,:],
                    colorscale='Viridis',
                    size=5,
                    opacity=0.6,
                    colorbar=dict(title='夏普比率')
                ),
                name='随机组合',
                hovertemplate='收益: %{y:.1f}%<br>波动: %{x:.1f}%<br>夏普: %{marker.color:.2f}'
            ))
            
            # 最优组合点
            fig_efficient.add_trace(go.Scatter(
                x=[optimal_vol * 100],
                y=[optimal_return * 100],
                mode='markers',
                marker=dict(color='red', size=15, symbol='star'),
                name='最优组合',
                hovertemplate=f'<b>最优组合</b><br>收益: {optimal_return*100:.1f}%<br>波动: {optimal_vol*100:.1f}%<br>夏普: {optimal_sharpe:.2f}'
            ))
            
            # 等权组合点
            fig_efficient.add_trace(go.Scatter(
                x=[equal_vol * 100],
                y=[equal_return * 100],
                mode='markers',
                marker=dict(color='blue', size=12, symbol='circle'),
                name='等权组合',
                hovertemplate=f'<b>等权组合</b><br>收益: {equal_return*100:.1f}%<br>波动: {equal_vol*100:.1f}%<br>夏普: {equal_sharpe:.2f}'
            ))
            
            # 单个策略点
            for name in selected_strategies:
                perf = strategy_results[name]['performance']
                strat_vol = perf['年化波动率'] / 100
                strat_ret = perf['年化收益率'] / 100
                strat_sharpe = perf['夏普比率']
                fig_efficient.add_trace(go.Scatter(
                    x=[strat_vol * 100],
                    y=[strat_ret * 100],
                    mode='markers+text',
                    marker=dict(size=10),
                    text=name[:4],
                    textposition='top right',
                    name=name,
                    hovertemplate=f'<b>{name}</b><br>收益: {strat_ret*100:.1f}%<br>波动: {strat_vol*100:.1f}%<br>夏普: {strat_sharpe:.2f}'
                ))
            
            fig_efficient.update_layout(
                title='马科维茨有效前沿 - 风险收益散点图',
                xaxis_title='年化波动率 (%)',
                yaxis_title='年化收益率 (%)',
                height=550,
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
            )
            
            st.plotly_chart(fig_efficient, use_container_width=True)
            
            st.markdown("---")
            
            # ========== 第五步：最优权重展示 ==========
            st.markdown("## ⚖️ 最优策略权重分配")
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                # 权重饼图
                weights_df = pd.DataFrame({
                    '策略': selected_strategies,
                    '权重': optimal_weights * 100
                })
                weights_df = weights_df.sort_values('权重', ascending=False)
                
                fig_weights = go.Figure(data=[go.Pie(
                    labels=weights_df['策略'],
                    values=weights_df['权重'],
                    textinfo='label+percent',
                    textposition='inside',
                    hole=0.4,
                    marker=dict(colors=px.colors.qualitative.Set3)
                )])
                
                fig_weights.update_layout(
                    title='最优组合权重分配',
                    height=400
                )
                
                st.plotly_chart(fig_weights, use_container_width=True)
            
            with col2:
                # 权重表格
                st.markdown("### 权重详情")
                
                weights_display = []
                for name, weight in zip(selected_strategies, optimal_weights):
                    perf = strategy_results[name]['performance']
                    weights_display.append({
                        '策略名称': name,
                        '分配权重(%)': round(weight * 100, 1),
                        '独立年化(%)': round(perf['年化收益率'], 1),
                        '独立夏普': round(perf['夏普比率'], 2),
                        '独立最大回撤(%)': round(perf['最大回撤'], 1)
                    })
                
                df_weights = pd.DataFrame(weights_display).sort_values('分配权重(%)', ascending=False)
                st.dataframe(df_weights, use_container_width=True, height=400)
            
            st.markdown("---")
            
            # ========== 第六步：组合绩效对比 ==========
            st.markdown("## 📊 组合绩效对比分析")
            
            # 计算组合净值曲线
            optimal_equity = pd.Series(0.0, index=strategy_results[selected_strategies[0]]['equity'].index)
            equal_equity = pd.Series(0.0, index=strategy_results[selected_strategies[0]]['equity'].index)
            
            for i, name in enumerate(selected_strategies):
                equity = strategy_results[name]['equity']
                optimal_equity += equity * optimal_weights[i]
                equal_equity += equity * equal_weights[i]
            
            # 计算组合绩效指标
            def calculate_performance(equity, name):
                returns = equity.pct_change().dropna()
                total_return = (equity.iloc[-1] / equity.iloc[0] - 1) * 100
                cagr = (equity.iloc[-1] / equity.iloc[0]) ** (252 / len(returns)) - 1
                annual_vol = returns.std() * np.sqrt(252) * 100
                sharpe = (cagr * 100) / annual_vol if annual_vol > 0 else 0
                
                rolling_max = equity.expanding().max()
                drawdown = (equity - rolling_max) / rolling_max
                max_dd = drawdown.min() * 100
                
                calmar = cagr * 100 / abs(max_dd) if max_dd != 0 else 0
                
                return {
                    '组合': name,
                    '总收益率(%)': round(total_return, 1),
                    '年化收益率(%)': round(cagr * 100, 1),
                    '年化波动率(%)': round(annual_vol, 1),
                    '最大回撤(%)': round(max_dd, 1),
                    '夏普比率': round(sharpe, 2),
                    '卡玛比率': round(calmar, 2)
                }
            
            # 计算所有对比项
            comparison_data = [calculate_performance(optimal_equity, "✅ 最优权重组合")]
            comparison_data.append(calculate_performance(equal_equity, "📐 等权重组合"))
            
            for name in selected_strategies:
                perf = strategy_results[name]['performance']
                comparison_data.append({
                    '组合': name,
                    '总收益率(%)': round(perf['总收益率'], 1),
                    '年化收益率(%)': round(perf['年化收益率'], 1),
                    '年化波动率(%)': round(perf['年化波动率'], 1),
                    '最大回撤(%)': round(perf['最大回撤'], 1),
                    '夏普比率': round(perf['夏普比率'], 2),
                    '卡玛比率': round(perf['卡玛比率'], 2)
                })
            
            df_comparison = pd.DataFrame(comparison_data)
            
            # 高亮显示最优组合
            def highlight_optimal(row):
                if '最优' in row['组合']:
                    return ['background-color: #d4edda'] * len(row)
                elif '等权' in row['组合']:
                    return ['background-color: #cce5ff'] * len(row)
                else:
                    return [''] * len(row)
            
            st.dataframe(
                df_comparison.style.apply(highlight_optimal, axis=1),
                use_container_width=True,
                height=300
            )
            
            # 改进幅度
            st.markdown("### 📈 优化效果")
            col1, col2, col3 = st.columns(3)
            
            opt_data = comparison_data[0]
            eq_data = comparison_data[1]
            
            with col1:
                sharpe_improvement = (opt_data['夏普比率'] - eq_data['夏普比率']) / max(abs(eq_data['夏普比率']), 0.001) * 100
                st.metric("夏普比率提升", f"{sharpe_improvement:.1f}%", 
                         f"从 {eq_data['夏普比率']:.2f} 到 {opt_data['夏普比率']:.2f}")
            
            with col2:
                cagr_improvement = (opt_data['年化收益率(%)'] - eq_data['年化收益率(%)']) / max(abs(eq_data['年化收益率(%)']), 0.001) * 100
                st.metric("年化收益率变化", f"{cagr_improvement:+.1f}%",
                         f"从 {eq_data['年化收益率(%)']:.1f}% 到 {opt_data['年化收益率(%)']:.1f}%")
            
            with col3:
                dd_improvement = (abs(eq_data['最大回撤(%)']) - abs(opt_data['最大回撤(%)'])) / abs(eq_data['最大回撤(%)']) * 100
                st.metric("最大回撤改善", f"{dd_improvement:+.1f}%",
                         f"从 {eq_data['最大回撤(%)']:.1f}% 到 {opt_data['最大回撤(%)']:.1f}%")
            
            st.markdown("---")
            
            # ========== 第七步：净值曲线对比 ==========
            st.markdown("## 📈 净值曲线对比")
            
            fig_comparison = go.Figure()
            
            # 最优组合
            fig_comparison.add_trace(go.Scatter(
                x=optimal_equity.index,
                y=optimal_equity.values / initial_capital,
                name='最优权重组合',
                line=dict(color='red', width=3),
                hovertemplate='净值: %{y:.3f}<extra></extra>'
            ))
            
            # 等权组合
            fig_comparison.add_trace(go.Scatter(
                x=equal_equity.index,
                y=equal_equity.values / initial_capital,
                name='等权重组合',
                line=dict(color='blue', width=2, dash='dash'),
                hovertemplate='净值: %{y:.3f}<extra></extra>'
            ))
            
            # 单个策略（淡色）
            for name in selected_strategies:
                equity = strategy_results[name]['equity']
                fig_comparison.add_trace(go.Scatter(
                    x=equity.index,
                    y=equity.values / initial_capital,
                    name=name,
                    line=dict(width=1.5),
                    opacity=0.4,
                    hovertemplate='净值: %{y:.3f}<extra></extra>'
                ))
            
            fig_comparison.update_layout(
                title='组合净值曲线对比（标准化，初始=1）',
                height=500,
                hovermode='x unified',
                yaxis_title='净值',
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
            )
            
            st.plotly_chart(fig_comparison, use_container_width=True)
            
            st.markdown("---")
            
            # ========== 第八步：相关性分析 ==========
            st.markdown("## 🔗 策略间相关性矩阵")
            
            corr_matrix = all_returns.corr()
            
            fig_corr = go.Figure(data=go.Heatmap(
                z=corr_matrix.values,
                x=corr_matrix.columns,
                y=corr_matrix.index,
                colorscale='RdBu_r',
                zmid=0,
                zmin=-1,
                zmax=1,
                text=[[f'{v:.2f}' for v in row] for row in corr_matrix.values],
                texttemplate='%{text}',
                textfont={"size": 11},
                colorbar=dict(title='相关系数')
            ))
            
            fig_corr.update_layout(
                title='策略日收益率相关性矩阵',
                height=500
            )
            
            st.plotly_chart(fig_corr, use_container_width=True)
            
            st.info("💡 **解读建议**：相关系数越接近0或负数，策略间分散化效果越好。高度正相关的策略（>0.7）同时配置意义不大。")
            
            st.markdown("---")
            
            # ========== 第九步：配置建议 ==========
            st.markdown("## 💡 配置建议与总结")
            
            # 自动化分析
            high_corr_pairs = []
            for i in range(len(selected_strategies)):
                for j in range(i+1, len(selected_strategies)):
                    if corr_matrix.iloc[i, j] > 0.7:
                        high_corr_pairs.append((selected_strategies[i], selected_strategies[j], corr_matrix.iloc[i, j]))
            
            if len(high_corr_pairs) > 0:
                st.warning("⚠️ **高相关性警告**：发现以下策略对相关性过高 (>0.7)，建议减少同时配置：")
                for s1, s2, corr in high_corr_pairs:
                    st.write(f"   - {s1} ↔ {s2}: {corr:.2f}")
            
            # 总结建议
            sharpe_gain = (optimal_sharpe - equal_sharpe) / max(abs(equal_sharpe), 0.001) * 100
            
            if sharpe_gain > 10:
                st.success(f"✅ **优化效果显著**：最优组合相对等权组合夏普比率提升 {sharpe_gain:.1f}%，建议采用优化后的权重配置")
            elif sharpe_gain > 0:
                st.info(f"ℹ️ **优化效果一般**：最优组合相对等权组合夏普比率提升 {sharpe_gain:.1f}%，差异不大，可根据实际情况选择")
            else:
                st.warning(f"⚠️ **优化效果不佳**：最优组合相对等权组合夏普比率下降 {-sharpe_gain:.1f}%，建议调整策略选择或约束条件")
            
            # 推荐配置
            st.markdown("### 📋 推荐配置摘要")
            for _, row in weights_df.head(3).iterrows():
                st.markdown(f"- **{row['策略']}**: {row['权重']:.1f}%")
            
            st.caption(f"标的: {symbol_name} | 回测区间: {start_date} ~ {end_date} | 优化目标: {optimization_target}")

st.markdown("---")
st.caption("Rock Quant 2.0 - 顽岩量价模型 | 马科维茨投资组合优化")
