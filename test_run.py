"""
Test Run: Business Risk Analysis Demo

This script demonstrates how small business owners can use the 
risk analysis service to assess their business risk and get 
actionable recommendations.

Run this file to see examples of the risk analysis in action:
    python test_run.py
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from risk_engine.business_risk_service import (
    BusinessRiskService, 
    BusinessOwnerInput, 
    analyze_my_business
)


def print_header(text: str):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_result(result):
    """Print a formatted risk analysis result"""
    # Risk level emoji
    level_emoji = {
        "Low": "🟢",
        "Medium": "🟡", 
        "High": "🔴"
    }
    
    emoji = level_emoji.get(result.risk_level, "⚪")
    
    print(f"\n📊 Business: {result.business_name}")
    print(f"   {emoji} Risk Level: {result.risk_level}")
    print(f"   📈 Risk Score: {result.risk_score:.1f}%")
    print(f"   🎯 Confidence: {result.confidence:.0%}")
    
    print(f"\n🔍 Top Risk Factors:")
    for factor in result.top_risk_factors:
        print(f"   • {factor['factor']}: {factor['impact']}")
        if factor['description']:
            print(f"     └─ {factor['description']}")
    
    print(f"\n📍 Location Insights:")
    print(f"   • Neighborhood: {result.neighborhood_insights['neighborhood']}")
    print(f"   • Environment: {result.neighborhood_insights['business_environment']}")
    print(f"   • Development: {result.neighborhood_insights['development_activity']}")
    
    print(f"\n📊 Comparison:")
    print(f"   • Industry Average Risk: {result.industry_average_risk:.1f}%")
    print(f"   • Neighborhood Average: {result.neighborhood_average_risk:.1f}%")
    
    print(f"\n💡 Recommendations:")
    for i, rec in enumerate(result.recommendations, 1):
        print(f"   {i}. {rec}")


def demo_new_restaurant():
    """Demo: New restaurant in the Mission district"""
    print_header("EXAMPLE 1: New Restaurant in Mission")
    
    print("\n👤 Business Owner Input:")
    print("   - Business Name: Maria's Tacos")
    print("   - Year Started: 2024")
    print("   - Industry: Restaurant")
    print("   - Neighborhood: Mission")
    
    result = analyze_my_business(
        business_name="Maria's Tacos",
        year_started=2024,
        industry="restaurant",
        neighborhood="Mission"
    )
    
    print_result(result)


def demo_established_law_firm():
    """Demo: Established law firm in Financial District"""
    print_header("EXAMPLE 2: Established Law Firm")
    
    print("\n👤 Business Owner Input:")
    print("   - Business Name: Smith & Associates")
    print("   - Year Started: 2015")
    print("   - Industry: Legal/Professional Services")
    print("   - Neighborhood: Financial District")
    
    result = analyze_my_business(
        business_name="Smith & Associates",
        year_started=2015,
        industry="legal",
        neighborhood="Financial District"
    )
    
    print_result(result)


def demo_new_retail_tenderloin():
    """Demo: New retail shop in challenging neighborhood"""
    print_header("EXAMPLE 3: New Retail in Tenderloin (Higher Risk)")
    
    print("\n👤 Business Owner Input:")
    print("   - Business Name: Urban Boutique")
    print("   - Year Started: 2025")
    print("   - Industry: Retail")
    print("   - Neighborhood: Tenderloin")
    print("   - Has License: No (forgot to register!)")
    
    result = analyze_my_business(
        business_name="Urban Boutique",
        year_started=2025,
        industry="retail",
        neighborhood="Tenderloin",
        has_license=False  # Missing business license
    )
    
    print_result(result)


def demo_tech_startup():
    """Demo: Tech startup in SOMA"""
    print_header("EXAMPLE 4: Tech Startup in SOMA")
    
    print("\n👤 Business Owner Input:")
    print("   - Business Name: AI Solutions Inc")
    print("   - Year Started: 2022")
    print("   - Industry: Technology")
    print("   - Neighborhood: SOMA")
    
    result = analyze_my_business(
        business_name="AI Solutions Inc",
        year_started=2022,
        industry="tech",
        neighborhood="SOMA"
    )
    
    print_result(result)


def demo_hotel():
    """Demo: Small hotel/B&B"""
    print_header("EXAMPLE 5: Small Hotel in Marina")
    
    print("\n👤 Business Owner Input:")
    print("   - Business Name: Marina Bay Inn")
    print("   - Year Started: 2018")
    print("   - Industry: Hospitality")
    print("   - Neighborhood: Marina")
    print("   - Is Hotel/B&B: Yes")
    
    result = analyze_my_business(
        business_name="Marina Bay Inn",
        year_started=2018,
        industry="hotel",
        neighborhood="Marina",
        is_hotel=True
    )
    
    print_result(result)


def demo_quick_check():
    """Demo: Quick risk check with minimal input"""
    print_header("EXAMPLE 6: Quick Risk Check (Minimal Input)")
    
    service = BusinessRiskService()
    
    businesses = [
        ("Coffee Corner", 2023, "cafe", "Castro"),
        ("Downtown Dental", 2019, "healthcare", "FiDi"),
        ("Night Owl Bar", 2024, "bar", "North Beach"),
        ("Sunset Yoga", 2021, "fitness", "Sunset"),
    ]
    
    print("\n📋 Quick Risk Assessment for Multiple Businesses:\n")
    print(f"{'Business':<20} {'Industry':<12} {'Location':<15} {'Risk':<10} {'Score':<10}")
    print("-" * 70)
    
    for name, year, industry, neighborhood in businesses:
        result = service.quick_risk_check(
            business_name=name,
            year_started=year,
            industry=industry,
            neighborhood=neighborhood
        )
        
        level_emoji = {"Low": "🟢", "Medium": "🟡", "High": "🔴"}.get(result['risk_level'], "⚪")
        
        print(f"{name:<20} {industry:<12} {neighborhood:<15} {level_emoji} {result['risk_level']:<6} {result['risk_score']:<10}")


def demo_interactive():
    """Interactive demo - let user input their business info"""
    print_header("INTERACTIVE: Analyze Your Business")
    
    print("\n📝 Enter your business information:\n")
    
    try:
        name = input("   Business Name: ").strip() or "My Business"
        year = int(input("   Year Started (e.g., 2020): ").strip() or "2020")
        industry = input("   Industry (restaurant/retail/tech/etc): ").strip() or "other"
        neighborhood = input("   SF Neighborhood: ").strip() or "Mission"
        
        print("\n⏳ Analyzing your business risk...")
        
        result = analyze_my_business(
            business_name=name,
            year_started=year,
            industry=industry,
            neighborhood=neighborhood
        )
        
        print_result(result)
        
    except KeyboardInterrupt:
        print("\n\n👋 Analysis cancelled.")
    except ValueError as e:
        print(f"\n❌ Invalid input: {e}")


def main():
    """Main demo runner"""
    print("\n" + "🏢" * 35)
    print("\n   SMALL BUSINESS RISK ANALYZER - DEMO")
    print("   Powered by SF Open Data + Machine Learning")
    print("\n" + "🏢" * 35)
    
    # Run all demos
    demo_new_restaurant()
    demo_established_law_firm()
    demo_new_retail_tenderloin()
    demo_tech_startup()
    demo_hotel()
    demo_quick_check()
    
    # Ask if user wants interactive mode
    print("\n" + "=" * 70)
    try:
        response = input("\n🎯 Want to analyze YOUR business? (y/n): ").strip().lower()
        if response == 'y':
            demo_interactive()
    except KeyboardInterrupt:
        pass
    
    print("\n" + "=" * 70)
    print("   Thank you for using the Small Business Risk Analyzer!")
    print("   Built for SF small business owners with ❤️")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
