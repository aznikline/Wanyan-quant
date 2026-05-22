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
from realism import RealismConfig
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

# ========== 策略实战指南配置 ==========
STRATEGY_GUIDE = {
    "双均线策略": {
        "适用场景": "趋势明确的大盘股、指数基金；适合中长期持有",
        "避免场景": "震荡市来回打脸；小票容易被操纵",
        "参数建议": "稳健型：短10日 + 长50日；敏感型：短5日 + 长20日；长线：短20日 + 长120日",
        "实战技巧": "突破后等收盘确认再进场；配合成交量放大确认；大盘不好时仓位减半",
        "常见陷阱": "震荡市频繁交易滑点吃掉收益；参数过短噪音多；牛市末期滞后进场"
    },
    "MACD策略": {
        "适用场景": "中期趋势跟踪；大市值股票、宽基指数",
        "避免场景": "震荡市金叉死叉频繁无效；短期波动噪音大",
        "参数建议": "默认12/26/9适合大多数情况；短线可调整为6/13/5；长线可19/39/9",
        "实战技巧": "顶背离比底背离准确率高；结合0轴上方金叉胜率更高；二次金叉比首次金叉可靠",
        "常见陷阱": "0轴以下频繁金叉都是反弹；MACD滞后，趋势末期信号出现太晚"
    },
    "RSI超买超卖策略": {
        "适用场景": "震荡市；波段操作；配合布林带效果更好",
        "避免场景": "单边牛市RSI80以上还能涨；单边熊市20以下还能跌",
        "参数建议": "标准14日；短线6日；长线25日；超买阈值70-80，超卖阈值20-30",
        "实战技巧": "RSI顶底背离是最强信号；RSI50以上强势，50以下弱势；极端值等待第二次确认",
        "常见陷阱": "单边趋势中超买超卖反复打脸；只看RSI不看大趋势"
    },
    "布林带突破策略": {
        "适用场景": "横盘突破；波动率放大时；配合成交量确认",
        "避免场景": "低波动时期上下轨道窄；假突破频繁",
        "参数建议": "标准20日+2倍标准差；敏感型10日+1.5倍；稳健型30日+2.5倍",
        "实战技巧": "布林带收窄后突破是最强信号；突破时必须带量；跌破中轨止损离场",
        "常见陷阱": "假突破太多，需结合其他指标；收缩时间越长，突破空间越大"
    },
    "布林带策略": {
        "适用场景": "震荡市；波段操作；中低波动率标的",
        "避免场景": "单边趋势市；高波动暴涨暴跌票",
        "参数建议": "标准20日+2倍标准差；敏感型15日+1.8倍；稳健型25日+2.2倍",
        "实战技巧": "价格触碰下轨+RSI超卖时买入；触碰上轨+RSI超买时卖出；中轨作为加减仓依据",
        "常见陷阱": "趋势来了上下轨反而变成反向指标；参数太敏感交易频繁滑点高"
    },
    "KDJ随机指标策略": {
        "适用场景": "短线交易；震荡市；小盘股和题材股",
        "避免场景": "大盘蓝筹；长期趋势跟踪",
        "参数建议": "标准9/3/3；短线5/2/2；长线14/3/3",
        "实战技巧": "J值触底反弹+金叉胜率高；二次金叉；顶底背离；K线形态配合",
        "常见陷阱": "钝化后高位反复金叉；信号太灵敏噪音多；只看交叉不看位置"
    },
    "DMA平均线差策略": {
        "适用场景": "中期趋势跟踪；大盘指数；ETF基金",
        "避免场景": "震荡市；短期波动",
        "参数建议": "标准10/50/10；短线5/25/5；长线20/100/20",
        "实战技巧": "DMA穿0轴是强信号；背离比金叉死叉更重要；配合MACD双确认",
        "常见陷阱": "交叉信号太多真假难辨；滞后于价格变化"
    },
    "成交量突破策略": {
        "适用场景": "突破确认；趋势启动点；龙头股启动信号",
        "避免场景": "高位放量出货；对倒放量假突破",
        "参数建议": "放量2倍以上算有效突破；缩量到均量1/2以下确认调整结束",
        "实战技巧": "突破后回踩不破再进场；天量见天价地量见地价；量价背离是反转信号",
        "常见陷阱": "主力对倒造假成交量；高位放量是出货不是突破；放量滞涨要小心"
    }
}

st.title(" 策略回测")
st.caption("单策略回测与深度绩效分析")

# ========== 数据源选择（优化版）==========
with st.sidebar:
    st.markdown("### 数据源配置")
    
    data_sources = [
        ("📊 模拟历史数据", "simulated", "内置数据，无需网络，快速回测"),
        ("🌐 Akshare 免费数据", "akshare", "免费开源数据，覆盖A股/指数/期货"),
        ("💎 Tushare 专业数据", "tushare", "专业金融数据库，需Token，数据稳定"),
    ]
    
    # 卡片式数据源选择UI
    current_source = st.session_state.get('data_source', 'simulated')
    
    for display_name, source_id, desc in data_sources:
        is_selected = current_source == source_id
        button_type = "primary" if is_selected else "secondary"
        
        if st.button(f"{display_name}", type=button_type, use_container_width=True, key=f"ds_{source_id}"):
            st.session_state['data_source'] = source_id
            st.rerun()
        
        if is_selected:
            st.caption(f"  {desc}")
    
    selected_source = st.session_state.get('data_source', 'simulated')
    
    # Tushare Token配置优化
    if selected_source == 'tushare':
        st.markdown("---")
        st.markdown("#### Tushare Token 设置")
        
        current_token = st.session_state.get('tushare_token', '')
        has_token = len(current_token) > 20
        
        if has_token:
            st.success("✅ Token已配置，数据源可用")
            if st.button("🔄 更新Token", type="secondary", use_container_width=True):
                st.session_state['tushare_token'] = ''
                st.rerun()
        else:
            tushare_token = st.text_input(
                "输入Tushare Token",
                type="password",
                help="访问 https://tushare.pro/user/token 注册获取",
                placeholder="请输入您的Token...",
                key="tushare_input"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ 保存", type="primary", use_container_width=True):
                    if len(tushare_token) > 20:
                        st.session_state['tushare_token'] = tushare_token
                        loader.set_tushare_token(tushare_token)
                        st.success("Token已保存！")
                        st.rerun()
                    else:
                        st.error("Token格式不正确")
            with col2:
                st.link_button("🔗 获取Token", "https://tushare.pro/user/token", use_container_width=True)
    
    loader.set_data_source(selected_source)
    
    # 数据源可用性状态
    available, msg = loader.check_data_source_available(selected_source)
    st.markdown("---")
    
    if available and selected_source != 'simulated':
        st.success(f"✅ 数据源连接正常")
    elif not available and selected_source != 'simulated':
        st.warning(f"⚠️ {msg}，将使用模拟数据进行回测")
        st.session_state['data_source'] = 'simulated'
        selected_source = 'simulated'
    else:
        st.info("💡 使用模拟数据进行快速回测演示")
    
    # ========== 真实性模式 Lv.1 ==========
    st.markdown("---")
    st.subheader("🔍 真实模式设置")
    realism_enable = st.toggle(
        "启用真实回测",
        value=st.session_state.get("realism_enable", True),
        help="启用后加入滑点、佣金、印花税、涨跌停过滤、T+1 限制，代价是净值下降。推荐一直开。"
    )
    st.session_state["realism_enable"] = realism_enable

    with st.expander("高级：成本与市场机制参数", expanded=False):
        realism_slip = st.slider("滑点比例‰", 0.0, 5.0, 1.0, 0.1) / 1000
        realism_comm = st.slider("佣金率万", 0.0, 10.0, 2.5, 0.1) / 10000
        realism_stamp = st.slider("印花税‰（仅卖出）", 0.0, 2.0, 1.0, 0.1) / 1000
        realism_t1 = st.checkbox("T+1 限制（A股）", value=True)
        realism_limit = st.checkbox("涨跌停过滤", value=True)
        realism_is_st = st.checkbox("ST 股（5% 涨跌幅）", value=False)

    st.session_state["realism_cfg"] = RealismConfig(
        enable=realism_enable,
        enable_slippage=True,
        enable_cost=True,
        enable_price_limit=realism_limit,
        enable_t_plus_1=realism_t1,
        slippage_ratio=realism_slip,
        commission_rate=realism_comm,
        stamp_tax_rate=realism_stamp,
        is_st=realism_is_st,
    )
    
    st.markdown("---")

st.markdown("---")

# ========== 快速参数处理 ==========
# 从首页快速开始按钮传过来的参数
default_strategy = 0
default_symbol = 0
auto_run = False

# 处理快速开始日期参数
import datetime as dt
default_start = pd.to_datetime("2020-01-01")
default_end = pd.to_datetime("2023-12-31")

if 'quick_start_date' in st.session_state:
    default_start = pd.to_datetime(st.session_state.quick_start_date)
if 'quick_end_date' in st.session_state:
    default_end = pd.to_datetime(st.session_state.quick_end_date)

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
        start_date = st.date_input("开始日期", default_start, key="start_date")
    with col2:
        end_date = st.date_input("结束日期", default_end, key="end_date")
    
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
    
    # ========== 策略实战指南 ==========
    st.markdown("---")
    with st.expander("💡 策略实战指南", expanded=True):
        if strategy_name in STRATEGY_GUIDE:
            guide = STRATEGY_GUIDE[strategy_name]
            st.markdown("**✅ 什么时候用**")
            st.caption(guide["适用场景"])
            st.markdown("**❌ 什么时候别用**")
            st.caption(guide["避免场景"])
            st.markdown("**⚙️ 参数建议**")
            st.caption(guide["参数建议"])
            st.markdown("**💡 实战技巧**")
            st.caption(guide["实战技巧"])
            st.markdown("**🕳️ 常见陷阱**")
            st.caption(guide["常见陷阱"])
        else:
            st.caption("该策略暂无实战指南")

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
            realism_cfg = st.session_state.get("realism_cfg", RealismConfig(enable=False))
            engine = BacktestEngine(config, realism_config=realism_cfg)
            
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
            
            # ========== 回测完成主动提醒 ==========
            perf = result.performance
            annual_return = perf['年化收益率(CAGR)']
            max_returns = perf['年化收益率(CAGR)']
            max_drawdown = perf['最大回撤']
            win_rate = perf['胜率']
            total_trades = perf['总交易次数']
            sharpe = perf['夏普比率']
            
            # 生成策略表现评估
            if annual_return > 15 and max_drawdown < 20 and win_rate > 50:
                toast_icon = "🎉"
                toast_msg = f"策略表现优秀！年化{annual_return:.1f}%，最大回撤{max_drawdown:.1f}%，胜率{win_rate:.1f}%，共{total_trades}笔交易，夏普{sharpe:.2f}"
            elif annual_return > 5:
                toast_icon = "✅"
                toast_msg = f"回测完成！年化{annual_return:.1f}%，最大回撤{max_drawdown:.1f}%，胜率{win_rate:.1f}%"
            else:
                toast_icon = "⚠️"
                toast_msg = f"回测完成，表现一般！年化{annual_return:.1f}%，最大回撤{max_drawdown:.1f}%"
            
            st.toast(toast_msg, icon=toast_icon)
            
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
    
    # ========== 真实性统计 ==========
    rs = perf.get("realism_stats", {})
    if perf.get("realism_enabled") and rs:
        bb, bs, bt = rs.get('blocked_buy', 0), rs.get('blocked_sell', 0), rs.get('blocked_t1', 0)
        if bb + bs + bt > 0:
            st.warning(
                f"真实模式干预统计：涨停阻买 {bb} 次 | 跌停阻卖 {bs} 次 | T+1 阻卖 {bt} 次"
            )
        else:
            st.info("真实模式已启用，本次回测未触发阻断事件")
    
    # ========== 核心结论指标（第一层） ==========
    st.subheader("核心结论")
    
    col1, col2, col3 = st.columns(3)
    
    # 指标评估颜色
    annual_return = perf['年化收益率(CAGR)']
    max_drawdown = perf['最大回撤']
    win_rate = perf['胜率']
    
    def get_return_status(val):
        if val > 20: return ("🟢", "优秀")
        elif val > 15: return ("🟡", "良好")
        elif val > 10: return ("🟡", "一般")
        else: return ("🔴", "较差")
    
    def get_drawdown_status(val):
        if val < 15: return ("🟢", "优秀")
        elif val < 25: return ("🟡", "良好")
        elif val < 35: return ("🟡", "一般")
        else: return ("🔴", "较差")
    
    def get_winrate_status(val):
        if val > 55: return ("🟢", "优秀")
        elif val > 50: return ("🟡", "良好")
        elif val > 40: return ("🟡", "一般")
        else: return ("🔴", "较差")
    
    with col1:
        status_icon, status_text = get_return_status(annual_return)
        st.metric("年化收益率", f"{annual_return:.2f}%")
        st.caption(f"{status_icon} {status_text}")
    
    with col2:
        status_icon, status_text = get_drawdown_status(max_drawdown)
        st.metric("最大回撤", f"{max_drawdown:.2f}%")
        st.caption(f"{status_icon} {status_text}")
    
    with col3:
        status_icon, status_text = get_winrate_status(win_rate)
        st.metric("胜率", f"{win_rate:.1f}%")
        st.caption(f"{status_icon} {status_text}")
    
    st.markdown("---")
    
    # ========== 第二层：净值曲线和交易记录 ==========
    st.subheader("净值曲线")
    
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
        height=400,
        hovermode="x unified",
        yaxis_title="净值",
        yaxis2=dict(title="回撤(%)", overlaying="y", side="right", range=[-100, 0]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig_equity, use_container_width=True)
    
    # 最近5笔交易
    st.subheader("最近交易")
    if len(result.trades) > 0:
        recent_trades = pd.DataFrame(result.trades).tail().sort_values('entry_date', ascending=False)
        recent_trades_display = recent_trades[['entry_date', 'exit_date', 'entry_price', 'exit_price', 'return_pct']].copy()
        recent_trades_display.columns = ['进场日期', '离场日期', '进场价', '离场价', '收益率%']
        st.dataframe(recent_trades_display, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # ========== 详细分析展开按钮 ==========
    if 'show_detail' not in st.session_state:
        st.session_state.show_detail = False
    
    col1, col2 = st.columns([3, 1])
    with col2:
        detail_label = "收起详细分析" if st.session_state.show_detail else "展开详细分析"
        if st.button(detail_label, use_container_width=True):
            st.session_state.show_detail = not st.session_state.show_detail
            st.rerun()
    
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
    
    # ========== 参数自动优化推荐 ==========
    st.markdown("---")
    with st.expander("🔧 参数自动优化推荐", expanded=False):
        st.markdown("自动搜索最优参数组合，基于回测结果智能推荐优化方向")
        
        col1, col2 = st.columns(2)
        with col1:
            optimize_target = st.selectbox(
                "优化目标",
                ["夏普比率最大化", "卡玛比率最大化", "年化收益率最大化", "最大回撤最小化", "胜率最大化"],
                index=0
            )
            max_iterations = st.slider("搜索粒度", 10, 100, 30, help="数值越大搜索越精确，耗时越长")
        
        with col2:
            search_range = st.slider("搜索范围 (%)", 30, 150, 80, help="在当前参数基础上的上下浮动范围")
            risk_penalty = st.checkbox("风险惩罚", value=True, help="对高回撤参数组合施加惩罚")
        
        if st.button("🚀 开始参数优化", type="primary", use_container_width=True):
            with st.spinner("正在搜索最优参数组合，预计需要 30-60 秒..."):
                strategy = create_strategy(strategy_name)
                param_schema = strategy.get_params_schema()
                
                # 准备待优化参数列表
                param_combinations = []
                for param_name, config in param_schema.items():
                    current_val = getattr(strategy, param_name)
                    param_type = config.get('type', 'int')
                    min_val = config.get('min', 1)
                    max_val = config.get('max', 200)
                    
                    # 计算搜索范围
                    search_min = max(min_val, int(current_val * (100 - search_range) / 100))
                    search_max = min(max_val, int(current_val * (100 + search_range) / 100))
                    
                    # 生成候选值
                    if param_type == 'int':
                        step = max(1, (search_max - search_min) // int(max_iterations / len(param_schema)))
                        values = list(range(search_min, search_max + 1, step))
                    else:
                        step = (search_max - search_min) / int(max_iterations / len(param_schema))
                        values = [round(search_min + i * step, 2) for i in range(int((search_max - search_min) / step) + 1)]
                    
                    param_combinations.append((param_name, values, param_type))
                
                # 网格搜索
                best_score = -float('inf')
                best_params = {}
                results = []
                
                # 简化：每个参数测试5个值，笛卡尔积
                from itertools import product
                param_values_list = []
                param_names = []
                for p_name, p_values, _ in param_combinations:
                    # 每个参数最多取5个值，避免组合爆炸
                    sampled = p_values[::max(1, len(p_values) // 5)][:5]
                    param_values_list.append(sampled)
                    param_names.append(p_name)
                
                config = BacktestConfig(initial_capital=initial_capital)
                realism_cfg_opt = st.session_state.get("realism_cfg", RealismConfig(enable=False))
                engine = BacktestEngine(config, realism_config=realism_cfg_opt)
                
                progress = st.progress(0)
                total = len(list(product(*param_values_list)))
                
                for idx, param_values in enumerate(product(*param_values_list)):
                    # 设置参数
                    test_strategy = create_strategy(strategy_name)
                    for p_name, p_val in zip(param_names, param_values):
                        setattr(test_strategy, p_name, p_val)
                    
                    # 回测
                    signals = test_strategy.generate_signals(data)
                    test_result = engine.run(data, signals)
                    perf = test_result.performance
                    
                    # 计算综合评分
                    if optimize_target == "夏普比率最大化":
                        score = perf['夏普比率']
                    elif optimize_target == "卡玛比率最大化":
                        score = perf['卡玛比率']
                    elif optimize_target == "年化收益率最大化":
                        score = perf['年化收益率(CAGR)']
                    elif optimize_target == "最大回撤最小化":
                        score = -perf['最大回撤']  # 取负数，越小越好
                    elif optimize_target == "胜率最大化":
                        score = perf['胜率']
                    else:
                        score = perf['夏普比率']
                    
                    # 风险惩罚
                    if risk_penalty and perf['最大回撤'] > 30:
                        score *= 0.7  # 回撤>30%惩罚30%
                    elif risk_penalty and perf['最大回撤'] > 20:
                        score *= 0.85  # 回撤>20%惩罚15%
                    
                    results.append({
                        'params': dict(zip(param_names, param_values)),
                        '年化%': round(perf['年化收益率(CAGR)'], 2),
                        '最大回撤%': round(perf['最大回撤'], 2),
                        '夏普比率': round(perf['夏普比率'], 2),
                        '卡玛比率': round(perf['卡玛比率'], 2),
                        '胜率%': round(perf['胜率'], 2),
                        'score': round(score, 3)
                    })
                    
                    if score > best_score:
                        best_score = score
                        best_params = dict(zip(param_names, param_values))
                    
                    progress.progress(min(idx / total, 1.0))
                
                progress.empty()
                
                # 展示结果
                st.success(f"✅ 优化完成！共测试 {total} 组参数")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**🏆 最优参数组合**")
                    for p_name, p_val in best_params.items():
                        current_val = getattr(strategy, p_name)
                        change = ((p_val - current_val) / current_val) * 100
                        delta = f"{change:+.1f}%"
                        st.metric(p_name, p_val, delta=delta)
                
                with col2:
                    best_result = [r for r in results if r['params'] == best_params][0]
                    st.markdown("**📊 预期优化效果**")
                    st.metric("年化收益率", f"{best_result['年化%']:.2f}%", 
                             delta=f"{best_result['年化%'] - perf['年化收益率(CAGR)']:+.2f}%")
                    st.metric("最大回撤", f"{best_result['最大回撤%']:.2f}%",
                             delta=f"{best_result['最大回撤%'] - perf['最大回撤']:+.2f}%",
                             delta_color="inverse")
                    st.metric("夏普比率", f"{best_result['夏普比率']:.2f}",
                             delta=f"{best_result['夏普比率'] - perf['夏普比率']:+.2f}")
                
                # Top5推荐参数
                st.markdown("**📋 Top5 参数组合推荐**")
                top5 = sorted(results, key=lambda x: -x['score'])[:5]
                top5_df = []
                for r in top5:
                    row = {**r['params']}
                    row['年化%'] = r['年化%']
                    row['最大回撤%'] = r['最大回撤%']
                    row['夏普比率'] = r['夏普比率']
                    row['综合评分'] = r['score']
                    top5_df.append(row)
                
                st.dataframe(pd.DataFrame(top5_df), use_container_width=True, hide_index=True)
                
                # 一键应用最优参数
                if st.button("✅ 一键应用最优参数", type="secondary"):
                    for p_name, p_val in best_params.items():
                        key = f"param_{strategy_name}_{p_name}"
                        st.session_state[f"value_{key}"] = p_val
                        if key in st.session_state:
                            st.session_state[key] = p_val
                    st.success("参数已应用！重新运行回测即可查看效果")
    
    # ========== 详细分析内容（第三层） ==========
    if st.session_state.show_detail:
        st.markdown("---")
        st.subheader("详细分析")
        
        # 完整绩效指标
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总收益率", f"{perf['总收益率']:.2f}%")
        with col2:
            st.metric("卡玛比率", f"{perf['卡玛比率']:.2f}")
        with col3:
            st.metric("夏普比率", f"{perf['夏普比率']:.2f}")
        with col4:
            st.metric("交易次数", perf['总交易次数'])
        
        # 完整的月度热力图和其他分析（从下面移上来）
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
                    realism_cfg_scan = st.session_state.get("realism_cfg", RealismConfig(enable=False))
                    engine = BacktestEngine(config, realism_config=realism_cfg_scan)
                    
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

# ========== 7. AI智能分析专区 ==========
if 'last_result' in st.session_state:
    st.subheader("🤖 AI智能分析")
    
    if st.button("🧠 启动AI深度分析", type="primary", use_container_width=True):
        with st.spinner("AI正在深度分析策略表现，请稍候..."):
            try:
                from src.ai_analyzer import AIStrategyAnalyzer
                
                analyzer = AIStrategyAnalyzer()
                ai_result = analyzer.analyze(
                    equity_curve=st.session_state.last_result.equity_curve,
                    trades=st.session_state.last_result.trades,
                    perf=st.session_state.last_perf,
                    strategy_name=st.session_state.last_strategy,
                    symbol_name=st.session_state.last_symbol
                )
                
                # ===== 7.1 综合评分卡片 =====
                st.markdown("## 📊 策略综合评分")
                
                # 评分仪表盘
                score = ai_result.score
                
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    # 评级徽章
                    grade_colors = {'S': '#1a9641', 'A': '#a6d96a', 'B': '#fdae61', 'C': '#f46d43', 'D': '#d73027', 'F': '#000000'}
                    st.markdown(f'''<div style='text-align: center; padding: 30px; background: linear-gradient(135deg, {grade_colors.get(score.grade, '#666')}20 0%, {grade_colors.get(score.grade, '#666')}40 100%); border-radius: 20px; border: 3px solid {grade_colors.get(score.grade, '#666')};'>
                        <div style='font-size: 60px; font-weight: bold; color: {grade_colors.get(score.grade, '#666')};'>{score.grade}</div>
                        <div style='font-size: 24px; color: #333;'>综合评级</div>
                        <div style='font-size: 48px; font-weight: bold; color: #1a1a1a; margin-top: 10px;'>{score.overall_score:.0f}</div>
                        <div style='font-size: 14px; color: #666;'>满分 100 分</div>
                    </div>''', unsafe_allow_html=True)
                
                # 5维度得分条形图
                st.markdown("### 五维度详细得分")
                
                import plotly.graph_objects as go
                
                categories = ['收益能力', '风险控制', '风险调整收益', '稳定性', '交易质量']
                scores = [score.return_score, score.risk_score, score.risk_adjusted_score, score.consistency_score, score.trading_quality_score]
                max_scores = [40, 20, 15, 10, 15]  # 各维度满分
                percentages = [s/m*100 for s, m in zip(scores, max_scores)]
                
                fig_radar = go.Figure(data=go.Bar(
                    x=categories,
                    y=percentages,
                    text=[f'{s:.0f}/{m}' for s, m in zip(scores, max_scores)],
                    textposition='auto',
                    marker_color=['#2ecc71' if p >= 70 else '#f39c12' if p >= 50 else '#e74c3c' for p in percentages],
                ))
                
                fig_radar.update_layout(
                    height=350,
                    yaxis_title='得分百分比 (%)',
                    yaxis_range=[0, 105],
                    showlegend=False
                )
                
                st.plotly_chart(fig_radar, use_container_width=True)
                
                # 优势与不足并列
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("### ✅ 策略优势")
                    for s in score.strengths:
                        st.success(f"• {s}")
                with col2:
                    st.markdown("### ⚠️ 待改进项")
                    for w in score.weaknesses:
                        st.warning(f"• {w}")
                
                st.markdown("---")
                
                # ===== 7.2 收益归因分析 =====
                st.markdown("## 🔬 五维度收益归因分析")
                attr = ai_result.attribution
                
                # 饼图
                fig_pie = go.Figure(data=[go.Pie(
                    labels=['📈 趋势捕捉', '🌊 波动择时', '⚖️ 均值回归', '🎯 仓位管理', '🎲 运气成分'],
                    values=[abs(attr.trend_capture), abs(attr.volatility_timing), abs(attr.mean_reversion), 
                           abs(attr.position_sizing), abs(attr.luck_factor)],
                    hole=.4,
                    marker_colors=['#3498db', '#9b59b6', '#1abc9c', '#f39c12', '#e74c3c'],
                    textinfo='label+percent',
                    textposition='outside'
                )])
                
                fig_pie.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig_pie, use_container_width=True)
                
                # 归因解读表格
                attr_data = [
                    ['📈 趋势捕捉', f'{abs(attr.trend_capture):.1f}%', analyzer._interpret_attribution_factor('trend', attr.trend_capture)],
                    ['🌊 波动择时', f'{abs(attr.volatility_timing):.1f}%', analyzer._interpret_attribution_factor('volatility', attr.volatility_timing)],
                    ['⚖️ 均值回归', f'{abs(attr.mean_reversion):.1f}%', analyzer._interpret_attribution_factor('mean_reversion', attr.mean_reversion)],
                    ['🎯 仓位管理', f'{abs(attr.position_sizing):.1f}%', analyzer._interpret_attribution_factor('position', attr.position_sizing)],
                    ['🎲 运气成分', f'{abs(attr.luck_factor):.1f}%', analyzer._interpret_attribution_factor('luck', attr.luck_factor)],
                ]
                
                import pandas as pd
                attr_df = pd.DataFrame(attr_data, columns=['收益来源', '贡献占比', 'AI解读'])
                st.dataframe(attr_df, use_container_width=True, hide_index=True)
                
                st.markdown("---")
                
                # ===== 7.3 多智能体辩论评估 =====
                st.markdown("## 🗣️ 多智能体辩论评估")
                st.caption("4位不同风格的AI专家独立评估，兼听则明")
                
                debate = ai_result.debate_results
                
                # 专家卡片
                cols = st.columns(2)
                for i, agent in enumerate(debate):
                    with cols[i % 2]:
                        rec_colors = {
                            '强烈推荐': '#1a9641',
                            '可以使用': '#a6d96a', 
                            '谨慎使用': '#fdae61',
                            '不推荐': '#d73027'
                        }
                        color = rec_colors.get(agent.recommendation, '#666')
                        
                        with st.expander(f"**{agent.role.value}** | {agent.recommendation} (置信度: {agent.confidence}%)", expanded=True):
                            st.markdown(f"**观点：** {agent.opinion}")
                            st.markdown("**核心论据：**")
                            for point in agent.key_points:
                                st.markdown(f"- {point}")
                
                st.markdown("---")
                
                # ===== 7.4 AI完整解读 =====
                st.markdown("## 📝 AI完整解读报告")
                
                with st.expander("展开完整AI分析报告", expanded=True):
                    st.markdown(ai_result.interpretation.replace('### ', '#### '))
                
                st.markdown("---")
                
                # ===== 7.5 改进建议 =====
                st.markdown("## 💡 改进建议")
                for i, rec in enumerate(score.recommendations[:5], 1):
                    st.info(f"**{i}.** {rec}")
                
                # 最终结论
                st.markdown("## 🎯 最终结论")
                final_conclusion = ai_result.final_conclusion if ai_result.final_conclusion else "分析完成，请参考以上各维度评估结果"
                st.success(final_conclusion)
                
                # 缓存AI结果
                st.session_state.last_ai_result = ai_result
                
            except Exception as e:
                st.error(f"AI分析失败: {str(e)}")
                st.caption("请确保已完成回测且ai_analyzer模块存在")
                import traceback
                st.code(traceback.format_exc())

st.markdown("---")
st.caption("Rock Quant 2.6 - 顽岩AI量化分析系统")
