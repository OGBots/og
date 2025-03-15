"""
Configuration settings for the Telegram Bot
"""
import os
from datetime import datetime, timedelta

# Bot Token
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Bot name and styling
BOT_NAME = "OG PREDICTOR⚡"
BOT_LOGO = "⚡"
BOT_STYLE = {
    "welcome_emoji": "⚡",
    "success_emoji": "✅",
    "error_emoji": "❌",
    "warning_emoji": "⚠️",
    "info_emoji": "ℹ️",
    "prediction_emoji": "🔮",
    "cooldown_emoji": "⏱",
    "result_emoji": "🎯",
    "app_emoji": "📱",
    "game_emoji": "🎰",
    "pattern_emoji": "🔍",
    "admin_emoji": "🛠",
    "free_emoji": "🆓",
    "pro_emoji": "💥",
    "channel_emoji": "📢",
    "separator": "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
}

# Default settings
DEFAULT_FREE_PREDICTIONS = 5
DEFAULT_FREE_PERIOD_DAYS = 7
DEFAULT_REQUIRED_CHANNEL = ""  # Will be set by admin
DEFAULT_LOG_CHANNEL = ""  # Will be set by admin

# App and Game defaults
DEFAULT_APPS = ["1win", "Bet365", "Fun88"]
DEFAULT_GAMES = {
    "WINGO": {
        "cooldown": 0,  # 1 minute
        "patterns": {},
        "result_format": ["Big", "Small"]
    },
    "K3": {
        "cooldown": 0,  # 3 minutes
        "patterns": {},
        "result_format": ["Big Odd", "Big Even", "Small Odd", "Small Even"]
    }
}

# Admin IDs (list of Telegram user IDs who can access admin commands)
ADMIN_IDS = [6459253633]  # @SatsNova
