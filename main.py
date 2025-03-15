"""
Main entry point for the Telegram Gambling Prediction Bot
with mutex locking to prevent multiple instances
"""
import os
import logging
import threading
import time
import socket
import sys
import atexit
import errno
from flask import Flask
from bot import run_bot

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Set admin credentials
ADMIN_ID = 6459253633
ADMIN_USERNAME = "@SatsNova"

# Bot thread handle
bot_thread = None
bot_running = False
MUTEX_SOCKET = None
MUTEX_PORT = 49152  # Choose a port for mutex
MUTEX_LOCK_FILE = "/tmp/telegram_bot_mutex.lock"

# Create app for gunicorn compatibility
app = Flask(__name__)

@app.route('/')
def home():
    """Return bot status"""
    return "Telegram Bot Status Page - Please use app.py instead"

def check_process_running(pid):
    """Check if a process with the given PID is running"""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False

def acquire_mutex():
    """Try to acquire mutex to ensure only one bot instance runs"""
    global MUTEX_SOCKET
    
    # First check the file-based mutex
    try:
        # Check if the lock file exists and contains a valid PID
        if os.path.exists(MUTEX_LOCK_FILE):
            try:
                with open(MUTEX_LOCK_FILE, "r") as f:
                    pid = int(f.read().strip())
                
                # Check if the process with this PID is still running
                if check_process_running(pid):
                    logger.warning(f"Lock file exists with PID {pid} and process is still running")
                    return False
                else:
                    logger.warning(f"Lock file exists with PID {pid} but process is not running, removing stale lock")
                    os.remove(MUTEX_LOCK_FILE)
            except (ValueError, IOError) as e:
                logger.warning(f"Error reading lock file: {e}, removing")
                try:
                    os.remove(MUTEX_LOCK_FILE)
                except:
                    pass
        
        # Create a new lock file with our PID
        with open(MUTEX_LOCK_FILE, "w") as f:
            f.write(str(os.getpid()))
        logger.info(f"Created lock file with PID {os.getpid()}")
    except Exception as e:
        logger.error(f"Error managing lock file: {e}")
    
    # Now also do the socket-based mutex as additional protection
    try:
        # Clean up any existing socket
        if MUTEX_SOCKET:
            try:
                MUTEX_SOCKET.close()
            except:
                pass
            MUTEX_SOCKET = None
        
        # Try to forcibly release any existing mutex that might be stuck
        try:
            # Force the release with SO_REUSEADDR
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(1)
            try:
                sock.bind(('localhost', MUTEX_PORT))
                sock.close()
            except:
                pass
        except:
            pass
        
        # Now create our own socket
        MUTEX_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        MUTEX_SOCKET.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            MUTEX_SOCKET.bind(('localhost', MUTEX_PORT))
            MUTEX_SOCKET.listen(1)  # Actually listen on the socket to prevent others from binding
            logger.info(f"Successfully acquired mutex on port {MUTEX_PORT}")
            return True
        except socket.error as e:
            logger.warning(f"Could not acquire mutex on port {MUTEX_PORT}: {e}")
            return False
    except Exception as e:
        logger.error(f"Error setting up socket mutex: {e}")
        return False

def release_mutex():
    """Release the mutex socket and file lock"""
    global MUTEX_SOCKET
    
    # Release socket mutex
    if MUTEX_SOCKET:
        try:
            MUTEX_SOCKET.close()
            logger.info("Released mutex socket")
        except Exception as e:
            logger.error(f"Error releasing mutex socket: {e}")
        MUTEX_SOCKET = None
    
    # Release file mutex
    try:
        # Only remove the lock file if it contains our PID
        if os.path.exists(MUTEX_LOCK_FILE):
            try:
                with open(MUTEX_LOCK_FILE, "r") as f:
                    pid = int(f.read().strip())
                
                if pid == os.getpid():
                    os.remove(MUTEX_LOCK_FILE)
                    logger.info(f"Removed lock file for PID {pid}")
            except (ValueError, IOError) as e:
                logger.warning(f"Error reading lock file during cleanup: {e}")
                try:
                    os.remove(MUTEX_LOCK_FILE)
                except:
                    pass
    except Exception as e:
        logger.error(f"Error removing lock file: {e}")
        
    # Extra cleanup - try to forcibly free the port just to be sure
    try:
        # Force the release with SO_REUSEADDR
        cleanup_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cleanup_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        cleanup_socket.settimeout(1)
        try:
            cleanup_socket.bind(('localhost', MUTEX_PORT))
            cleanup_socket.close()
            logger.info(f"Force-released mutex port {MUTEX_PORT} during cleanup")
        except:
            pass
    except:
        pass

# Register mutex release on exit
atexit.register(release_mutex)

def ensure_bot_running():
    """Ensure the bot is running, with retry logic"""
    global bot_thread, bot_running
    
    # Check for bot token
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set. Please set it and try again.")
        return
    
    # Try to acquire mutex (if we don't have it already)
    if not MUTEX_SOCKET and not acquire_mutex():
        logger.info("Mutex acquisition failed - not starting bot instance")
        return
    
    # If bot thread exists but is not alive, clean it up
    if bot_thread and not bot_thread.is_alive():
        logger.warning("Bot thread died, restarting...")
        bot_thread = None
        bot_running = False
        
    # Start a new bot thread if needed
    if not bot_thread:
        try:
            bot_thread = threading.Thread(target=run_bot, name="TelegramBotThread")
            bot_thread.daemon = True
            bot_thread.start()
            bot_running = True
            logger.info("Bot thread started successfully")
        except Exception as e:
            logger.error(f"Error starting bot thread: {e}")
            bot_running = False

def monitor_bot():
    """Monitor the bot and restart if needed"""
    while True:
        try:
            ensure_bot_running()
        except Exception as e:
            logger.error(f"Error in bot monitor: {e}")
        time.sleep(30)  # Check every 30 seconds

def main():
    """Main function to run the bot"""
    logger.info("Starting Telegram Gambling Prediction Bot")
    
    # Try to acquire mutex
    if not acquire_mutex():
        logger.warning("Another bot instance is already running. Exiting.")
        return
    
    # Start the bot
    ensure_bot_running()
    
    # Start the monitoring thread
    monitor_thread = threading.Thread(target=monitor_bot, name="BotMonitorThread")
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # Keep main thread alive (only needed for direct execution, not when imported)
    try:
        while bot_thread and bot_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")

# Start the bot immediately when this module is imported (if mutex available)
ensure_bot_running()

if __name__ == "__main__":
    main()
