import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import BacktestConfig
from backtest_engine import BacktestEngine
from strategies import get_all_strategies, create_strategy
from data_loader import DataLoader

st.set_page_config(
    page_title="多标的分析 - Rock Quant 2.0",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🎯 多标的批量回测")
st.markdown("同一策略在不同标的上的批量回测与横向对比分析，快速筛选最优标的")
st.markdown("---")

# 侧边栏参数
st.sidebar.header("回测参数")

strategy_name = st.sidebar.selectbox("选择策略", get_all_strategies())
loader = DataLoader()
preset_symbols = list(loader.preset_symbols.keys())

# 多标的选择
selected_symbols = st.sidebar.multiselect(
    "选择标的（可多选）",
    preset_symbols,
    default=preset_symbols[:5]  # 默认选前5个
)

col1, col2 = st.sidebar.columns(2)
with col1:
    start_date = st.date_input("开始日期", pd.to_datetime("2020-01-01"))
with col2:
    end_date = st.date_input("结束日期", pd.to_datetime("2023-12-31"))

initial_capital = st.sidebar.number_input("初始资金", value=1000000, step=100000)

if st.sidebar.button("🚀 开始批量回测", type="primary"):
    if len(selected_symbols) == 0:
        st.error("请至少选择一个标的")
    else:
        with st.spinner(f"正在批量回测 {len(selected_symbols)} 个标的..."):
            # 批量回测
            results = []
            progress_bar = st.progress(0)
            
            for idx, symbol_name in enumerate(selected_symbols):
                try:
                    symbol_code = loader.preset_symbols[symbol_name]
                    data = loader.load_data(symbol_code, str(start_date), str(end_date))
                    
                    if len(data) < 30:  # 数据太少跳过
                        continue
                    
                    config = BacktestConfig(initial_capital=initial_capital)
                    engine = BacktestEngine(config)
                    strategy = create_strategy(strategy_name)
                    signals = strategy.generate_signals(data)
                    result = engine.run(data, signals)
                    
                    perf = result.performance
                    results.append({
                        '标的名称': symbol_name,
                        '标的代码': symbol_code,
                        '总收益率': perf['总收益率'],
                        '年化收益率': perf['年化收益率(CAGR)'],
                        '最大回撤': perf['最大回撤'],
                        '夏普比率': perf['夏普比率'],
                        '卡玛比率': perf['卡玛比率'],
                        '索提诺比率': perf['索提诺比率'],
                        '胜率': perf['胜率'],
                        '盈亏比': perf['盈亏比'],
                        '交易次数': perf['总交易次数'],
                        '年化波动率': perf['年化波动率'],
                        '净值曲线': result.equity_curve,
                        '交易明细': result.trades,
                        '回测成功': True
                    })
                    
                except Exception as e:
                    results.append({
                        '标的名称': symbol_name,
                        '回测成功': False,
                        '错误信息': str(e)
                    })
                
                progress_bar.progress((idx + 1) / len(selected_symbols))
                time.sleep(0.1)
            
            st.success(f"批量回测完成！成功 {sum(1 for r in results if r.get('回测成功', False))}/{len(results)}")
            
            # 筛选成功的结果
            successful_results = [r for r in results if r.get('回测成功', False)]
            
            if len(successful_results) == 0:
                st.error("所有标的回测均失败，请检查数据或参数")
            else:
                # ========== 第一部分：净值曲线对比 ==========
                st.markdown("## 📈 净值曲线对比")
                st.caption("所有标的的标准化净值曲线对比（初始值均为1）")
                
                fig_equity = go.Figure()
                colors = px.colors.qualitative.Set1 + px.colors.qualitative.Set2
                
                for idx, result in enumerate(successful_results):
                    # 标准化净值曲线
                    normalized_equity = result['净值曲线'] / initial_capital
                    fig_equity.add_trace(go.Scatter(
                        x=normalized_equity.index,
                        y=normalized_equity.values,
                        name=result['标的名称'],
                        line=dict(color=colors[idx % len(colors)], width=2),
                        hovertemplate='%{y:.3f}<extra></extra>'
                    ))
                
                fig_equity.update_layout(
                    title=f'{strategy_name} - 多标的净值曲线对比（标准化）',
                    height=500,
                    hovermode='x unified',
                    yaxis_title='净值（初始=1）',
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
                )
                
                st.plotly_chart(fig_equity, use_container_width=True)
                
                st.markdown("---")
                
                # ========== 第二部分：核心绩效排名表格 ==========
                st.markdown("## 🏆 核心绩效排名")
                st.caption("点击列标题可按该列排序，快速找到最优标的")
                
                # 构建排名表格
                ranking_data = []
                for r in successful_results:
                    ranking_data.append({
                        '标的名称': r['标的名称'],
                        '总收益率(%)': round(r['总收益率'], 2),
                        '年化收益率(%)': round(r['年化收益率'], 2),
                        '最大回撤(%)': round(r['最大回撤'], 2),
                        '夏普比率': round(r['夏普比率'], 2),
                        '卡玛比率': round(r['卡玛比率'], 2),
                        '索提诺比率': round(r['索提诺比率'], 2),
                        '胜率(%)': round(r['胜率'], 2),
                        '盈亏比': round(r['盈亏比'], 2),
                        '交易次数': r['交易次数']
                    })
                
                df_ranking = pd.DataFrame(ranking_data)
                
                # 高性能表格
                st.dataframe(
                    df_ranking,
                    use_container_width=True,
                    column_config={
                        '总收益率(%)': st.column_config.NumberColumn('总收益率', help='回测区间总收益率'),
                        '年化收益率(%)': st.column_config.NumberColumn('年化', help='年化收益率CAGR'),
                        '最大回撤(%)': st.column_config.NumberColumn('最大回撤', help='最大回撤（越小越好）'),
                        '夏普比率': st.column_config.NumberColumn('夏普', help='风险调整后收益（越高越好）'),
                        '卡玛比率': st.column_config.NumberColumn('卡玛', help='收益/回撤比（越高越好）'),
                        '索提诺比率': st.column_config.NumberColumn('索提诺', help='下行风险调整后收益'),
                        '胜率(%)': st.column_config.NumberColumn('胜率', help='盈利交易占比'),
                        '盈亏比': st.column_config.NumberColumn('盈亏比', help='平均盈利/平均亏损'),
                        '交易次数': st.column_config.NumberColumn('交易次数')
                    },
                    height=400
                )
                
                st.markdown("---")
                
                # ========== 第三部分：雷达图对比 ==========
                st.markdown("## 📡 多维能力雷达图")
                st.caption("从6个核心维度对比各标的的策略表现，越靠外表现越好")
                
                # 选择最多5个标的展示雷达图（避免太乱）
                radar_symbols = st.multiselect(
                    "选择要对比的标的（最多5个）",
                    [r['标的名称'] for r in successful_results],
                    default=[r['标的名称'] for r in successful_results[:3]]
                )
                
                if len(radar_symbols) > 0:
                    # 归一化指标（0-100分）
                    radar_data = []
                    metrics = ['年化收益率', '夏普比率', '卡玛比率', '索提诺比率', '胜率', '盈亏比']
                    
                    # 计算各指标的最大最小值用于归一化
                    metric_values = {m: [] for m in metrics}
                    for r in successful_results:
                        metric_values['年化收益率'].append(r['年化收益率'])
                        metric_values['夏普比率'].append(r['夏普比率'])
                        metric_values['卡玛比率'].append(r['卡玛比率'])
                        metric_values['索提诺比率'].append(r['索提诺比率'])
                        metric_values['胜率'].append(r['胜率'])
                        metric_values['盈亏比'].append(r['盈亏比'])
                    
                    fig_radar = go.Figure()
                    
                    for idx, symbol_name in enumerate(radar_symbols):
                        result = next(r for r in successful_results if r['标的名称'] == symbol_name)
                        
                        # 归一化到0-100分
                        normalized_values = []
                        for m in metrics:
                            min_val = min(metric_values[m])
                            max_val = max(metric_values[m])
                            if max_val == min_val:
                                normalized = 50
                            else:
                                normalized = (result[m] - min_val) / (max_val - min_val) * 100
                            normalized_values.append(normalized)
                        
                        fig_radar.add_trace(go.Scatterpolar(
                            r=normalized_values,
                            theta=['年化收益', '夏普比率', '卡玛比率', '索提诺比率', '胜率', '盈亏比'],
                            fill='toself',
                            name=symbol_name,
                            line=dict(color=colors[idx % len(colors)])
                        ))
                    
                    fig_radar.update_layout(
                        polar=dict(
                            radialaxis=dict(
                                visible=True,
                                range=[0, 100]
                            )
                        ),
                        height=500,
                        title='策略多维度能力对比（归一化0-100分）'
                    )
                    
                    st.plotly_chart(fig_radar, use_container_width=True)
                
                st.markdown("---")
                
                # ========== 第四部分：散点图分析 ==========
                st.markdown("## 🎨 收益-风险散点图")
                st.caption("X轴=风险（最大回撤），Y轴=收益（年化收益率），气泡大小=夏普比率")
                
                scatter_x = st.selectbox("X轴指标", ['最大回撤', '年化波动率', '交易次数'], index=0)
                scatter_y = st.selectbox("Y轴指标", ['年化收益率', '总收益率', '卡玛比率'], index=0)
                
                fig_scatter = go.Figure()
                
                x_values = [r[scatter_x] for r in successful_results]
                y_values = [r[scatter_y] for r in successful_results]
                sharpe_values = [r['夏普比率'] * 5 for r in successful_results]  # 放大用于气泡大小
                
                for idx, result in enumerate(successful_results):
                    fig_scatter.add_trace(go.Scatter(
                        x=[result[scatter_x]],
                        y=[result[scatter_y]],
                        mode='markers+text',
                        marker=dict(
                            size=sharpe_values[idx],
                            color=colors[idx % len(colors)],
                            opacity=0.7,
                            line=dict(width=1, color='white')
                        ),
                        text=result['标的名称'],
                        textposition='top center',
                        name=result['标的名称'],
                        hovertemplate=(
                            f"<b>{result['标的名称']}</b><br>"
                            f"{scatter_x}: {result[scatter_x]:.2f}<br>"
                            f"{scatter_y}: {result[scatter_y]:.2f}<br>"
                            f"夏普: {result['夏普比率']:.2f}<br>"
                            f"胜率: {result['胜率']:.1f}%"
                        )
                    ))
                
                fig_scatter.update_layout(
                    title=f'{scatter_y} vs {scatter_x} 散点图（气泡大小=夏普比率）',
                    height=500,
                    xaxis_title=scatter_x,
                    yaxis_title=scatter_y,
                    showlegend=False
                )
                
                st.plotly_chart(fig_scatter, use_container_width=True)
                
                st.markdown("---")
                
                # ========== 第五部分：单标的详情 ==========
                st.markdown("## 🔍 单标的详细分析")
                
                detail_symbol = st.selectbox(
                    "选择查看详情的标的",
                    [r['标的名称'] for r in successful_results]
                )
                
                if detail_symbol:
                    detail_result = next(r for r in successful_results if r['标的名称'] == detail_symbol)
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("总收益率", f"{detail_result['总收益率']:.2f}%")
                        st.metric("年化收益率", f"{detail_result['年化收益率']:.2f}%")
                    with col2:
                        st.metric("最大回撤", f"{detail_result['最大回撤']:.2f}%", delta_color="inverse")
                        st.metric("年化波动率", f"{detail_result['年化波动率']:.2f}%")
                    with col3:
                        st.metric("夏普比率", f"{detail_result['夏普比率']:.2f}")
                        st.metric("卡玛比率", f"{detail_result['卡玛比率']:.2f}")
                    with col4:
                        st.metric("胜率", f"{detail_result['胜率']:.1f}%")
                        st.metric("盈亏比", f"{detail_result['盈亏比']:.2f}")
                    
                    # 显示交易明细
                    with st.expander("查看交易明细"):
                        trades = detail_result['交易明细']
                        if len(trades) > 0:
                            trades_display = trades.copy()
                            trades_display['entry_date'] = pd.to_datetime(trades_display['entry_date']).dt.strftime('%Y-%m-%d')
                            trades_display['exit_date'] = pd.to_datetime(trades_display['exit_date']).dt.strftime('%Y-%m-%d')
                            st.dataframe(trades_display, use_container_width=True)
                        else:
                            st.info("该标的下无交易记录")
                
                st.markdown("---")
                
                # ========== 第六部分：综合排名与总结 ==========
                st.markdown("## 📊 综合分析总结")
                
                # 计算综合得分（简单加权）
                for r in successful_results:
                    # 夏普40% + 卡玛30% + 年化20% + 胜率10%（需要归一化）
                    sharpe_rank = sorted(successful_results, key=lambda x: x['夏普比率'], reverse=True).index(r)
                    calmar_rank = sorted(successful_results, key=lambda x: x['卡玛比率'], reverse=True).index(r)
                    cagr_rank = sorted(successful_results, key=lambda x: x['年化收益率'], reverse=True).index(r)
                    winrate_rank = sorted(successful_results, key=lambda x: x['胜率'], reverse=True).index(r)
                    
                    # 排名越靠前得分越高
                    n = len(successful_results)
                    r['综合得分'] = round((
                        (n - sharpe_rank) * 0.4 +
                        (n - calmar_rank) * 0.3 +
                        (n - cagr_rank) * 0.2 +
                        (n - winrate_rank) * 0.1
                    ) / n * 100, 1)
                
                # 按综合得分排序
                sorted_results = sorted(successful_results, key=lambda x: x['综合得分'], reverse=True)
                
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.markdown("### 🏅 综合排名 TOP 3")
                    for i, r in enumerate(sorted_results[:3]):
                        medal = ['🥇', '🥈', '🥉'][i]
                        st.markdown(f"{medal} **第{i+1}名**: {r['标的名称']} - 综合得分 {r['综合得分']}分")
                        st.caption(f"夏普{r['夏普比率']:.2f} | 卡玛{r['卡玛比率']:.2f} | 年化{r['年化收益率']:.1f}% | 胜率{r['胜率']:.1f}%")
                
                with col2:
                    st.markdown("### 💡 策略适用性分析")
                    
                    # 简单的自动化分析
                    avg_sharpe = np.mean([r['夏普比率'] for r in successful_results])
                    avg_winrate = np.mean([r['胜率'] for r in successful_results])
                    
                    if avg_sharpe > 1.5 and avg_winrate > 50:
                        st.success(f"✅ {strategy_name} 在这批标的上表现优秀！平均夏普{avg_sharpe:.2f}，平均胜率{avg_winrate:.1f}%")
                    elif avg_sharpe > 1.0:
                        st.info(f"ℹ️ {strategy_name} 在这批标的上表现尚可，平均夏普{avg_sharpe:.2f}，建议进一步筛选标的")
                    else:
                        st.warning(f"⚠️ {strategy_name} 在这批标的上表现一般，平均夏普{avg_sharpe:.2f}，建议优化策略参数或换策略")
                    
                    # 找出最适合的标的类型
                    winners = [r['标的名称'] for r in sorted_results[:3]]
                    st.caption(f"表现较好的标的: {', '.join(winners)}")

st.markdown("---")
st.caption("Rock Quant 2.0 - 顽岩量价模型 | 多标的批量回测分析")
