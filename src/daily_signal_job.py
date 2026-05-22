"""
daily_signal_job.py - 每日盘后信号任务（cron 调度入口）

用法：
  python src/daily_signal_job.py                      # 默认配置
  python src/daily_signal_job.py --source akshare     # 指定数据源
  python src/daily_signal_job.py --push feishu        # 推送飞书
  python src/daily_signal_job.py --push file          # 推送文件

也可由 OpenClaw cron 每日 15:30 触发：
  python /path/to/Wanyan-quant/src/daily_signal_job.py --push feishu
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from live_signal import generate_multi_signals, push_to_file, push_to_console
from realism import RealismConfig
from notifier import push_to_feishu_webhook, push_all


# 默认观察列表
DEFAULT_WATCHLIST = {
    "000001.SZ": "平安银行",
    "600519.SH": "贵州茅台",
    "000300.SH": "沪深300",
    "000905.SH": "中证500",
    "000016.SH": "上证50",
}

DEFAULT_STRATEGIES = ["双均线策略", "MACD策略"]


def run_daily_job(
    watchlist: dict = None,
    strategies: list = None,
    data_source: str = "akshare",
    push_channels: list = None,
    feishu_webhook: str = "",
    feishu_secret: str = "",
):
    """每日信号生成主流程"""
    watchlist = watchlist or DEFAULT_WATCHLIST
    strategies = strategies or DEFAULT_STRATEGIES
    push_channels = push_channels or ["console"]

    today = datetime.now().strftime("%Y-%m-%d")
    print(f"[{today}] Rock Quant 每日信号任务启动")

    all_reports = []
    for strategy_name in strategies:
        report = generate_multi_signals(
            watchlist, strategy_name,
            data_source=data_source,
            realism_config=RealismConfig(enable=True),
        )
        all_reports.append(report)

        # 合并信号
        if all_reports and all_reports[0] is not report:
            all_reports[0].signals.extend(report.signals)

    # 使用第一个 report 作为主报告（带所有策略的信号）
    main_report = all_reports[0] if all_reports else SignalReport(date=today)

    # 推送
    channels = {}
    if "console" in push_channels:
        push_to_console(main_report)
    if "file" in push_channels:
        channels["file"] = {"path": "signals/latest.txt"}
    if "feishu" in push_channels and feishu_webhook:
        channels["feishu"] = {"webhook": feishu_webhook, "secret": feishu_secret}

    if channels:
        results = push_all(main_report, channels)
        for ch, r in results.items():
            status = r.get("status", "unknown")
            print(f"  推送 {ch}: {status}")
            if r.get("error"):
                print(f"    错误: {r['error']}")

    return main_report


def main():
    parser = argparse.ArgumentParser(description="Rock Quant 每日信号任务")
    parser.add_argument("--source", default="akshare", help="数据源: akshare/tushare/simulated")
    parser.add_argument("--push", nargs="+", default=["console"],
                        help="推送通道: console/file/feishu/email")
    parser.add_argument("--feishu-webhook", default="", help="飞书 Webhook URL")
    parser.add_argument("--feishu-secret", default="", help="飞书签名密钥")
    args = parser.parse_args()

    run_daily_job(
        data_source=args.source,
        push_channels=args.push,
        feishu_webhook=args.feishu_webhook,
        feishu_secret=args.feishu_secret,
    )


if __name__ == "__main__":
    main()
