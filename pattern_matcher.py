"""
Pattern Matcher for predicting game outcomes based on historical patterns
"""
from typing import List, Dict, Optional

class PatternMatcher:
    """Handles pattern matching and prediction logic"""
    
    @staticmethod
    def find_matching_patterns(patterns: Dict[str, str], results: List[str]) -> List[str]:
        """
        Find patterns that match with the given results
        
        Args:
            patterns: Dictionary of pattern -> prediction mappings
            results: List of recent game results
            
        Returns:
            List of predicted outcomes from matching patterns
        """
        if not patterns or not results:
            return []
            
        matches = []
        results_str = ','.join(results)
        
        for pattern_str, prediction in patterns.items():
            pattern = pattern_str.split(',')
            pattern_len = len(pattern)
            
            # Skip patterns longer than results
            if pattern_len > len(results):
                continue
                
            # Check if any segment of results matches the pattern
            for i in range(len(results) - pattern_len + 1):
                segment = results[i:i + pattern_len]
                if segment == pattern:
                    matches.append(prediction)
                    
        return matches
    
    @staticmethod
    def get_best_prediction(matching_predictions: List[str]) -> Optional[str]:
        """
        Get the most common prediction from the matching patterns
        
        Args:
            matching_predictions: List of predictions from matching patterns
            
        Returns:
            Most common prediction or None if no matches
        """
        if not matching_predictions:
            return None
            
        # Count occurrences of each prediction
        prediction_counts = {}
        for pred in matching_predictions:
            prediction_counts[pred] = prediction_counts.get(pred, 0) + 1
            
        # Find prediction with highest count
        best_prediction = None
        highest_count = 0
        
        for pred, count in prediction_counts.items():
            if count > highest_count:
                highest_count = count
                best_prediction = pred
                
        return best_prediction
    
    @staticmethod
    def predict(patterns: Dict[str, str], results: List[str]) -> Optional[str]:
        """
        Make a prediction based on results and patterns
        
        Args:
            patterns: Dictionary of pattern -> prediction mappings
            results: List of recent game results
            
        Returns:
            Predicted outcome or None if no matches
        """
        matching_predictions = PatternMatcher.find_matching_patterns(patterns, results)
        return PatternMatcher.get_best_prediction(matching_predictions)
