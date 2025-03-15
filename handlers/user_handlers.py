"""
User command handlers for the Telegram bot
"""
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler

from data_manager import data_manager
from pattern_matcher import PatternMatcher
from config import BOT_NAME, BOT_STYLE
from utils.helpers import (
    check_channel_membership, build_app_selector, build_game_selector,
    build_prediction_result_buttons, format_results_for_display
)

# Conversation states
SELECT_APP = 0
SELECT_GAME = 1
ENTER_RESULTS = 2

# User data context keys
APP_KEY = "selected_app"
GAME_KEY = "selected_game"
AWAITING_RESULTS_KEY = "awaiting_results"

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler for /start command"""
    user = update.effective_user
    user_id = user.id

    # Reset conversation state and user data for a fresh start
    context.user_data.clear()

    # Register user if not already registered
    data_manager.register_user(user_id, user.username)

    # Check channel membership
    if not await check_channel_membership(update, context):
        return ConversationHandler.END

    # Ensure the user exists before accessing
    user_data = data_manager.get_user(user_id) or {}
    free_predictions = user_data.get('free_predictions_left', 0)

    welcome_text = (
        f"{BOT_STYLE['welcome_emoji']} Welcome to {BOT_NAME} {BOT_STYLE['welcome_emoji']}\n"
        f"{BOT_STYLE['separator']}\n\n"
        f"Hello, {user.first_name}! {BOT_STYLE['prediction_emoji']}\n\n"
        f"I'll help you predict gambling game outcomes using advanced pattern recognition.\n\n"
        f"{BOT_STYLE['free_emoji']} FREE PREDICTIONS: You have {free_predictions} remaining.\n"
        f"{BOT_STYLE['pro_emoji']} PRO ACCESS: Buy our PRO plan for more!\n\n"
        f"This bot is fully powered by @SatsNova {BOT_STYLE['welcome_emoji']}\n\n"
        f"{BOT_STYLE['app_emoji']} Please select an app to start predicting:"
    )

    # Show app selection keyboard
    reply_markup = build_app_selector()
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

    return SELECT_APP

async def handle_predict(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler for /predict command"""
    # Reset conversation state and user data for a fresh start
    context.user_data.clear()

    # Register user
    user = update.effective_user
    user_id = user.id
    data_manager.register_user(user_id, user.username)

    # Check channel membership
    if not await check_channel_membership(update, context):
        return ConversationHandler.END

    # Ensure the user exists before accessing
    user_data = data_manager.get_user(user_id) or {'free_predictions': 0}

    predict_text = (
        f"{BOT_STYLE['prediction_emoji']} *{BOT_NAME} PREDICTION SERVICE* {BOT_STYLE['prediction_emoji']}\n"
        f"{BOT_STYLE['separator']}\n\n"
        f"{BOT_STYLE['free_emoji']} You have {user_data.get('free_predictions_left', 0)} free predictions remaining. Buy Pro Plan for unlimited predictions from @SatsNova {BOT_STYLE['welcome_emoji']}\n\n"
        f"{BOT_STYLE['app_emoji']} Select an app to continue:"
    )

    # Show app selection keyboard
    reply_markup = build_app_selector()
    await update.message.reply_text(predict_text, reply_markup=reply_markup, parse_mode='Markdown')

    return SELECT_APP

async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /help command"""
    help_text = (
        "🔮 *Gambling Prediction Bot Help* 🔮\n\n"
        "*Available Commands:*\n"
        "/start - Start using the bot\n"
        "/predict - Make a new prediction\n"
        "/help - Show this help message\n"
        "/buy - View pro plans and pricing\n\n"

        "*Getting Predictions:*\n"
        "1. Select an app (like BDWIN, DAMAN)\n"
        "2. Select a game (like WINGO, K3)\n"
        "3. Enter the last 10 results when prompted\n"
        "4. Get prediction for next result\n"
        "5. Verify prediction accuracy\n\n"

        "*User Levels:*\n"
        "🆓 *Free User:*\n"
        "- Limited predictions\n"
        "- Basic support\n\n"
        "💎 *Pro User:*\n"
        "- Unlimited predictions\n"
        "- Priority support\n\n"

        "*Important Notes:*\n"
        "• Must join required channel\n"
        "• This is not a hack or mod that claims things like 'Server Connected,' etc. All such claims are fake. There is no app or bot in the world that is actually connected to the game servers. I know this because I also develop these types of gambling games.\n"
        "• Use /buy to upgrade to Pro"
    )

    await update.message.reply_text(help_text, parse_mode='Markdown')

async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler for /cancel command"""
    await update.message.reply_text("Operation cancelled. Use /predict to make a new prediction.")
    return ConversationHandler.END

async def handle_results_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    """Handle user input of last results"""
    user_id = update.effective_user.id
    message_text = update.message.text

    # Check if we're awaiting results
    if not context.user_data.get(AWAITING_RESULTS_KEY, False):
        return None

    app = context.user_data.get(APP_KEY)
    game = context.user_data.get(GAME_KEY)

    if not app or not game:
        await update.message.reply_text("❌ Error: No app or game selected. Please use /predict to start over.")
        return ConversationHandler.END

    # Parse results
    results = [r.strip() for r in message_text.split(',')]

    # Validate results
    game_info = data_manager.get_all_games().get(game, {})
    valid_formats = game_info.get('result_format', [])

    invalid_results = [r for r in results if r not in valid_formats]
    if invalid_results:
        format_list = ', '.join(valid_formats)
        await update.message.reply_text(
            f"❌ Invalid results format. Please use only these values: {format_list}\n"
            f"Example: {', '.join(valid_formats[:3] if len(valid_formats) > 3 else valid_formats)}"
        )
        return ENTER_RESULTS

    # Store results
    data_manager.update_user_results(user_id, app, game, results)

    # Check if user can make a prediction (cooldown, free limits)
    can_predict, message, _ = data_manager.can_predict(user_id, game)

    if not can_predict:
        await update.message.reply_text(f"❌ {message}")
        return ConversationHandler.END

    # Make prediction
    patterns = game_info.get('patterns', {})
    prediction = PatternMatcher.predict(patterns, results)

    if prediction:
        # Record prediction
        data_manager.record_prediction(user_id, app, game, prediction)

        # Send prediction with verification buttons
        reply_markup = build_prediction_result_buttons(app, game)
        await update.message.reply_text(f"🔮 Prediction: {prediction}", reply_markup=reply_markup)
    else:
        await update.message.reply_text(
            "⚠️ No matching patterns found. Try with different results or contact the admin."
        )

    # Reset awaiting results flag
    context.user_data[AWAITING_RESULTS_KEY] = False

    return ConversationHandler.END

def build_result_selector(app: str, game: str, context: ContextTypes.DEFAULT_TYPE) -> InlineKeyboardMarkup:
    """Builds the inline keyboard for selecting results."""
    game_info = data_manager.get_all_games().get(game, {})
    valid_formats = game_info.get('result_format', [])

    result_keyboard = []
    for value in valid_formats:
        result_keyboard.append([
            InlineKeyboardButton(value, callback_data=f"result_{app}_{game}_{value}")
        ])
    result_keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_to_apps")])
    return InlineKeyboardMarkup(result_keyboard)


def register_user_handlers(application):
    """Register user command handlers"""
    # Create conversation handler for the prediction flow with enhanced handling
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", handle_start),
            CommandHandler("predict", handle_predict)
        ],
        states={
            SELECT_APP: [],  # App selection handled by callback handlers
            SELECT_GAME: [],  # Game selection handled by callback handlers
            ENTER_RESULTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_results_input)]
        },
        fallbacks=[
            CommandHandler("cancel", handle_cancel),
            # Allow start/predict commands to restart the conversation
            CommandHandler("start", handle_start), 
            CommandHandler("predict", handle_predict),
            CommandHandler("help", handle_help)
        ],
        name="prediction_conversation",
        persistent=False,
        allow_reentry=True,  # Allow re-entering the conversation with the same command
        per_chat=False,      # Don't restrict by chat, track by user_id instead
        per_user=True,       # Track conversation separately for each user
        per_message=False,   # Don't create a new conversation for each message
        conversation_timeout=300  # Timeout after 5 minutes of inactivity
    )

    # Save a reference to the conversation handler for timeout checks
    application.conversation_handler = conv_handler

    # Add the conversation handler to the application
    application.add_handler(conv_handler)

    # Add help, buy and plan handlers
    application.add_handler(CommandHandler("help", handle_help))
    application.add_handler(CommandHandler("buy", handle_buy))
    application.add_handler(CommandHandler("myplan", handle_myplan))

async def handle_buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /buy command"""
    try:
        user_id = update.effective_user.id
        buy_text = (
            "💎 *Pro Plan Features* 💎\n\n"
            "✨ Unlimited predictions\n"
            "✨ Priority support\n\n"
            "*Available Plans:*\n"
            "🎯 1 Day Pro Access - 399Rs\n"
            "🎯 30 Days Pro Access - 999Rs\n"
            "🎯 Lifetime Duration - 1999Rs\n"
            "🎯 Custom Access\n\n"
            "*How to Purchase:*\n"
            "Contact @SatsNova to purchase your preferred plan.\n\n"
        )
        await update.message.reply_text(buy_text, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ An error occurred: {str(e)}")
async def handle_myplan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /myplan command"""
    user_id = update.effective_user.id
    user = data_manager.get_user(user_id)

    if not user:
        await update.message.reply_text("❌ User not found. Please use /start first.")
        return

    is_pro = user.get('is_pro', False)
    free_predictions = user.get('free_predictions_left', 0)
    free_expiry = user.get('free_expiry')

    if isinstance(free_expiry, str):
        free_expiry = datetime.fromisoformat(free_expiry)

    if is_pro:
        pro_expiry = user.get('pro_expiry')
        if pro_expiry:
            if isinstance(pro_expiry, str):
                pro_expiry = datetime.fromisoformat(pro_expiry)
            expiry_date = pro_expiry.strftime("%Y-%m-%d")
            days_left = max(0, (pro_expiry - datetime.now()).days)
            plan_text = (
                "💎 *Your Plan Details* 💎\n\n"
                "✨ *Status:* Pro User\n"
                f"✨ *Expires:* {expiry_date} ({days_left} days left)\n"
                "✨ *Features:*\n"
                "• Unlimited predictions\n"
                "• Priority support"
            )
        else:
            plan_text = (
                "💎 *Your Plan Details* 💎\n\n"
                "✨ *Status:* Pro User\n"
                "✨ *Plan:* Lifetime Access\n"
                "✨ *Features:*\n"
                "• Unlimited predictions\n"
                "• Priority support"
            )
    else:
        days_left = (free_expiry - datetime.now()).days if free_expiry else 0
        plan_text = (
            "🆓 *Your Plan Details* 🆓\n\n"
            f"✨ *Status:* Free User\n"
            f"✨ *Predictions Left:* {free_predictions}\n"
            f"✨ *Trial Days Left:* {max(0, days_left)}\n\n"
            "Use /buy to upgrade to Pro for:\n"
            "• Unlimited predictions\n"
            "• Priority support"
        )

    await update.message.reply_text(plan_text, parse_mode='Markdown')