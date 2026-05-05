import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from strategies import get_all_strategies, create_strategy
from data_loader import DataLoader
from config import BacktestConfig
from backtest_engine import BacktestEngine

st.set_page_config(page_title="多策略对比 - Rock Quant", page_icon="📊", layout="wide")

st.title("多策略对比分析")
st.markdown("---")

# 标的和时间范围选择
col1, col2 = st.columns(2)
with col1:
    loader = DataLoader()
    preset_symbols = list(loader.preset_symbols.keys()
    symbol_name = st.selectbox("选择回测标的", list(preset_symbols), index=0)
with col2:
    col2_1, col2_2 = st.columns(2)
    with col2_1:
        start_date = st.date_input("开始日期", value=pd.to_datetime("2020-01-01"))
    with col2_2:
        end_date = st.date_input("结束日期", value=pd.to_datetime("2023-12-31"))

st.markdown("---")

# 策略选择
st.subheader("选择要对比的策略")
strategy_categories = {
    "趋势跟踪类": ["双均线策略", "MACD策略", "DMA平均线差策略", "TRIX三重指数策略", "均线多头发散策略", "唐奇安通道突破策略"],
    "震荡反转类": ["RSI超买超卖策略", "KDJ随机指标策略", "CCI顺势指标策略", "WR威廉指标策略", "MOM动量线策略", "ROC变动率策略", "BIAS乖离率策略"],
    "通道突破类": ["布林带突破策略", "肯特纳通道突破策略"],
    "量价配合类": ["成交量突破策略", "OBV能量潮策略", "VR容量比率策略", "EMV简易波动策略"],
    "趋势强弱类": ["DMI趋向指标策略"],
}

# 按分类显示策略复选框
selected_strategies = []
for category, strategies in strategy_categories.items():
    with st.expander(f"{category} ({len(strategies)}"):
        for strategy_name in strategies:
            if st.checkbox(strategy_name, key=f"check_{strategy_name}"):
                selected_strategies.append(strategy_name)

st.markdown("---")

if st.button("🚀 批量回测所有选中策略", type="primary", disabled=len(selected_strategies)==0):
    if len(selected_strategies) == 0:
        st.warning("请至少选择一个策略")
    else:
        with st.spinner(f"正在回测 {len(selected_strategies)} 个策略..."):
            # 加载数据
            symbol_code = loader.preset_symbols[symbol_name]
            data = loader.load_data(symbol_code, str(start_date), str(end_date))
            config = BacktestConfig(initial_capital=1000000)
            engine = BacktestEngine(config)
            
            # 批量回测
            results = []
            equity_curves = {}
            
            progress_bar = st.progress(0)
            for i, strategy_name in enumerate(selected_strategies):
                strategy = create_strategy(strategy_name)
                signals = strategy.generate_signals(data)
                result = engine.run(data, signals)
                perf = result.performance
                results.append({
                    "策略名称": strategy_name,
                    "总收益率": f"{perf['总收益率']:.2f}%",
                    "年化收益率": f"{perf['年化收益率(CAGR)']:.2f}%",
                    "夏普比率": f"{perf['夏普比率']:.2f}",
                    "最大回撤": f"{perf['最大回撤']:.2f}%",
                    "卡玛比率": f"{perf['卡玛比率']:.2f}",
                    "交易次数": perf['总交易次数'],
                    "胜率": f"{perf['胜率']:.1f}%",
                    "盈亏比": f"{perf['盈亏比']:.1f}",
                })
                equity_curves[strategy_name] = result.equity_curve
                progress_bar.progress((i + 1) / len(selected_strategies))
            
            # 显示对比表格
            st.subheader("📊 策略对比结果")
            df = pd.DataFrame(results)
            st.dataframe(df, use_container_width=True)
            
            # 净值曲线对比
            st.subheader("📈 净值曲线对比")
            fig = go.Figure()
            colors = px.colors.qualitative.Plotly
            for i, (name, curve) in enumerate(equity_curves.items()):
                fig.add_trace(go.Scatter(x=curve.index, y=curve.values, name=name, line=dict(color=colors[i % len(colors)], width=2))
            fig.update_layout(height=500, hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)
            
            # 散点图：收益率 vs 最大回撤
            st.subheader("🎯 收益风险散点图")
            scatter_data = []
            for i, strategy_name in enumerate(selected_strategies):
                strategy = create_strategy(strategy_name)
                signals = strategy.generate_signals(data)
                result = engine.run(data, signals)
                perf = result.performance
                scatter_data.append({
                    "策略名称": strategy_name,
                    "总收益率": perf['总收益率'],
                    "最大回撤": abs(perf['最大回撤'])
                })
            
            scatter_df = pd.DataFrame(scatter_data)
            fig = px.scatter(scatter_df, x="最大回撤", y="总收益率", color="策略名称", text="策略名称", color_discrete_sequence=colors[:len(scatter_df)])
            fig.update_traces(textposition='top center')
            st.plotly_chart(fig, use_container_width=True)
            
            # 雷达图对比
            if len(selected_strategies) >= 2:
                st.subheader("🕸️ 策略能力雷达图")
                from math import pi
                
                categories = ['总收益率', '夏普比率', '胜率', '盈亏比', '抗回撤']
                
                fig = go.Figure()
                
                for strategy_name in selected_strategies[:5]:
                    strategy = create_strategy(strategy_name)
                    signals = strategy.generate_signals(data)
                    result = engine.run(data, signals)
                    perf = result.performance
                    
                    values = [
                        max(0, perf['总收益率']),
                        max(0, perf['夏普比率'] * 10),
                        perf['胜率'],
                        min(50),
                        100 - abs(perf['最大回撤'])
                    ]
                    
                    fig.add_trace(go.Scatterpolar(r=values, theta=categories, fill='toself', name=strategy_name))
                
                fig.update_layout(polar=dict(radialaxis=dict(visible=True)), showlegend=True)
                st.plotly_chart(fig, use_container_width=True)
