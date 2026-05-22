"""
pages/09_模拟盘.py - Lv.3 模拟盘交易中心
"""
import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import json
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from paper_trader import MockAccount, BrokerAdapter, PaperTrader, OrderStatus
from realism import RealismConfig
from live_signal import generate_multi_signals, TradeSignal

st.set_page_config(page_title="模拟盘 - Rock Quant", layout="wide")
st.title("模拟盘交易中心")
st.caption("信号→下单→账户管理 全闭环 | 当前为本地 Mock 模式")

# ============ 初始化 broker / trader ============
if "paper_broker" not in st.session_state:
    st.session_state["paper_broker"] = BrokerAdapter(
        mode="mock", initial_capital=1_000_000,
        realism_config=RealismConfig(enable=True),
    )
    st.session_state["paper_trader"] = PaperTrader(
        st.session_state["paper_broker"],
        trade_dir="paper_trades",
    )

broker: BrokerAdapter = st.session_state["paper_broker"]
trader: PaperTrader = st.session_state["paper_trader"]
account: MockAccount = broker.account

# ============ 侧边栏 ============
with st.sidebar:
    st.header("账户配置")
    st.metric("初始资金", f"￥{account.initial_capital:,.0f}")
    st.metric("可用现金", f"￥{account.cash:,.2f}")
    market_value = sum(p.market_value for p in account.positions.values())
    st.metric("持仓市值", f"￥{market_value:,.2f}")
    total = account.cash + market_value
    pnl_pct = (total / account.initial_capital - 1) * 100
    st.metric("总资产", f"￥{total:,.2f}", f"{pnl_pct:+.2f}%")

    st.markdown("---")
    if st.button("重置账户", type="secondary"):
        del st.session_state["paper_broker"]
        del st.session_state["paper_trader"]
        st.rerun()

# ============ 标签页 ============
tabs = st.tabs(["持仓概览", "执行信号", "交易历史", "账户摘要"])

# 持仓概览
with tabs[0]:
    if account.positions:
        rows = []
        for sym, pos in account.positions.items():
            rows.append({
                "标的": f"{pos.name}({sym})",
                "数量": pos.quantity,
                "均价": f"{pos.avg_cost:.2f}",
                "现价": f"{pos.current_price:.2f}",
                "市值": f"{pos.market_value:,.2f}",
                "浮盈": f"{pos.unrealized_pnl:+,.2f}",
                "浮盈%": f"{pos.unrealized_pnl_pct:+.2f}%",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("当前无持仓")

# 执行信号
with tabs[1]:
    st.subheader("从策略生成并执行信号")

    col1, col2 = st.columns(2)
    with col1:
        watch_text = st.text_area(
            "观察列表（代码:名称，每行一个）",
            value="000001.SZ:平安银行\n600519.SH:贵州茅台",
            height=120,
        )
    with col2:
        from strategies import get_all_strategies
        strategy = st.selectbox("策略", get_all_strategies())
        data_source = st.selectbox("数据源", ["simulated", "akshare", "tushare"])

    if st.button("生成并执行", type="primary"):
        watchlist = {}
        for line in watch_text.strip().splitlines():
            if ":" in line:
                c, n = line.strip().split(":", 1)
                watchlist[c.strip()] = n.strip()

        with st.spinner("正在生成并执行信号..."):
            report = generate_multi_signals(
                watchlist, strategy, data_source=data_source,
                realism_config=RealismConfig(enable=True),
            )
            results = []
            today = datetime.now().strftime("%Y-%m-%d")
            for sig in report.signals:
                order = trader.execute_signal(sig, today=today)
                # 更新价格
                account.update_prices({sig.symbol: sig.price})
                results.append({
                    "标的": f"{sig.name}({sig.symbol})",
                    "信号": sig.action,
                    "价格": sig.price,
                    "目标仓位": f"{sig.position:.0%}",
                    "执行结果": order.status.value if order else "无操作",
                    "成交量": order.filled_quantity if order else 0,
                    "原因": order.reason if order and order.reason else "-",
                })
            trader.save_daily_log(today)

        st.success(f"已执行 {len(results)} 条信号")
        st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

# 交易历史
with tabs[2]:
    if trader.trade_log:
        df = pd.DataFrame(trader.trade_log)
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.download_button(
            "下载交易日志",
            data=json.dumps(trader.trade_log, ensure_ascii=False, indent=2),
            file_name=f"trades_{datetime.now().strftime('%Y%m%d')}.json",
        )
    else:
        st.info("暂无交易记录")

# 账户摘要
with tabs[3]:
    st.code(account.summary(), language="plaintext")

    st.subheader("历史快照")
    if account.snapshots:
        snap_rows = []
        for d, snap in sorted(account.snapshots.items()):
            snap_rows.append({
                "日期": d,
                "总资产": f"{snap.total_assets:,.2f}",
                "现金": f"{snap.cash:,.2f}",
                "市值": f"{snap.market_value:,.2f}",
                "日盈亏": f"{snap.daily_pnl:+,.2f}",
                "日收益%": f"{snap.daily_return_pct:+.2f}%",
            })
        st.dataframe(pd.DataFrame(snap_rows), use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("Rock Quant 2.8 - Lv.3 模拟盘 | 切换 BrokerAdapter mode=easytrader/qmt 可对接真实券商")
