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

st.set_page_config(page_title="参数敏感性分析 - Rock Quant", page_icon="📊", layout="wide")

st.title("参数敏感性分析")
st.markdown("---")

# 选择策略和标的
col1, col2 = st.columns(2)
with col1:
    strategy_name = st.selectbox("选择策略", get_all_strategies(), index=0)
with col2:
    loader = DataLoader()
    preset_symbols = list(loader.preset_symbols.keys())
    symbol_name = st.selectbox("选择回测标的", preset_symbols, index=0)

st.markdown("---")

# 获取策略参数
strategy = create_strategy(strategy_name)
params_schema = strategy.get_params_schema()

if len(params_schema) == 0:
    st.info("该策略没有可调节参数")
else:
    st.subheader("选择要扫描的参数范围")
    
    param_ranges = {}
    for param_name, param_info in params_schema.items():
        st.markdown(f"**{param_name}")
        col_a, col_b = st.columns(2)
        default_min = param_info.get('min', 1)
        default_max = param_info.get('max', 100)
        default_val = param_info.get('default', 14)
        with col_a:
            min_val = st.number_input(f"最小值", value=default_min, key=f"{param_name}_min")
        with col_b:
            max_val = st.number_input(f"最大值", value=default_max, key=f"{param_name}_max")
        step = st.number_input(f"步长", value=max(1, int(default_val/5), key=f"{param_name}_step")
        param_ranges[param_name] = (int(min_val), int(max_val), int(step))
        st.markdown("---")

if st.button("开始参数扫描", type="primary"):
    with st.spinner("正在参数扫描..."):
        # 加载数据
        symbol_code = loader.preset_symbols[symbol_name]
        data = loader.load_data(symbol_code, "2020-01-01", "2023-12-31")
        config = BacktestConfig(initial_capital=1000000)
        engine = BacktestEngine(config)
        
        # 单参数扫描
        if len(param_ranges) == 1:
            param_name = list(param_ranges.keys())[0]
            min_val, max_val, step = param_ranges[param_name]
            
            results = []
            values = list(range(min_val, max_val + step, step))
            
            progress_bar = st.progress(0)
            for i, val in enumerate(values):
                strategy = create_strategy(strategy_name, **{param_name: val})
                signals = strategy.generate_signals(data)
                result = engine.run(data, signals)
                perf = result.performance
                results.append({
                    param_name: val,
                    "总收益率": perf['总收益率'],
                    "夏普比率": perf['夏普比率'],
                    "最大回撤": perf['最大回撤'],
                    "胜率": perf['胜率'],
                    "交易次数": perf['总交易次数'],
                })
                progress_bar.progress((i + 1) / len(values))
            
            df = pd.DataFrame(results)
            
            st.subheader("📊 单参数敏感性分析结果")
            st.dataframe(df, use_container_width=True)
            
            # 绘制多指标对比图
            st.subheader("📈 参数影响趋势")
            fig = make_subplots(rows=2, cols=2, subplot_titles=("总收益率", "夏普比率", "最大回撤", "胜率"))
            
            fig.add_trace(go.Scatter(x=df[param_name], y=df["总收益率"], name="总收益率"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df[param_name], y=df["夏普比率"], name="夏普比率"), row=1, col=2)
            fig.add_trace(go.Scatter(x=df[param_name], y=df["最大回撤"], name="最大回撤"), row=2, col=1)
            fig.add_trace(go.Scatter(x=df[param_name], y=df["胜率"], name="胜率"), row=2, col=2)
            
            fig.update_layout(height=600)
            st.plotly_chart(fig, use_container_width=True)
            
            # 最佳参数推荐
            st.subheader("🎯 最佳参数推荐")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                best_return = df.loc[df["总收益率"].idxmax()]
                st.metric("收益最大化参数", f"{best_return[param_name]}", f"{best_return['总收益率']:.2f}%")
            with col2:
                best_sharpe = df.loc[df["夏普比率"].idxmax()]
                st.metric("夏普最大化参数", f"{best_sharpe[param_name]}", f"{best_sharpe['夏普比率']:.2f}")
            with col3:
                best_dd = df.loc[df["最大回撤"].idxmax()] # 注意这里取最大回撤绝对值最小
                st.metric("回撤最小化参数", f"{best_dd[param_name]}", f"{best_dd['最大回撤']:.2f}%")
            with col4:
                best_win = df.loc[df["胜率"].idxmax()]
                st.metric("胜率最大化参数", f"{best_win[param_name]}", f"{best_win['胜率']:.1f}%")
        
        # 双参数热力图
        elif len(param_ranges) == 2:
            param_names = list(param_ranges.keys())
            p1_min, p1_max, p1_step = param_ranges[param_names[0]]
            p2_min, p2_max, p2_step = param_ranges[param_names[1]]
            
            p1_values = list(range(p1_min, p1_max + p1_step, p1_step))
            p2_values = list(range(p2_min, p2_max + p2_step, p2_step))
            
            heatmap_data = []
            
            total = len(p1_values) * len(p2_values)
            progress_bar = st.progress(0)
            count = 0
            
            for p1 in p1_values:
                row = []
                for p2 in p2_values:
                    strategy = create_strategy(strategy_name, **{param_names[0]: p1, param_names[1]: p2})
                    signals = strategy.generate_signals(data)
                    result = engine.run(data, signals)
                    perf = result.performance
                    row.append(perf['夏普比率'])
                    count += 1
                    progress_bar.progress(count / total)
                heatmap_data.append(row)
            
            st.subheader("🔥 双参数敏感性热力图 (夏普比率)")
            df_heatmap = pd.DataFrame(heatmap_data, index=p1_values, columns=p2_values)
            
            fig = px.imshow(df_heatmap, 
                          labels=dict(x=param_names[1], y=param_names[0], color="夏普比率"),
                          x=p2_values,
                          y=p1_values,
                          color_continuous_scale='RdYlGn',
                          aspect='auto')
            fig.update_layout(height=600)
            st.plotly_chart(fig, use_container_width=True)
            
            # 找出最优参数组合
            flat_data = []
            for i, p1 in enumerate(p1_values):
                for j, p2 in enumerate(p2_values):
                    flat_data.append({
                        param_names[0]: p1,
                        param_names[1]: p2,
                        "夏普比率": heatmap_data[i][j]
                    })
            
            flat_df = pd.DataFrame(flat_data)
            best = flat_df.loc[flat_df["夏普比率"].idxmax()]
            
            st.subheader("🎯 最优参数组合")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(param_names[0], best[param_names[0]])
            with col2:
                st.metric(param_names[1], best[param_names[1]])
            with col3:
                st.metric("最佳夏普比率", f"{best['夏普比率']:.2f}")
        
        else:
            st.info("当前支持最多2个参数的敏感性分析")
