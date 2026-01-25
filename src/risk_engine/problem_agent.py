"""
Business Problem Agent - Uses Gemini with web search to find specific problems
and generates actionable solutions with SF city department contacts
"""

import json
import time
import logging
import re
from typing import Dict, List, Optional
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
        self.gemini_client = None
        self._init_gemini()
        
    def _init_gemini(self):
        """Initialize Gemini client for web search"""
        try:
            if Config.GEMINI_API_KEY:
                from google import genai
                self.gemini_client = genai.Client(api_key=Config.GEMINI_API_KEY)
                logger.info("Gemini client initialized for web search")
            else:
                logger.warning("GEMINI_API_KEY not configured, web search will use fallback")
        except Exception as e:
            logger.warning(f"Failed to initialize Gemini: {e}")
            self.gemini_client = None
        
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        pass
    
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
        # Extended list of reasoning keywords to filter out
        reasoning_keywords = ['we need', 'let me', 'i should', 'output', 'generate', 'provide', 'ensure', 
                             'must', 'should', 'example', 'format', 'let\'s', 'craft', 'make sure', 
                             'here are', 'here is', 'following', 'note:', 'query', 'search for', 'single line']
        
        for line in all_lines:
            line = line.strip()
            # Skip empty lines, comments, numbered items, and reasoning text
            if (line and 
                not line.startswith('#') and 
                not re.match(r'^\d+[\.\)]\s*', line) and  # Skip numbered items
                len(line) > 15 and  # Must be substantial (increased from 10)
                len(line) < 100 and  # Not too long (reduced from 150)
                not any(keyword in line.lower() for keyword in reasoning_keywords) and
                not line.startswith(('Output', 'Generate', 'Provide', 'Format', 'Example', 'Let', 'Make', 'Here')) and
                ':' not in line):  # Skip lines with colons (likely instructions)
                # Clean up: remove quotes, bullets, etc.
                line = re.sub(r'^["\'•\-\*]\s*', '', line)  # Remove leading quotes/bullets
                line = re.sub(r'\s*["\']$', '', line)  # Remove trailing quotes
                line = line.strip()
                # Must have at least 3 words and contain location-related terms
                words = line.split()
                if (len(words) >= 3 and 
                    any(loc in line.lower() for loc in ['sf', 'san francisco', 'mission', 'soma', 'downtown'])):
                    queries.append(line)
        
        # If we didn't get enough queries, try to extract from the response more aggressively
        if len(queries) < 3:
            # Look for query-like patterns (phrases with location + keywords)
            query_pattern = re.compile(r'\b(?:Mission District|San Francisco|SF)\s+[^\.\n:]{10,80}', re.IGNORECASE)
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
            if q_lower not in seen and len(q_lower) > 15:
                unique_queries.append(q)
                seen.add(q_lower)
                if len(unique_queries) >= 5:
                    break
        
        # Use fallback queries if we couldn't extract good ones
        if len(unique_queries) < 3:
            return [
                f"{location} {industry} closure homelessness",
                f"{location} {industry} noise complaints",
                f"San Francisco {industry} permit delays",
                f"{location} business closure city problems",
                f"SF {industry} shutdown Reddit"
            ]
        
        return unique_queries[:5]
    
    def _scrape_sources(self, queries: List[str], risk_input: Dict) -> List[Dict]:
        """Use Gemini with web search (grounding) to find relevant sources"""
        
        scraped_content = []
        
        # Check if Gemini is available
        if not self.gemini_client:
            logger.warning("Gemini not initialized, falling back to synthetic sources")
            return self._create_synthetic_sources(queries)
        
        profile = risk_input.get("profile", {})
        industry = profile.get("industry", "business")
        location = profile.get("location", "San Francisco")
        
        try:
            from google.genai import types
            
            # Combine queries into a single research prompt
            queries_text = "\n".join([f"- {q}" for q in queries])
            
            research_prompt = f"""You are a research assistant. Search the web for recent news and information about San Francisco business problems.

I need to find real articles, news stories, and reports about these topics:
{queries_text}

Focus on:
1. Recent news about {industry} businesses in {location} facing problems
2. City-related issues (homelessness, permits, noise, violations)
3. Business closures and their causes
4. Reddit discussions or community reports

For each relevant source you find, provide:
- The article/source title
- The URL
- A brief summary of the content
- The type of source (news, reddit, report, etc.)

Format your response as a JSON array:
[
  {{
    "title": "Article title",
    "url": "https://...",
    "summary": "Brief summary of content",
    "source_type": "news"
  }}
]

Find at least 5-10 relevant sources. Return ONLY the JSON array."""

            print("   🔍 Gemini: Searching web for relevant sources...")
            
            # Use Gemini with Google Search grounding
            response = self.gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=research_prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    temperature=0.3,
                    max_output_tokens=4000
                )
            )
            
            response_text = response.text
            print(f"   📄 Gemini response received ({len(response_text)} chars)")
            
            # Parse the JSON response
            # Try to extract JSON from the response
            json_match = re.search(r'\[[\s\S]*\]', response_text)
            if json_match:
                json_text = json_match.group(0)
                try:
                    # Clean the JSON text - remove control characters that can break parsing
                    # Keep only printable ASCII and common whitespace
                    cleaned_json = ''.join(
                        char for char in json_text 
                        if char in '\n\r\t' or (ord(char) >= 32 and ord(char) < 127) or ord(char) > 127
                    )
                    # Also replace problematic escape sequences
                    cleaned_json = cleaned_json.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                    # Fix double-escaped sequences
                    cleaned_json = re.sub(r'\\\\([nrt])', r'\\\1', cleaned_json)
                    
                    sources = json.loads(cleaned_json)
                    
                    for source in sources:
                        url = source.get("url", "")
                        title = source.get("title", "")
                        summary = source.get("summary", "")
                        source_type = source.get("source_type", "other")
                        
                        if url and title:
                            scraped_content.append({
                                "source_type": source_type,
                                "url": url,
                                "title": title,
                                "content": summary[:2000],
                                "query": queries[0] if queries else ""
                            })
                            print(f"      ✓ Added: {title[:50]}...")
                    
                except json.JSONDecodeError as e:
                    # Silent warning - grounding metadata fallback will handle this
                    logger.debug(f"JSON parse fallback to grounding metadata: {e}")
            
            # Also extract grounding metadata if available
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                    grounding = candidate.grounding_metadata
                    if hasattr(grounding, 'grounding_chunks'):
                        for chunk in grounding.grounding_chunks:
                            if hasattr(chunk, 'web') and chunk.web:
                                web = chunk.web
                                url = getattr(web, 'uri', '') or getattr(web, 'url', '')
                                title = getattr(web, 'title', '') or 'Web Source'
                                
                                # Avoid duplicates
                                existing_urls = [s['url'] for s in scraped_content]
                                if url and url not in existing_urls:
                                    scraped_content.append({
                                        "source_type": self._classify_source(url),
                                        "url": url,
                                        "title": title,
                                        "content": f"Source from Gemini web search for {industry} in {location}",
                                        "query": queries[0] if queries else ""
                                    })
                                    print(f"      ✓ Grounding source: {title[:50]}...")
            
        except Exception as e:
            print(f"   ❌ Gemini error: {e}")
            logger.error(f"Gemini web search error: {e}")
        
        # If we have sources, return them
        if scraped_content:
            print(f"   ✅ Gemini: Successfully found {len(scraped_content)} sources")
            logger.info(f"Gemini: Successfully found {len(scraped_content)} sources")
            return scraped_content
        
        # No fallback - return empty list if Gemini fails
        # (Commented out synthetic fallback)
        print("   ⚠️ Gemini found no sources. No fallback will be used.")
        logger.warning("No sources found from Gemini, returning empty list")
        return []
        
        # # Final fallback: Create synthetic sources (DISABLED)
        # print("   ⚠️ Gemini found no sources, using synthetic fallback...")
        # logger.info("No sources found, creating synthetic sources from queries")
        # return self._create_synthetic_sources(queries)
    
    def _create_synthetic_sources(self, queries: List[str]) -> List[Dict]:
        """Create synthetic sources as fallback (DISABLED - kept for reference)"""
        # This method is no longer called but kept for reference
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
                import urllib.parse
                encoded_query = urllib.parse.quote_plus(query)
                search_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Referer': 'https://duckduckgo.com/',
                }
                
                response = requests.get(search_url, headers=headers, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Try multiple selectors for DuckDuckGo results
                results = soup.find_all('div', class_='result') or soup.find_all('div', class_='results_links')
                print(f"      Requests fallback: Found {len(results)} results for '{query[:40]}...'")
                
                for result in results[:5]:  # Top 5 results
                    try:
                        # Try multiple ways to find the link
                        link_elem = result.find('a', class_='result__a') or result.find('a', href=True)
                        
                        if link_elem:
                            url = link_elem.get('href', '')
                            
                            # DuckDuckGo URLs need decoding
                            if url and ('duckduckgo.com/l/' in url or url.startswith('/l/')):
                                # Extract actual URL from DuckDuckGo redirect
                                if 'uddg=' in url:
                                    url_parts = url.split('uddg=')
                                    if len(url_parts) > 1:
                                        url = urllib.parse.unquote(url_parts[1].split('&')[0])
                            
                            title = link_elem.get_text(strip=True)
                            snippet_elem = result.find('a', class_='result__snippet') or result.find('span')
                            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                            
                            if url and url.startswith('http') and title and len(title) > 5:
                                scraped_content.append({
                                    "source_type": self._classify_source(url),
                                    "url": url,
                                    "title": title or "No title",
                                    "content": snippet[:2000] if snippet else f"Content from {url}",
                                    "query": query
                                })
                                print(f"      ✓ Requests: Added {title[:40]}...")
                    except Exception as e:
                        logger.debug(f"Error processing DuckDuckGo result: {e}")
                        continue
                
                time.sleep(2)  # Rate limiting
                
            except Exception as e:
                print(f"      ❌ Requests error: {e}")
                logger.warning(f"Error in requests scraping for '{query}': {e}")
                continue
        
        print(f"      Requests fallback scraped {len(scraped_content)} sources total")
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
            # Silent debug log - fallback will handle this
            logger.debug(f"No JSON found in response, using content-based fallback")
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

