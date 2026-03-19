"""
Notification Module
通知模組 - 支援 LINE Notify、Email、Telegram
"""

import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

from config import NOTIFICATION

logger = logging.getLogger(__name__)


class Notifier:
    """多管道通知發送器"""

    def __init__(self, config: dict = None):
        self.config = config or NOTIFICATION

    def send_screening_report(self, scores: list, run_date: str = "") -> bool:
        """發送篩選結果報告"""
        if not run_date:
            run_date = datetime.now().strftime("%Y-%m-%d %H:%M")

        if not scores:
            message = f"📊 台股巴菲特篩選報告 ({run_date})\n\n本次篩選無符合條件標的。"
        else:
            message = self._format_report(scores, run_date)

        success = False

        # LINE Notify
        token = self.config.get("line_notify_token", "")
        if token:
            success |= self._send_line_notify(message, token)

        # Email
        if self.config.get("email_enabled"):
            success |= self._send_email(
                subject=f"台股巴菲特篩選報告 {run_date}",
                body=message
            )

        # Telegram
        if self.config.get("telegram_enabled"):
            success |= self._send_telegram(message)

        if not token and not self.config.get("email_enabled") and not self.config.get("telegram_enabled"):
            # 沒有設定通知管道，只印到 console
            print("\n" + "=" * 60)
            print(message)
            print("=" * 60)
            return True

        return success

    # ----------------------------------------------------------
    # 格式化報告
    # ----------------------------------------------------------
    def _format_report(self, scores: list, run_date: str) -> str:
        """格式化篩選報告"""
        lines = [
            f"📊 台股巴菲特篩選報告",
            f"🗓 {run_date}",
            f"{'─' * 40}",
            f"✅ 篩選通過: {len(scores)} 檔",
            "",
        ]

        for rank, s in enumerate(scores, 1):
            passed_emoji = "🌟" if s.total_score >= 80 else "✅" if s.total_score >= 70 else "📌"
            lines.append(
                f"{passed_emoji} #{rank} [{s.stock_id}] {s.name}\n"
                f"   總分: {s.total_score:.1f}/100  通過: {s.passed_criteria}/7\n"
                f"   ROE:{s.roe_avg:.1f}%  P/E:{s.pe_ratio:.1f}  P/B:{s.pb_ratio:.2f}  "
                f"負債:{s.debt_ratio:.0f}%  殖利率:{s.dividend_yield:.1f}%\n"
                f"   現價: {s.current_price:.2f}  毛利率:{s.gross_margin:.1f}%  "
                f"營收成長:{s.revenue_growth:.1f}%"
            )

        lines += [
            "",
            f"{'─' * 40}",
            "💡 聲明: 本報告僅供參考，不構成投資建議。",
            "   投資有風險，請自行判斷進出場時機。",
        ]

        return "\n".join(lines)

    # ----------------------------------------------------------
    # LINE Notify
    # ----------------------------------------------------------
    def _send_line_notify(self, message: str, token: str) -> bool:
        """發送 LINE Notify 通知"""
        url = "https://notify-api.line.me/api/notify"
        headers = {"Authorization": f"Bearer {token}"}

        # LINE 訊息長度限制 1000 字元，分段發送
        chunks = self._split_message(message, max_len=900)
        success = True

        for chunk in chunks:
            try:
                resp = requests.post(
                    url,
                    headers=headers,
                    data={"message": chunk},
                    timeout=15
                )
                if resp.status_code == 200:
                    logger.info("LINE Notify 發送成功")
                else:
                    logger.error(f"LINE Notify 失敗: {resp.status_code} {resp.text}")
                    success = False
            except Exception as e:
                logger.error(f"LINE Notify 例外: {e}")
                success = False

        return success

    # ----------------------------------------------------------
    # Email
    # ----------------------------------------------------------
    def _send_email(self, subject: str, body: str) -> bool:
        """發送 Email 通知"""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.config["email_sender"]
            msg["To"] = ", ".join(self.config["email_recipients"])

            # 純文字版
            msg.attach(MIMEText(body, "plain", "utf-8"))

            # HTML 版 (格式更美觀)
            html_body = self._to_html(body)
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            with smtplib.SMTP(self.config["smtp_host"], self.config["smtp_port"]) as server:
                server.ehlo()
                server.starttls()
                server.login(self.config["email_sender"], self.config["email_password"])
                server.sendmail(
                    self.config["email_sender"],
                    self.config["email_recipients"],
                    msg.as_string()
                )
            logger.info("Email 發送成功")
            return True
        except Exception as e:
            logger.error(f"Email 發送失敗: {e}")
            return False

    def _to_html(self, text: str) -> str:
        """將純文字轉換為 HTML"""
        rows = []
        for line in text.split("\n"):
            line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if line.startswith("📊") or line.startswith("✅") or line.startswith("🌟"):
                rows.append(f"<p><b>{line}</b></p>")
            elif line.startswith("─"):
                rows.append("<hr>")
            else:
                rows.append(f"<p>{line}</p>")
        return f"""
        <html><body style="font-family: monospace; font-size: 14px;">
        {''.join(rows)}
        </body></html>
        """

    # ----------------------------------------------------------
    # Telegram
    # ----------------------------------------------------------
    def _send_telegram(self, message: str) -> bool:
        """發送 Telegram Bot 通知"""
        token = self.config.get("telegram_bot_token", "")
        chat_id = self.config.get("telegram_chat_id", "")
        if not token or not chat_id:
            return False

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        chunks = self._split_message(message, max_len=4000)
        success = True

        for chunk in chunks:
            try:
                resp = requests.post(
                    url,
                    json={"chat_id": chat_id, "text": chunk, "parse_mode": "HTML"},
                    timeout=15
                )
                if resp.status_code != 200:
                    logger.error(f"Telegram 失敗: {resp.text}")
                    success = False
            except Exception as e:
                logger.error(f"Telegram 例外: {e}")
                success = False

        return success

    # ----------------------------------------------------------
    # 工具方法
    # ----------------------------------------------------------
    @staticmethod
    def _split_message(message: str, max_len: int = 900) -> list[str]:
        """將長訊息分段"""
        if len(message) <= max_len:
            return [message]
        chunks = []
        while message:
            if len(message) <= max_len:
                chunks.append(message)
                break
            # 在 max_len 前找換行點
            split_at = message.rfind("\n", 0, max_len)
            if split_at == -1:
                split_at = max_len
            chunks.append(message[:split_at])
            message = message[split_at:].lstrip("\n")
        return chunks
