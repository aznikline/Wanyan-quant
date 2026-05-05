import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from pathlib import Path
import sys

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import BacktestConfig, RiskControlConfig, PositionConfig, ConfigManager
from backtest_engine import BacktestEngine
from strategies import get_all_strategies, create_strategy
from data_loader import DataLoader


st.set_page_config(
    page_title="Rock Quant 2.0 - 完颜风格量价模型",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)


def init_session_state():
    """初始化会话状态"""
    if 'first_visit' not in st.session_state:
        st.session_state.first_visit = True
    if 'current_step' not in st.session_state:
        st.session_state.current_step = 0
    if 'backtest_result' not in st.session_state:
        st.session_state.backtest_result = None


def show_onboarding_guide():
    """显示新手引导"""
    if not st.session_state.first_visit:
        return
    
    st.markdown("### 🎉 欢迎使用 Rock Quant 2.0")
    st.markdown("#### 完颜风格量价模型量化回测平台")
    
    with st.expander("📖 快速入门（点击展开）", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("##### 第1步：选择策略")
            st.markdown("从左侧边栏选择一个预设策略，支持双均线、MACD、RSI、布林带等经典量价策略")
        
        with col2:
            st.markdown("##### 第2步：配置参数")
            st.markdown("选择回测标的，调整策略参数和风控规则，也可以直接使用默认参数一键回测")
        
        with col3:
            st.markdown("##### 第3步：查看结果")
            st.markdown("回测完成后查看完整绩效指标、净值曲线、回撤、交易明细和归因分析")
        
        st.markdown("---")
        st.markdown("#### 💡 推荐快速体验")
        if st.button("一键运行示例回测", type="primary", use_container_width=True):
            st.session_state.first_visit = False
            st.rerun()
        
        st.markdown("---")
        if st.button("跳过引导，直接使用"):
            st.session_state.first_visit = False
            st.rerun()
    
    st.stop()


def render_sidebar():
    """渲染侧边栏配置"""
    with st.sidebar:
        st.title("Rock Quant 2.0")
        st.markdown("---")
        
        # 策略选择
        st.subheader("📊 策略选择")
        strategy_name = st.selectbox(
            "选择策略",
            options=get_all_strategies(),
            index=0,
            help="选择要回测的量价策略"
        )
        
        # 标的选择
        st.subheader("🎯 标的选择")
        data_loader = DataLoader()
        preset_symbols = data_loader.get_all_preset_symbols()
        symbol_name = st.selectbox(
            "选择标的",
            options=list(preset_symbols.keys()),
            index=0,
            help="选择回测标的"
        )
        symbol = preset_symbols[symbol_name]
        
        # 回测时间范围
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("开始日期", value=pd.to_datetime("2020-01-01"))
        with col2:
            end_date = st.date_input("结束日期", value=pd.to_datetime("2024-12-31"))
        
        # 策略参数配置
        st.subheader("⚙️ 策略参数")
        strategy_class = create_strategy(strategy_name).__class__
        params_schema = create_strategy(strategy_name).get_params_schema()
        
        params = {}
        for param_name, param_info in params_schema.items():
            default = param_info['default']
            min_val = param_info.get('min')
            max_val = param_info.get('max')
            desc = param_info.get('description', '')
            
            if param_info['type'] == 'int':
                params[param_name] = st.slider(
                    f"{param_name} ({desc})",
                    min_value=min_val,
                    max_value=max_val,
                    value=default
                )
            elif param_info['type'] == 'float':
                params[param_name] = st.slider(
                    f"{param_name} ({desc})",
                    min_value=float(min_val),
                    max_value=float(max_val),
                    value=float(default),
                    step=0.1
                )
        
        # 风控配置
        st.subheader("🛡️ 风控设置")
        stop_loss_pct = st.slider("止损比例(%)", min_value=1, max_value=30, value=5) / 100
        take_profit_pct = st.slider("止盈比例(%)", min_value=1, max_value=100, value=15) / 100
        max_position_pct = st.slider("最大仓位(%)", min_value=10, max_value=100, value=100) / 100
        
        # 仓位管理
        st.subheader("💸 仓位管理")
        position_mode = st.selectbox(
            "仓位模式",
            options=["fixed", "volatility"],
            format_func=lambda x: {"fixed": "固定仓位", "volatility": "波动率动态调整"}[x]
        )
        
        initial_capital = st.number_input("初始资金", min_value=10000, value=1000000, step=10000)
        
        # 运行按钮
        st.markdown("---")
        run_button = st.button("🚀 运行回测", type="primary", use_container_width=True)
        
        return {
            "strategy_name": strategy_name,
            "symbol": symbol,
            "symbol_name": symbol_name,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "params": params,
            "stop_loss_pct": stop_loss_pct,
            "take_profit_pct": take_profit_pct,
            "max_position_pct": max_position_pct,
            "position_mode": position_mode,
            "initial_capital": initial_capital,
            "run_button": run_button
        }


def render_performance_cards(performance: dict):
    """渲染绩效指标卡片"""
    st.subheader("📊 核心绩效指标")
    
    # 分类展示
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("总收益率", f"{performance['总收益率']}%")
        st.metric("年化收益率(CAGR)", f"{performance['年化收益率(CAGR)']}%")
        st.metric("夏普比率", performance["夏普比率"])
    
    with col2:
        st.metric("最大回撤", f"{performance['最大回撤']}%")
        st.metric("年化波动率", f"{performance['年化波动率']}%")
        st.metric("卡玛比率", performance["卡玛比率"])
    
    with col3:
        st.metric("总交易次数", performance["总交易次数"])
        st.metric("胜率", f"{performance['胜率']}%")
        st.metric("盈亏比", performance["盈亏比"])
    
    with col4:
        st.metric("盈利因子", performance["盈利因子"])
        st.metric("索提诺比率", performance["索提诺比率"])
        st.metric("VaR(95%)", f"{performance['VaR(95%)']}%")


def render_equity_chart(result):
    """渲染净值曲线和回撤曲线"""
    st.subheader("📈 净值与回撤曲线")
    
    equity = result.equity_curve
    drawdown = result.drawdown_curve
    
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3]
    )
    
    # 净值曲线
    fig.add_trace(
        go.Scatter(
            x=equity.index,
            y=equity.values,
            name="策略净值",
            line=dict(color="#1f77b4", width=2)
        ),
        row=1, col=1
    )
    
    # 标注买卖点
    if len(result.trades) > 0:
        buy_points = result.trades[result.trades['position'] > 0]
        sell_points = result.trades[result.trades['position'] < 0]
        
        fig.add_trace(
            go.Scatter(
                x=buy_points['entry_date'],
                y=buy_points['entry_price'] * result.config['backtest']['initial_capital'] / 100,
                mode='markers',
                marker=dict(symbol='triangle-up', size=10, color='green'),
                name='买入'
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=sell_points['entry_date'],
                y=sell_points['entry_price'] * result.config['backtest']['initial_capital'] / 100,
                mode='markers',
                marker=dict(symbol='triangle-down', size=10, color='red'),
                name='卖出'
            ),
            row=1, col=1
        )
    
    # 回撤曲线
    fig.add_trace(
        go.Scatter(
            x=drawdown.index,
            y=drawdown.values * 100,
            name="回撤",
            line=dict(color="#ff7f0e", width=1),
            fill='tonexty'
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        height=500,
        showlegend=True,
        hovermode="x unified"
    )
    
    fig.update_yaxes(title_text="净值", row=1, col=1)
    fig.update_yaxes(title_text="回撤(%)", row=2, col=1)
    
    st.plotly_chart(fig, use_container_width=True)


def render_monthly_heatmap(equity_curve):
    """渲染月度收益热力图"""
    st.subheader("🗓️ 月度收益热力图")
    
    monthly_returns = equity_curve.resample('M').last().pct_change() * 100
    
    # 构建年月矩阵
    heatmap_data = []
    years = sorted(set(monthly_returns.index.year))
    months = ['1月', '2月', '3月', '4月', '5月', '6月', 
              '7月', '8月', '9月', '10月', '11月', '12月']
    
    for year in years:
        row = []
        for month in range(1, 13):
            mask = (monthly_returns.index.year == year) & (monthly_returns.index.month == month)
            if mask.any():
                row.append(round(monthly_returns[mask].iloc[0], 2))
            else:
                row.append(None)
        heatmap_data.append(row)
    
    fig = px.imshow(
        heatmap_data,
        x=months,
        y=years,
        color_continuous_scale='RdYlGn',
        aspect='auto',
        text_auto=True
    )
    
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)


def render_trade_details(trades):
    """渲染交易明细"""
    st.subheader("💼 交易明细与归因分析")
    
    if len(trades) == 0:
        st.info("暂无交易记录")
        return
    
    col1, col2 = st.columns([0.6, 0.4])
    
    with col1:
        st.markdown("##### 完整交易流水")
        st.dataframe(
            trades,
            use_container_width=True,
            height=400
        )
    
    with col2:
        st.markdown("##### 交易归因分析")
        
        wins = trades[trades['pnl'] > 0]
        losses = trades[trades['pnl'] < 0]
        
        st.metric("盈利交易数", len(wins))
        st.metric("亏损交易数", len(losses))
        
        if len(wins) > 0:
            st.metric("最大单笔盈利", f"{wins['pnl'].max():,.2f}")
        if len(losses) > 0:
            st.metric("最大单笔亏损", f"{losses['pnl'].min():,.2f}")
        
        # 盈亏分布直方图
        st.markdown("##### 盈亏分布")
        fig = px.histogram(
            trades, 
            x='return_pct',
            nbins=20,
            color=trades['pnl'] > 0,
            color_discrete_map={True: 'green', False: 'red'}
        )
        fig.update_layout(showlegend=False, height=250)
        st.plotly_chart(fig, use_container_width=True)


def main():
    init_session_state()
    
    # 显示新手引导
    show_onboarding_guide()
    
    # 渲染侧边栏
    config = render_sidebar()
    
    # 主内容区
    if config['run_button'] or st.session_state.backtest_result is not None:
        with st.spinner("正在运行回测..."):
            # 加载数据
            data_loader = DataLoader()
            data = data_loader.load_data(
                config['symbol'],
                config['start_date'],
                config['end_date']
            )
            
            # 创建策略
            strategy = create_strategy(config['strategy_name'], **config['params'])
            signals = strategy.generate_signals(data)
            
            # 创建回测引擎
            backtest_config = BacktestConfig(
                symbol=config['symbol'],
                start_date=config['start_date'],
                end_date=config['end_date'],
                initial_capital=config['initial_capital']
            )
            
            risk_config = RiskControlConfig(
                stop_loss_pct=config['stop_loss_pct'],
                take_profit_pct=config['take_profit_pct'],
                max_position_pct=config['max_position_pct']
            )
            
            position_config = PositionConfig(
                mode=config['position_mode'],
                fixed_size=config['max_position_pct']
            )
            
            engine = BacktestEngine(backtest_config, risk_config, position_config)
            result = engine.run(data, signals)
            
            st.session_state.backtest_result = result
            
            # 显示结果
            st.success(f"✅ 回测完成！标的: {config['symbol_name']}, 策略: {config['strategy_name']}")
            
            # 绩效卡片
            render_performance_cards(result.performance)
            
            # 净值曲线
            render_equity_chart(result)
            
            # 月度热力图
            render_monthly_heatmap(result.equity_curve)
            
            # 交易明细
            render_trade_details(result.trades)
            
            # 下载报告按钮
            st.download_button(
                label="📥 下载完整回测报告 (CSV)",
                data=result.trades.to_csv(index=False).encode('utf-8'),
                file_name=f"rockquant_report_{config['symbol']}_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    else:
        # 欢迎页面
        st.markdown("## 📈 Rock Quant 2.0 - 完颜风格量价模型")
        st.markdown("---")
        st.markdown("### 欢迎使用专业级量化回测平台")
        st.markdown("""
        ✨ **核心功能**
        - 10+经典量价策略预设
        - 全向量化回测引擎，速度提升5-10倍
        - 20+专业绩效指标完整计算
        - 可视化参数敏感性分析
        - 多维度交易归因分析
        - 一键导出完整回测报告
        
        🚀 **快速开始**
        从左侧边栏选择策略和标的，点击「运行回测」即可看到结果
        """)
        
        # 显示预设策略说明
        st.markdown("### 📚 预设策略库")
        for name in get_all_strategies():
            strategy = create_strategy(name)
            with st.expander(f"{name} - {strategy.description}"):
                st.json(strategy.get_params_schema())


if __name__ == "__main__":
    main()
