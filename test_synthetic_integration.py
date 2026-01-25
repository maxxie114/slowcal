"""
Test script to verify synthetic data integration.
Runs CaseManagerAgent in synthetic mode.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.agents.case_manager import CaseManagerAgent

def test_synthetic_flow():
    print("🚀 Starting Synthetic Data Integration Test")
    
    # Initialize Case Manager (LLM agents disabled for speed/cost if desired, 
    # but we want to see if they can 'see' the data)
    manager = CaseManagerAgent(enable_llm_agents=False)
    
    # Test business ID from synthetic_evidence.json
    test_query = "Kumari Arun"
    
    print(f"--- Analyzing '{test_query}' in SYNTHETIC MODE ---")
    
    result = manager.analyze(
        business_query=test_query,
        options={"use_synthetic": True}
    )
    
    if result.success:
        print("\n✅ Analysis Successful!")
        risk = result.response.get("risk", {})
        print(f"Risk Score: {risk.get('score')} ({risk.get('band')})")
        
        signals = result.response.get("signals", {})
        print("\nSignals acquired:")
        for source, data in signals.items():
            if isinstance(data, dict):
                # Count records or specific fields
                count = data.get("permit_count_12m") or data.get("incident_count_12m") or data.get("total_matches") or "N/A"
                print(f" - {source}: {count}")
            else:
                print(f" - {source}: Unknown format")
                
        # Check for evidence refs
        audit = result.response.get("audit", {})
        print(f"\nAudit pulled at: {audit.get('data_pulled_at')}")
    else:
        print("\n❌ Analysis Failed!")
        for error in result.context.errors:
            print(f"Error: {error}")

if __name__ == "__main__":
    test_synthetic_flow()
