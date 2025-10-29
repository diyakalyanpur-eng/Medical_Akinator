import numpy as np
#import pandas as pd

class OptimalCalculator:
    """Calculate optimal questions using information theory"""
    
    def __init__(self, disease_matrix_df):
        self.df = disease_matrix_df
        self.feature_columns = [col for col in self.df.columns 
                               if col not in ['disease_id', 'disease_name', 
                                            'difficulty', 'category']]
    
    def calculate_entropy(self, n_diseases):
        """Calculate uncertainty for n diseases"""
        if n_diseases <= 1:
            return 0
        return np.log2(n_diseases)
    
    def calculate_information_gain(self, feature, remaining_diseases):
        """Calculate information gain for a feature"""
        if len(remaining_diseases) <= 1:
            return 0
        
        current_entropy = self.calculate_entropy(len(remaining_diseases))
        
        # Get value distribution
        feature_values = self.df.loc[remaining_diseases, feature]
        value_counts = feature_values.value_counts()
        value_counts = value_counts[value_counts.index != 'N/A']
        
        if len(value_counts) == 0:
            return 0
        
        # Calculate weighted entropy
        weighted_entropy = 0
        total = len(remaining_diseases)
        
        for value, count in value_counts.items():
            probability = count / total
            subset_entropy = self.calculate_entropy(count)
            weighted_entropy += probability * subset_entropy
        
        return current_entropy - weighted_entropy
    
    def find_optimal_path(self, target_disease_id):
        """Find optimal question sequence"""
        target_idx = self.df[self.df['disease_id'] == target_disease_id].index[0]
        remaining_diseases = self.df.index.tolist()
        questions_asked = []
        pathway = []
        
        max_iterations = 30
        iteration = 0
        
        while len(remaining_diseases) > 1 and iteration < max_iterations:
            iteration += 1
            
            best_feature = None
            best_gain = -1
            
            for feature in self.feature_columns:
                if feature in questions_asked:
                    continue
                
                gain = self.calculate_information_gain(feature, remaining_diseases)
                
                if gain > best_gain:
                    best_gain = gain
                    best_feature = feature
            
            if best_feature is None or best_gain <= 0:
                break
            
            questions_asked.append(best_feature)
            target_answer = self.df.loc[target_idx, best_feature]
            
            pathway.append({
                'field': best_feature,
                'information_gain': round(best_gain, 3),
                'diseases_before': len(remaining_diseases)
            })
            
            remaining_diseases = [
                idx for idx in remaining_diseases
                if self.df.loc[idx, best_feature] == target_answer
            ]
            
            pathway[-1]['diseases_after'] = len(remaining_diseases)
        
        return len(questions_asked), pathway
    
    def calculate_all_optimal(self):
        """Calculate optimal for all diseases"""
        optimal_data = {}
        
        for idx, row in self.df.iterrows():
            disease_id = row['disease_id']
            difficulty = row['difficulty']
            
            num_questions, pathway = self.find_optimal_path(disease_id)
            
            # Apply clinical adjustments
            multipliers = {'easy': 1.0, 'moderate': 1.2, 'hard': 1.5}
            multiplier = multipliers.get(difficulty, 1.2)
            realistic_optimal = int(num_questions * multiplier) + 2
            
            optimal_data[disease_id] = {
                'disease_name': row['disease_name'],
                'difficulty': difficulty,
                'theoretical_minimum': num_questions,
                'realistic_optimal': realistic_optimal,
                'excellent_threshold': max(3, realistic_optimal - 1),
                'acceptable_maximum': int(realistic_optimal * 1.5),
                'optimal_pathway': pathway
            }
        
        return optimal_data