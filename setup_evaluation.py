#!/usr/bin/env python3
"""
One-time setup script to generate optimal question data
Run this after you have your diseases.json file ready
"""

import json
import os
from pathlib import Path
from evaluation.field_extractor import FieldExtractor
from evaluation.matrix_builder import MatrixBuilder
from evaluation.optimal_calculator import OptimalCalculator

def main():
    print("="*60)
    print("Disease Akinator - Evaluation System Setup")
    print("="*60)
    
    # Paths
    data_dir = Path("data")
    diseases_file = data_dir / "diseases.json"
    generated_dir = data_dir / "generated"
    
    # Create generated directory
    generated_dir.mkdir(exist_ok=True)
    
    # Load diseases
    print("\n[1/4] Loading diseases...")
    if not diseases_file.exists():
        print(f"❌ Error: {diseases_file} not found!")
        return
    
    with open(diseases_file, 'r', encoding='utf-8') as f:
        diseases = json.load(f)
    
    print(f"✓ Loaded {len(diseases)} diseases")
    
    # Extract fields
    print("\n[2/4] Extracting fields from disease data...")
    extractor = FieldExtractor()
    field_data = extractor.process_diseases(diseases)
    print(f"✓ Extracted {len(field_data)} unique fields")
    
    # Build matrix
    print("\n[3/4] Building disease-feature matrix...")
    builder = MatrixBuilder(field_data)
    matrix_df = builder.build_matrix(diseases)
    
    # Save matrix
    matrix_file = generated_dir / "disease_matrix.csv"
    matrix_df.to_csv(matrix_file, index=False)
    print(f"✓ Built matrix: {matrix_df.shape[0]} diseases × {matrix_df.shape[1]} features")
    print(f"✓ Saved to {matrix_file}")
    
    # Calculate optimal questions
    print("\n[4/4] Calculating optimal questions for each disease...")
    calculator = OptimalCalculator(matrix_df)
    optimal_data = calculator.calculate_all_optimal()
    
    # Save optimal data
    optimal_file = generated_dir / "optimal_questions.json"
    with open(optimal_file, 'w', encoding='utf-8') as f:
        json.dump(optimal_data, f, indent=2)
    
    print(f"✓ Calculated optimal paths for {len(optimal_data)} diseases")
    print(f"✓ Saved to {optimal_file}")
    
    # Print summary
    print("\n" + "="*60)
    print("Setup Complete! 🎉")
    print("="*60)
    
    print("\nSummary Statistics:")
    all_optimal = [d['realistic_optimal'] for d in optimal_data.values()]
    print(f"  Average optimal questions: {sum(all_optimal)/len(all_optimal):.1f}")
    print(f"  Range: {min(all_optimal)} - {max(all_optimal)} questions")
    
    # By difficulty
    by_diff = {}
    for d in optimal_data.values():
        diff = d['difficulty']
        by_diff.setdefault(diff, []).append(d['realistic_optimal'])
    
    print("\n  By difficulty:")
    for diff, values in sorted(by_diff.items()):
        print(f"    {diff}: avg {sum(values)/len(values):.1f} questions")
    
    print("\n✓ Your API is now ready with evaluation system!")
    print("  Start your server: python app.py")

if __name__ == '__main__':
    main()