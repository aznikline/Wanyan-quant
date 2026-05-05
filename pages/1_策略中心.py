import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.strategies import get_all_strategies, create_strategy
from src.data_loader import DataLoader
from src.config import BacktestConfig
from src.backtest_engine import BacktestEngine
from strategy_docs import get_strategy_doc

st.set_page_config(page_title="策略深度百科 - Rock Quant", page_icon="📚", layout="wide")

st.title("📚 策略深度百科")
st.markdown("每个策略都包含完整的原理说明、公式推导、实盘经验、常见陷阱、改进方向")
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
    doc = get_strategy_doc(strategy_name)
    
    with st.expander(f"📌 {strategy_name} {'✅ 深度百科已上线' if doc else '⏳ 深度百科编写中'}", expanded=False):
        if doc:
            # 策略基本信息
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f"**中文名称：** {doc['name_cn']}")
            with col2:
                st.markdown(f"**英文名称：** {doc['name_en']}")
            with col3:
                st.markdown(f"**发明者：** {doc['inventor']}")
            with col4:
                st.markdown(f"**发明年份：** {doc['year']}")
            
            st.markdown("---")
            
            tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                "📖 核心原理", 
                "📐 完整公式", 
                "✅ 优缺点", 
                "🎯 适用&失效场景", 
                "💡 实盘经验", 
                "⚠️ 常见陷阱"
            ])
            
            with tab1:
                st.markdown("### 核心原理")
                st.markdown(doc['core_principle'])
            
            with tab2:
                st.markdown("### 完整公式与经典用法")
                st.markdown(doc['formula'])
            
            with tab3:
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("### ✅ 核心优势")
                    for adv in doc['advantages']:
                        st.markdown(f"- {adv}")
                with col2:
                    st.markdown("### ❌ 固有缺陷")
                    for disadv in doc['disadvantages']:
                        st.markdown(f"- {disadv}")
            
            with tab4:
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("### ✅ 适用行情")
                    for s in doc['适用_scenarios']:
                        st.markdown(f"- {s}")
                with col2:
                    st.markdown("### ❌ 失效行情")
                    for f in doc['failure_scenarios']:
                        st.markdown(f"- {f}")
            
            with tab5:
                st.markdown("### 💡 实盘经验与参数建议")
                for tip in doc['real_trade_tips']:
                    st.markdown(f"- {tip}")
                st.markdown("")
                st.info("💡 以上均为实盘踩坑总结，不是书本理论")
            
            with tab6:
                st.markdown("### ⚠️ 常见陷阱与避坑指南")
                for pitfall in doc['common_pitfalls']:
                    st.markdown(f"{pitfall}")
                st.markdown("")
                st.markdown("### 🚀 改进与优化方向")
                for imp in doc['improvement_directions']:
                    st.markdown(f"- {imp}")
            
            st.markdown("---")
        else:
            st.info("该策略深度百科正在编写中，敬请期待...")
            st.markdown("---")
        
        # 参数配置与回测区
        st.markdown("### ⚙️ 参数配置与回测")
        strategy = create_strategy(strategy_name)
        params_schema = strategy.get_params_schema()
        params = {}
        param_cols = st.columns(min(3, len(params_schema)) if len(params_schema) > 0 else 1)
        for i, (param_name, param_info) in enumerate(params_schema.items()):
            with param_cols[i % 3]:
                default = param_info.get('default', 14)
                min_val = param_info.get('min', 1)
                max_val = param_info.get('max', 120)
                params[param_name] = st.slider(f"{param_name}", min_value=min_val, max_value=max_val, value=default, key=f"slider_{strategy_name}_{param_name}")
        
        st.markdown("---")
        
        if st.button(f"🚀 运行回测 - {strategy_name}", key=f"btn_{strategy_name}"):
            with st.spinner("正在回测..."):
                loader = DataLoader()
                data = loader.load_data("000001.SZ", "2020-01-01", "2023-12-31")
                config = BacktestConfig(initial_capital=1000000)
                engine = BacktestEngine(config)
                strategy_inst = create_strategy(strategy_name, **params)
                signals = strategy_inst.generate_signals(data)
                result = engine.run(data, signals)
                perf = result.performance
                
                st.markdown("### 📊 回测结果")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("总收益率", f"{perf['总收益率']:.2f}%")
                    st.metric("交易次数", perf['总交易次数'])
                with col2:
                    st.metric("年化收益率", f"{perf['年化收益率(CAGR)']:.2f}%")
                    st.metric("胜率", f"{perf['胜率']:.1f}%")
                with col3:
                    st.metric("夏普比率", f"{perf['夏普比率']:.2f}")
                    st.metric("盈亏比", f"{perf['盈亏比']:.1f}")
                with col4:
                    st.metric("最大回撤", f"{perf['最大回撤']:.2f}%")
                    st.metric("卡玛比率", f"{perf['卡玛比率']:.2f}")
                
                import plotly.graph_objects as go
                
                st.markdown("### 📈 净值曲线")
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=result.equity_curve.index, y=result.equity_curve.values, name="策略净值", line=dict(color="#1f77b4", width=2)))
                fig.update_layout(height=400, hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)
                
                # 回测结果解读
                st.markdown("### 📝 结果专业解读")
                
                interpretation = []
                if perf['总收益率'] > 20:
                    interpretation.append("✅ **收益表现优秀**：该参数组合在回测期内收益显著，具备实战价值")
                elif perf['总收益率'] > 0:
                    interpretation.append("⚠️ **收益表现一般**：该参数组合能赚钱但不突出，建议优化参数")
                else:
                    interpretation.append("❌ **收益表现较差**：该参数组合在回测期内亏损，不建议实盘使用")
                
                if perf['夏普比率'] > 1.5:
                    interpretation.append("✅ **风险收益比优秀**：夏普比率>1.5，每承担1单位风险获得1.5单位以上收益")
                elif perf['夏普比率'] > 0.8:
                    interpretation.append("⚠️ **风险收益比一般**：夏普比率在0.8-1.5之间，还有优化空间")
                else:
                    interpretation.append("❌ **风险收益比较差**：夏普比率<0.8，承担的风险没有获得足够补偿")
                
                if perf['胜率'] > 50:
                    interpretation.append(f"✅ **胜率优秀**：胜率{perf['胜率']:.1f}%，超过50%意味着多数交易赚钱")
                elif perf['胜率'] > 35:
                    interpretation.append(f"⚠️ **胜率正常**：胜率{perf['胜率']:.1f}%，趋势跟踪策略的典型胜率区间")
                else:
                    interpretation.append(f"❌ **胜率较低**：胜率{perf['胜率']:.1f}%，需要更高的盈亏比才能盈利")
                
                if abs(perf['最大回撤']) < 15:
                    interpretation.append(f"✅ **回撤控制良好**：最大回撤{perf['最大回撤']:.2f}%，大多数人可以接受")
                elif abs(perf['最大回撤']) < 30:
                    interpretation.append(f"⚠️ **回撤较大**：最大回撤{perf['最大回撤']:.2f}%，需要较强的心理承受能力")
                else:
                    interpretation.append(f"❌ **回撤过大**：最大回撤{perf['最大回撤']:.2f}%，实盘很可能坚持不下来")
                
                if perf['盈亏比'] > 2:
                    interpretation.append(f"✅ **盈亏比优秀**：盈亏比{perf['盈亏比']:.1f}，赚一次够亏两次以上")
                elif perf['盈亏比'] > 1:
                    interpretation.append(f"⚠️ **盈亏比一般**：盈亏比{perf['盈亏比']:.1f}，需要配合较高胜率才能盈利")
                else:
                    interpretation.append(f"❌ **盈亏比较差**：盈亏比{perf['盈亏比']:.1f}，长期来看很难盈利")
                
                for item in interpretation:
                    st.markdown(item)
                
                # 改进建议
                st.markdown("")
                st.markdown("### 🎯 改进建议")
                
                suggestions = []
                if perf['胜率'] < 40:
                    suggestions.append("- 建议增加趋势过滤条件，比如ADX>25才交易，过滤震荡期假信号")
                    suggestions.append("- 建议提高交易时间周期级别，日线信号比小时线噪音少")
                if abs(perf['最大回撤']) > 25:
                    suggestions.append("- 建议降低单笔仓位，或者加入止损机制控制回撤")
                    suggestions.append("- 建议多策略分散投资，降低单一策略的波动影响")
                if perf['夏普比率'] < 1:
                    suggestions.append("- 建议进行参数敏感性分析，找到更优的参数区间")
                    suggestions.append("- 建议测试其他标的，该策略可能更适合其他类型的资产")
                if perf['总交易次数'] > 100:
                    suggestions.append("- 交易过于频繁，建议调大参数周期，降低交易频率和滑点成本")
                if perf['总交易次数'] < 10:
                    suggestions.append("- 交易次数过少，统计显著性不足，回测结果参考价值有限")
                
                if suggestions:
                    for s in suggestions:
                        st.markdown(s)
                else:
                    st.markdown("- 该参数组合各项指标均衡，已具备实盘测试价值")
                
                # 交易明细预览
                if len(result.trades) > 0:
                    st.markdown("---")
                    st.markdown("### 📋 最近10笔交易明细")
                    recent_trades = result.trades.tail(10).copy()
                    recent_trades['盈亏(万元)'] = (recent_trades['盈亏金额'] / 10000).round(2)
                    recent_trades['持仓天数'] = (recent_trades['出场时间'] - recent_trades['入场时间']).dt.days
                    display_cols = ['入场时间', '出场时间', '方向', '入场价格', '出场价格', '盈亏(万元)', '持仓天数']
                    st.dataframe(recent_trades[display_cols], use_container_width=True)

st.markdown("---")
st.caption("💡 深度百科持续更新中，优先完善5大核心策略：双均线、MACD、RSI、布林带、唐奇安通道")
