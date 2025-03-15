"""
Simple entry point for the Flask app that checks bot status.
This is used for the gunicorn workflow only, and does NOT start the bot.
The bot runs separately in the telegram_bot workflow from main.py.
"""
import os
import logging
import socket
from flask import Flask, jsonify

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Bot status check port (same as mutex port in main.py)
BOT_MUTEX_PORT = 49152

@app.route('/')
def home():
    """Return bot status by checking if mutex socket is in use"""
    # Check if the bot mutex port is in use (indicating bot is running)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # If this connection succeeds, the port is not in use, so bot is NOT running
        sock.bind(('localhost', BOT_MUTEX_PORT))
        sock.close()
        bot_status = "stopped"
        message = "Telegram Bot is not running. Please start the telegram_bot workflow."
    except socket.error:
        # If we get an error, the port is in use, so bot IS running
        bot_status = "running"
        message = "Telegram Bot is running. No web interface available."
    
    return jsonify({
        "status": bot_status,
        "message": message
    })

# This will make it compatible with how gunicorn starts the app
# by importing main as a module and accessing its app attribute
try:
    # Try to load from main, will fail and we'll use our own app
    from main import app as main_app
    app = main_app
except (ImportError, AttributeError):
    # Just use our own app
    logger.info("Using app.py Flask app instead of main:app")