"""
Live test of BusinessProblemAgent with real web scraping
This will actually scrape the web for business problems
"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent))

from src.risk_engine.problem_agent import BusinessProblemAgent

def live_agent_run():
    """Run agent with real web scraping"""
    
    print("=" * 80)
    print("LIVE BUSINESS PROBLEM AGENT TEST")
    print("=" * 80)
    print("\n⚠️  This will perform REAL web scraping and may take 5-10 minutes")
    print("⚠️  Make sure your DGX Spark instance is running at 192.168.128.252:8000\n")
    
    # Real input from ML model
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
    
    print("📥 INPUT:")
    print(json.dumps(risk_input, indent=2))
    
    print("\n" + "=" * 80)
    print("RUNNING AGENT WITH REAL WEB SCRAPING...")
    print("=" * 80)
    
    try:
        # Use real agent with Playwright (no mocking)
        with BusinessProblemAgent() as agent:
            print("\n1️⃣ Generating search queries using Nemotron...")
            queries = agent._generate_search_queries(risk_input)
            print(f"   ✅ Generated {len(queries)} queries:")
            for i, q in enumerate(queries, 1):
                print(f"      {i}. {q}")
            
            print("\n2️⃣ Scraping real web sources (this may take a few minutes)...")
            print("   ⏳ Please wait while we scrape news articles, Reddit, and reports...")
            scraped = agent._scrape_sources(queries, risk_input)
            print(f"   ✅ Scraped {len(scraped)} real sources")
            for i, s in enumerate(scraped[:5], 1):  # Show first 5
                print(f"      {i}. {s['title'][:60]}... ({s['source_type']})")
            
            print("\n3️⃣ Extracting problems using Nemotron...")
            problems = agent._extract_problems(scraped, risk_input, scraped)
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
                "risk_profile": risk_input.get("profile", {}),
                "scraped_sources_count": len(scraped)
            }
            
            print("\n" + "=" * 80)
            print("📤 OUTPUT:")
            print("=" * 80)
            
            print("\n📋 SUMMARY:")
            print(results["summary"])
            
            print(f"\n🔍 PROBLEMS FOUND: {len(results['problems'])}")
            print(f"📰 SOURCES SCRAPED: {results['scraped_sources_count']}")
            
            for i, problem in enumerate(results["problems"], 1):
                print(f"\n{i}. {problem.get('problem', 'Unknown')}")
                print(f"   Severity: {problem.get('severity', 'unknown').upper()}")
                print(f"   Department: {problem.get('city_department', 'N/A')}")
                print(f"   Sources: {len(problem.get('sources', []))} source(s)")
                
                if problem.get('solutions'):
                    print("   Solutions:")
                    for j, sol in enumerate(problem['solutions'], 1):
                        print(f"      {j}. {sol.get('action', 'N/A')}")
                        print(f"         Contact: {sol.get('contact', 'N/A')}")
                        print(f"         Timeline: {sol.get('expected_timeline', 'N/A')}")
                        if sol.get('source_citation'):
                            print(f"         Source: {sol.get('source_citation')}")
            
            # Save to file
            output_file = Path("live_agent_output.json")
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
    results = live_agent_run()
    
    if results:
        print("\n" + "=" * 80)
        print("✅ LIVE RUN COMPLETE")
        print("=" * 80)
        print(f"\nFound {len(results['problems'])} problems from {results['scraped_sources_count']} real sources")
    else:
        print("\n" + "=" * 80)
        print("❌ LIVE RUN FAILED")
        print("=" * 80)

