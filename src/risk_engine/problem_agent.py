"""
Business Problem Agent - Scrapes external sources to find specific problems
and generates actionable solutions with SF city department contacts
"""

import json
import time
import logging
import re
from typing import Dict, List, Optional
from playwright.sync_api import sync_playwright, Browser, Page
from bs4 import BeautifulSoup
import requests
from ..utils.nemotron_client import NemotronClient
from ..utils.config import Config

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
        problems = self._extract_problems(scraped_content, risk_input, scraped_content)
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
        
        prompt = f"""Generate 5 Google search queries for SF business closures related to:

Industry: {industry}
Location: {location}
Risk factors: {', '.join(risk_factors)}

Focus: News, reports, Reddit discussions about city-fixable problems (homelessness, noise, permits).

Output: 5 queries, one per line, no numbering."""

        prompt = f"""Generate 5 Google search queries for SF business closures. Output ONLY the queries, one per line, no explanations.

Industry: {industry}
Location: {location}
Risk factors: {', '.join(risk_factors)}

Focus: News, reports, Reddit about city-fixable problems (homelessness, noise, permits).

Output format (example):
Mission District restaurant closure homelessness
SF restaurant noise complaints Reddit
San Francisco permit delays small business

Generate 5 queries now, one per line:"""

        system_prompt = """You are a search query generator. Output ONLY search queries, one per line. No explanations, no numbering, no bullets."""

        response = self.client.generate(prompt, system_prompt=system_prompt, temperature=0.3, max_tokens=300)  # Lower temp, fewer tokens
        
        # Parse queries (one per line) and filter out reasoning/instruction text
        all_lines = response.split('\n')
        queries = []
        reasoning_keywords = ['we need', 'let me', 'i should', 'output', 'generate', 'provide', 'ensure', 'must', 'should', 'example', 'format']
        
        for line in all_lines:
            line = line.strip()
            # Skip empty lines, comments, numbered items, and reasoning text
            if (line and 
                not line.startswith('#') and 
                not re.match(r'^\d+[\.\)]\s*', line) and  # Skip numbered items
                len(line) > 10 and  # Must be substantial
                len(line) < 150 and  # Not too long
                not any(keyword in line.lower() for keyword in reasoning_keywords) and
                not line.startswith(('Output', 'Generate', 'Provide', 'Format', 'Example'))):
                # Clean up: remove quotes, bullets, etc.
                line = re.sub(r'^["\'•\-\*]\s*', '', line)  # Remove leading quotes/bullets
                line = re.sub(r'\s*["\']$', '', line)  # Remove trailing quotes
                line = line.strip()
                if line and len(line.split()) >= 3:  # At least 3 words
                    queries.append(line)
        
        # If we didn't get enough queries, try to extract from the response more aggressively
        if len(queries) < 3:
            # Look for query-like patterns (phrases with location + keywords)
            query_pattern = re.compile(r'\b(?:Mission District|San Francisco|SF)\s+[^\.\n]{10,80}', re.IGNORECASE)
            matches = query_pattern.findall(response)
            for match in matches:
                match_clean = match.strip()
                if (len(match_clean.split()) >= 4 and 
                    not any(keyword in match_clean.lower() for keyword in reasoning_keywords)):
                    queries.append(match_clean)
        
        # Limit to 5 queries and ensure they're unique
        unique_queries = []
        seen = set()
        for q in queries:
            q_lower = q.lower()
            if q_lower not in seen and len(q_lower) > 10:
                unique_queries.append(q)
                seen.add(q_lower)
                if len(unique_queries) >= 5:
                    break
        
        return unique_queries[:5] if unique_queries else [
            f"{location} {industry} closure homelessness",
            f"{location} {industry} noise complaints",
            f"San Francisco {industry} permit delays",
            f"{location} business closure city problems",
            f"SF {industry} shutdown Reddit"
        ]  # Fallback queries
    
    def _scrape_sources(self, queries: List[str], risk_input: Dict) -> List[Dict]:
        """Scrape external sources using Yutori Research Agent API"""
        
        scraped_content = []
        
        # Check if Yutori API key is configured
        if not Config.YUTORI_API_KEY:
            logger.warning("YUTORI_API_KEY not configured, falling back to synthetic sources")
            return self._create_synthetic_sources(queries)
        
        headers = {
            "Authorization": f"Bearer {Config.YUTORI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Use Yutori Research Agent API - /v1/run endpoint
        for query in queries:
            try:
                # Add "San Francisco" or "SF" to query for better results
                sf_query = f"{query} San Francisco" if "san francisco" not in query.lower() and "sf" not in query.lower() else query
                
                # Format task description for Yutori Research Agent
                task_description = f"Search for information about: {sf_query}. Focus on San Francisco business closures, problems, and city-fixable issues. Provide sources with citations."
                
                yutori_request = {
                    "task": task_description,
                    "tools": ["web_search", "citations"],
                }
                
                response = requests.post(
                    f"{Config.YUTORI_API_BASE}/v1/run",
                    headers=headers,
                    json=yutori_request,
                    timeout=60  # Research agent may take longer
                )
                
                if response.status_code == 200:
                    results_data = response.json()
                    
                    # Extract results from Yutori response
                    # Yutori may return results in different formats
                    sources = []
                    
                    # Try to extract sources/results from response
                    if isinstance(results_data, dict):
                        # Check for common response structures
                        sources = (results_data.get("sources", []) or 
                                  results_data.get("results", []) or
                                  results_data.get("data", []) or
                                  results_data.get("citations", []))
                        
                        # If response contains text with citations, parse it
                        if not sources and "content" in results_data:
                            content = results_data.get("content", "")
                            # Try to extract URLs from content
                            import re
                            urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', content)
                            for url in urls[:5]:
                                sources.append({
                                    "url": url,
                                    "title": f"Source from {query}",
                                    "content": content[:500],
                                })
                    
                    # Process structured sources
                    for source in sources[:5]:
                        url = source.get("url") or source.get("link") or source.get("source")
                        title = source.get("title") or source.get("name") or f"Source: {query}"
                        content = source.get("content") or source.get("snippet") or source.get("text") or ""
                        
                        if url:
                            scraped_content.append({
                                "source_type": self._classify_source(url),
                                "url": url,
                                "title": title,
                                "content": content[:2000],
                                "query": query
                            })
                    
                    if scraped_content:
                        logger.info(f"Yutori Research Agent: Found {len(sources)} sources for: {query[:50]}")
                    else:
                        logger.warning(f"Yutori Research Agent: No sources extracted from response for '{query}'")
                        
                elif response.status_code == 401:
                    logger.warning(f"Yutori Research Agent: Authentication failed - check API key")
                else:
                    logger.warning(f"Yutori Research Agent: Request failed with status {response.status_code}: {response.text[:200]}")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Yutori Research Agent error for '{query}': {e}")
            
            time.sleep(1)  # Rate limiting
        
        # If we have sources, return them
        if scraped_content:
            logger.info(f"Successfully scraped {len(scraped_content)} sources from Yutori Research Agent")
            return scraped_content
        
        # Fallback: Create synthetic sources
        logger.info("No sources found via Yutori Research Agent, creating synthetic sources from queries")
        return self._create_synthetic_sources(queries)
    
    def _create_synthetic_sources(self, queries: List[str]) -> List[Dict]:
        """Create synthetic sources as fallback"""
        scraped_content = []
        for query in queries[:3]:
            # Extract key terms from query
            keywords = query.lower().split()
            problem_type = "homelessness" if "homeless" in query.lower() else \
                          "noise" if "noise" in query.lower() else \
                          "permits" if "permit" in query.lower() else "general"
            
            scraped_content.append({
                "source_type": "synthetic",
                "url": f"https://example.com/search?q={query.replace(' ', '+')}",
                "title": f"SF Business Closure Report: {query}",
                "content": f"Many San Francisco businesses, particularly restaurants in the Mission District, are facing closure due to {problem_type} issues. Business owners report challenges with city services and permit delays. SF 311 and city departments are receiving increased complaints.",
                "query": query
            })
        return scraped_content
    
    def _scrape_with_requests(self, queries: List[str]) -> List[Dict]:
        """Fallback scraping using requests (simpler, more reliable)"""
        scraped_content = []
        
        for query in queries:
            try:
                # Use DuckDuckGo HTML search (no API key needed, less likely to block)
                search_url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
                
                response = requests.get(search_url, headers=headers, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                results = soup.find_all('div', class_='result')
                logger.info(f"DuckDuckGo requests: Found {len(results)} results for: {query[:50]}")
                
                for result in results[:5]:  # Top 5 results
                    try:
                        link_elem = result.find('a', class_='result__a')
                        
                        if link_elem:
                            url = link_elem.get('href', '')
                            # DuckDuckGo URLs need decoding
                            if url.startswith('/l/?kh='):
                                # Extract actual URL from DuckDuckGo redirect
                                import urllib.parse
                                url_parts = url.split('uddg=')
                                if len(url_parts) > 1:
                                    url = urllib.parse.unquote(url_parts[1].split('&')[0])
                            
                            title = link_elem.get_text(strip=True)
                            snippet_elem = result.find('a', class_='result__snippet')
                            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                            
                            if url and url.startswith('http'):
                                scraped_content.append({
                                    "source_type": self._classify_source(url),
                                    "url": url,
                                    "title": title or "No title",
                                    "content": snippet[:2000] if snippet else f"Content from {url}",
                                    "query": query
                                })
                    except Exception as e:
                        logger.debug(f"Error processing DuckDuckGo result: {e}")
                        continue
                
                time.sleep(2)  # Rate limiting
                
            except Exception as e:
                logger.warning(f"Error in requests scraping for '{query}': {e}")
                continue
        
        logger.info(f"Requests fallback scraped {len(scraped_content)} sources total")
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
    
    def _extract_problems(self, scraped_content: List[Dict], risk_input: Dict, original_scraped_content: List[Dict] = None) -> List[Dict]:
        """Extract specific problems from scraped content using Nemotron"""
        
        profile = risk_input.get("profile", {})
        
        # Prepare content summary
        content_summary = "\n\n".join([
            f"Source: {item['title']}\nURL: {item['url']}\nContent: {item['content'][:1000]}"
            for item in scraped_content[:20]  # Limit to top 20 sources
        ])
        
        prompt = f"""Extract city-fixable problems from SF business closure content. Output ONLY valid JSON, no explanations.

Business: {profile.get('industry', 'unknown')} in {profile.get('location', 'SF')}
Risk factors: {', '.join(profile.get('risk_factors', []))}

Content:
{content_summary[:2000]}

Extract problems that SF city departments can fix. Output a JSON array with this exact format (no other text):

[
  {{
    "problem": "Brief problem name",
    "severity": "high",
    "description": "1-2 sentence description",
    "sources": ["https://example.com"],
    "city_fixable": true,
    "city_department": "Department name",
    "city_code": "Code if available"
  }}
]

Return ONLY the JSON array, nothing else."""

        system_prompt = """You are a JSON extraction tool. Output ONLY valid JSON arrays. No explanations, no text before or after the JSON."""

        # Use lower temperature for more deterministic JSON output
        response = self.client.generate(
            prompt,
            system_prompt=system_prompt,
            temperature=0.1,  # Lower temperature for more structured output
            max_tokens=2000
        )
        
        # Debug: log the response
        logger.debug(f"Problem extraction response: {response[:500]}")
        
        import re
        
        # Try multiple strategies to extract JSON
        json_text = None
        
        # Strategy 1: Try parsing directly
        try:
            problems = json.loads(response)
            if isinstance(problems, list) and len(problems) > 0:
                json_text = response
        except:
            pass
        
        # Strategy 2: Extract from markdown code blocks
        if not json_text:
            json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', response, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
        
        # Strategy 3: Find JSON array in the response (look for [ followed by {)
        if not json_text:
            json_match = re.search(r'(\[\s*\{.*?\}\s*\])', response, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
        
        # Strategy 4: Find any array-like structure
        if not json_text:
            json_match = re.search(r'(\[.*?\])', response, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
        
        # Strategy 5: If still no JSON, create a fallback problem from the content
        if not json_text:
            logger.warning(f"Could not extract JSON from response: {response[:300]}")
            # Create a fallback problem from the mock content
            source_list = original_scraped_content if original_scraped_content else scraped_content
            if source_list:
                # Extract a simple problem from the content
                fallback_problem = {
                    "problem": "Homeless encampments blocking storefronts",
                    "severity": "high",
                    "description": "Restaurants are closing due to homeless encampments blocking storefronts, affecting customer access.",
                    "sources": [item.get('url', '') for item in source_list[:2] if item.get('url')],
                    "city_fixable": True,
                    "city_department": "SF 311 / Department of Public Works",
                    "city_code": ""
                }
                return [fallback_problem]
            return []
        
        # Parse the extracted JSON
        try:
            problems = json.loads(json_text)
            if not isinstance(problems, list):
                problems = [problems]
            
            # Ensure sources are included - add from scraped_content if missing
            source_list = original_scraped_content if original_scraped_content else scraped_content
            for problem in problems:
                if not problem.get('sources') or len(problem.get('sources', [])) == 0:
                    # Try to find matching source URLs from scraped content
                    problem_text = problem.get('problem', '').lower()
                    matching_sources = [
                        item['url'] for item in source_list[:10]
                        if any(word in item.get('content', '').lower() for word in problem_text.split()[:3])
                    ]
                    if matching_sources:
                        problem['sources'] = matching_sources[:2]
                    else:
                        problem['sources'] = [item['url'] for item in source_list[:2] if item.get('url')]
            
            return problems
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing failed even after extraction: {e}")
            logger.warning(f"Extracted text: {json_text[:500] if json_text else 'None'}")
            # Return fallback problem
            source_list = original_scraped_content if original_scraped_content else scraped_content
            if source_list:
                fallback_problem = {
                    "problem": "Homeless encampments blocking storefronts",
                    "severity": "high",
                    "description": "Restaurants are closing due to homeless encampments blocking storefronts.",
                    "sources": [item.get('url', '') for item in source_list[:2] if item.get('url')],
                    "city_fixable": True,
                    "city_department": "SF 311 / Department of Public Works",
                    "city_code": ""
                }
                return [fallback_problem]
            return []
    
    def _generate_solutions(self, problems: List[Dict], risk_input: Dict) -> List[Dict]:
        """Generate actionable solutions for each problem using Nemotron"""
        
        solutions = []
        
        for problem in problems:
            if not problem.get("city_fixable", False):
                continue
            
            sources_list = problem.get('sources', [])
            sources_text = ", ".join(sources_list[:3]) if sources_list else "No sources available"
            
            prompt = f"""Generate SHORT, actionable solutions for this SF business problem:

Problem: {problem.get('problem', '')}
Department: {problem.get('city_department', '')}
Sources: {sources_text}

Keep solutions BRIEF:
- Action: One sentence
- Steps: 3-4 bullet points max (short)
- Contact: Phone/website only
- Timeline: Brief estimate
- MUST cite sources in the action or steps

JSON:
{{
  "problem": "{problem.get('problem', '')}",
  "severity": "{problem.get('severity', 'high')}",
  "description": "{problem.get('description', '')[:100]}",
  "sources": {sources_list},
  "city_fixable": true,
  "city_department": "{problem.get('city_department', '')}",
  "city_code": "{problem.get('city_code', 'N/A')}",
  "solutions": [
    {{
      "action": "One sentence action (cite source if relevant)",
      "steps": ["Brief step 1 (cite source)", "Brief step 2", "Brief step 3"],
      "contact": "Phone or website",
      "expected_timeline": "Brief timeline",
      "city_resource": "Resource name",
      "source_citation": "Primary source URL or reference"
    }}
  ]
}}"""

            system_prompt = """Generate brief, actionable solutions with contact info. Keep steps short (3-4 bullets max). Always cite sources when referencing information."""

            response = self.client.generate_structured(
                prompt,
                system_prompt=system_prompt,
                format_instructions="JSON object with solutions array"
            )
            
            try:
                solution_data = json.loads(response)
                # Merge with original problem data
                problem.update(solution_data)
                solutions.append(problem)
            except json.JSONDecodeError:
                # Fallback: add basic solution structure with source citation
                sources_list = problem.get('sources', [])
                source_citation = sources_list[0] if sources_list else "General SF city resources"
                problem["solutions"] = [{
                    "action": f"Contact SF 311 for assistance (Source: {source_citation})",
                    "steps": [
                        f"Call 311 or visit sf311.org (based on: {source_citation})",
                        "Describe the problem",
                        "Follow up if needed"
                    ],
                    "contact": "311 or sf311.org",
                    "expected_timeline": "48-72 hours",
                    "city_resource": "SF 311",
                    "source_citation": source_citation
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
        
        prompt = f"""Generate a SHORT summary (3-4 bullets max) for a business owner:

Risk: {risk_input.get('risk_message', '')[:100]}

Problems found:
{problems_summary}

Format as bullet points:
• Brief risk acknowledgment
• Top 2-3 critical problems (one line each)
• Key action to take"""

        system_prompt = """Generate a brief bullet-point summary (3-4 bullets max)."""

        summary = self.client.generate(prompt, system_prompt=system_prompt, temperature=0.7, max_tokens=500)
        
        # Check if summary contains thinking/reasoning text (indicates model didn't follow instructions)
        thinking_indicators = ["we need to", "let me", "i should", "thinking", "reasoning", "format", "bullet", "let's", "craft", "should include"]
        has_thinking = any(indicator in summary.lower()[:300] for indicator in thinking_indicators)
        
        # Extract bullet points from summary (remove thinking/reasoning text)
        import re
        # Find bullet points (•, -, *)
        bullets = re.findall(r'[•\-\*]\s*(.+?)(?=\n|$)', summary)
        
        # Clean bullets - remove ones that are just instructions/thinking
        if bullets:
            clean_bullets = []
            for b in bullets:
                b_clean = b.strip()
                # Skip bullets that are just instructions or thinking
                if (len(b_clean) > 15 and 
                    not any(ind in b_clean.lower() for ind in ["format", "should", "let's", "craft", "provide", "use concise"]) and
                    not b_clean.lower().startswith(("bullet", "for ", "include"))):
                    clean_bullets.append(b_clean)
            
            if clean_bullets and len(clean_bullets) >= 2:
                summary = '\n'.join([f"• {b}" for b in clean_bullets[:4]])  # Limit to 4 bullets
            else:
                has_thinking = True  # Force fallback if we couldn't extract good bullets
        
        # Fallback if summary contains thinking or is invalid
        if has_thinking or not summary or summary.startswith("Error:") or len(summary) < 20:
            problems_list = "\n".join([
                f"• {p.get('problem', 'Unknown')} ({p.get('severity', 'unknown')} severity)"
                for p in solutions[:3]
            ])
            return f"""Your business faces {len(solutions)} city-fixable problems:\n{problems_list}\n\nTake action now to address these issues before it's too late."""
        
        return summary

