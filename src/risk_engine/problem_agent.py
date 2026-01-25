"""
Business Problem Agent - Scrapes external sources to find specific problems
and generates actionable solutions with SF city department contacts
"""

import json
import time
import logging
from typing import Dict, List, Optional
from playwright.sync_api import sync_playwright, Browser, Page
from bs4 import BeautifulSoup
import requests
from ..utils.nemotron_client import NemotronClient

logger = logging.getLogger(__name__)

class BusinessProblemAgent:
    """Agent that finds business problems from external sources and generates solutions"""
    
    # SF City Departments and Codes
    SF_DEPARTMENTS = {
        "311": {
            "name": "SF 311",
            "contact": "311 or sf311.org",
            "description": "General city services and reporting"
        },
        "public_works": {
            "name": "Department of Public Works",
            "contact": "311 or dpw.sfgov.org",
            "description": "Homeless encampments, street cleaning, infrastructure"
        },
        "planning": {
            "name": "Planning Department",
            "contact": "sfplanning.org",
            "description": "Permits, zoning, land use"
        },
        "health": {
            "name": "Department of Public Health",
            "contact": "sfdph.org",
            "description": "Health permits, violations, food safety"
        },
        "police": {
            "name": "SFPD",
            "contact": "911 (emergency) or sfpd.org",
            "description": "Public safety, crime prevention"
        },
        "economic_workforce": {
            "name": "Office of Economic and Workforce Development",
            "contact": "oewd.org",
            "description": "Business support, grants, resources"
        }
    }
    
    # Priority sources for scraping
    SOURCE_PRIORITIES = [
        "news",      # News articles
        "reports",   # Industry reports/studies
        "reddit",    # Reddit discussions
        "reviews",   # Yelp/Google Reviews
        "social"     # Twitter/X
    ]
    
    def __init__(self, nemotron_client: Optional[NemotronClient] = None):
        """
        Initialize the Business Problem Agent
        
        Args:
            nemotron_client: Optional NemotronClient instance
        """
        self.client = nemotron_client or NemotronClient()
        self.browser: Optional[Browser] = None
        self.playwright = None
        
    def __enter__(self):
        """Context manager entry"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def analyze_business_risk(self, risk_input: Dict) -> Dict:
        """
        Main entry point: Analyze business risk and generate problems + solutions
        
        Args:
            risk_input: JSON input with risk profile
                Example:
                {
                    "risk_score": 0.73,
                    "risk_message": "Based on 100,000 historical SF businesses...",
                    "profile": {
                        "industry": "restaurant",
                        "age": "young",
                        "risk_factors": ["high violations", "young age", "restaurant industry"],
                        "business_age_years": 2,
                        "total_violations": 5,
                        "location": "Mission District"
                    }
                }
        
        Returns:
            Dictionary with problems and solutions
        """
        logger.info("Starting business problem analysis")
        
        # Step 1: Generate search queries using Nemotron
        search_queries = self._generate_search_queries(risk_input)
        logger.info(f"Generated {len(search_queries)} search queries")
        
        # Step 2: Scrape external sources
        scraped_content = self._scrape_sources(search_queries, risk_input)
        logger.info(f"Scraped {len(scraped_content)} sources")
        
        # Step 3: Extract problems using Nemotron
        problems = self._extract_problems(scraped_content, risk_input)
        logger.info(f"Extracted {len(problems)} problems")
        
        # Step 4: Generate solutions using Nemotron
        solutions = self._generate_solutions(problems, risk_input)
        logger.info(f"Generated solutions for {len(solutions)} problems")
        
        # Step 5: Generate summary
        summary = self._generate_summary(solutions, risk_input)
        
        return {
            "problems": solutions,
            "summary": summary,
            "risk_profile": risk_input.get("profile", {})
        }
    
    def _generate_search_queries(self, risk_input: Dict) -> List[str]:
        """Generate search queries from risk profile using Nemotron"""
        
        profile = risk_input.get("profile", {})
        risk_factors = profile.get("risk_factors", [])
        industry = profile.get("industry", "")
        location = profile.get("location", "San Francisco")
        
        prompt = f"""Generate 5 specific Google search queries to find news articles, reports, and discussions about why businesses in San Francisco are closing, specifically related to this business profile:

Business Profile:
- Industry: {industry}
- Location: {location}
- Risk Factors: {', '.join(risk_factors)}
- Business Age: {profile.get('business_age_years', 'unknown')} years
- Violations: {profile.get('total_violations', 0)}

Focus on finding:
1. News articles about SF business closures
2. Industry reports on business failures
3. Reddit discussions about business challenges
4. Specific problems that can be addressed with city help (homelessness, noise, permits, etc.)

Generate exactly 5 search queries, one per line, without numbering or bullets."""

        system_prompt = """You are an expert at generating effective web search queries. Generate specific, targeted queries that will find relevant information about business closures and problems in San Francisco."""

        response = self.client.generate(prompt, system_prompt=system_prompt, temperature=0.8, max_tokens=500)
        
        # Parse queries (one per line)
        queries = [q.strip() for q in response.split('\n') if q.strip() and not q.strip().startswith('#')]
        
        # Limit to 5 queries
        return queries[:5]
    
    def _scrape_sources(self, queries: List[str], risk_input: Dict) -> List[Dict]:
        """Scrape external sources using Playwright"""
        
        scraped_content = []
        
        if not self.browser:
            logger.warning("Browser not initialized, using requests fallback")
            return self._scrape_with_requests(queries)
        
        for query in queries:
            try:
                # Use Google Search
                page = self.browser.new_page()
                page.set_default_timeout(30000)
                
                # Search Google
                search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}&num=10"
                page.goto(search_url)
                time.sleep(2)  # Rate limiting
                
                # Extract search results
                results = page.query_selector_all('div.g')
                
                for i, result in enumerate(results[:10]):  # Top 10 results
                    try:
                        # Extract link and title
                        link_elem = result.query_selector('a')
                        title_elem = result.query_selector('h3')
                        
                        if link_elem and title_elem:
                            url = link_elem.get_attribute('href')
                            title = title_elem.inner_text()
                            
                            if url and url.startswith('http'):
                                # Visit the page and scrape content
                                try:
                                    page2 = self.browser.new_page()
                                    page2.goto(url, timeout=30000)
                                    time.sleep(2)
                                    
                                    content = page2.content()
                                    soup = BeautifulSoup(content, 'html.parser')
                                    
                                    # Extract main text content
                                    text_content = self._extract_text(soup)
                                    
                                    scraped_content.append({
                                        "source_type": self._classify_source(url),
                                        "url": url,
                                        "title": title,
                                        "content": text_content[:5000],  # Limit content length
                                        "query": query
                                    })
                                    
                                    page2.close()
                                except Exception as e:
                                    logger.warning(f"Error scraping {url}: {e}")
                                    continue
                    except Exception as e:
                        logger.warning(f"Error processing search result: {e}")
                        continue
                
                page.close()
                time.sleep(2)  # Rate limiting between queries
                
            except Exception as e:
                logger.error(f"Error scraping query '{query}': {e}")
                continue
        
        return scraped_content
    
    def _scrape_with_requests(self, queries: List[str]) -> List[Dict]:
        """Fallback scraping using requests (simpler, less effective)"""
        scraped_content = []
        
        for query in queries:
            try:
                # Use DuckDuckGo HTML search (no API key needed)
                search_url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                response = requests.get(search_url, headers=headers, timeout=10)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                results = soup.find_all('div', class_='result')
                
                for result in results[:5]:
                    try:
                        link_elem = result.find('a', class_='result__a')
                        title_elem = result.find('a', class_='result__a')
                        
                        if link_elem:
                            url = link_elem.get('href', '')
                            title = link_elem.get_text()
                            
                            scraped_content.append({
                                "source_type": self._classify_source(url),
                                "url": url,
                                "title": title,
                                "content": result.find('a', class_='result__snippet').get_text() if result.find('a', class_='result__snippet') else "",
                                "query": query
                            })
                    except Exception as e:
                        continue
                
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error in requests scraping: {e}")
                continue
        
        return scraped_content
    
    def _classify_source(self, url: str) -> str:
        """Classify source type from URL"""
        url_lower = url.lower()
        
        if any(domain in url_lower for domain in ['sfchronicle', 'sfexaminer', 'sfist', 'eater', 'sfgate']):
            return "news"
        elif 'reddit.com' in url_lower:
            return "reddit"
        elif any(domain in url_lower for domain in ['yelp', 'google.com/maps', 'tripadvisor']):
            return "reviews"
        elif any(domain in url_lower for domain in ['twitter.com', 'x.com']):
            return "social"
        elif any(domain in url_lower for domain in ['.edu', '.gov', 'report', 'study']):
            return "reports"
        else:
            return "other"
    
    def _extract_text(self, soup: BeautifulSoup) -> str:
        """Extract main text content from HTML"""
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def _extract_problems(self, scraped_content: List[Dict], risk_input: Dict) -> List[Dict]:
        """Extract specific problems from scraped content using Nemotron"""
        
        profile = risk_input.get("profile", {})
        
        # Prepare content summary
        content_summary = "\n\n".join([
            f"Source: {item['title']}\nURL: {item['url']}\nContent: {item['content'][:1000]}"
            for item in scraped_content[:20]  # Limit to top 20 sources
        ])
        
        prompt = f"""Analyze the following scraped content about San Francisco business closures and extract specific problems that businesses face. Focus on problems that can be addressed with help from San Francisco city departments.

Business Profile:
- Industry: {profile.get('industry', 'unknown')}
- Location: {profile.get('location', 'San Francisco')}
- Risk Factors: {', '.join(profile.get('risk_factors', []))}

Scraped Content:
{content_summary}

Extract specific problems that:
1. Are mentioned in the content
2. Can be fixed with help from SF city departments (homelessness, noise pollution, parking, permits, code enforcement, public safety, etc.)
3. Are relevant to the business profile

For each problem, identify:
- The specific problem description
- Severity (high/medium/low)
- Which SF city department can help
- Relevant SF municipal codes if mentioned

Format as JSON array with this structure:
[
  {{
    "problem": "Specific problem description",
    "severity": "high|medium|low",
    "description": "Detailed description from sources",
    "sources": ["URL1", "URL2"],
    "city_fixable": true,
    "city_department": "Department name",
    "city_code": "SF Municipal Code reference if available"
  }}
]"""

        system_prompt = """You are an expert at analyzing business problems and identifying city-fixable issues. Extract specific, actionable problems that San Francisco city departments can address."""

        response = self.client.generate_structured(
            prompt,
            system_prompt=system_prompt,
            format_instructions="JSON array of problem objects",
            temperature=0.3
        )
        
        try:
            # Try to parse JSON (may need cleaning)
            problems = json.loads(response)
            if not isinstance(problems, list):
                problems = [problems]
            return problems
        except json.JSONDecodeError:
            # Fallback: try to extract JSON from response
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            
            logger.warning("Could not parse problems as JSON, returning empty list")
            return []
    
    def _generate_solutions(self, problems: List[Dict], risk_input: Dict) -> List[Dict]:
        """Generate actionable solutions for each problem using Nemotron"""
        
        solutions = []
        
        for problem in problems:
            if not problem.get("city_fixable", False):
                continue
            
            prompt = f"""Generate actionable solutions for this business problem in San Francisco:

Problem: {problem.get('problem', '')}
Description: {problem.get('description', '')}
City Department: {problem.get('city_department', '')}
City Code: {problem.get('city_code', 'N/A')}

Business Profile:
- Industry: {risk_input.get('profile', {}).get('industry', '')}
- Location: {risk_input.get('profile', {}).get('location', 'San Francisco')}

Generate specific, actionable solutions that include:
1. What action the business owner should take
2. Step-by-step instructions
3. How to contact the relevant SF city department
4. Expected timeline for resolution
5. Any relevant SF municipal codes or regulations

Format as JSON:
{{
  "problem": "Problem description",
  "severity": "high|medium|low",
  "description": "Detailed description",
  "sources": ["URL1"],
  "city_fixable": true,
  "city_department": "Department name",
  "city_code": "SF Municipal Code reference",
  "solutions": [
    {{
      "action": "Specific action to take",
      "steps": ["Step 1", "Step 2", "Step 3"],
      "contact": "How to contact (phone, website, etc.)",
      "expected_timeline": "Expected resolution time",
      "city_resource": "Specific city resource or program"
    }}
  ]
}}"""

            system_prompt = """You are an expert advisor on San Francisco city services and business support. Provide specific, actionable solutions with exact contact information and steps."""

            response = self.client.generate_structured(
                prompt,
                system_prompt=system_prompt,
                format_instructions="JSON object with solutions array",
                temperature=0.4
            )
            
            try:
                solution_data = json.loads(response)
                # Merge with original problem data
                problem.update(solution_data)
                solutions.append(problem)
            except json.JSONDecodeError:
                # Fallback: add basic solution structure
                problem["solutions"] = [{
                    "action": "Contact SF 311 for assistance",
                    "steps": ["Call 311 or visit sf311.org", "Describe the problem", "Follow up if needed"],
                    "contact": "311 or sf311.org",
                    "expected_timeline": "48-72 hours",
                    "city_resource": "SF 311"
                }]
                solutions.append(problem)
        
        return solutions
    
    def _generate_summary(self, solutions: List[Dict], risk_input: Dict) -> str:
        """Generate executive summary using Nemotron"""
        
        if not solutions:
            return "No city-fixable problems identified from external sources. Consider general business best practices and compliance."
        
        problems_summary = "\n".join([
            f"- {p.get('problem', 'Unknown')} ({p.get('severity', 'unknown')} severity)"
            for p in solutions
        ])
        
        prompt = f"""Generate a concise executive summary (2-3 paragraphs) for a business owner facing these problems:

Risk Profile: {risk_input.get('risk_message', '')}

Identified Problems:
{problems_summary}

The summary should:
1. Acknowledge the business risk
2. Highlight the most critical problems
3. Emphasize that these problems can be addressed with city help
4. Provide hope and actionable next steps"""

        system_prompt = """You are a business advisor providing clear, encouraging guidance to small business owners in San Francisco."""

        summary = self.client.generate(prompt, system_prompt=system_prompt, temperature=0.7, max_tokens=500)
        
        return summary

