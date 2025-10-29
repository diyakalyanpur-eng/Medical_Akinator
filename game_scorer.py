import numpy as np

class GameScorer:
    """Score student performance"""
    
    def __init__(self, optimal_data):
        self.optimal_data = optimal_data
    
    def estimate_information_gain(self, questions_asked):
        """Estimate average information gain per question"""
        # Track unique fields asked
        seen_fields = set()
        total_gain = 0
        
        for q in questions_asked:
            # Simple heuristic: first time = high gain, repeat = low gain
            question_text = q.get('question', '').lower()
            
            # Extract rough "topic" from question
            topic = self._extract_topic(question_text)
            
            if topic not in seen_fields:
                total_gain += 1.0
                seen_fields.add(topic)
            else:
                total_gain += 0.1  # Redundant question
        
        avg_gain = total_gain / len(questions_asked) if questions_asked else 0
        return avg_gain
    
    def _extract_topic(self, question):
        """Extract main topic from question"""
        # Simple keyword extraction
        keywords = ['fever', 'cough', 'pain', 'onset', 'duration', 
                   'contacts', 'travel', 'symptoms', 'temperature']
        
        for keyword in keywords:
            if keyword in question:
                return keyword
        
        return question[:20]  # First 20 chars as fallback
    
    def calculate_efficiency_score(self, num_questions, optimal, max_points=400):
        """Calculate efficiency score"""
        thresholds = {
            'excellent': optimal - 1,
            'optimal': optimal,
            'acceptable': int(optimal * 1.5)
        }
        
        if num_questions <= thresholds['excellent']:
            return max_points
        elif num_questions <= thresholds['optimal']:
            return int(max_points * 0.875)
        elif num_questions <= thresholds['acceptable']:
            excess = num_questions - thresholds['optimal']
            max_excess = thresholds['acceptable'] - thresholds['optimal']
            penalty_ratio = excess / max_excess
            return int(300 - (penalty_ratio * 200))
        else:
            excess = num_questions - thresholds['acceptable']
            return max(0, 100 - (excess * 20))
    
    def calculate_quality_score(self, avg_information_gain, max_points=200):
        """Calculate question quality score"""
        if avg_information_gain >= 0.80:
            return max_points
        elif avg_information_gain >= 0.60:
            return int(max_points * 0.75)
        elif avg_information_gain >= 0.40:
            return int(max_points * 0.50)
        else:
            return int(max_points * 0.25)
    
    def get_performance_tier(self, num_questions, optimal_data):
        """Get performance tier description"""
        if num_questions <= optimal_data['excellent_threshold']:
            return "Excellent - Top 10%"
        elif num_questions <= optimal_data['realistic_optimal']:
            return "Very Good - Optimal"
        elif num_questions <= optimal_data['acceptable_maximum']:
            return "Good - Acceptable"
        else:
            return "Needs Improvement"
    
    def calculate_score(self, disease_id, questions_asked, correct, hints_used=0):
        """Calculate comprehensive score"""
        if disease_id not in self.optimal_data:
            # Fallback scoring if disease not in optimal data
            return self._fallback_score(questions_asked, correct)
        
        optimal_info = self.optimal_data[disease_id]
        optimal = optimal_info['realistic_optimal']
        
        # 1. Accuracy (400 points)
        accuracy_points = 400 if correct else 0
        
        # 2. Efficiency (400 points)
        efficiency_points = self.calculate_efficiency_score(
            len(questions_asked), 
            optimal
        )
        
        # 3. Quality (200 points)
        avg_ig = self.estimate_information_gain(questions_asked)
        quality_points = self.calculate_quality_score(avg_ig)
        
        # 4. Penalties
        hint_penalty = hints_used * 50
        
        # Total
        total_score = accuracy_points + efficiency_points + quality_points - hint_penalty
        total_score = max(0, min(1000, total_score))
        
        # Performance tier
        tier = self.get_performance_tier(len(questions_asked), optimal_info)
        
        return {
            'total_score': total_score,
            'breakdown': {
                'accuracy': accuracy_points,
                'efficiency': efficiency_points,
                'quality': quality_points,
                'hint_penalty': -hint_penalty
            },
            'metrics': {
                'questions_asked': len(questions_asked),
                'optimal_questions': optimal,
                'efficiency_ratio': round(len(questions_asked) / optimal, 2) if optimal > 0 else 0,
                'avg_information_gain': round(avg_ig, 2)
            },
            'performance_tier': tier,
            'optimal_info': {
                'theoretical_minimum': optimal_info['theoretical_minimum'],
                'realistic_optimal': optimal_info['realistic_optimal'],
                'your_performance': tier
            }
        }
    
    def _fallback_score(self, questions_asked, correct):
        """Fallback scoring when optimal data not available"""
        base_score = 400 if correct else 0
        efficiency = max(0, 100 - len(questions_asked) * 5)
        
        return {
            'total_score': base_score + efficiency,
            'breakdown': {
                'accuracy': base_score,
                'efficiency': efficiency,
                'quality': 0,
                'hint_penalty': 0
            },
            'metrics': {
                'questions_asked': len(questions_asked),
                'optimal_questions': 10,
                'efficiency_ratio': len(questions_asked) / 10
            },
            'performance_tier': 'Unknown',
            'optimal_info': None
        }