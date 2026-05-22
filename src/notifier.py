"""
notifier.py - Lv.6 信号推送通道（飞书 / 邮件 / 文件）
"""
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, List
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from live_signal import SignalReport, TradeSignal


def _to_feishu_text(report: SignalReport) -> str:
    """构造飞书富文本内容"""
    lines = [
        f"📊 Rock Quant 每日信号 - {report.date}",
        f"数据源: {report.data_source} | 策略: {report.strategy}",
        f"数据新鲜度: {report.data_freshness}",
        "-" * 30,
    ]
    buy = [s for s in report.signals if s.action == "buy"]
    sell = [s for s in report.signals if s.action == "sell"]
    hold = [s for s in report.signals if s.action == "hold"]

    if buy:
        lines.append(f"🟢 买入信号 ({len(buy)})")
        for s in buy:
            lines.append(f"  {s.name}({s.symbol}) 仓{s.position:.0%} @{s.price:.2f}")
    if sell:
        lines.append(f"🔴 卖出信号 ({len(sell)})")
        for s in sell:
            lines.append(f"  {s.name}({s.symbol}) 仓{s.position:.0%} @{s.price:.2f}")
    if hold:
        lines.append(f"⚪ 持仓观望 ({len(hold)})")
    if not report.signals:
        lines.append("今日无信号")
    if report.error:
        lines.append(f"⚠️ {report.error}")

    return "\n".join(lines)


def push_to_feishu_webhook(report: SignalReport, webhook_url: str,
                            secret: Optional[str] = None) -> Dict:
    """
    推送到飞书自定义机器人 webhook
    webhook_url: 飞书群机器人 webhook 地址
    """
    text = _to_feishu_text(report)
    payload = {
        "msg_type": "text",
        "content": {"text": text},
    }
    # 若启用签名校验
    if secret:
        import hmac
        import hashlib
        import base64
        import time
        timestamp = str(int(time.time()))
        string_to_sign = f"{timestamp}\n{secret}"
        sign = base64.b64encode(
            hmac.new(string_to_sign.encode(), digestmod=hashlib.sha256).digest()
        ).decode()
        payload["timestamp"] = timestamp
        payload["sign"] = sign

    try:
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {"status": "ok", "response": resp.read().decode()}
    except urllib.error.URLError as e:
        return {"status": "error", "error": str(e)}


def push_to_email(report: SignalReport, smtp_config: Dict,
                  to_addrs: List[str]) -> Dict:
    """推送邮件（按需用）"""
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.header import Header

        msg = MIMEText(report.summary(), "plain", "utf-8")
        msg["Subject"] = Header(f"Rock Quant 信号 {report.date}", "utf-8")
        msg["From"] = smtp_config["from"]
        msg["To"] = ", ".join(to_addrs)

        with smtplib.SMTP_SSL(smtp_config["host"], smtp_config.get("port", 465)) as s:
            s.login(smtp_config["user"], smtp_config["password"])
            s.sendmail(smtp_config["from"], to_addrs, msg.as_string())

        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def push_all(report: SignalReport, channels: Dict) -> Dict[str, Dict]:
    """
    统一推送入口
    channels = {
        "feishu": {"webhook": "...", "secret": "..."},
        "email":  {"smtp": {...}, "to": [...]},
        "file":   {"path": "signals/latest.txt"}
    }
    """
    results = {}
    if "feishu" in channels:
        cfg = channels["feishu"]
        results["feishu"] = push_to_feishu_webhook(
            report, cfg["webhook"], cfg.get("secret"))
    if "email" in channels:
        cfg = channels["email"]
        results["email"] = push_to_email(report, cfg["smtp"], cfg["to"])
    if "file" in channels:
        from live_signal import push_to_file
        path = push_to_file(report, channels["file"]["path"])
        results["file"] = {"status": "ok", "path": path}
    return results
