"""
Confidence scoring for session analysis.
Pure algorithmic approach - no AI/ML needed.
"""

from typing import Dict, Optional


class ConfidenceScorer:
    """Calculate confidence scores for volatility predictions."""
    
    # Scoring weights
    WEIGHTS = {
        "sample_size": 0.40,      # Historical pattern sample size
        "pattern_strength": 0.25,  # How strong the expansion pattern is
        "event_catalyst": 0.20,    # Presence of high-impact event
        "data_quality": 0.15       # Data recency and completeness
    }
    
    @staticmethod
    def calculate_confidence(
        occurrences: int,
        expansion_rate: float,
        has_event: bool,
        data_age_days: int = 30,
        max_data_age: int = 60
    ) -> float:
        """
        Calculate overall confidence score.
        
        Args:
            occurrences: Number of similar historical patterns found
            expansion_rate: Rate at which patterns expanded (0-1)
            has_event: Whether high-impact event is scheduled
            data_age_days: How old the data is (lower = better)
            max_data_age: Maximum acceptable data age
            
        Returns:
            Confidence score (0.0 to 0.85)
            
        Scoring breakdown:
            - Sample size: More patterns = higher confidence
            - Pattern strength: Extreme expansion rates (near 0 or 1) = higher confidence
            - Event catalyst: Events add certainty to volatility expectations
            - Data quality: Fresh data = higher confidence
        """
        # 1. Sample Size Score (0-0.40)
        # More historical matches = more confidence
        # Target: 120 matches for max score
        sample_score = min(occurrences / 120, 1.0) * ConfidenceScorer.WEIGHTS["sample_size"]
        
        # 2. Pattern Strength Score (0-0.25)
        # Extreme rates (near 0 or 1) indicate clearer patterns
        # Neutral rate (0.5) indicates uncertainty
        pattern_certainty = abs(expansion_rate - 0.5) * 2  # 0-1 scale
        pattern_score = pattern_certainty * ConfidenceScorer.WEIGHTS["pattern_strength"]
        
        # 3. Event Catalyst Score (0-0.20)
        # Events provide additional certainty about volatility
        event_score = ConfidenceScorer.WEIGHTS["event_catalyst"] if has_event else 0.0
        
        # 4. Data Quality Score (0-0.15)
        # Fresher data = higher quality
        # Penalize data older than 30 days
        data_freshness = max(0, 1 - (data_age_days / max_data_age))
        data_score = data_freshness * ConfidenceScorer.WEIGHTS["data_quality"]
        
        # Total score
        total = sample_score + pattern_score + event_score + data_score
        
        # Cap at 0.85 (never 100% certain in markets)
        return round(min(total, 0.85), 2)
    
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
        sample_component = min(occurrences / 120, 1.0) * ConfidenceScorer.WEIGHTS["sample_size"]
        
        pattern_certainty = abs(expansion_rate - 0.5) * 2
        pattern_component = pattern_certainty * ConfidenceScorer.WEIGHTS["pattern_strength"]
        
        event_component = ConfidenceScorer.WEIGHTS["event_catalyst"] if has_event else 0.0
        
        data_freshness = max(0, 1 - (data_age_days / max_data_age))
        data_component = data_freshness * ConfidenceScorer.WEIGHTS["data_quality"]
        
        return {
            "sample_size_score": round(sample_component, 3),
            "pattern_strength_score": round(pattern_component, 3),
            "event_catalyst_score": round(event_component, 3),
            "data_quality_score": round(data_component, 3),
            "total": round(
                min(sample_component + pattern_component + event_component + data_component, 0.85),
                2
            )
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
        Adjust confidence based on current volatility regime.
        
        Args:
            base_confidence: Initial confidence score
            current_atr: Current ATR
            avg_atr: Historical average ATR
            adjustment_factor: Max adjustment amount
            
        Returns:
            Adjusted confidence score
        """
        if avg_atr == 0:
            return base_confidence
        
        # If current volatility is very different from average, reduce confidence
        volatility_ratio = current_atr / avg_atr
        
        # Penalize extreme deviations (both high and low)
        if volatility_ratio > 1.5 or volatility_ratio < 0.5:
            # Unusual volatility regime, reduce confidence
            adjustment = -adjustment_factor
        elif 0.8 <= volatility_ratio <= 1.2:
            # Normal regime, slight boost
            adjustment = adjustment_factor * 0.5
        else:
            adjustment = 0
        
        adjusted = base_confidence + adjustment
        return round(max(0.0, min(adjusted, 0.85)), 2)