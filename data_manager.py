"""
Data Manager for handling bot data storage and retrieval
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

import config

class DataManager:
    """Manages data storage and retrieval for the Telegram bot"""
    
    def __init__(self):
        # Initialize data structures
        self.users = {}
        self.games = config.DEFAULT_GAMES.copy()
        self.apps = config.DEFAULT_APPS.copy()
        self.required_channel = config.DEFAULT_REQUIRED_CHANNEL
        self.log_channel = config.DEFAULT_LOG_CHANNEL
        self.free_predictions = config.DEFAULT_FREE_PREDICTIONS
        self.free_period_days = config.DEFAULT_FREE_PERIOD_DAYS
        
        # Load data from file if exists
        self._load_data()
    
    def _load_data(self):
        """Load data from file if exists"""
        try:
            if os.path.exists('bot_data.json'):
                with open('bot_data.json', 'r') as file:
                    data = json.load(file)
                    self.users = data.get('users', {})
                    self.games = data.get('games', self.games)
                    self.apps = data.get('apps', self.apps)
                    self.required_channel = data.get('required_channel', self.required_channel)
                    self.log_channel = data.get('log_channel', self.log_channel)
                    self.free_predictions = data.get('free_predictions', self.free_predictions)
                    self.free_period_days = data.get('free_period_days', self.free_period_days)
                    
                    # Convert string keys in users dict to integers
                    self.users = {int(k): v for k, v in self.users.items()}
                    
                    # Convert timestamp strings to datetime objects
                    for user_id, user_data in self.users.items():
                        if 'prediction_history' in user_data:
                            for i, pred in enumerate(user_data['prediction_history']):
                                if 'timestamp' in pred and isinstance(pred['timestamp'], str):
                                    user_data['prediction_history'][i]['timestamp'] = datetime.fromisoformat(pred['timestamp'])
                        
                        if 'last_predictions' in user_data:
                            for game, pred in user_data['last_predictions'].items():
                                if 'timestamp' in pred and isinstance(pred['timestamp'], str):
                                    user_data['last_predictions'][game]['timestamp'] = datetime.fromisoformat(pred['timestamp'])
                        
                        if 'free_expiry' in user_data and isinstance(user_data['free_expiry'], str):
                            user_data['free_expiry'] = datetime.fromisoformat(user_data['free_expiry'])
        except Exception as e:
            print(f"Error loading data: {e}")
    
    def _save_data(self):
        """Save data to file"""
        try:
            # Convert datetime objects to ISO format strings for JSON serialization
            serializable_users = {}
            for user_id, user_data in self.users.items():
                serializable_user = user_data.copy()
                
                if 'prediction_history' in serializable_user:
                    for i, pred in enumerate(serializable_user['prediction_history']):
                        if 'timestamp' in pred and isinstance(pred['timestamp'], datetime):
                            serializable_user['prediction_history'][i]['timestamp'] = pred['timestamp'].isoformat()
                
                if 'last_predictions' in serializable_user:
                    for game, pred in serializable_user['last_predictions'].items():
                        if 'timestamp' in pred and isinstance(pred['timestamp'], datetime):
                            serializable_user['last_predictions'][game]['timestamp'] = pred['timestamp'].isoformat()
                
                if 'free_expiry' in serializable_user and isinstance(serializable_user['free_expiry'], datetime):
                    serializable_user['free_expiry'] = serializable_user['free_expiry'].isoformat()
                
                serializable_users[str(user_id)] = serializable_user
            
            data = {
                'users': serializable_users,
                'games': self.games,
                'apps': self.apps,
                'required_channel': self.required_channel,
                'log_channel': self.log_channel,
                'free_predictions': self.free_predictions,
                'free_period_days': self.free_period_days
            }
            
            with open('bot_data.json', 'w') as file:
                json.dump(data, file, indent=2)
        except Exception as e:
            print(f"Error saving data: {e}")
    
    def register_user(self, user_id: int, username: Optional[str] = None) -> Dict:
        """Register a new user or return existing user data"""
        if user_id not in self.users and str(user_id) not in self.users:
            free_expiry = datetime.now() + timedelta(days=self.free_period_days)
            self.users[user_id] = {
                'username': username,
                'joined_date': datetime.now().isoformat(),
                'is_pro': False,
                'free_predictions': self.free_predictions,  # Changed to match key used elsewhere
                'free_expiry': free_expiry,
                'prediction_history': [],
                'last_results': {},
                'last_predictions': {}
            }
            self._save_data()
        elif str(user_id) in self.users and user_id not in self.users:
            # Handle string key case if it exists
            self.users[user_id] = self.users[str(user_id)]
            del self.users[str(user_id)]
            self._save_data()
            
        return self.users[user_id]
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user data by ID"""
        return self.users.get(user_id)
    
    def update_user_results(self, user_id: int, app: str, game: str, results: List[str]) -> None:
        """Update a user's last results for a specific game"""
        if user_id not in self.users:
            self.register_user(user_id)
        
        if 'last_results' not in self.users[user_id]:
            self.users[user_id]['last_results'] = {}
            
        key = f"{app}_{game}"
        self.users[user_id]['last_results'][key] = results
        self._save_data()
    
    def get_user_results(self, user_id: int, app: str, game: str) -> List[str]:
        """Get a user's last results for a specific game"""
        user = self.get_user(user_id)
        if not user or 'last_results' not in user:
            return []
            
        key = f"{app}_{game}"
        return user['last_results'].get(key, [])
    
    def record_prediction(self, user_id: int, app: str, game: str, prediction: str, correct: Optional[bool] = None) -> None:
        """Record a user's prediction"""
        if user_id not in self.users:
            self.register_user(user_id)
        
        # Record in history
        if 'prediction_history' not in self.users[user_id]:
            self.users[user_id]['prediction_history'] = []
            
        pred_record = {
            'app': app,
            'game': game,
            'prediction': prediction,
            'correct': correct,
            'timestamp': datetime.now()
        }
        
        self.users[user_id]['prediction_history'].append(pred_record)
        
        # Record as last prediction for cooldown check
        if 'last_predictions' not in self.users[user_id]:
            self.users[user_id]['last_predictions'] = {}
            
        self.users[user_id]['last_predictions'][game] = {
            'prediction': prediction,
            'timestamp': datetime.now()
        }
        
        # Decrement free predictions if not pro
        if not self.users[user_id].get('is_pro', False):
            self.users[user_id]['free_predictions_left'] = max(0, self.users[user_id].get('free_predictions_left', 0) - 1)
        
        self._save_data()
    
    def can_predict(self, user_id: int, game: str) -> Tuple[bool, str, int]:
        """Check if user can make a prediction based on cooldown and available predictions"""
        user = self.get_user(user_id)
        if not user:
            return False, "User not registered", 0
        
        # Check if pro or has free predictions
        is_pro = user.get('is_pro', False)
        free_left = user.get('free_predictions_left', 0)
        free_expiry = user.get('free_expiry')
        
        # Convert free_expiry if it's a string
        if isinstance(free_expiry, str):
            free_expiry = datetime.fromisoformat(free_expiry)
        
        # Check if free trial expired
        if not is_pro and free_expiry and datetime.now() > free_expiry:
            return False, "Your free trial has expired. Upgrade to Pro to continue.\n Use /buy to purchase a pro plan.", 0
        
        # Check if out of free predictions
        if not is_pro and free_left <= 0:
            return False, "You've used all your free predictions. Upgrade to Pro for unlimited access.\n Use /buy to purchase a pro plan.", 0
        
        # Check cooldown
        last_predictions = user.get('last_predictions', {})
        if game in last_predictions:
            last_pred = last_predictions[game]
            last_time = last_pred.get('timestamp')
            
            # Convert timestamp if it's a string
            if isinstance(last_time, str):
                last_time = datetime.fromisoformat(last_time)
            
            game_cooldown = self.games.get(game, {}).get('cooldown', 60)  # default 60s
            cooldown_end = last_time + timedelta(seconds=game_cooldown)
            
            if datetime.now() < cooldown_end:
                seconds_left = int((cooldown_end - datetime.now()).total_seconds())
                return False, f"Cooldown active. Try again in {seconds_left} seconds.", seconds_left
        
        return True, "", 0
    
    def update_after_correct_prediction(self, user_id: int, app: str, game: str) -> None:
        """Update user's last results after a correct prediction"""
        user = self.get_user(user_id)
        if not user:
            return
            
        key = f"{app}_{game}"
        results = user.get('last_results', {}).get(key, [])
        if not results:
            return
            
        last_pred = user.get('last_predictions', {}).get(game, {}).get('prediction')
        if not last_pred:
            return
            
        # Add the new result (which was the prediction) and remove the oldest
        if len(results) >= 10:
            results = results[1:] + [last_pred]
        else:
            results = results + [last_pred]
            
        self.users[user_id]['last_results'][key] = results
        self._save_data()
    
    def add_pattern(self, game: str, pattern: List[str], result: str) -> bool:
        """Add a prediction pattern for a game"""
        if game not in self.games:
            return False
            
        if 'patterns' not in self.games[game]:
            self.games[game]['patterns'] = {}
            
        pattern_key = ','.join(pattern)
        self.games[game]['patterns'][pattern_key] = result
        self._save_data()
        return True
    
    def remove_pattern(self, game: str, pattern: List[str]) -> bool:
        """Remove a prediction pattern from a game"""
        if game not in self.games or 'patterns' not in self.games[game]:
            return False
            
        pattern_key = ','.join(pattern)
        if pattern_key in self.games[game]['patterns']:
            del self.games[game]['patterns'][pattern_key]
            self._save_data()
            return True
        return False
    
    def set_cooldown(self, game: str, cooldown: int) -> bool:
        """Set cooldown for a game"""
        if game not in self.games:
            return False
            
        self.games[game]['cooldown'] = cooldown
        self._save_data()
        return True
    
    def add_game(self, game: str, cooldown: int = 60, result_format: Optional[List[str]] = None) -> bool:
        """Add a new game"""
        if game in self.games:
            return False
            
        if not result_format:
            result_format = ["Big", "Small"]
            
        self.games[game] = {
            'cooldown': cooldown,
            'patterns': {},
            'result_format': result_format
        }
        self._save_data()
        return True
    
    def delete_game(self, game: str) -> bool:
        """Delete a game"""
        if game not in self.games:
            return False
            
        del self.games[game]
        
        # If all games are deleted, restore default games
        if not self.games:
            self.games = config.DEFAULT_GAMES.copy()
            
        self._save_data()
        return True
    
    def set_free_predictions(self, count: int) -> None:
        """Set number of free predictions"""
        self.free_predictions = count
        self._save_data()
    
    def set_free_period(self, days: int) -> None:
        """Set free period duration in days"""
        self.free_period_days = days
        self._save_data()
    
    def set_log_channel(self, channel: str) -> None:
        """Set the log channel"""
        self.log_channel = channel
        self._save_data()
    
    def set_required_channel(self, channel: str) -> None:
        """Set the required channel for users to join"""
        self.required_channel = channel
        self._save_data()
    
    def get_all_games(self) -> Dict:
        """Get all games data"""
        return self.games
    
    def get_all_apps(self) -> List[str]:
        """Get all apps"""
        return self.apps
    
    def add_app(self, app: str) -> bool:
        """Add a new app"""
        if app in self.apps:
            return False
        self.apps.append(app)
        self._save_data()
        return True
    
    def delete_app(self, app: str) -> bool:
        """Delete an app"""
        if app not in self.apps:
            return False
        self.apps.remove(app)
        
        # If all apps are deleted, restore default apps
        if not self.apps:
            self.apps = config.DEFAULT_APPS.copy()
            
        self._save_data()
        return True
    
    def get_required_channel(self) -> str:
        """Get required channel for users to join"""
        return self.required_channel
    
    def get_log_channel(self) -> str:
        """Get log channel"""
        return self.log_channel

# Create global instance
data_manager = DataManager()
