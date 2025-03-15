"""
Admin command handlers for the Telegram bot
"""
from typing import Dict, Any, List, Optional, Union

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, filters

import config
from data_manager import data_manager
from utils.helpers import parse_pattern_command, parse_remove_pattern_command, send_log_message

async def handle_setcooldown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /setcooldown command"""
    # Check if user is admin
    if update.effective_user.id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    # Check command arguments
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("❌ Usage: /setcooldown <game> <seconds>")
        return
    
    game = args[0].upper()
    
    try:
        cooldown = int(args[1])
        if cooldown < 0:
            await update.message.reply_text("❌ Cooldown must be a positive number.")
            return
    except ValueError:
        await update.message.reply_text("❌ Cooldown must be a number.")
        return
    
    # Check if game exists
    if game not in data_manager.get_all_games():
        await update.message.reply_text(f"❌ Game '{game}' does not exist.")
        return
    
    # Set cooldown
    data_manager.set_cooldown(game, cooldown)
    await update.message.reply_text(f"✅ Cooldown for {game} set to {cooldown} seconds.")

async def handle_setpattern(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /setpattern command"""
    # Check if user is admin
    if update.effective_user.id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    # Get the full command text
    full_text = update.message.text
    command_parts = full_text.split(' ', 1)
    
    if len(command_parts) < 2:
        await update.message.reply_text(
            "❌ Usage: /setpattern GAME pattern1, pattern2, ... = result\n"
            "Example: /setpattern WINGO Big, Big, Small = Small"
        )
        return
    
    pattern_text = command_parts[1]
    parsed = parse_pattern_command(pattern_text)
    
    if not parsed:
        await update.message.reply_text(
            "❌ Invalid format. Use one of these formats:\n"
            "1. Simple format: /setpattern GAME pattern1, pattern2, ... = result\n"
            "   Example: /setpattern WINGO Big, Big, Small = Small\n\n"
            "2. Bracket format: /setpattern GAME [pattern1, pattern2, ...] → result\n"
            "   Example: /setpattern WINGO [Big, Big, Small] → Small"
        )
        return
    
    game = parsed['game'].upper()
    pattern = parsed['pattern']
    result = parsed['result']
    
    # Check if game exists
    if game not in data_manager.get_all_games():
        await update.message.reply_text(f"❌ Game '{game}' does not exist.")
        return
    
    # Add pattern
    data_manager.add_pattern(game, pattern, result)
    await update.message.reply_text(
        f"✅ Pattern added for {game}:\n"
        f"Pattern: {', '.join(pattern)}\n"
        f"Prediction: {result}"
    )

async def handle_removepattern(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /removepattern command"""
    # Check if user is admin
    if update.effective_user.id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    # Get the full command text
    full_text = update.message.text
    command_parts = full_text.split(' ', 1)
    
    if len(command_parts) < 2:
        await update.message.reply_text(
            "❌ Usage: /removepattern GAME pattern1, pattern2, ...\n"
            "Example: /removepattern WINGO Big, Big, Small"
        )
        return
    
    pattern_text = command_parts[1]
    parsed = parse_remove_pattern_command(pattern_text)
    
    if not parsed:
        await update.message.reply_text(
            "❌ Invalid format. Use one of these formats:\n"
            "1. Simple format: /removepattern GAME pattern1, pattern2, ...\n"
            "   Example: /removepattern WINGO Big, Big, Small\n\n"
            "2. Bracket format: /removepattern GAME [pattern1, pattern2, ...]\n"
            "   Example: /removepattern WINGO [Big, Big, Small]"
        )
        return
    
    game = parsed['game'].upper()
    pattern = parsed['pattern']
    
    # Check if game exists
    if game not in data_manager.get_all_games():
        await update.message.reply_text(f"❌ Game '{game}' does not exist.")
        return
    
    # Remove pattern
    success = data_manager.remove_pattern(game, pattern)
    
    if success:
        await update.message.reply_text(
            f"✅ Pattern removed from {game}:\n"
            f"Pattern: {', '.join(pattern)}"
        )
    else:
        await update.message.reply_text(
            f"❌ Pattern not found for {game}:\n"
            f"Pattern: {', '.join(pattern)}"
        )

async def handle_addgame(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /addgame command"""
    # Check if user is admin
    if update.effective_user.id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    # Check command arguments
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("❌ Usage: /addgame <GameName> [cooldown]")
        return
    
    game = args[0].upper()
    cooldown = 60  # default cooldown
    
    if len(args) > 1:
        try:
            cooldown = int(args[1])
            if cooldown < 0:
                await update.message.reply_text("❌ Cooldown must be a positive number.")
                return
        except ValueError:
            await update.message.reply_text("❌ Cooldown must be a number.")
            return
    
    # Add game
    success = data_manager.add_game(game, cooldown)
    
    if success:
        await update.message.reply_text(f"✅ Game '{game}' added with {cooldown}s cooldown.")
    else:
        await update.message.reply_text(f"❌ Game '{game}' already exists.")

async def handle_deletegame(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /deletegame command"""
    # Check if user is admin
    if update.effective_user.id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    # Check command arguments
    args = context.args
    if len(args) != 1:
        await update.message.reply_text("❌ Usage: /deletegame <GameName>")
        return
    
    game = args[0].upper()
    
    # Delete game
    success = data_manager.delete_game(game)
    
    if success:
        await update.message.reply_text(f"✅ Game '{game}' deleted.")
    else:
        await update.message.reply_text(f"❌ Game '{game}' not found.")

async def handle_setfree(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /setfree command"""
    # Check if user is admin
    if update.effective_user.id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    # Check command arguments
    args = context.args
    if len(args) != 1:
        await update.message.reply_text("❌ Usage: /setfree <count>")
        return
    
    try:
        count = int(args[0])
        if count < 0:
            await update.message.reply_text("❌ Free prediction count must be a positive number.")
            return
    except ValueError:
        await update.message.reply_text("❌ Free prediction count must be a number.")
        return
    
    # Set free predictions
    data_manager.set_free_predictions(count)
    await update.message.reply_text(f"✅ Free predictions set to {count} per user.")

async def handle_setfreetime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /setfreetime command"""
    # Check if user is admin
    if update.effective_user.id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    # Check command arguments
    args = context.args
    if len(args) != 1:
        await update.message.reply_text("❌ Usage: /setfreetime <days>")
        return
    
    try:
        days = int(args[0])
        if days < 0:
            await update.message.reply_text("❌ Free time must be a positive number of days.")
            return
    except ValueError:
        await update.message.reply_text("❌ Free time must be a number of days.")
        return
    
    # Set free period
    data_manager.set_free_period(days)
    await update.message.reply_text(f"✅ Free access period set to {days} days.")

async def handle_setlogchannel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /setlogchannel command"""
    # Check if user is admin
    if update.effective_user.id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    # Check command arguments
    args = context.args
    if len(args) != 1:
        await update.message.reply_text("❌ Usage: /setlogchannel <@Channel>")
        return
    
    channel = args[0]
    
    # Ensure channel starts with @
    if not channel.startswith('@'):
        channel = '@' + channel
    
    # Set log channel
    data_manager.set_log_channel(channel)
    await update.message.reply_text(f"✅ Log channel set to {channel}.")
    
    # Test sending a message to the channel
    try:
        await send_log_message(context, "✅ This is a test message from the prediction bot.")
        await update.message.reply_text("✅ Test message sent to channel successfully.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Could not send test message to channel: {str(e)}")

async def handle_setchannel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /setchannel command"""
    # Check if user is admin
    if update.effective_user.id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    # Check command arguments
    args = context.args
    if len(args) != 1:
        await update.message.reply_text("❌ Usage: /setchannel <@Channel>")
        return
    
    channel = args[0]
    
    # Ensure channel starts with @
    if not channel.startswith('@'):
        channel = '@' + channel
    
    # Set required channel
    data_manager.set_required_channel(channel)
    await update.message.reply_text(f"✅ Required channel set to {channel}.")

async def handle_addapp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /addapp command"""
    # Check if user is admin
    if update.effective_user.id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    # Check command arguments
    args = context.args
    if len(args) != 1:
        await update.message.reply_text("❌ Usage: /addapp <AppName>")
        return
    
    app = args[0]
    
    # Add app
    success = data_manager.add_app(app)
    
    if success:
        await update.message.reply_text(f"✅ App '{app}' added.")
    else:
        await update.message.reply_text(f"❌ App '{app}' already exists.")

async def handle_deleteapp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /deleteapp command"""
    # Check if user is admin
    if update.effective_user.id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    # Check command arguments
    args = context.args
    if len(args) != 1:
        await update.message.reply_text("❌ Usage: /deleteapp <AppName>")
        return
    
    app = args[0]
    
    # Delete app
    success = data_manager.delete_app(app)
    
    if success:
        await update.message.reply_text(f"✅ App '{app}' deleted.")
    else:
        await update.message.reply_text(f"❌ App '{app}' not found.")

async def handle_admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /adminhelp command"""
    # Check if user is admin
    if update.effective_user.id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    help_text = (
        "🛠 *Admin Commands* 🛠\n\n"
        "*Game Management:*\n"
        "/setcooldown <game> <seconds> - Set cooldown for a game\n"
        "/addgame <GameName> [cooldown] - Add a new game\n"
        "/deletegame <GameName> - Remove a game\n\n"
        
        "*App Management:*\n"
        "/addapp <AppName> - Add a new app\n"
        "/deleteapp <AppName> - Remove an app\n\n"
        
        "*Pattern Management:*\n"
        "/setpattern <GAME> pattern1, pattern2, ... = result - Add a pattern (easy format)\n"
        "/setpattern <GAME> [pattern1, pattern2, ...] → result - Add a pattern (bracket format)\n"
        "/removepattern <GAME> pattern1, pattern2, ... - Remove a pattern (easy format)\n"
        "/removepattern <GAME> [pattern1, pattern2, ...] - Remove a pattern (bracket format)\n\n"
        
        "*User Settings:*\n"
        "/setfree <count> - Set free predictions per user\n"
        "/setfreetime <days> - Set free access duration\n\n"
        
        "*Channel Settings:*\n"
        "/setlogchannel <@Channel> - Set log channel\n"
        "/setchannel <@Channel> - Set required channel\n\n"
        
        "*User Management:*\n"
        "/addpro <user_id> - Add pro access for a user\n"
        "/removepro <user_id> - Remove pro access from a user\n"
        "/listusers - Show all users and their status\n"
        "/broadcast <message> - Send message to all users\n\n"
        
        "*Help:*\n"
        "/adminhelp - Show this help message\n"
        "/og - Show compact admin commands list"
    )
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def handle_addpro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /addpro command"""
    if update.effective_user.id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    args = context.args
    if len(args) < 1 or len(args) > 2:
        await update.message.reply_text("❌ Usage: /addpro <user_id> [days]")
        return
    
    try:
        user_id = int(args[0])
        days = int(args[1]) if len(args) > 1 else 0  # 0 means lifetime
        
        user = data_manager.get_user(user_id)
        if not user:
            await update.message.reply_text("❌ User not found.")
            return
        
        user['is_pro'] = True
        if days > 0:
            user['pro_expiry'] = (datetime.now() + timedelta(days=days)).isoformat()
        else:
            user['pro_expiry'] = None  # Lifetime access
            
        data_manager._save_data()
        
        duration = "lifetime" if days == 0 else f"{days} days"
        await update.message.reply_text(f"✅ User {user_id} is now a pro user for {duration}.")
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID or days format.")

async def handle_removepro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /removepro command"""
    if update.effective_user.id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    args = context.args
    if len(args) != 1:
        await update.message.reply_text("❌ Usage: /removepro <user_id>")
        return
    
    try:
        user_id = int(args[0])
        user = data_manager.get_user(user_id)
        if not user:
            await update.message.reply_text("❌ User not found.")
            return
        
        user['is_pro'] = False
        data_manager._save_data()
        await update.message.reply_text(f"✅ Pro status removed from user {user_id}.")
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID format.")

async def handle_listusers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /listusers command"""
    if update.effective_user.id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    users = data_manager.users
    user_list = []
    for user_id, user_data in users.items():
        status = "💎 Pro" if user_data.get('is_pro') else "🆓 Free"
        username = user_data.get('username', 'No username')
        user_list.append(f"ID: {user_id}\nUsername: {username}\nStatus: {status}\n")
    
    if user_list:
        await update.message.reply_text("👥 *User List*:\n\n" + "\n".join(user_list), parse_mode='Markdown')
    else:
        await update.message.reply_text("No users found.")

async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /broadcast command"""
    if update.effective_user.id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    message = ' '.join(context.args)
    if not message:
        await update.message.reply_text("❌ Usage: /broadcast <message>")
        return
    
    success = 0
    failed = 0
    for user_id in data_manager.users:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
            success += 1
        except Exception:
            failed += 1
    
    await update.message.reply_text(
        f"✅ Broadcast completed:\nSuccess: {success}\nFailed: {failed}"
    )

async def handle_admin_og(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /og command - shows compact admin command list"""
    # Check if user is admin
    if update.effective_user.id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    help_text = (
        "🛠 *Admin Commands Quick Guide* 🛠\n\n"
        "🎮 *Game:*\n"
        "/setcooldown WINGO 60\n"
        "/addgame XYZGAME 120\n"
        "/deletegame XYZGAME\n\n"
        
        "📱 *App:*\n"
        "/addapp NewApp\n"
        "/deleteapp OldApp\n\n"
        
        "🔍 *Patterns:*\n"
        "/setpattern WINGO Big, Big, Small = Small\n"
        "/removepattern WINGO Big, Big, Small\n\n"
        
        "⚙️ *Settings:*\n"
        "/setfree 5 (free predictions)\n"
        "/setfreetime 7 (days)\n"
        "/setlogchannel @YourLogChannel\n"
        "/setchannel @YourRequiredChannel\n\n"
        
        "ℹ️ Use /adminhelp for detailed info"
    )
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

def register_admin_handlers(application):
    """Register admin command handlers"""
    application.add_handler(CommandHandler("setcooldown", handle_setcooldown, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("setpattern", handle_setpattern, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("removepattern", handle_removepattern, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("addgame", handle_addgame, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("deletegame", handle_deletegame, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("setfree", handle_setfree, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("setfreetime", handle_setfreetime, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("setlogchannel", handle_setlogchannel, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("setchannel", handle_setchannel, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("addapp", handle_addapp, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("deleteapp", handle_deleteapp, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("adminhelp", handle_admin_help, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("og", handle_admin_og, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("addpro", handle_addpro, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("removepro", handle_removepro, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("listusers", handle_listusers, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("broadcast", handle_broadcast, filters=filters.ChatType.PRIVATE))
