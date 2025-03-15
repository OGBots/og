"""
Callback query handlers for the Telegram bot
"""
from typing import Dict, Any, List, Optional, Union

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackQueryHandler, ConversationHandler

from data_manager import data_manager
from pattern_matcher import PatternMatcher
from utils.helpers import (
    check_channel_membership, build_app_selector, build_game_selector,
    build_prediction_result_buttons, format_results_for_display, send_log_message
)
from handlers.user_handlers import SELECT_APP, SELECT_GAME, ENTER_RESULTS, APP_KEY, GAME_KEY, AWAITING_RESULTS_KEY

async def handle_app_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle app selection callback"""
    query = update.callback_query
    await query.answer()

    # Handle the case when no apps are available
    if query.data == "none_app":
        await query.edit_message_text(
            "❌ No apps are available. Please ask an admin to add apps first.")
        return ConversationHandler.END

    app = query.data.replace("app_", "")
    context.user_data[APP_KEY] = app

    # Show game selection keyboard
    reply_markup = build_game_selector(app)
    await query.edit_message_text(
        f"Selected app: {app}\nPlease select a game:",
        reply_markup=reply_markup
    )

    return SELECT_GAME

async def handle_back_to_apps(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle back to apps callback"""
    query = update.callback_query
    await query.answer()

    # Clear app selection
    if APP_KEY in context.user_data:
        del context.user_data[APP_KEY]

    # Show app selection keyboard
    reply_markup = build_app_selector()
    await query.edit_message_text(
        "🔮 Select an app to start predicting.",
        reply_markup=reply_markup
    )

    return SELECT_APP

async def handle_game_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle game selection callback"""
    query = update.callback_query
    await query.answer()

    # Handle the case when no games are available
    if query.data == "none":
        await query.edit_message_text(
            "❌ No games are available. Please ask an admin to add games first.")
        return ConversationHandler.END

    # Extract app and game from callback data
    data_parts = query.data.replace("game_", "").split("_")
    if len(data_parts) != 2:
        await query.edit_message_text("❌ Error: Invalid game selection.")
        return ConversationHandler.END

    app = data_parts[0]
    game = data_parts[1]

    context.user_data[APP_KEY] = app
    context.user_data[GAME_KEY] = game

    # Get game format information
    game_info = data_manager.get_all_games().get(game, {})
    result_format = game_info.get('result_format', [])
    valid_formats = [r.strip() for r in result_format] #added to handle extra spaces

    # Check if user has results for this game
    user_id = update.effective_user.id
    results = data_manager.get_user_results(user_id, app, game)

    if results:
        # User has previous results, show them and ask to confirm or update
        formatted_results = format_results_for_display(results)

        # Check if user can make a prediction (cooldown, free limits)
        can_predict, message, seconds_left = data_manager.can_predict(user_id, game)

        if not can_predict:
            # Show cooldown message
            if seconds_left > 0:
                await query.edit_message_text(
                    f"⏳ {message}\n\n"
                    f"Your last results: {formatted_results}"
                )
            else:
                # Show other limitation message (free trial/predictions)
                await query.edit_message_text(f"❌ {message}")
            return ConversationHandler.END

        # Create keyboard to proceed or update results
        keyboard = [
            [
                InlineKeyboardButton("✅ Use these results", callback_data=f"use_results_{app}_{game}"),
                InlineKeyboardButton("🔄 Update results", callback_data=f"update_results_{app}_{game}")
            ],
            [InlineKeyboardButton("⬅️ Back", callback_data="back_to_apps")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"Selected app: {app}, Game: {game}\n\n"
            f"Your last results: {formatted_results}\n\n"
            f"Do you want to use these results or update them?",
            reply_markup=reply_markup
        )

        return ENTER_RESULTS
    else:
        # User doesn't have results, ask for input
        context.user_data[AWAITING_RESULTS_KEY] = True

        # Show result selection buttons
        result_keyboard = []
        for value in valid_formats:
            result_keyboard.append([
                InlineKeyboardButton(value, callback_data=f"result_{app}_{game}_{value}")
            ])
        result_keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_to_apps")])
        reply_markup = InlineKeyboardMarkup(result_keyboard)

        # Store empty results list in user data
        context.user_data['current_results'] = []

        await query.edit_message_text(
            f"Selected app: {app}, Game: {game}\n\n"
            f"Select your last 10 results one by one:\n"
            f"Selected (0/10): None",
            reply_markup=reply_markup
        )

        return ENTER_RESULTS

async def handle_use_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle using existing results callback"""
    query = update.callback_query
    await query.answer()

    # Extract app and game from callback data
    data_parts = query.data.replace("use_results_", "").split("_")
    if len(data_parts) != 2:
        await query.edit_message_text("❌ Error: Invalid selection.")
        return ConversationHandler.END

    app = data_parts[0]
    game = data_parts[1]
    user_id = update.effective_user.id

    # Get user's results
    results = data_manager.get_user_results(user_id, app, game)

    if not results:
        await query.edit_message_text(
            "❌ No results found. Please use /predict to start over."
        )
        return ConversationHandler.END

    # Check if user can make a prediction (cooldown, free limits)
    can_predict, message, _ = data_manager.can_predict(user_id, game)

    if not can_predict:
        await query.edit_message_text(f"❌ {message}")
        return ConversationHandler.END

    # Make prediction
    game_info = data_manager.get_all_games().get(game, {})
    patterns = game_info.get('patterns', {})
    prediction = PatternMatcher.predict(patterns, results)

    if prediction:
        # Record prediction
        data_manager.record_prediction(user_id, app, game, prediction)

        # Send prediction with verification buttons
        reply_markup = build_prediction_result_buttons(app, game)
        await query.edit_message_text(
            f"🔮 Prediction: {prediction}",
            reply_markup=reply_markup
        )
    else:
        await query.edit_message_text(
            "⚠️ No matching patterns found. Try with different results or contact the admin."
        )

    return ConversationHandler.END

async def handle_update_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle updating results callback"""
    query = update.callback_query
    await query.answer()

    # Extract app and game from callback data
    data_parts = query.data.replace("update_results_", "").split("_")
    if len(data_parts) != 2:
        await query.edit_message_text("❌ Error: Invalid selection.")
        return ConversationHandler.END

    app = data_parts[0]
    game = data_parts[1]

    context.user_data[APP_KEY] = app
    context.user_data[GAME_KEY] = game
    context.user_data[AWAITING_RESULTS_KEY] = True

    # Get game format information
    game_info = data_manager.get_all_games().get(game, {})
    result_format = game_info.get('result_format', [])
    format_text = ', '.join(result_format)

    # Show result selection buttons
    game_info = data_manager.get_all_games().get(game, {})
    valid_formats = game_info.get('result_format', [])
    
    # Store empty results list in user data
    context.user_data['current_results'] = []
    
    # Create keyboard with result options
    result_keyboard = []
    for value in valid_formats:
        result_keyboard.append([
            InlineKeyboardButton(value, callback_data=f"result_{app}_{game}_{value}")
        ])
    result_keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_to_apps")])
    reply_markup = InlineKeyboardMarkup(result_keyboard)
    
    await query.edit_message_text(
        f"Selected app: {app}, Game: {game}\n\n"
        f"Select your last 10 results one by one:\n"
        f"Selected (0/10): None",
        reply_markup=reply_markup
    )

    return ENTER_RESULTS

async def handle_correct_prediction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle correct prediction callback"""
    query = update.callback_query
    await query.answer()

    # Extract app and game from callback data
    data_parts = query.data.replace("correct_", "").split("_")
    if len(data_parts) != 2:
        await query.edit_message_text("❌ Error: Invalid selection.")
        return

    app = data_parts[0]
    game = data_parts[1]
    user_id = update.effective_user.id

    # Get prediction from the message
    message_text = query.message.text
    prediction = message_text.replace("🔮 Prediction: ", "").strip()

    # Get current results
    results = data_manager.get_user_results(user_id, app, game)
    if results:
        # Remove oldest result and add correct prediction
        results = results[1:] + [prediction]
        data_manager.update_user_results(user_id, app, game, results)

    # Send log message to admin channel
    log_message = (
        "✅ Prediction Log\n"
        f"🏆 App: {app}\n"
        f"🎰 Game: {game}\n"
        f"🔮 Predicted: {prediction}\n"
        f"🎯 Correct ✅"
    )
    await send_log_message(context, log_message)

    # Update the prediction message
    formatted_results = format_results_for_display(results)
    await query.edit_message_text(
        f"✅ Your prediction was correct!\n"
        f"🔮 Prediction: {prediction}\n\n"
        f"Updated results: {formatted_results}\n\n"
        f"Use /predict to make a new prediction."
    )

async def handle_wrong_prediction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle wrong prediction callback"""
    query = update.callback_query
    await query.answer()

    # Extract app and game from callback data
    data_parts = query.data.replace("wrong_", "").split("_")
    if len(data_parts) != 2:
        await query.edit_message_text("❌ Error: Invalid selection.")
        return

    app = data_parts[0]
    game = data_parts[1]
    user_id = update.effective_user.id

    # Get prediction from the message
    message_text = query.message.text
    prediction = message_text.replace("🔮 Prediction: ", "").strip()

    # Get current results
    results = data_manager.get_user_results(user_id, app, game)
    if results:
        # Get game format information
        game_info = data_manager.get_all_games().get(game, {})
        valid_formats = game_info.get('result_format', [])
        
        # Create buttons for all possible results
        keyboard = []
        for value in valid_formats:
            if value != prediction:  # Only show options different from wrong prediction
                keyboard.append([InlineKeyboardButton(f"✅ Add {value}", callback_data=f"add_result_{app}_{game}_{value}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"❌ Prediction was wrong.\n"
            f"🔮 Predicted: {prediction}\n\n"
            f"Current results: {format_results_for_display(results)}\n\n"
            f"Click below to add the correct result:",
            reply_markup=reply_markup
        )
    else:
        await query.edit_message_text(
            f"❌ Sorry for wrong prediction.\n"
            f"🔮 Prediction: {prediction}\n\n"
            f"Use /predict to make a new prediction."
        )

async def handle_add_result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle adding correct result after wrong prediction"""
    query = update.callback_query
    await query.answer()

    # Extract data from callback
    data_parts = query.data.replace("add_result_", "").split("_")
    if len(data_parts) != 3:
        await query.edit_message_text("❌ Error: Invalid selection.")
        return

    app, game, correct_result = data_parts
    user_id = update.effective_user.id

    # Get and update results
    results = data_manager.get_user_results(user_id, app, game)
    if results:
        # Remove oldest result and add correct result
        results = results[1:] + [correct_result]
        data_manager.update_user_results(user_id, app, game, results)
        
        formatted_results = format_results_for_display(results)
        await query.edit_message_text(
            f"✅ Results updated!\n"
            f"Added result: {correct_result}\n\n"
            f"New results: {formatted_results}\n\n"
            f"Use /predict to make a new prediction."
        )
    else:
        await query.edit_message_text(
            "❌ Error: No results found. Use /predict to start over."
        )

async def handle_check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle check membership callback"""
    query = update.callback_query
    await query.answer()

    # Check if user is now a member of the required channel
    if await check_channel_membership(update, context):
        # User is now a member, show welcome message with app selection
        reply_markup = build_app_selector()
        await query.edit_message_text(
            "✅ Channel verification successful!\n\n"
            "🔮 Select an app to start predicting.",
            reply_markup=reply_markup
        )

        return SELECT_APP
    return ConversationHandler.END

async def handle_result_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data_parts = query.data.replace("result_", "").split("_")
    if len(data_parts) != 3:
        await query.edit_message_text("Invalid result selection.")
        return ConversationHandler.END
    app, game, result = data_parts
    current_results = context.user_data.get('current_results', [])
    current_results.append(result)
    context.user_data['current_results'] = current_results
    if len(current_results) == 10:
        # Proceed to prediction
        await handle_submit_results(update,context)
        return ConversationHandler.END
    else:
        # Show updated message
        await query.edit_message_text(
            f"Selected app: {app}, Game: {game}\n\n"
            f"Select your last 10 results one by one:\n"
            f"Selected ({len(current_results)}/10): {', '.join(current_results)}",
            reply_markup = build_result_selector(app,game,context)
        )
        return ENTER_RESULTS

async def handle_submit_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    app = context.user_data[APP_KEY]
    game = context.user_data[GAME_KEY]
    results = context.user_data['current_results']
    #Save results to the database here
    data_manager.update_user_results(update.effective_user.id, app, game, results)
    #Continue with prediction logic
    game_info = data_manager.get_all_games().get(game, {})
    patterns = game_info.get('patterns', {})
    prediction = PatternMatcher.predict(patterns, results)

    if prediction:
        # Record prediction
        data_manager.record_prediction(update.effective_user.id, app, game, prediction)

        # Send prediction with verification buttons
        reply_markup = build_prediction_result_buttons(app, game)
        await update.callback_query.edit_message_text(
            f"🔮 Prediction: {prediction}",
            reply_markup=reply_markup
        )
    else:
        await update.callback_query.edit_message_text(
            "⚠️ No matching patterns found. Try with different results or contact the admin."
        )
    return ConversationHandler.END

def build_result_selector(app, game, context):
    game_info = data_manager.get_all_games().get(game, {})
    result_format = game_info.get('result_format', [])
    valid_formats = [r.strip() for r in result_format]
    result_keyboard = []
    for value in valid_formats:
        result_keyboard.append([
            InlineKeyboardButton(value, callback_data=f"result_{app}_{game}_{value}")
        ])
    result_keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_to_apps")])
    return InlineKeyboardMarkup(result_keyboard)

def register_callback_handlers(application):
    """Register callback query handlers"""
    application.add_handler(CallbackQueryHandler(handle_app_selection, pattern=r"^app_|^none_app$"))
    application.add_handler(CallbackQueryHandler(handle_back_to_apps, pattern=r"^back_to_apps$"))
    application.add_handler(CallbackQueryHandler(handle_game_selection, pattern=r"^game_|^none$"))
    application.add_handler(CallbackQueryHandler(handle_use_results, pattern=r"^use_results_"))
    application.add_handler(CallbackQueryHandler(handle_update_results, pattern=r"^update_results_"))
    application.add_handler(CallbackQueryHandler(handle_correct_prediction, pattern=r"^correct_"))
    application.add_handler(CallbackQueryHandler(handle_wrong_prediction, pattern=r"^wrong_"))
    application.add_handler(CallbackQueryHandler(handle_check_membership, pattern=r"^check_membership$"))
    application.add_handler(CallbackQueryHandler(handle_result_selection, pattern=r"^result_"))
    application.add_handler(CallbackQueryHandler(handle_submit_results, pattern=r"^submit_results$"))
    application.add_handler(CallbackQueryHandler(handle_add_result, pattern=r"^add_result_"))