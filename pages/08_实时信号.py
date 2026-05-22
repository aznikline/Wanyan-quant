"""
pages/08_实时信号.py - Lv.2 实时信号中心
"""
import streamlit as st
import pandas as pd
from pathlib import Path
import sys
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from live_signal import (
    generate_signals, generate_multi_signals,
    push_to_file, TradeSignal, SignalReport,
)
from realism import RealismConfig
from data_loader import DataLoader

st.set_page_config(page_title="实时信号 - Rock Quant", layout="wide")
st.title("实时信号中心")
st.caption("每日盘后自动跑策略 → 输出交易信号")

# ============ 侧边栏配置 ============
with st.sidebar:
    st.header("信号配置")

    data_source = st.selectbox("数据源", ["simulated", "akshare", "tushare"], index=0)

    st.subheader("观察列表")
    default_watch = "000001.SZ:平安银行\n600519.SH:贵州茅台\n000300.SH:沪深300\n000905.SH:中证500"
    watch_text = st.text_area("代码:名称（每行一个）", value=default_watch, height=150)

    st.subheader("策略选择")
    from strategies import get_all_strategies
    all_strategies = get_all_strategies()
    strategy_name = st.selectbox("策略", all_strategies, index=0)

    st.subheader("真实模式")
    realism_on = st.checkbox("启用真实模式", value=True)

    run_btn = st.button("生成信号", type="primary", use_container_width=True)

# ============ 解析观察列表 ============
watchlist = {}
for line in watch_text.strip().splitlines():
    if ":" in line:
        code, name = line.strip().split(":", 1)
        watchlist[code.strip()] = name.strip()
    elif line.strip():
        watchlist[line.strip()] = line.strip()

# ============ 生成信号 ============
if run_btn or "signal_report" in st.session_state:
    if run_btn:
        with st.spinner("正在生成信号..."):
            r_cfg = RealismConfig(enable=realism_on)
            report = generate_multi_signals(
                watchlist, strategy_name,
                data_source=data_source,
                realism_config=r_cfg,
            )
            st.session_state["signal_report"] = report
    else:
        report = st.session_state["signal_report"]

    # ============ 展示报告 ============
    st.markdown(f"### 信号报告 - {report.date}")

    # 数据新鲜度
    freshness_map = {
        "fresh": ("数据最新", "✅"),
        "stale": ("数据过期", "⚠️"),
        "no_data": ("无数据", "❌"),
        "unknown": ("未知", "❓"),
    }
    label, icon = freshness_map.get(report.data_freshness, ("未知", "❓"))
    st.metric("数据新鲜度", f"{icon} {label}")

    if report.error:
        st.error(f"错误: {report.error}")

    # 信号表格
    if report.signals:
        rows = []
        for s in report.signals:
            action_icon = {"buy": "🟢 买入", "sell": "🔴 卖出", "hold": "⚪ 观望"}.get(s.action, s.action)
            rows.append({
                "标的": f"{s.name}({s.symbol})",
                "信号": action_icon,
                "仓位": f"{s.position:.0%}",
                "价格": f"{s.price:.2f}",
                "日期": s.date,
                "策略": s.strategy,
                "理由": s.reason or "-",
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # 导出
        out_text = report.summary()
        st.download_button(
            "下载信号报告",
            data=out_text,
            file_name=f"signal_{report.date}.txt",
            mime="text/plain",
        )
    else:
        st.info("今日无交易信号")

    # ============ 历史信号文件 ============
    st.markdown("---")
    st.subheader("历史信号文件")
    sig_dir = Path("signals")
    if sig_dir.exists():
        files = sorted(sig_dir.glob("*.txt"), reverse=True)[:10]
        if files:
            for f in files:
                with st.expander(f.name):
                    st.code(f.read_text(encoding="utf-8"), language="plaintext")
        else:
            st.caption("暂无历史信号文件")
    else:
        st.caption("暂无历史信号文件")

st.markdown("---")
st.caption("Rock Quant 2.7 - Lv.2 实时信号中心")
