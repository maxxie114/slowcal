"""
Simulated test of BusinessProblemAgent with mock data
This test uses mocked scraping to avoid actual web requests
"""

import sys
from pathlib import Path
import json
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).parent))

from src.risk_engine.problem_agent import BusinessProblemAgent
from src.utils.nemotron_client import NemotronClient

# Mock scraped content (simulating what would be scraped)
MOCK_SCRAPED_CONTENT = [
    {
        "source_type": "news",
        "url": "https://sfchronicle.com/business/restaurant-closures",
        "title": "SF Restaurants Closing Due to Homeless Encampments",
        "content": "Many restaurants in San Francisco's Mission District are struggling with homeless encampments blocking their storefronts. Business owners report customers avoiding their establishments due to safety concerns. SF 311 has been receiving increased complaints about encampments near businesses.",
        "query": "San Francisco restaurant closures Mission District"
    },
    {
        "source_type": "reddit",
        "url": "https://reddit.com/r/sanfrancisco/business-struggles",
        "title": "Restaurant owner struggling with noise complaints",
        "content": "I own a restaurant in SF and neighbors keep filing noise complaints. The city's noise ordinance enforcement is strict. I've tried working with SFPD but the complaints keep coming. This is affecting my business license renewal.",
        "query": "SF restaurant noise complaints"
    },
    {
        "source_type": "news",
        "url": "https://sfexaminer.com/business/permits-delays",
        "title": "Permit Delays Crippling Small Businesses",
        "content": "Small businesses in San Francisco face months-long delays for permits from the Planning Department. Restaurant owners report waiting 6+ months for simple permit modifications. The Planning Department acknowledges the backlog.",
        "query": "SF Planning Department permit delays"
    }
]

def simulate_agent_run():
    """Simulate a full agent run with mocked scraping"""
    
    print("=" * 80)
    print("SIMULATED BUSINESS PROBLEM AGENT TEST")
    print("=" * 80)
    
    # Simulated input from ML model
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
    
    print("\n📥 INPUT:")
    print(json.dumps(risk_input, indent=2))
    
    print("\n" + "=" * 80)
    print("RUNNING AGENT (with mocked scraping)...")
    print("=" * 80)
    
    # Mock the scraping method to return our mock data
    with patch.object(BusinessProblemAgent, '_scrape_sources', return_value=MOCK_SCRAPED_CONTENT):
        # Also mock Playwright initialization to avoid browser launch
        with patch('src.risk_engine.problem_agent.sync_playwright'):
            try:
                # Initialize agent (will use real Nemotron API)
                agent = BusinessProblemAgent()
                
                print("\n1️⃣ Generating search queries...")
                queries = agent._generate_search_queries(risk_input)
                print(f"   ✅ Generated {len(queries)} queries:")
                for i, q in enumerate(queries, 1):
                    print(f"      {i}. {q}")
                
                print("\n2️⃣ Scraping sources (MOCKED)...")
                scraped = agent._scrape_sources(queries, risk_input)
                print(f"   ✅ Using {len(scraped)} mock sources")
                
                print("\n3️⃣ Extracting problems using Nemotron...")
                problems = agent._extract_problems(scraped, risk_input)
                print(f"   ✅ Extracted {len(problems)} problems")
                
                print("\n4️⃣ Generating solutions using Nemotron...")
                solutions = agent._generate_solutions(problems, risk_input)
                print(f"   ✅ Generated solutions for {len(solutions)} problems")
                
                print("\n5️⃣ Generating summary...")
                summary = agent._generate_summary(solutions, risk_input)
                print("   ✅ Summary generated")
                
                # Compile final results
                results = {
                    "problems": solutions,
                    "summary": summary,
                    "risk_profile": risk_input.get("profile", {})
                }
                
                print("\n" + "=" * 80)
                print("📤 OUTPUT:")
                print("=" * 80)
                
                print("\n📋 SUMMARY:")
                print(results["summary"])
                
                print(f"\n🔍 PROBLEMS FOUND: {len(results['problems'])}")
                for i, problem in enumerate(results["problems"], 1):
                    print(f"\n{i}. {problem.get('problem', 'Unknown')}")
                    print(f"   Severity: {problem.get('severity', 'unknown').upper()}")
                    print(f"   Department: {problem.get('city_department', 'N/A')}")
                    print(f"   City Code: {problem.get('city_code', 'N/A')}")
                    
                    if problem.get('solutions'):
                        print("   Solutions:")
                        for j, sol in enumerate(problem['solutions'], 1):
                            print(f"      {j}. {sol.get('action', 'N/A')}")
                            print(f"         Contact: {sol.get('contact', 'N/A')}")
                            print(f"         Timeline: {sol.get('expected_timeline', 'N/A')}")
                            if sol.get('steps'):
                                print(f"         Steps:")
                                for step in sol['steps']:
                                    print(f"           - {step}")
                
                # Save to file
                output_file = Path("simulated_agent_output.json")
                with open(output_file, 'w') as f:
                    json.dump(results, f, indent=2)
                print(f"\n💾 Full output saved to: {output_file}")
                
                return results
                
            except Exception as e:
                print(f"\n❌ ERROR: {e}")
                import traceback
                traceback.print_exc()
                return None

if __name__ == "__main__":
    results = simulate_agent_run()
    
    if results:
        print("\n" + "=" * 80)
        print("✅ SIMULATION COMPLETE")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("❌ SIMULATION FAILED")
        print("=" * 80)

