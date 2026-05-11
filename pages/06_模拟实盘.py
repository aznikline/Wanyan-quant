import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import BacktestConfig
from backtest_engine import BacktestEngine
from strategies import get_all_strategies, create_strategy
from data_loader import DataLoader

st.set_page_config(
    page_title="模拟实盘 - Rock Quant",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 全局初始化
loader = DataLoader()
preset_symbols = list(loader.preset_symbols.keys())
all_strategies = get_all_strategies()

# 模拟实盘状态持久化
if 'paper_trading' not in st.session_state:
    st.session_state.paper_trading = {
        'positions': {},          # 持仓：symbol -> {size, entry_price, entry_time, strategy}
        'cash': 1000000,         # 可用资金
        'history': [],            # 交易历史
        'total_pnl': 0,           # 累计盈亏
        'win_count': 0,           # 盈利次数
        'loss_count': 0,          # 亏损次数
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

pt = st.session_state.paper_trading

st.title("模拟实盘交易")
st.markdown("基于实时信号的模拟交易系统，验证策略实盘表现，零风险体验量化交易")

# ========== 侧边栏：账户概览 ==========
with st.sidebar:
    st.header("账户概览")
    
    total_assets = pt['cash']
    for symbol, pos in pt['positions'].items():
        # 使用最新收盘价计算市值
        if symbol in loader.preset_symbols:
            try:
                latest_data = loader.load_data(loader.preset_symbols[symbol], 
                                               str(datetime.now().date() - timedelta(days=30)),
                                               str(datetime.now().date()))
                if len(latest_data) > 0:
                    latest_price = latest_data.iloc[-1]['close']
                    market_value = abs(pos['size']) * latest_price
                    total_assets += market_value
            except:
                pass
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("总资产", f"¥{total_assets:,.0f}")
    with col2:
        total_return = (total_assets - 1000000) / 1000000 * 100
        st.metric("累计收益率", f"{total_return:+.2f}%", delta_color="normal")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("可用资金", f"¥{pt['cash']:,.0f}")
    with col2:
        total_trades = pt['win_count'] + pt['loss_count']
        win_rate = pt['win_count'] / total_trades * 100 if total_trades > 0 else 0
        st.metric("交易胜率", f"{win_rate:.1f}%")
    
    st.metric("持仓数量", f"{len(pt['positions'])} 只")
    
    st.markdown("---")
    st.subheader("操作")
    if st.button("重置账户", type="secondary", use_container_width=True):
        st.session_state.paper_trading = {
            'positions': {},
            'cash': 1000000,
            'history': [],
            'total_pnl': 0,
            'win_count': 0,
            'loss_count': 0,
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        st.success("账户已重置")
        st.rerun()

# ========== 主内容区 ==========
tab1, tab2, tab3, tab4 = st.tabs(["📊 实时信号", "💼 当前持仓", "📜 交易历史", "⚙️ 策略配置"])

with tab1:
    st.subheader("实时交易信号")
    
    # 配置监控股票池
    monitor_symbols = st.multiselect(
        "选择监控股票池",
        preset_symbols,
        default=["沪深300", "中证500", "上证指数", "创业板指"],
        max_selections=10
    )
    
    monitor_strategy = st.selectbox("选择交易策略", all_strategies, index=0)
    lookback_days = st.slider("回看天数", 30, 365, 120)
    
    if st.button("扫描最新信号", type="primary"):
        if len(monitor_symbols) == 0:
            st.warning("请至少选择一只监控标的")
        else:
            signal_results = []
            strategy = create_strategy(monitor_strategy)
            
            progress = st.progress(0)
            for idx, symbol in enumerate(monitor_symbols):
                try:
                    end_date = datetime.now().date()
                    start_date = end_date - timedelta(days=lookback_days)
                    data = loader.load_data(loader.preset_symbols[symbol], str(start_date), str(end_date))
                    
                    if len(data) < 30:
                        continue
                    
                    signals = strategy.generate_signals(data)
                    latest_signal = signals.iloc[-1]
                    prev_signal = signals.iloc[-2] if len(signals) > 1 else 0
                    
                    # 判断信号类型
                    if latest_signal != prev_signal:
                        if latest_signal > 0 and prev_signal <= 0:
                            signal_type = "🟢 买入信号"
                        elif latest_signal < 0 and prev_signal >= 0:
                            signal_type = "🔴 卖出/做空信号"
                        else:
                            signal_type = "⚪ 仓位调整"
                        is_new = True
                    else:
                        if latest_signal > 0:
                            signal_type = "🟢 持有多头"
                        elif latest_signal < 0:
                            signal_type = "🔴 持有空头"
                        else:
                            signal_type = "⚪ 空仓观望"
                        is_new = False
                    
                    latest_price = data.iloc[-1]['close']
                    price_change = (latest_price / data.iloc[-2]['close'] - 1) * 100 if len(data) > 1 else 0
                    
                    signal_results.append({
                        "标的": symbol,
                        "信号": signal_type,
                        "最新信号": is_new,
                        "最新价格": round(latest_price, 2),
                        "日涨跌%": round(price_change, 2),
                        "持仓方向": "多头" if latest_signal > 0 else "空头" if latest_signal < 0 else "空仓",
                        "信号日期": data.index[-1].strftime("%Y-%m-%d")
                    })
                    
                except Exception as e:
                    st.warning(f"{symbol} 数据加载失败: {str(e)}")
                
                progress.progress((idx + 1) / len(monitor_symbols))
            
            progress.empty()
            
            if len(signal_results) > 0:
                df = pd.DataFrame(signal_results)
                
                # 高亮最新信号
                def highlight_new(row):
                    if row['最新信号']:
                        return ['background-color: #fff3cd'] * len(row)
                    return [''] * len(row)
                
                df_styled = df.style.apply(highlight_new, axis=1)
                st.dataframe(df_styled, use_container_width=True, hide_index=True)
                
                # 快捷交易按钮
                st.subheader("一键模拟交易")
                for result in signal_results:
                    if result['最新信号'] and "买入" in result['信号']:
                        if st.button(f"买入 {result['标的']} @ ¥{result['最新价格']}", 
                                   type="primary", key=f"buy_{result['标的']}"):
                            symbol = result['标的']
                            price = result['最新价格']
                            # 使用30%资金买入
                            position_value = pt['cash'] * 0.3
                            position_size = int(position_value / price / 100) * 100  # 整手买入
                            
                            if position_size > 0 and pt['cash'] >= position_size * price:
                                pt['positions'][symbol] = {
                                    'size': position_size,
                                    'entry_price': price,
                                    'entry_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    'strategy': monitor_strategy
                                }
                                pt['cash'] -= position_size * price
                                pt['history'].append({
                                    'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    'symbol': symbol,
                                    'action': '买入',
                                    'size': position_size,
                                    'price': price,
                                    'amount': position_size * price,
                                    'strategy': monitor_strategy
                                })
                                st.success(f"模拟买入成功：{symbol} {position_size}股 @ ¥{price}")
                                st.rerun()
            else:
                st.info("当前没有检测到有效信号")

with tab2:
    st.subheader("当前持仓")
    
    if len(pt['positions']) == 0:
        st.info("当前没有持仓")
    else:
        position_data = []
        for symbol, pos in pt['positions'].items():
            # 获取最新价格
            try:
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=7)
                data = loader.load_data(loader.preset_symbols[symbol], str(start_date), str(end_date))
                latest_price = data.iloc[-1]['close'] if len(data) > 0 else pos['entry_price']
            except:
                latest_price = pos['entry_price']
            
            market_value = abs(pos['size']) * latest_price
            pnl = (latest_price - pos['entry_price']) * pos['size']
            pnl_pct = (latest_price / pos['entry_price'] - 1) * 100
            
            position_data.append({
                "标的": symbol,
                "持仓数量": abs(pos['size']),
                "持仓方向": "多头" if pos['size'] > 0 else "空头",
                "入场价格": round(pos['entry_price'], 2),
                "最新价格": round(latest_price, 2),
                "持仓市值": round(market_value, 0),
                "浮动盈亏": round(pnl, 2),
                "盈亏%": round(pnl_pct, 2),
                "入场时间": pos['entry_time'],
                "使用策略": pos['strategy']
            })
        
        df = pd.DataFrame(position_data)
        
        def highlight_pnl(row):
            if row['浮动盈亏'] > 0:
                return ['background-color: #d4edda' if '盈亏' in col or '盈亏%' in col else '' for col in df.columns]
            elif row['浮动盈亏'] < 0:
                return ['background-color: #f8d7da' if '盈亏' in col or '盈亏%' in col else '' for col in df.columns]
            return [''] * len(df.columns)
        
        df_styled = df.style.apply(highlight_pnl, axis=1)
        st.dataframe(df_styled, use_container_width=True, hide_index=True)
        
        # 平仓操作
        st.subheader("平仓操作")
        close_symbol = st.selectbox("选择平仓标的", list(pt['positions'].keys()))
        if close_symbol and st.button("全部平仓", type="primary"):
            pos = pt['positions'][close_symbol]
            try:
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=7)
                data = loader.load_data(loader.preset_symbols[close_symbol], str(start_date), str(end_date))
                exit_price = data.iloc[-1]['close'] if len(data) > 0 else pos['entry_price']
            except:
                exit_price = pos['entry_price']
            
            pnl = (exit_price - pos['entry_price']) * pos['size']
            amount = abs(pos['size']) * exit_price
            
            pt['cash'] += amount
            pt['total_pnl'] += pnl
            
            if pnl > 0:
                pt['win_count'] += 1
            else:
                pt['loss_count'] += 1
            
            pt['history'].append({
                'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'symbol': close_symbol,
                'action': '卖出平仓',
                'size': abs(pos['size']),
                'price': exit_price,
                'amount': amount,
                'pnl': pnl,
                'strategy': pos['strategy']
            })
            
            del pt['positions'][close_symbol]
            
            st.success(f"平仓成功：{close_symbol}，盈亏: ¥{pnl:+.2f}")
            st.rerun()

with tab3:
    st.subheader("交易历史")
    
    if len(pt['history']) == 0:
        st.info("暂无交易记录")
    else:
        df = pd.DataFrame(pt['history'])
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # 统计分析
        if len(pt['history']) >= 2:
            st.subheader("交易统计")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("总交易次数", len(pt['history']))
            with col2:
                win_rate = pt['win_count'] / (pt['win_count'] + pt['loss_count']) * 100 if (pt['win_count'] + pt['loss_count']) > 0 else 0
                st.metric("胜率", f"{win_rate:.1f}%")
            with col3:
                st.metric("盈利次数", pt['win_count'])
            with col4:
                st.metric("亏损次数", pt['loss_count'])

with tab4:
    st.subheader("策略参数配置")
    
    config_strategy = st.selectbox("配置策略", all_strategies, key="config_strategy")
    strategy = create_strategy(config_strategy)
    param_schema = strategy.get_params_schema()
    
    st.markdown(f"**{config_strategy} 参数配置**")
    for param_name, param_config in param_schema.items():
        param_type = param_config.get('type', 'int')
        param_default = param_config.get('default', 20)
        param_min = param_config.get('min', 1)
        param_max = param_config.get('max', 200)
        
        if param_type == 'int':
            val = st.slider(param_name, min_value=param_min, max_value=param_max, value=param_default)
        elif param_type == 'float':
            val = st.slider(param_name, min_value=float(param_min), max_value=float(param_max), value=float(param_default))
        
        setattr(strategy, param_name, val)
    
    st.info("参数配置将在下次信号扫描时生效")

# 底部风险提示
st.markdown("---")
st.caption("⚠️ 风险提示：模拟实盘仅供策略验证和学习使用，不构成实盘投资建议。历史回测表现不代表未来收益，投资有风险，入市需谨慎。")
