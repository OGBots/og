"""
Helper functions for the Telegram bot
"""
from typing import List, Dict, Any, Union, Optional
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from data_manager import data_manager

async def is_channel_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Check if user is a member of the required channel
    
    Args:
        update: Telegram update object
        context: Telegram context object
        
    Returns:
        True if user is a member of the required channel, False otherwise
    """
    user_id = update.effective_user.id
    required_channel = data_manager.get_required_channel()
    
    # If no required channel is set, return True
    if not required_channel:
        return True
    
    try:
        # Try to get chat member status
        chat_member = await context.bot.get_chat_member(chat_id=required_channel, user_id=user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except TelegramError as e:
        print(f"Error checking channel membership: {e}")
        # In case of error, assume user is not a member to enforce the requirement
        return False

async def check_channel_membership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Check if user is a member of the required channel and send message if not
    
    Args:
        update: Telegram update object
        context: Telegram context object
        
    Returns:
        True if user is a member of the required channel, False otherwise
    """
    if await is_channel_member(update, context):
        return True
    
    required_channel = data_manager.get_required_channel()
    if not required_channel:
        return True
    
    # Create a cleaner channel name for display (remove @ if present)
    display_channel = required_channel
    if display_channel.startswith('@'):
        display_channel = display_channel
    else:
        display_channel = f"@{display_channel.replace('https://t.me/', '').replace('http://t.me/', '')}"
    
    # Create inline keyboard with join and check buttons
    keyboard = [
        [
            InlineKeyboardButton("✅ Join Now", url=f"https://t.me/{display_channel.replace('@', '')}"),
            InlineKeyboardButton("🔄 Check Again", callback_data="check_membership")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.effective_message.reply_text(
        f"⚠️ You must join {display_channel} to use this bot!",
        reply_markup=reply_markup
    )
    return False

def build_app_selector() -> InlineKeyboardMarkup:
    """Build an inline keyboard markup for app selection"""
    apps = data_manager.get_all_apps()
    keyboard = []
    
    if not apps:
        # If no apps are available, show a message
        keyboard.append([InlineKeyboardButton("No apps available", callback_data="none_app")])
        return InlineKeyboardMarkup(keyboard)
    
    # Create buttons in rows of 2
    row = []
    for i, app in enumerate(apps):
        row.append(InlineKeyboardButton(app, callback_data=f"app_{app}"))
        if len(row) == 2 or i == len(apps) - 1:
            keyboard.append(row)
            row = []
    
    return InlineKeyboardMarkup(keyboard)

def build_game_selector(app: str) -> InlineKeyboardMarkup:
    """Build an inline keyboard markup for game selection"""
    games = data_manager.get_all_games()
    keyboard = []
    
    # Create buttons in rows of 2
    row = []
    game_list = list(games.keys())  # Convert to list explicitly to avoid dictionary changed size during iteration
    
    if not game_list:
        # If no games are available, show a message
        keyboard.append([InlineKeyboardButton("No games available", callback_data="none")])
    else:
        for i, game in enumerate(game_list):
            row.append(InlineKeyboardButton(game, callback_data=f"game_{app}_{game}"))
            if len(row) == 2 or i == len(game_list) - 1:
                keyboard.append(row)
                row = []
    
    # Add back button
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_to_apps")])
    
    return InlineKeyboardMarkup(keyboard)

def build_prediction_result_buttons(app: str, game: str) -> InlineKeyboardMarkup:
    """Build an inline keyboard markup for prediction result verification"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Correct", callback_data=f"correct_{app}_{game}"),
            InlineKeyboardButton("❌ Wrong", callback_data=f"wrong_{app}_{game}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_result_selector(app: str, game: str, context: Dict) -> InlineKeyboardMarkup:
    """Build result selection keyboard with current progress"""
    current_results = context.user_data.get('current_results', [])
    game_info = data_manager.get_all_games().get(game, {})
    result_format = game_info.get('result_format', [])
    
    keyboard = []
    # Show current progress
    if current_results:
        keyboard.append([InlineKeyboardButton(
            f"Selected ({len(current_results)}/10): {', '.join(current_results)}", 
            callback_data="none"
        )])
    
    # Add result buttons
    for value in result_format:
        keyboard.append([InlineKeyboardButton(value, callback_data=f"result_{app}_{game}_{value}")])
    
    # Add back button
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_to_apps")])
    
    return InlineKeyboardMarkup(keyboard)

def format_results_for_display(results: List[str]) -> str:
    """Format results for display in a message"""
    if not results:
        return "No results available"
    return ', '.join(results)

async def send_log_message(context: ContextTypes.DEFAULT_TYPE, message: str) -> None:
    """Send a message to the log channel"""
    log_channel = data_manager.get_log_channel()
    if not log_channel:
        return
    
    try:
        await context.bot.send_message(chat_id=log_channel, text=message)
    except Exception as e:
        print(f"Error sending log message: {e}")

def parse_pattern_command(pattern_text: str) -> Optional[Dict[str, Any]]:
    """
    Parse a pattern command like:
    "/setpattern WINGO [Big, Big, Small] → Small" (arrow format)
    or
    "/setpattern WINGO Big, Big, Small = Small" (equals format)
    
    Returns:
        Dict with game, pattern and result, or None if invalid format
    """
    try:
        # First determine which format is used
        if '→' in pattern_text:
            separator = '→'
        elif '=' in pattern_text:
            separator = '='
        else:
            return None
            
        # Split by the separator
        parts = pattern_text.split(separator)
        if len(parts) != 2:
            return None
        
        pattern_part = parts[0].strip()
        result = parts[1].strip()
        
        # Try to extract game name and pattern
        # First check if we have brackets format [Big, Big, Small]
        import re
        if '[' in pattern_part and ']' in pattern_part:
            # Old format with brackets
            game_pattern_parts = pattern_part.split('[')
            if len(game_pattern_parts) != 2:
                return None
            
            game = game_pattern_parts[0].strip()
            pattern_str = '[' + game_pattern_parts[1]
            
            # Extract pattern values
            pattern_match = re.search(r'\[(.*?)\]', pattern_str)
            if not pattern_match:
                return None
            
            pattern_values = [p.strip() for p in pattern_match.group(1).split(',')]
        else:
            # New simplified format without brackets
            # First word is the game name, rest is the pattern
            parts = pattern_part.split(maxsplit=1)
            if len(parts) != 2:
                return None
                
            game = parts[0].strip()
            # Use comma as separator for pattern values
            pattern_values = [p.strip() for p in parts[1].split(',')]
        
        return {
            'game': game,
            'pattern': pattern_values,
            'result': result
        }
    except Exception as e:
        print(f"Error parsing pattern: {e}")
        return None

def parse_remove_pattern_command(pattern_text: str) -> Optional[Dict[str, Any]]:
    """
    Parse a remove pattern command like:
    "/removepattern WINGO [Big, Big, Small]" (bracket format)
    or
    "/removepattern WINGO Big, Big, Small" (simple format)
    
    Returns:
        Dict with game and pattern, or None if invalid format
    """
    try:
        import re
        # Check if we're using the bracket format
        if '[' in pattern_text and ']' in pattern_text:
            # Old format with brackets
            game_pattern_parts = pattern_text.split('[')
            if len(game_pattern_parts) != 2:
                return None
            
            game = game_pattern_parts[0].strip()
            pattern_str = '[' + game_pattern_parts[1]
            
            # Extract pattern values
            pattern_match = re.search(r'\[(.*?)\]', pattern_str)
            if not pattern_match:
                return None
            
            pattern_values = [p.strip() for p in pattern_match.group(1).split(',')]
        else:
            # New simplified format without brackets
            # First word is the game name, rest is the pattern
            parts = pattern_text.split(maxsplit=1)
            if len(parts) != 2:
                return None
                
            game = parts[0].strip()
            # Use comma as separator for pattern values
            pattern_values = [p.strip() for p in parts[1].split(',')]
        
        return {
            'game': game,
            'pattern': pattern_values
        }
    except Exception as e:
        print(f"Error parsing remove pattern: {e}")
        return None
