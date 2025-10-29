import json
from collections import defaultdict

class FieldExtractor:
    """Extract all fields from disease data structure"""
    
    def __init__(self):
        self.field_data = defaultdict(lambda: {
            'appears_in': [],
            'values': set()
        })
    
    def extract_fields(self, data, prefix=''):
        """Recursively extract fields from nested dict"""
        fields = {}
        
        for key, value in data.items():
            current_path = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                nested_fields = self.extract_fields(value, current_path)
                fields.update(nested_fields)
            elif isinstance(value, list):
                continue  # Skip lists
            else:
                fields[current_path] = str(value)
        
        return fields
    
    def process_diseases(self, diseases):
        """Process all diseases and extract fields"""
        for disease in diseases:
            disease_id = disease.get('id', 'unknown')
            fields = self.extract_fields(disease)
            
            for field_path, value in fields.items():
                self.field_data[field_path]['appears_in'].append(disease_id)
                self.field_data[field_path]['values'].add(value)
        
        return self.field_data