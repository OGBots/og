"""
Main Telegram bot module with enhanced error handling and restart capabilities
"""
import logging
import asyncio
import signal
import time
import sys
import traceback
from telegram.ext import Application, ConversationHandler

import config
from handlers.admin_handlers import register_admin_handlers
from handlers.user_handlers import register_user_handlers
from handlers.callback_handlers import register_callback_handlers

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global settings for bot management
MAX_RETRIES = 5
RETRY_INTERVAL = 5  # seconds
SHUTDOWN_FLAG = False
CURRENT_APPLICATION = None  # Global reference to current application

async def bot_error_handler(update, context):
    """Enhanced error handler for bot updates"""
    error_message = str(context.error)
    logger.error(f"Update {update} caused error: {error_message}")
    
    # Log full traceback for better debugging
    error_traceback = traceback.format_exception(
        type(context.error), context.error, context.error.__traceback__
    )
    logger.error(f"Error traceback: {''.join(error_traceback)}")
    
    # Send more informative message to user if possible
    if update and update.effective_chat:
        try:
            user_message = (
                "❌ Error: An issue occurred while processing your request.\n"
                f"Details: {error_message}\n\n"
                "Please try the following:\n"
                "1. Wait a few seconds and try again\n"
                "2. Use /start to restart the conversation\n"
                "3. Use /help for command guidance"
            )
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=user_message,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Failed to send error message to user: {e}")

def signal_handler(sig, frame):
    """Handle termination signals gracefully"""
    global SHUTDOWN_FLAG
    logger.info(f"Received signal {sig}, initiating shutdown...")
    SHUTDOWN_FLAG = True

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def create_bot():
    """Create and configure bot application with better error handling"""
    try:
        # Create application
        application = Application.builder().token(config.BOT_TOKEN).build()
        
        # Register handlers
        register_admin_handlers(application)
        register_user_handlers(application)
        register_callback_handlers(application)
        
        # Set up error handler
        application.add_error_handler(bot_error_handler)
        
        return application
    except Exception as e:
        logger.error(f"Failed to create bot application: {e}")
        traceback.print_exc()
        return None

async def run_bot_async():
    """Run the bot asynchronously with restart capability"""
    global CURRENT_APPLICATION, SHUTDOWN_FLAG
    
    retries = 0
    while not SHUTDOWN_FLAG and retries < MAX_RETRIES:
        try:
            # Get bot application
            application = create_bot()
            if not application:
                raise Exception("Failed to create application")
            
            CURRENT_APPLICATION = application
            
            # Start the bot with enhanced error handling
            await application.initialize()
            await application.start()
            
            # Start polling with optimized parameters for better reliability
            # This helps prevent the bot from getting stuck when receiving multiple commands
            await application.updater.start_polling(
                allowed_updates=['message', 'callback_query', 'my_chat_member'],
                drop_pending_updates=True,
                read_timeout=10,
                write_timeout=10,
                connect_timeout=10,
                pool_timeout=5
            )
            
            logger.info("Bot successfully started and is polling for updates")
            
            # Reset retries when successfully started
            retries = 0
            
            # Keep the bot running until shutdown is requested
            while not SHUTDOWN_FLAG:
                await asyncio.sleep(1)
                
                # Periodically check if polling is still active
                if not application.updater.running:
                    logger.warning("Updater stopped unexpectedly, attempting to restart...")
                    try:
                        await application.updater.start_polling(
                            allowed_updates=['message', 'callback_query', 'my_chat_member'],
                            drop_pending_updates=False
                        )
                        logger.info("Updater successfully restarted")
                    except Exception as e:
                        logger.error(f"Failed to restart updater: {e}")
                        raise  # Let outer loop handle the restart
                        
                # Periodic check for bot health
                # Add any additional health checks here if needed
                pass
            
            # Graceful shutdown
            logger.info("Gracefully shutting down bot...")
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
            logger.info("Bot has been shut down")
            return
            
        except Exception as e:
            retries += 1
            logger.error(f"Error in bot operation (attempt {retries}/{MAX_RETRIES}): {e}")
            traceback.print_exc()
            
            # Clean up if partially started
            if CURRENT_APPLICATION:
                try:
                    await CURRENT_APPLICATION.updater.stop()
                    await CURRENT_APPLICATION.stop()
                    await CURRENT_APPLICATION.shutdown()
                except Exception as cleanup_e:
                    logger.error(f"Error during cleanup: {cleanup_e}")
            
            CURRENT_APPLICATION = None
            
            # Wait before retrying
            if not SHUTDOWN_FLAG and retries < MAX_RETRIES:
                logger.info(f"Retrying in {RETRY_INTERVAL} seconds...")
                await asyncio.sleep(RETRY_INTERVAL)
    
    if retries >= MAX_RETRIES:
        logger.critical(f"Failed to start bot after {MAX_RETRIES} attempts. Giving up.")

def run_bot():
    """Run the bot with proper error handling and logging"""
    logger.info("Starting Telegram Bot")
    
    try:
        # Create a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the bot asynchronously
        loop.run_until_complete(run_bot_async())
    except Exception as e:
        logger.critical(f"Fatal error in bot runner: {e}")
        traceback.print_exc()
    finally:
        logger.info("Bot runner has finished")
