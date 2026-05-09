import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import BacktestConfig
from backtest_engine import BacktestEngine
from strategies import get_all_strategies, create_strategy
from data_loader import DataLoader

st.set_page_config(
    page_title="策略回测 - Rock Quant",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== 全局初始化 - 放在最前面避免作用域问题 ==========
loader = DataLoader()
preset_symbols = list(loader.preset_symbols.keys())
all_strategies = get_all_strategies()

st.title(" 策略回测")
st.caption("单策略回测与深度绩效分析")

# ========== 数据源选择 ==========
col_data1, col_data2 = st.columns([3, 1])
with col_data1:
    data_sources = [
        ("模拟数据", "simulated"),
        ("Akshare 免费实盘数据", "akshare"),
        ("Tushare 专业数据", "tushare"),
    ]
    source_labels = [s[0] for s in data_sources]
    source_codes = [s[1] for s in data_sources]
    
    default_source_idx = source_codes.index(st.session_state.get('data_source', 'simulated')) if st.session_state.get('data_source', 'simulated') in source_codes else 0
    selected_source_label = st.selectbox("选择数据源", source_labels, index=default_source_idx, key="data_source_select")
    selected_source = source_codes[source_labels.index(selected_source_label)]
    st.session_state['data_source'] = selected_source
    
    # Tushare Token输入
    if selected_source == 'tushare':
        tushare_token = st.text_input("Tushare Token", type="password", 
                                      value=st.session_state.get('tushare_token', ''),
                                      help="请输入您的 Tushare Token，可在 https://tushare.pro/user/token 获取")
        st.session_state['tushare_token'] = tushare_token
        loader.set_tushare_token(tushare_token)
    
    loader.set_data_source(selected_source)
    
    # 检查数据源可用性
    available, msg = loader.check_data_source_available(selected_source)
    if not available:
        st.warning(f" {msg}")
    elif selected_source == 'simulated':
        st.info(" 当前使用模拟数据进行演示，真实数据可选择 Akshare 或 Tushare")
    else:
        st.success(f" 数据源已切换至 {selected_source_label}")
    
    st.markdown("---")

st.markdown("---")

# ========== 快速参数处理 ==========
# 从首页快速开始按钮传过来的参数
default_strategy = 0
default_symbol = 0
auto_run = False

if 'quick_strategy' in st.session_state and st.session_state.quick_strategy in all_strategies:
    default_strategy = all_strategies.index(st.session_state.quick_strategy)
    auto_run = True  # 从快速开始进来，自动回测
    
if 'quick_symbol' in st.session_state and st.session_state.quick_symbol in preset_symbols:
    default_symbol = preset_symbols.index(st.session_state.quick_symbol)

# ========== 侧边栏参数配置 ==========
with st.sidebar:
    st.header("回测参数")
    
    strategy_name = st.selectbox("选择策略", all_strategies, index=default_strategy, key="strategy_name")
    symbol_name = st.selectbox("选择标的", preset_symbols, index=default_symbol, key="symbol_name")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("开始日期", pd.to_datetime("2020-01-01"), key="start_date")
    with col2:
        end_date = st.date_input("结束日期", pd.to_datetime("2023-12-31"), key="end_date")
    
    st.subheader("资金配置")
    initial_capital = st.number_input("初始资金", value=1000000, step=100000, key="initial_capital")
    
    # 策略参数动态生成 - 所有参数都存到 session_state
    st.subheader("策略参数")
    strategy = create_strategy(strategy_name)
    param_schema = strategy.get_params_schema()
    
    for param_name, param_config in param_schema.items():
        param_type = param_config.get('type', 'int')
        param_default = param_config.get('default', 20)
        param_min = param_config.get('min', 1)
        param_max = param_config.get('max', 200)
        
        key = f"param_{strategy_name}_{param_name}"
        
        if param_type == 'int':
            st.session_state[f"value_{key}"] = st.slider(
                param_name, 
                min_value=param_min, 
                max_value=param_max, 
                value=param_default,
                key=key
            )
        elif param_type == 'float':
            st.session_state[f"value_{key}"] = st.slider(
                param_name, 
                min_value=float(param_min), 
                max_value=float(param_max), 
                value=float(param_default),
                key=key
            )

# ========== 运行回测 ==========
# 手动点击回测按钮 或 从快速开始自动触发（加个flag防止重复触发）
run_triggered = st.button(" 开始回测", type="primary") or (auto_run and 'last_result' not in st.session_state and 'auto_run_done' not in st.session_state)

if run_triggered:
    try:
        with st.spinner("回测计算中..."):
            # 标记自动回测已完成，防止重复触发
            if auto_run:
                st.session_state['auto_run_done'] = True
                # 清除快速开始标记
                if 'quick_strategy' in st.session_state:
                    del st.session_state['quick_strategy']
            
            symbol_code = loader.preset_symbols[symbol_name]
            try:
                data = loader.load_data(symbol_code, str(start_date), str(end_date), data_source=selected_source)
            except Exception as e:
                st.error(f"数据加载失败: {str(e)}")
                if selected_source == 'akshare':
                    st.info("提示：Akshare 部分指数数据可能无法获取，建议先使用模拟数据测试")
                st.stop()
            
            if len(data) < 30:
                st.warning(" 数据量太少，建议选择更长的时间范围（至少30个交易日）")
            
            config = BacktestConfig(initial_capital=initial_capital)
            engine = BacktestEngine(config)
            
            # 关键修复：每次回测都重新创建strategy对象，从session_state读取参数
            strategy = create_strategy(strategy_name)
            for param_name in param_schema.keys():
                key = f"param_{strategy_name}_{param_name}"
                if key in st.session_state:
                    setattr(strategy, param_name, st.session_state[f"value_{key}"])
            
            signals = strategy.generate_signals(data)
            result = engine.run(data, signals)
            perf = result.performance
            
            # 缓存到session_state
            st.session_state.last_result = result
            st.session_state.last_perf = perf
            st.session_state.last_strategy = strategy_name
            st.session_state.last_symbol = symbol_name
            st.session_state.start_date = start_date
            st.session_state.end_date = end_date
            st.session_state.initial_capital = initial_capital
            
    except Exception as e:
        st.error(f" 回测失败: {str(e)}")
        st.caption("如果问题持续，请检查参数设置或刷新页面重试")

# ========== 展示结果 ==========
if 'last_result' in st.session_state:
    result = st.session_state.last_result
    perf = st.session_state.last_perf
    current_strategy = st.session_state.last_strategy
    current_symbol = st.session_state.last_symbol
    
    st.success(f"回测完成 - {current_strategy} @ {current_symbol}")
    
    # ========== PDF导出按钮 ==========
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("📄 导出专业PDF报告", type="secondary", use_container_width=True):
            with st.spinner("正在生成专业PDF报告，请稍候..."):
                try:
                    from pdf_generator import PDFReportGenerator
                    
                    pdf_gen = PDFReportGenerator()
                    missing = pdf_gen.check_dependencies()
                    if missing:
                        st.error(f"缺少依赖库: {', '.join(missing)}")
                        st.code(f"pip install {' '.join(missing)}", language="bash")
                    else:
                        pdf_buffer = pdf_gen.generate_report(
                            result=result,
                            strategy_name=current_strategy,
                            symbol_name=current_symbol,
                            start_date=str(st.session_state.start_date),
                            end_date=str(st.session_state.end_date),
                            initial_capital=st.session_state.initial_capital,
                            perf=perf
                        )
                        
                        # 生成文件名
                        filename = f"{current_strategy}_{current_symbol}_{st.session_state.start_date}_{st.session_state.end_date}_回测报告.pdf"
                        filename = filename.replace(' ', '_').replace('/', '')
                        
                        st.success(" PDF报告生成成功！")
                        
                        # 提供下载按钮
                        st.download_button(
                            label="⬇️ 点击下载PDF报告",
                            data=pdf_buffer,
                            file_name=filename,
                            mime="application/pdf",
                            type="primary",
                            use_container_width=True
                        )
                except Exception as e:
                    st.error(f"报告生成失败: {str(e)}")
                    st.caption("请检查控制台输出或联系技术支持")
    
    st.markdown("---")
    
    # ========== 1. 核心绩效卡片 ==========
    st.subheader(" 核心绩效指标")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("总收益率", f"{perf['总收益率']:.2f}%")
        st.metric("年化收益率", f"{perf['年化收益率(CAGR)']:.2f}%")
    with col2:
        st.metric("最大回撤", f"{perf['最大回撤']:.2f}%", delta_color="inverse")
        st.metric("卡玛比率", f"{perf['卡玛比率']:.2f}")
    with col3:
        st.metric("夏普比率", f"{perf['夏普比率']:.2f}")
        st.metric("索提诺比率", f"{perf['索提诺比率']:.2f}")
    with col4:
        st.metric("交易次数", perf['总交易次数'])
        st.metric("胜率", f"{perf['胜率']:.1f}%")
    
    st.markdown("---")
    
    # ========== 2. 净值曲线 ==========
    st.subheader(" 净值曲线")
    
    fig_equity = go.Figure()
    fig_equity.add_trace(go.Scatter(
        x=result.equity_curve.index, 
        y=result.equity_curve.values, 
        name="策略净值", 
        line=dict(color="#1f77b4", width=2)
    ))
    
    # 添加回撤
    fig_equity.add_trace(go.Scatter(
        x=result.drawdown_curve.index,
        y=result.drawdown_curve.values * 100,
        name="回撤(%)",
        line=dict(color="#ff7f0e", width=1),
        yaxis="y2"
    ))
    
    fig_equity.update_layout(
        height=450,
        hovermode="x unified",
        yaxis_title="净值",
        yaxis2=dict(title="回撤(%)", overlaying="y", side="right", range=[-100, 0]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig_equity, use_container_width=True)
    st.markdown("---")
    
    # ========== 3. 月度收益率热力图 ==========
    st.subheader("🗓️ 月度收益率热力图")
    
    equity_daily = result.equity_curve
    monthly_equity = equity_daily.resample('M').last()
    monthly_returns = monthly_equity.pct_change().dropna() * 100
    
    monthly_data = []
    for date, ret in monthly_returns.items():
        monthly_data.append({
            'year': date.year,
            'month': date.month,
            'return': round(ret, 2)
        })
    
    df_monthly = pd.DataFrame(monthly_data)
    pivot_data = df_monthly.pivot(index='year', columns='month', values='return')
    pivot_data.columns = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月']
    
    fig_heatmap = go.Figure(data=go.Heatmap(
        z=pivot_data.values,
        x=pivot_data.columns,
        y=pivot_data.index.astype(str),
        colorscale='RdYlGn',
        zmid=0,
        text=[[f"{v:.2f}%" for v in row] for row in pivot_data.values],
        texttemplate='%{text}',
        showscale=True,
        colorbar=dict(title="收益率%")
    ))
    
    fig_heatmap.update_layout(height=300)
    st.plotly_chart(fig_heatmap, use_container_width=True)
    
    # 月度统计
    col1, col2, col3 = st.columns(3)
    with col1:
        best_month = df_monthly.loc[df_monthly['return'].idxmax()]
        st.metric("历史最佳单月", f"{best_month['return']:.2f}%", 
                 f"{int(best_month['year'])}年{int(best_month['month'])}月")
    with col2:
        worst_month = df_monthly.loc[df_monthly['return'].idxmin()]
        st.metric("历史最差单月", f"{worst_month['return']:.2f}%",
                 f"{int(worst_month['year'])}年{int(worst_month['month'])}月", delta_color="inverse")
    with col3:
        positive_months = len(df_monthly[df_monthly['return'] > 0])
        total_months = len(df_monthly)
        st.metric("月度胜率", f"{positive_months/total_months*100:.1f}%",
                 f"{positive_months}/{total_months}个月")
    
    st.markdown("---")
    
    # ========== 4. 参数敏感性分析（高级功能）
    with st.expander(" 参数敏感性分析 - 扫描最优参数区间"):
        st.caption("自动扫描策略核心参数在不同取值下的表现，找到鲁棒性最强的参数区间")
        
        strategy = create_strategy(current_strategy)
        default_params = strategy.get_params_schema()
        
        if len(default_params) >= 1:
            # 选择要扫描的参数
            param_names = list(default_params.keys())
            scan_param = st.selectbox("选择要扫描的参数", param_names)
            
            # 获取参数范围
            p_config = default_params[scan_param]
            p_min = p_config.get('min', 5)
            p_max = p_config.get('max', 200)
            p_default = p_config.get('default', 20)
            
            col1, col2 = st.columns(2)
            with col1:
                scan_start = st.number_input("扫描起始值", value=p_min, min_value=p_min, max_value=p_max)
            with col2:
                scan_end = st.number_input("扫描结束值", value=min(p_max, p_max), min_value=p_min, max_value=p_max)
            
            scan_step = st.slider("扫描步长", 2, 20, 5)
            
            if st.button("开始参数扫描", type="primary"):
                with st.spinner(f"正在扫描 {scan_param} 的参数敏感性..."):
                    # 生成扫描参数列表
                    scan_values = list(range(int(scan_start), int(scan_end) + 1, scan_step))
                    
                    # 从session_state读取回测参数，避免变量作用域问题
                    scan_symbol = st.session_state.get('last_symbol', symbol_name)
                    symbol_code = loader.preset_symbols[scan_symbol]
                    s_date = st.session_state.get('start_date', start_date)
                    e_date = st.session_state.get('end_date', end_date)
                    capital = st.session_state.get('initial_capital', initial_capital)
                    
                    data = loader.load_data(symbol_code, str(s_date), str(e_date))
                    config = BacktestConfig(initial_capital=capital)
                    engine = BacktestEngine(config)
                    
                    # 批量回测
                    scan_results = []
                    
                    for val in scan_values:
                        test_strategy = create_strategy(current_strategy)
                        setattr(test_strategy, scan_param, val)
                        signals = test_strategy.generate_signals(data)
                        result = engine.run(data, signals)
                        perf = result.performance
                        
                        scan_results.append({
                            '参数值': val,
                            '总收益率%': round(perf['总收益率'], 2),
                            '年化收益率%': round(perf['年化收益率(CAGR)'], 2),
                            '最大回撤%': round(perf['最大回撤'], 2),
                            '夏普比率': round(perf['夏普比率'], 2),
                            '卡玛比率': round(perf['卡玛比率'], 2),
                            '胜率%': round(perf['胜率'], 1),
                            '交易次数': perf['总交易次数']
                        })
                    
                    df_scan = pd.DataFrame(scan_results)
                    
                    # 绘制折线图
                    col1, col2 = st.columns([1, 1])
                    
                    with col1:
                        st.markdown("#### 夏普比率变化趋势")
                        fig_sharpe = go.Figure()
                        fig_sharpe.add_trace(go.Scatter(
                            x=df_scan['参数值'],
                            y=df_scan['夏普比率'],
                            mode='lines+markers+text',
                            text=df_scan['夏普比率'].round(2),
                            textposition='top center',
                            line=dict(color='#2ecc71', width=3),
                            marker=dict(size=10)
                        ))
                        # 标记最大值
                        best_s = df_scan.loc[df_scan['夏普比率'].idxmax()]
                        fig_sharpe.add_annotation(
                            x=best_s['参数值'], y=best_s['夏普比率'],
                            text=f"最优: {best_s['夏普比率']:.2f}",
                            showarrow=True, arrowhead=1, ax=0, ay=-40
                        )
                        fig_sharpe.update_layout(height=350, yaxis_title='夏普比率', xaxis_title=scan_param)
                        st.plotly_chart(fig_sharpe, use_container_width=True)
                    
                    with col2:
                        st.markdown("#### 卡玛比率变化趋势")
                        fig_calmar = go.Figure()
                        fig_calmar.add_trace(go.Scatter(
                            x=df_scan['参数值'],
                            y=df_scan['卡玛比率'],
                            mode='lines+markers+text',
                            text=df_scan['卡玛比率'].round(2),
                            textposition='top center',
                            line=dict(color='#3498db', width=3),
                            marker=dict(size=10)
                        ))
                        # 标记最大值
                        best_c = df_scan.loc[df_scan['卡玛比率'].idxmax()]
                        fig_calmar.add_annotation(
                            x=best_c['参数值'], y=best_c['卡玛比率'],
                            text=f"最优: {best_c['卡玛比率']:.2f}",
                            showarrow=True, arrowhead=1, ax=0, ay=-40
                        )
                        fig_calmar.update_layout(height=350, yaxis_title='卡玛比率', xaxis_title=scan_param)
                        st.plotly_chart(fig_calmar, use_container_width=True)
                    
                    # 收益回撤散点图
                    st.markdown("#### 收益-风险散点图")
                    fig_scatter = go.Figure()
                    for _, row in df_scan.iterrows():
                        fig_scatter.add_trace(go.Scatter(
                            x=[row['最大回撤%']],
                            y=[row['年化收益率%']],
                            mode='markers+text',
                            marker=dict(size=abs(row['夏普比率'])*5+8, color='RoyalBlue'),
                            text=str(row['参数值']),
                            textposition='top center',
                            name=f"参数={row['参数值']}",
                            hovertemplate=f"参数={row['参数值']}<br>年化={row['年化收益率%']:.1f}%<br>回撤={row['最大回撤%']:.1f}%<br>夏普={row['夏普比率']:.2f}"
                        ))
                    
                    fig_scatter.update_layout(
                        height=400,
                        xaxis_title='最大回撤 (%)',
                        yaxis_title='年化收益率 (%)',
                        showlegend=False
                    )
                    st.plotly_chart(fig_scatter, use_container_width=True)
                    
                    # 详细结果表
                    st.markdown("#### 详细扫描结果")
                    st.dataframe(df_scan, use_container_width=True, hide_index=True)
                    
                    # 最优参数建议
                    best_sharpe = df_scan.loc[df_scan['夏普比率'].idxmax()]
                    best_calmar = df_scan.loc[df_scan['卡玛比率'].idxmax()]
                    best_return = df_scan.loc[df_scan['年化收益率%'].idxmax()]
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.success(f" 最优夏普参数: {scan_param}={best_sharpe['参数值']}")
                        st.caption(f"夏普 {best_sharpe['夏普比率']:.2f} | 年化 {best_sharpe['年化收益率%']:.1f}%")
                    with col2:
                        st.success(f"⚖️ 最优卡玛参数: {scan_param}={best_calmar['参数值']}")
                        st.caption(f"卡玛 {best_calmar['卡玛比率']:.2f} | 回撤 {best_calmar['最大回撤%']:.1f}%")
                    with col3:
                        st.success(f" 最优收益参数: {scan_param}={best_return['参数值']}")
                        st.caption(f"年化 {best_return['年化收益率%']:.1f}% | 胜率 {best_return['胜率%']:.1f}%")
        else:
            st.info("该策略无可配置的参数，无法进行敏感性分析")
    
    st.markdown("---")
    
    # ========== 5. 交易盈亏分布 ==========
    st.subheader(" 交易盈亏分析")
    
    trades = result.trades
    if len(trades) > 0:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # 盈亏分布直方图
            fig_hist = go.Figure()
            wins = trades[trades['return_pct'] > 0]['return_pct']
            losses = trades[trades['return_pct'] < 0]['return_pct']
            
            fig_hist.add_trace(go.Histogram(
                x=wins, name='盈利交易', marker_color='#2ecc71', opacity=0.7, nbinsx=20
            ))
            fig_hist.add_trace(go.Histogram(
                x=losses, name='亏损交易', marker_color='#e74c3c', opacity=0.7, nbinsx=20
            ))
            
            fig_hist.update_layout(
                title='单笔交易收益率分布',
                height=350,
                xaxis_title='收益率%',
                yaxis_title='交易数量',
                barmode='overlay',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            st.plotly_chart(fig_hist, use_container_width=True)
        
        with col2:
            # 交易统计表格
            st.markdown("#### 交易统计")
            
            avg_win = wins.mean() if len(wins) > 0 else 0
            avg_loss = losses.mean() if len(losses) > 0 else 0
            
            stats_data = [
                ["平均单笔盈利", f"{avg_win:.2f}%"],
                ["平均单笔亏损", f"{avg_loss:.2f}%"],
                ["盈亏比", f"{abs(avg_win/avg_loss) if avg_loss != 0 else 0:.2f}"],
                ["单笔最大盈利", f"{trades['return_pct'].max():.2f}%"],
                ["单笔最大亏损", f"{trades['return_pct'].min():.2f}%"],
                ["盈利交易数", len(wins)],
                ["亏损交易数", len(losses)],
            ]
            
            df_stats = pd.DataFrame(stats_data, columns=["指标", "数值"])
            st.dataframe(df_stats, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # ========== 6. 交易明细 ==========
        with st.expander("查看详细交易记录"):
            trades_display = trades.copy()
            trades_display['entry_date'] = pd.to_datetime(trades_display['entry_date']).dt.strftime('%Y-%m-%d')
            trades_display['exit_date'] = pd.to_datetime(trades_display['exit_date']).dt.strftime('%Y-%m-%d')
            trades_display = trades_display[['entry_date', 'exit_date', 'entry_price', 'exit_price', 'position', 'return_pct', 'pnl']]
            trades_display.columns = ['入场日期', '出场日期', '入场价', '出场价', '仓位', '收益率%', '盈亏金额']
            st.dataframe(trades_display, use_container_width=True)

else:
    # 未回测时显示引导
    st.info("👈 请在左侧配置回测参数，点击「开始回测」按钮")
    
    # 快速示例
    st.markdown("###  快速上手")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**第一步**")
        st.caption("选择策略和标的，调整参数")
    with col2:
        st.markdown("**第二步**")
        st.caption("点击「开始回测」运行计算")
    with col3:
        st.markdown("**第三步**")
        st.caption("查看净值曲线和绩效分析")
    
    # 温馨提示
    st.markdown("---")
    st.markdown("###  使用提示")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.caption("**数据范围**")
        st.markdown("建议至少30个交易日以上的回测周期")
    with col_b:
        st.caption("**参数调整**")
        st.markdown("不同标的的最优参数可能有差异")
    with col_c:
        st.caption("**结果解读**")
        st.markdown("回测结果仅供参考，不构成投资建议")

st.markdown("---")
st.caption("Rock Quant 2.0 - 顽岩量价模型")
