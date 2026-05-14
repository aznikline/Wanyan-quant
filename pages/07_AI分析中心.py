import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.ai_analyzer import AIStrategyAnalyzer
from src.backtest_engine import BacktestEngine
from strategies import get_all_strategies, create_strategy
from data_loader import DataLoader

st.set_page_config(
    page_title="AI智能分析中心 - Rock Quant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== 初始化 ==========
loader = DataLoader()
analyzer = AIStrategyAnalyzer()
all_strategies = get_all_strategies()
preset_symbols = list(loader.preset_symbols.keys())

st.title("🧠 AI智能分析中心")
st.caption("Rock Quant 2.6 - 多维度AI分析 + 多智能体辩论评估")

# ========== 侧边栏配置 ==========
with st.sidebar:
    st.markdown("## 分析配置")
    
    # 多标的选择
    selected_symbols = st.multiselect(
        "选择标的进行对比分析",
        preset_symbols,
        default=[preset_symbols[0]] if preset_symbols else [],
        max_selections=5
    )
    
    # 多策略选择
    selected_strategies = st.multiselect(
        "选择策略进行对比分析",
        all_strategies,
        default=[all_strategies[0]] if all_strategies else [],
        max_selections=5
    )
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("开始日期", pd.to_datetime("2020-01-01"))
    with col2:
        end_date = st.date_input("结束日期", pd.to_datetime("2023-12-31"))
    
    initial_capital = st.number_input("初始资金", value=1000000, step=100000)
    
    st.markdown("---")
    enable_ai = st.checkbox("启用AI深度分析", value=True, help="包括多智能体辩论和收益归因")
    st.markdown("---")
    
    run_analysis = st.button("🚀 启动批量AI分析", type="primary", use_container_width=True)

# ========== 主分析区域 ==========
if run_analysis and selected_symbols and selected_strategies:
    with st.spinner("正在进行批量回测与AI深度分析..."):
        
        results = []
        progress_bar = st.progress(0)
        total_tasks = len(selected_symbols) * len(selected_strategies)
        current_task = 0
        
        for symbol_name in selected_symbols:
            symbol_code = loader.preset_symbols[symbol_name]
            try:
                data = loader.load_data(symbol_code, str(start_date), str(end_date))
            except Exception as e:
                st.error(f"{symbol_name} 数据加载失败: {str(e)}")
                continue
                
            for strategy_name in selected_strategies:
                current_task += 1
                progress_bar.progress(current_task / total_tasks)
                
                try:
                    # 回测
                    strategy = create_strategy(strategy_name)
                    signals = strategy.generate_signals(data)
                    
                    from config import BacktestConfig
                    config = BacktestConfig(initial_capital=initial_capital)
                    engine = BacktestEngine(config)
                    result = engine.run(data, signals)
                    perf = result.performance
                    
                    # AI分析
                    ai_result = None
                    if enable_ai and len(result.trades) > 0:
                        ai_result = analyzer.analyze(
                            equity_curve=result.equity_curve,
                            trades=result.trades,
                            perf=perf,
                            strategy_name=strategy_name,
                            symbol_name=symbol_name
                        )
                    
                    results.append({
                        'symbol': symbol_name,
                        'strategy': strategy_name,
                        'result': result,
                        'perf': perf,
                        'ai_result': ai_result
                    })
                    
                except Exception as e:
                    st.warning(f"{strategy_name} @ {symbol_name} 分析失败: {str(e)}")
                    continue
        
        progress_bar.empty()
        
        if not results:
            st.error("没有成功的分析结果，请检查参数配置")
            st.stop()
        
        # ===== 1. 综合排行榜 =====
        st.markdown("## 🏆 综合排行榜")
        st.caption("按AI综合评分排序，点击展开查看详细分析")
        
        ranking_data = []
        for r in results:
            perf = r['perf']
            ai_score = r['ai_result'].score.overall_score if r['ai_result'] else 0
            ai_grade = r['ai_result'].score.grade if r['ai_result'] else '-'
            
            ranking_data.append({
                '策略': r['strategy'],
                '标的': r['symbol'],
                'AI评分': ai_score,
                '评级': ai_grade,
                '年化收益%': round(perf['年化收益率(CAGR)'], 2),
                '最大回撤%': round(perf['最大回撤'], 2),
                '夏普比率': round(perf['夏普比率'], 2),
                '卡玛比率': round(perf['卡玛比率'], 2),
                '胜率%': round(perf['胜率'], 1),
                '交易次数': perf['总交易次数']
            })
        
        ranking_df = pd.DataFrame(ranking_data).sort_values('AI评分', ascending=False).reset_index(drop=True)
        
        # 彩色显示评级
        def highlight_grade(row):
            colors = {
                'S': 'background-color: #1a9641; color: white; font-weight: bold',
                'A': 'background-color: #a6d96a; color: white',
                'B': 'background-color: #fdae61; color: black',
                'C': 'background-color: #f46d43; color: white',
                'D': 'background-color: #d73027; color: white',
                'F': 'background-color: #000000; color: white'
            }
            return [colors.get(row['评级'], '')] * len(row)
        
        st.dataframe(
            ranking_df.style.apply(highlight_grade, axis=1),
            use_container_width=True,
            height=300
        )
        
        st.markdown("---")
        
        # ===== 2. 净值曲线对比 =====
        st.markdown("## 📈 净值曲线对比")
        
        fig_compare = go.Figure()
        for r in results:
            equity = r['result'].equity_curve
            label = f"{r['strategy']} @ {r['symbol']}"
            if r['ai_result']:
                grade = r['ai_result'].score.grade
                label += f" ({grade}级)"
            
            fig_compare.add_trace(go.Scatter(
                x=equity.index,
                y=equity.values,
                name=label,
                line=dict(width=2)
            ))
        
        fig_compare.update_layout(
            height=450,
            hovermode='x unified',
            yaxis_title='净值',
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
        )
        st.plotly_chart(fig_compare, use_container_width=True)
        
        st.markdown("---")
        
        # ===== 3. 雷达图多维度对比 =====
        st.markdown("## 🎯 五维度能力雷达图")
        
        if len(results) <= 5 and all(r['ai_result'] is not None for r in results):
            categories = ['收益能力', '风险控制', '风险调整收益', '稳定性', '交易质量']
            
            fig_radar = go.Figure()
            
            for r in results:
                score = r['ai_result'].score
                values = [
                    score.return_score / 40 * 100,
                    score.risk_score / 20 * 100,
                    score.risk_adjusted_score / 15 * 100,
                    score.consistency_score / 10 * 100,
                    score.trading_quality_score / 15 * 100
                ]
                
                label = f"{r['strategy']} @ {r['symbol']} ({score.grade})"
                fig_radar.add_trace(go.Scatterpolar(
                    r=values,
                    theta=categories,
                    fill='toself',
                    name=label,
                    opacity=0.6
                ))
            
            fig_radar.update_layout(
                height=500,
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                showlegend=True,
                legend=dict(orientation='h', yanchor='bottom', y=-0.2, xanchor='center', x=0.5)
            )
            st.plotly_chart(fig_radar, use_container_width=True)
        else:
            st.info("最多支持5组结果同时显示雷达图对比")
        
        st.markdown("---")
        
        # ===== 4. 各组合详细分析卡片 =====
        st.markdown("## 📋 各组合详细分析")
        
        for i, r in enumerate(results, 1):
            perf = r['perf']
            ai_result = r['ai_result']
            
            with st.expander(f"**{i}. {r['strategy']} @ {r['symbol']}** | {'AI评分: ' + str(round(ai_result.score.overall_score, 1)) + '/' + str(ai_result.score.grade) + '级' if ai_result else '基础分析'}", expanded=False):
                
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.metric("年化收益", f"{perf['年化收益率(CAGR)']:.2f}%")
                with col2:
                    st.metric("最大回撤", f"{perf['最大回撤']:.2f}%")
                with col3:
                    st.metric("夏普比率", f"{perf['夏普比率']:.2f}")
                with col4:
                    st.metric("卡玛比率", f"{perf['卡玛比率']:.2f}")
                with col5:
                    st.metric("胜率/次数", f"{perf['胜率']:.1f}% / {perf['总交易次数']}")
                
                if ai_result:
                    score = ai_result.score
                    attr = ai_result.attribution
                    
                    st.markdown("---")
                    
                    # 优势与不足
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown("### ✅ 策略优势")
                        for s in score.strengths[:3]:
                            st.success(f"• {s}")
                    with col_b:
                        st.markdown("### ⚠️ 待改进")
                        for w in score.weaknesses[:3]:
                            st.warning(f"• {w}")
                    
                    # 收益归因
                    st.markdown("### 🔬 收益归因")
                    attr_cols = st.columns(5)
                    attr_items = [
                        ("📈 趋势", attr.trend_capture),
                        ("🌊 波动", attr.volatility_timing),
                        ("⚖️ 均值", attr.mean_reversion),
                        ("🎯 仓位", attr.position_sizing),
                        ("🎲 运气", attr.luck_factor)
                    ]
                    for col, (name, val) in zip(attr_cols, attr_items):
                        col.metric(name, f"{abs(val):.1f}%")
                    
                    # 多智能体辩论摘要
                    st.markdown("### 🗣️ 专家意见")
                    debate_cols = st.columns(4)
                    for col, agent in zip(debate_cols, ai_result.debate_results):
                        with col:
                            rec_colors = {
                                '强烈推荐': '🟢',
                                '可以使用': '🟡',
                                '谨慎使用': '🟠',
                                '不推荐': '🔴'
                            }
                            st.markdown(f"**{rec_colors.get(agent.recommendation, '')} {agent.role.value}**")
                            st.caption(f"{agent.recommendation} ({agent.confidence}%)")
                
                st.markdown("---")

        # ===== 5. 配置建议 =====
        st.markdown("## 💡 资产配置建议")
        
        if len(results) >= 2 and all(r['ai_result'] is not None for r in results):
            # 基于AI评分的简单配置建议
            total_score = sum(r['ai_result'].score.overall_score for r in results)
            
            st.info("基于AI评分的简易资产配置建议（仅作参考，需结合实际风险偏好调整）")
            
            alloc_data = []
            for r in results:
                score = r['ai_result'].score
                weight = max(10, min(50, round(score.overall_score / total_score * 100, 1)))  # 10-50%范围
                alloc_data.append({
                    '策略/标的': f"{r['strategy']} @ {r['symbol']}",
                    'AI评分': score.overall_score,
                    '评级': score.grade,
                    '建议配置权重%': weight
                })
            
            alloc_df = pd.DataFrame(alloc_data).sort_values('建议配置权重%', ascending=False)
            st.dataframe(alloc_df, use_container_width=True, hide_index=True)
            
            # 饼图展示
            fig_alloc = go.Figure(data=[go.Pie(
                labels=[f"{x['策略/标的']} ({x['评级']})" for x in alloc_data],
                values=[x['建议配置权重%'] for x in alloc_data],
                hole=.4,
                textinfo='label+percent'
            )])
            fig_alloc.update_layout(height=400, title="建议资产配置比例")
            st.plotly_chart(fig_alloc, use_container_width=True)
        else:
            st.info("选择2组以上策略并启用AI分析后，将自动生成配置建议")

elif not selected_symbols or not selected_strategies:
    st.info("👈 请在左侧选择至少1个标的和1个策略，然后点击「启动批量AI分析」")
    
    # 演示说明
    st.markdown("## 📖 使用说明")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 🎯 核心功能")
        st.markdown("- 多标的、多策略批量回测")
        st.markdown("- AI智能综合评分与评级")
        st.markdown("- 五维度收益归因分析")
        st.markdown("- 4位AI专家辩论评估")
    
    with col2:
        st.markdown("### 🧠 AI评分维度")
        st.markdown("- 📈 收益能力 (40%)")
        st.markdown("- 🛡️ 风险控制 (20%)")
        st.markdown("- ⚖️ 风险调整收益 (15%)")
        st.markdown("- 📊 稳定性 (10%)")
        st.markdown("- 💹 交易质量 (15%)")
    
    with col3:
        st.markdown("### 🗣️ 专家团队")
        st.markdown("- 🛡️ 保守风控官")
        st.markdown("- 🚀 激进交易员")
        st.markdown("- 📊 统计分析师")
        st.markdown("- 🧠 行为金融专家")

st.markdown("---")
st.caption("Rock Quant 2.6 - AI智能量化分析系统 | AI分析仅供参考，不构成投资建议")
