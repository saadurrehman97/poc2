#!/usr/bin/env python3
"""
Quick Start Script for Neptune Plumbing Pipeline
Test the pipeline with a sample file
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from pipeline import run_full_pipeline
from config import Config

def main():
    """Run pipeline on a test file"""
    
    # Example: Update this path to your test file
    test_file = "/workspace/P1.1-PLUMBING-PLAN-Rev.1.pdf"
    
    print("=" * 80)
    print("Neptune Plumbing - Quick Start")
    print("=" * 80)
    print(f"\nTest file: {test_file}")
    print(f"Output dir: {Config.OUTPUT_BASE_DIR}\n")
    
    # Check if file exists
    if not Path(test_file).exists():
        print(f"❌ Error: Test file not found: {test_file}")
        print("\nPlease update the 'test_file' path in quickstart.py")
        return
    
    # Validate configuration
    errors = Config.validate()
    if errors:
        print("⚠️ Configuration issues detected:")
        for error in errors:
            print(f"  - {error}")
        print("\nPlease update paths in src/config.py")
        return
    
    # Run pipeline
    try:
        results = run_full_pipeline(
            test_file,
            output_dir="./outputs",
            dfine_conf=0.3
        )
        
        print("\n" + "=" * 80)
        print("✅ SUCCESS - Results summary:")
        print("=" * 80)
        print(f"Output directory: {results.get('output_directory', 'N/A')}")
        print(f"Total symbols detected: {len(results.get('final_best_estimates', {}))}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
