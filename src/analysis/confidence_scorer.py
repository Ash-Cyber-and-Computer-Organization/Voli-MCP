"""
Confidence scoring for session analysis.
Pure algorithmic approach - no AI/ML needed.
"""

from typing import Dict, Optional


class ConfidenceScorer:
    """Calculate confidence scores for volatility predictions."""

    @staticmethod
    def calculate_confidence(
        breakout_occurrences: int,
        total_occurrences: int
    ) -> float:
        """
        Calculate confidence score using the required formula:
        breakout_occurrences / total_occurrences
        """
        if total_occurrences <= 0:
            return 0.0
        return round(breakout_occurrences / total_occurrences, 2)
    
    @staticmethod
    def get_confidence_breakdown(
        occurrences: int,
        expansion_rate: float,
        has_event: bool,
        data_age_days: int = 30,
        max_data_age: int = 60
    ) -> Dict[str, float]:
        """
        Get detailed breakdown of confidence components.
        
        Args:
            Same as calculate_confidence
            
        Returns:
            Dict with component scores
        """
        return {
            "sample_size_score": 0.0,
            "pattern_strength_score": 0.0,
            "event_catalyst_score": 0.0,
            "data_quality_score": 0.0,
            "total": round(expansion_rate, 2)
        }
    
    @staticmethod
    def get_confidence_explanation(
        confidence: float,
        occurrences: int,
        expansion_rate: float,
        has_event: bool
    ) -> str:
        """
        Generate human-readable explanation of confidence score.
        
        Args:
            confidence: Calculated confidence score
            occurrences: Pattern matches
            expansion_rate: Historical expansion rate
            has_event: Event presence
            
        Returns:
            Explanation string
        """
        explanations = []
        
        # Sample size
        if occurrences >= 100:
            explanations.append("strong historical sample size")
        elif occurrences >= 50:
            explanations.append("moderate historical sample")
        else:
            explanations.append("limited historical data")
        
        # Pattern clarity
        if expansion_rate > 0.7:
            explanations.append("clear expansion pattern")
        elif expansion_rate < 0.3:
            explanations.append("clear range-bound pattern")
        else:
            explanations.append("mixed historical outcomes")
        
        # Event
        if has_event:
            explanations.append("high-impact event scheduled")
        
        # Overall assessment
        if confidence >= 0.70:
            prefix = "High confidence:"
        elif confidence >= 0.50:
            prefix = "Moderate confidence:"
        else:
            prefix = "Low confidence:"
        
        return f"{prefix} {', '.join(explanations)}."
    
    @staticmethod
    def adjust_for_volatility_regime(
        base_confidence: float,
        current_atr: float,
        avg_atr: float,
        adjustment_factor: float = 0.10
    ) -> float:
        """
        Retained for backward compatibility. Returns base confidence unchanged.
        """
        return round(max(0.0, min(base_confidence, 1.0)), 2)
