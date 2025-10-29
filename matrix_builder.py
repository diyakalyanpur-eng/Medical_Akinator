import pandas as pd

class MatrixBuilder:
    """Build disease-feature matrix"""
    
    def __init__(self, field_data):
        self.field_data = field_data
        self.feature_columns = list(field_data.keys())
    
    def get_field_value(self, data, field_path):
        """Navigate nested dict to get value"""
        keys = field_path.split('.')
        current = data
        
        try:
            for key in keys:
                current = current[key]
            return str(current)
        except (KeyError, TypeError):
            return "N/A"
    
    def build_matrix(self, diseases):
        """Build complete matrix"""
        matrix_data = []
        
        for disease in diseases:
            row = {
                'disease_id': disease.get('id', 'unknown'),
                'disease_name': disease.get('name', 'Unknown'),
                'difficulty': disease.get('difficulty', 'moderate'),
                'category': disease.get('category', 'unknown')
            }
            
            for field_path in self.feature_columns:
                row[field_path] = self.get_field_value(disease, field_path)
            
            matrix_data.append(row)
        
        return pd.DataFrame(matrix_data)