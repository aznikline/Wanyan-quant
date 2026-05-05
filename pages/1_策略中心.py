import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from strategies import get_all_strategies, create_strategy
from data_loader import DataLoader
from config import BacktestConfig
from backtest_engine import BacktestEngine

st.set_page_config(page_title="策略中心 - Rock Quant", page_icon="📊", layout="wide")

st.title("📊 策略中心")
st.markdown("---")

# 策略分类
strategy_categories = {
    "趋势跟踪类": ["双均线策略", "MACD策略", "DMA平均线差策略", "TRIX三重指数策略", "均线多头发散策略", "唐奇安通道突破策略"],
    "震荡反转类": ["RSI超买超卖策略", "KDJ随机指标策略", "CCI顺势指标策略", "WR威廉指标策略", "MOM动量线策略", "ROC变动率策略", "BIAS乖离率策略"],
    "通道突破类": ["布林带突破策略", "肯特纳通道突破策略"],
    "量价配合类": ["成交量突破策略", "OBV能量潮策略", "VR容量比率策略", "EMV简易波动策略"],
    "趋势强弱类": ["DMI趋向指标策略"],
}

# 侧边栏分类选择
selected_category = st.sidebar.selectbox("选择策略分类", list(strategy_categories.keys()))

st.header(f"{selected_category}")
st.markdown("---")

# 展示该分类下的所有策略
for strategy_name in strategy_categories[selected_category]:
    with st.expander(f"📌 {strategy_name}", expanded=False):
        strategy = create_strategy(strategy_name)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("#### 策略原理")
            if "双均线": st.markdown("- 短期均线上穿长期均线买入，下穿卖出")
            elif "MACD" in strategy_name:
                st.markdown("- MACD金叉买入，死叉卖出")
            elif "RSI" in strategy_name:
                st.markdown("- RSI低于超卖区间买入，超买区间卖出")
            elif "KDJ" in strategy_name:
                st.markdown("- K线上穿D线金叉买入，下穿死叉卖出")
            elif "布林带" in strategy_name:
                st.markdown("- 价格突破上轨买入，跌破中轨卖出")
            elif "唐奇安" in strategy_name:
                st.markdown("- 价格突破N日最高点买入，跌破N日最低点卖出")
            elif "CCI" in strategy_name:
                st.markdown("- CCI突破+100买入，跌破-100卖出")
            elif "WR" in strategy_name:
                st.markdown("- WR低于20超卖买入，高于80超买卖出")
            elif "MOM" in strategy_name:
                st.markdown("- MOM由负转正买入，由正转负卖出")
            elif "ROC" in strategy_name:
                st.markdown("- ROC上穿零轴买入，下穿零轴卖出")
            elif "BIAS" in strategy_name:
                st.markdown("- 负乖离达到阈值买入，正乖离止盈")
            elif "DMA" in strategy_name:
                st.markdown("- DMA上穿AMA买入，下穿卖出")
            elif "TRIX" in strategy_name:
                st.markdown("- TRIX金叉买入，死叉卖出")
            elif "均线多头" in strategy_name:
                st.markdown("- 5/10/20/60均线多头发散买入")
            elif "肯特纳" in strategy_name:
                st.markdown("- 价格突破上轨买入，跌破下轨卖出")
            elif "成交量突破" in strategy_name:
                st.markdown("- 价格突破均线+成交量放大确认买入")
            elif "OBV" in strategy_name:
                st.markdown("- OBV创新高价格没新高背离买入")
            elif "VR" in strategy_name:
                st.markdown("- VR低于40极度缩量买入，高于350放量卖出")
            elif "EMV" in strategy_name:
                st.markdown("- EMV由负转正买入，由正转负卖出")
            elif "DMI" in strategy_name:
                st.markdown("- +DI上穿-DI买入，下穿卖出，ADX过滤")
        
        with col2:
            st.markdown("#### 适用场景")
            if selected_category == "趋势跟踪类":
                st.markdown("- ✅ 明确的单边上涨/下跌趋势")
                st.markdown("- ❌ 震荡行情容易来回打脸")
            elif selected_category == "震荡反转类":
                st.markdown("- ✅ 区间震荡行情")
                st.markdown("- ❌ 强趋势行情容易卖飞/抄底半山腰")
            elif selected_category == "通道突破类":
                st.markdown("- ✅ 横盘整理后突破")
                st.markdown("- ✅ 波动率突破行情")
            elif selected_category == "量价配合类":
                st.markdown("- ✅ 假突破过滤")
                st.markdown("- ✅ 主力资金隐藏吸货识别")
            elif selected_category == "趋势强弱类":
                st.markdown("- ✅ 过滤震荡假信号")
                st.markdown("- ✅ 趋势强度确认")
        
        st.markdown("---")
        
        # 参数配置
        st.markdown("#### 参数配置")
        params_schema = strategy.get_params_schema()
        params = {}
        param_cols = st.columns(min(3, len(params_schema) if len(params_schema) > 0 else 1))
        for i, (param_name, param_info) in enumerate(params_schema.items()):
            with param_cols[i % 3]:
                default = param_info.get("default", 14)
                min_val = param_info.get("min", 1)
                max_val = param_info.get("max", 120)
                params[param_name] = st.slider(f"{param_name}", min_value=min_val, max_value=max_val, value=default)
        
        st.markdown("---")
        
        # 回测按钮
        if st.button(f"🚀 运行回测", key=f"btn_{strategy_name}"):
            with st.spinner("正在回测..."):
                loader = DataLoader()
                data = loader.load_data("000001.SZ", "2020-01-01", "2023-12-31")
                config = BacktestConfig(initial_capital=1000000)
                engine = BacktestEngine(config)
                strategy_inst = create_strategy(strategy_name, **params)
                signals = strategy_inst.generate_signals(data)
                result = engine.run(data, signals)
                perf = result.performance
                
                st.markdown("#### 📈 回测结果")
                
                # 核心指标
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("总收益率", f"{perf['总收益率']:.2f}%")
                    st.metric("交易次数", perf['总交易次数'])
                with col2:
                    st.metric("年化收益率", f"{perf['年化收益率(CAGR)']:.2f}%")
                    st.metric("胜率", f"{perf['胜率']:.1f}%")
                with col3:
                    st.metric("夏普比率", f"{perf['夏普比率']:.2f}")
                    st.metric("盈亏比", perf['盈亏比'])
                with col4:
                    st.metric("最大回撤", f"{perf['最大回撤']:.2f}%")
                    st.metric("卡玛比率", f"{perf['卡玛比率']:.2f}")
                
                # 净值曲线
                st.markdown("#### 净值曲线")
                import plotly.graph_objects as go
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=result.equity_curve.index, y=result.equity_curve.values, name="策略净值", line=dict(color="#1f77b4", width=2)))
                fig.update_layout(height=400, hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)
                
                # 交易明细预览
                if len(result.trades) > 0:
                    st.markdown("#### 交易明细预览")
                    st.dataframe(result.trades.head(10), use_container_width=True)
