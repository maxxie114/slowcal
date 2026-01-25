"""
Example usage of BusinessProblemAgent
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.risk_engine.problem_agent import BusinessProblemAgent

# Example input from ML model
risk_input = {
    "risk_score": 0.73,
    "risk_message": "Based on 100,000 historical SF businesses, 73% of businesses with your profile (high violations, young age, restaurant industry) closed within 2 years. You should take preventive action.",
    "profile": {
        "industry": "restaurant",
        "age": "young",
        "risk_factors": ["high violations", "young age", "restaurant industry"],
        "business_age_years": 2,
        "total_violations": 5,
        "location": "Mission District"
    }
}

# Use the agent
with BusinessProblemAgent() as agent:
    results = agent.analyze_business_risk(risk_input)
    
    print("=" * 80)
    print("BUSINESS PROBLEM ANALYSIS RESULTS")
    print("=" * 80)
    print("\nSUMMARY:")
    print(results["summary"])
    
    print("\n\nPROBLEMS AND SOLUTIONS:")
    for i, problem in enumerate(results["problems"], 1):
        print(f"\n{i}. {problem.get('problem', 'Unknown')}")
        print(f"   Severity: {problem.get('severity', 'unknown')}")
        print(f"   Department: {problem.get('city_department', 'N/A')}")
        
        if problem.get('solutions'):
            print("   Solutions:")
            for solution in problem['solutions']:
                print(f"     - {solution.get('action', 'N/A')}")
                print(f"       Contact: {solution.get('contact', 'N/A')}")
                print(f"       Timeline: {solution.get('expected_timeline', 'N/A')}")

