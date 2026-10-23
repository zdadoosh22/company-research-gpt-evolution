"""
Notification Dispatcher - Multi-Channel Alert Router (Discord, Telegram, Windows Toast)
Isolated Tactical Laboratory: daytrading/tools/notification_dispatcher.py

Dispatches institutional trade execution signals, regime transitions, and emergency cuts across:
1. Discord Webhooks: Rich embedded cards with color-coded regime headers, brackets, and risk metrics.
2. Telegram Bot API: MarkdownV2 formatted tactical execution alerts.
3. Windows Desktop Toast: Native Windows 10/11 notification banners via PowerShell.
4. CLI Banner Fallback: High-contrast console formatting for headless terminal operation.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request

SCRIPT_DIR = Path(__file__).resolve().parent
DAYTRADING_ROOT = SCRIPT_DIR.parent
CONFIG_DIR = DAYTRADING_ROOT / "config"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
WEBHOOK_CONFIG_FILE = CONFIG_DIR / "alert_webhooks.json"


class NotificationDispatcher:
    def __init__(self, config_path: Path = WEBHOOK_CONFIG_FILE):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> dict:
        if self.config_path.exists():
            try:
                return json.loads(self.config_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "discord_webhook_url": os.environ.get("TACTICAL_DISCORD_WEBHOOK", ""),
            "telegram_bot_token": os.environ.get("TACTICAL_TELEGRAM_BOT_TOKEN", ""),
            "telegram_chat_id": os.environ.get("TACTICAL_TELEGRAM_CHAT_ID", ""),
            "desktop_toasts_enabled": True
        }

    def dispatch_trade_signal(
        self,
        ticker: str,
        signal_type: str,  # "ENTRY_LONG", "STAGE_1_TAKE_PROFIT", "STAGE_2_RUNNER_EXIT", "EMERGENCY_PREMARKET_CUT"
        spot: float,
        stop_loss: float,
        stage_1_target: float,
        stage_2_target: float,
        position_size_gbp: float,
        shares: float,
        regime_state: str = "BULL_TREND",
        is_uk: bool = False,
        extra_note: str = ""
    ) -> dict:
        """Dispatches rich execution alert across all configured channels."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        sym = "£" if is_uk else "$"

        # Color coding for Discord embeds
        color_map = {
            "BULL_TREND": 0x00F59B,       # Neon Green
            "BULL_VOLATILE": 0xFFB800,    # Neon Amber
            "BEAR_CORRECTION": 0xFF8C00,  # Deep Amber
            "CRASH_PANIC": 0xFF2A5F       # Crimson
        }
        embed_color = color_map.get(regime_state, 0x00E5FF)

        title = f"TACTICAL SIGNAL: {signal_type} -> {ticker}"
        if is_uk:
            title += " [0% FX UK ISA]"

        summary_lines = [
            f"**Ticker**: `{ticker}` | **Regime**: `{regime_state}`",
            f"**Spot Entry**: `{sym}{spot:.2f}` | **Position Size**: `£{position_size_gbp:.2f}` (~{shares} units)",
            f"**Hard Stop**: `{sym}{stop_loss:.2f}` ({((stop_loss - spot)/spot)*100:+.1f}%)",
            f"**Stage 1 TP (50%)**: `{sym}{stage_1_target:.2f}` ({((stage_1_target - spot)/spot)*100:+.1f}%)",
            f"**Stage 2 TP / Trail**: `{sym}{stage_2_target:.2f}` ({((stage_2_target - spot)/spot)*100:+.1f}%)"
        ]
        if extra_note:
            summary_lines.append(f"**Note**: {extra_note}")

        payload_text = "\n".join(summary_lines)

        results = {
            "timestamp": timestamp,
            "discord_sent": False,
            "telegram_sent": False,
            "desktop_sent": False
        }

        # 1. Discord Webhook
        discord_url = self.config.get("discord_webhook_url")
        if discord_url and discord_url.startswith("http"):
            try:
                discord_payload = {
                    "username": "Aegis Tactical Dispatcher",
                    "avatar_url": "https://cdn-icons-png.flaticon.com/512/3135/3135715.png",
                    "embeds": [{
                        "title": title,
                        "description": payload_text,
                        "color": embed_color,
                        "footer": {"text": f"Trading 212 ISA Engine | {timestamp}"}
                    }]
                }
                req = urllib.request.Request(
                    discord_url,
                    data=json.dumps(discord_payload).encode("utf-8"),
                    headers={"Content-Type": "application/json", "User-Agent": "AegisTactical/1.0"}
                )
                with urllib.request.urlopen(req, timeout=4) as response:
                    results["discord_sent"] = response.status in (200, 204)
            except Exception as e:
                results["discord_error"] = str(e)

        # 2. Telegram Bot
        tg_token = self.config.get("telegram_bot_token")
        tg_chat = self.config.get("telegram_chat_id")
        if tg_token and tg_chat:
            try:
                tg_url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
                tg_payload = {
                    "chat_id": tg_chat,
                    "text": f"*{title}*\n\n{payload_text}",
                    "parse_mode": "Markdown"
                }
                req = urllib.request.Request(
                    tg_url,
                    data=json.dumps(tg_payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=4) as response:
                    results["telegram_sent"] = response.status == 200
            except Exception as e:
                results["telegram_error"] = str(e)

        # 3. Windows Desktop Toast Notification
        if self.config.get("desktop_toasts_enabled", True) and sys.platform == "win32":
            try:
                ps_script = f"""
                [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
                $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
                $texts = $template.GetElementsByTagName("text")
                $texts.Item(0).AppendChild($template.CreateTextNode("{title}")) > $null
                $texts.Item(1).AppendChild($template.CreateTextNode("Spot: {sym}{spot:.2f} | Size: £{position_size_gbp:.2f} | Stop: {sym}{stop_loss:.2f}")) > $null
                $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
                [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Aegis Tactical Engine").Show($toast)
                """
                subprocess.Popen(["powershell", "-NoProfile", "-Command", ps_script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                results["desktop_sent"] = True
            except Exception as e:
                results["desktop_error"] = str(e)

        # CLI Display Fallback
        print("\n" + "=" * 70)
        print(f"   [DISPATCHER ALERT] {title}")
        print("=" * 70)
        print(payload_text.replace("**", "").replace("`", ""))
        print("=" * 70 + "\n")

        return results


def main():
    parser = argparse.ArgumentParser(description="Multi-Channel Notification Dispatcher")
    parser.add_argument("--test", action="store_true", help="Send test alert across channels")
    parser.add_argument("--ticker", type=str, default="NVDA", help="Ticker symbol")
    parser.add_argument("--price", type=float, default=135.0, help="Spot price")
    args = parser.parse_args()

    dispatcher = NotificationDispatcher()
    is_uk = args.ticker.endswith(".L")
    res = dispatcher.dispatch_trade_signal(
        ticker=args.ticker,
        signal_type="ENTRY_LONG",
        spot=args.price,
        stop_loss=args.price * (0.945 if not is_uk else 0.948),
        stage_1_target=args.price * (1.085 if not is_uk else 1.050),
        stage_2_target=args.price * (1.160 if not is_uk else 1.110),
        position_size_gbp=333.33,
        shares=round(333.33 / (args.price if is_uk else args.price * 0.7465), 2),
        regime_state="BULL_TREND",
        is_uk=is_uk,
        extra_note="High-conviction 5-Day Squeeze Breakout with RVOL 1.82x"
    )
    print("Dispatch result:", res)


if __name__ == "__main__":
    main()
