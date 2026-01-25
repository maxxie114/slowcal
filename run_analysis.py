#!/usr/bin/env python3
"""
Run the SlowCal Multi-Agent Risk Analysis System

This script provides a simple way to run the complete risk analysis pipeline
for a San Francisco small business.

Usage:
    python run_analysis.py "Business Name, Address"
    python run_analysis.py --demo

Examples:
    python run_analysis.py "Blue Bottle Coffee, 300 Webster St"
    python run_analysis.py "Tartine Bakery, 600 Guerrero St, SF"
    python run_analysis.py --demo
"""

import argparse
import json
import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agents import CaseManagerAgent
from tools.nim_client import NIMClient


def print_banner():
    """Print the SlowCal banner"""
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   ███████╗██╗      ██████╗ ██╗    ██╗ ██████╗ █████╗ ██╗         ║
║   ██╔════╝██║     ██╔═══██╗██║    ██║██╔════╝██╔══██╗██║         ║
║   ███████╗██║     ██║   ██║██║ █╗ ██║██║     ███████║██║         ║
║   ╚════██║██║     ██║   ██║██║███╗██║██║     ██╔══██║██║         ║
║   ███████║███████╗╚██████╔╝╚███╔███╔╝╚██████╗██║  ██║███████╗    ║
║   ╚══════╝╚══════╝ ╚═════╝  ╚══╝╚══╝  ╚═════╝╚═╝  ╚═╝╚══════╝    ║
║                                                                   ║
║   SF Small Business Risk Intelligence Platform                    ║
║   Powered by Nemotron on DGX Spark                               ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
    """)


def check_nim_health():
    """Check if NIM endpoint is available"""
    print("🔍 Checking NIM endpoint health...")
    client = NIMClient(timeout=300.0)  # 5 min timeout for DGX
    
    if client.is_ready():
        print("✅ NIM endpoint is healthy")
        models = client.get_models()
        if models:
            print(f"   Available models: {', '.join(models[:3])}")
        return True
    else:
        print("⚠️  NIM endpoint not available - LLM features will be disabled")
        print("   Set NEMOTRON_BASE_URL environment variable to configure")
        return False


def run_analysis(business_query: str, horizon_months: int = 6, skip_llm: bool = False):
    """Run the complete risk analysis"""
    print(f"\n📊 Analyzing: {business_query}")
    print(f"   Horizon: {horizon_months} months")
    print("-" * 60)
    
    # Initialize manager
    manager = CaseManagerAgent(enable_llm_agents=not skip_llm)
    
    # Run analysis
    print("\n⏳ Running analysis pipeline...")
    result = manager.analyze(
        business_query=business_query,
        horizon_months=horizon_months,
        options={"skip_llm": skip_llm}
    )
    
    print(f"\n⏱️  Analysis completed in {result.duration_ms:.0f}ms")
    
    return result


def print_results(result):
    """Pretty print the analysis results"""
    if not result.success:
        print("\n❌ Analysis failed!")
        print(f"   Errors: {result.context.errors}")
        return
    
    response = result.response
    
    print("\n" + "=" * 60)
    print("📋 RISK ANALYSIS RESULTS")
    print("=" * 60)
    
    # Entity info
    entity = response.get("entity", {})
    print(f"\n🏢 Business: {entity.get('business_name', 'Unknown')}")
    print(f"   Address: {entity.get('address', 'Unknown')}")
    print(f"   Neighborhood: {entity.get('neighborhood', 'Unknown')}")
    print(f"   Match Confidence: {entity.get('match_confidence', 0):.0%}")
    
    # Risk score
    risk = response.get("risk", {})
    score = risk.get("score", 0)
    band = risk.get("band", "unknown")
    
    # Color-coded risk band
    band_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(band, "⚪")
    
    print(f"\n📈 Risk Assessment:")
    print(f"   {band_emoji} Score: {score:.2f} ({band.upper()} risk)")
    
    # Top drivers
    drivers = risk.get("top_drivers", [])
    if drivers:
        print(f"\n🎯 Top Risk Drivers:")
        for i, driver in enumerate(drivers[:5], 1):
            direction = "↑" if driver.get("direction") == "up" else "↓" if driver.get("direction") == "down" else "→"
            print(f"   {i}. {driver.get('driver', 'Unknown')} {direction}")
    
    # Strategy summary
    strategy = response.get("strategy", {})
    if strategy.get("summary"):
        print(f"\n💡 Strategy Summary:")
        # Print full summary wrapped at 80 chars
        summary = strategy['summary']
        words = summary.split()
        line = "   "
        for word in words:
            if len(line) + len(word) + 1 > 80:
                print(line)
                line = "   " + word
            else:
                line += " " + word if line.strip() else word
        if line.strip():
            print(line)
    
    # Workflow Plan (if available)
    workflow = strategy.get("workflow_plan", {})
    if workflow:
        print(f"\n📅 Workflow Plan:")
        for phase, desc in workflow.items():
            phase_label = phase.replace("_", " ").title()
            print(f"   • {phase_label}: {desc}")
    
    # Actions by horizon
    actions = strategy.get("actions", [])
    if actions:
        print(f"\n📋 Recommended Actions:")
        
        for horizon in ["2_weeks", "60_days", "6_months"]:
            horizon_actions = [a for a in actions if a.get("horizon") == horizon]
            if horizon_actions:
                horizon_label = {"2_weeks": "📌 Week 1-2", "60_days": "📆 Days 1-60", "6_months": "🗓️ Month 1-6"}.get(horizon, horizon)
                print(f"\n   {horizon_label}:")
                for action in horizon_actions:
                    impact = action.get("expected_impact", "medium")
                    effort = action.get("effort", "medium")
                    impact_icon = {"low": "○", "medium": "◐", "high": "●"}.get(impact, "○")
                    effort_icon = {"low": "💚", "medium": "💛", "high": "❤️"}.get(effort, "💛")
                    
                    # Action title
                    action_text = action.get('action', '')
                    print(f"\n   {impact_icon} {action_text[:75]}{'...' if len(action_text) > 75 else ''}")
                    
                    # Why it matters
                    why = action.get('why', '')
                    if why:
                        print(f"     Why: {why[:100]}{'...' if len(why) > 100 else ''}")
                    
                    # Success metric
                    metric = action.get('success_metric', '')
                    if metric:
                        print(f"     ✓ Success: {metric[:80]}")
                    
                    print(f"     Impact: {impact_icon} {impact.upper()} | Effort: {effort_icon} {effort}")
    
    # Questions for user
    questions = strategy.get("questions_for_user", [])
    if questions:
        print(f"\n❓ Questions to Consider:")
        for q in questions[:5]:
            print(f"   • {q}")
    
    # Risk if no action
    risk_if_no_action = strategy.get("risk_if_no_action", "")
    if risk_if_no_action:
        print(f"\n⚡ Risk if No Action:")
        print(f"   {risk_if_no_action[:200]}{'...' if len(risk_if_no_action) > 200 else ''}")
    
    # Limitations
    limitations = response.get("limitations", [])
    if limitations:
        print(f"\n⚠️  Limitations:")
        for lim in limitations[:3]:
            print(f"   • {lim}")
    
    # Audit info
    audit = response.get("audit", {})
    print(f"\n📝 Audit:")
    print(f"   QA Status: {audit.get('qa_status', 'Unknown')}")
    print(f"   Data pulled: {audit.get('data_pulled_at', 'Unknown')}")
    
    print("\n" + "=" * 60)


def save_results(result, output_file: str):
    """Save results to JSON file"""
    with open(output_file, "w") as f:
        json.dump(result.response, f, indent=2, default=str)
    print(f"\n💾 Results saved to: {output_file}")


def run_demo():
    """Run a demo with simulated data"""
    print("\n🎭 Running in DEMO mode (simulated data)")
    print("-" * 60)
    
    # Demo business
    demo_response = {
        "case_id": "demo-001",
        "as_of": datetime.now().isoformat(),
        "horizon_months": 6,
        "entity": {
            "entity_id": "demo-biz-001",
            "business_name": "Sample Coffee Shop",
            "address": "123 Market St, San Francisco, CA",
            "neighborhood": "Financial District",
            "match_confidence": 0.95
        },
        "risk": {
            "score": 0.42,
            "band": "medium",
            "model_version": "v1.0.0",
            "top_drivers": [
                {"driver": "complaints_311_6m", "direction": "up", "evidence_refs": ["e:311-001"]},
                {"driver": "permit_delays", "direction": "up", "evidence_refs": ["e:permit-001"]},
                {"driver": "neighborhood_vacancy", "direction": "stable", "evidence_refs": ["e:vacancy-001"]},
            ]
        },
        "strategy": {
            "summary": "Medium risk profile driven by recent complaint activity. Focus on addressing 311 complaints and expediting pending permits.",
            "actions": [
                {
                    "horizon": "2_weeks",
                    "action": "Review and respond to all open 311 complaints",
                    "why": "Recent complaint activity is driving risk score",
                    "expected_impact": "medium",
                    "effort": "low",
                    "evidence_refs": ["e:311-001"],
                },
                {
                    "horizon": "60_days",
                    "action": "Follow up on pending permit applications",
                    "why": "Permit delays indicate potential compliance issues",
                    "expected_impact": "medium",
                    "effort": "medium",
                    "evidence_refs": ["e:permit-001"],
                },
                {
                    "horizon": "6_months",
                    "action": "Develop proactive neighbor relations program",
                    "why": "Reduce future complaint likelihood",
                    "expected_impact": "high",
                    "effort": "medium",
                    "evidence_refs": ["e:311-001"],
                },
            ],
            "questions_for_user": [
                "Do you have any pending permit applications?",
                "What are your operating hours?",
            ]
        },
        "limitations": [
            "Demo mode - using simulated data",
        ],
        "audit": {
            "data_pulled_at": datetime.now().isoformat(),
            "qa_status": "PASS",
        }
    }
    
    # Create mock result
    class MockResult:
        success = True
        response = demo_response
        duration_ms = 150
        context = type('obj', (object,), {'errors': []})()
    
    return MockResult()


def main():
    parser = argparse.ArgumentParser(
        description="SlowCal Multi-Agent Risk Analysis System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_analysis.py "Blue Bottle Coffee, 300 Webster St"
  python run_analysis.py "Tartine Bakery, SF" --horizon 12
  python run_analysis.py --demo
  python run_analysis.py "My Business" --skip-llm --output results.json
        """
    )
    
    parser.add_argument(
        "business",
        nargs="?",
        help="Business name and/or address to analyze"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run in demo mode with simulated data"
    )
    parser.add_argument(
        "--horizon",
        type=int,
        default=6,
        help="Analysis horizon in months (default: 6)"
    )
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Skip LLM-based agents (faster, less detailed)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Save results to JSON file"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Minimal output"
    )
    
    args = parser.parse_args()
    
    # Print banner unless quiet
    if not args.quiet:
        print_banner()
    
    # Validate args
    if not args.demo and not args.business:
        parser.error("Please provide a business query or use --demo")
    
    # Check NIM health (unless demo mode)
    if not args.demo and not args.skip_llm:
        nim_available = check_nim_health()
        if not nim_available:
            args.skip_llm = True
    
    # Run analysis
    if args.demo:
        result = run_demo()
    else:
        result = run_analysis(
            business_query=args.business,
            horizon_months=args.horizon,
            skip_llm=args.skip_llm
        )
    
    # Print results
    if not args.quiet:
        print_results(result)
    
    # Save if requested
    if args.output:
        save_results(result, args.output)
    
    # Exit code
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
