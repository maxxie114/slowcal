# How to Run the Business Problem Agent

## Prerequisites

1. **Set your Nemotron API key** (required):
   ```bash
   export NEMOTRON_API_KEY=your_actual_api_key_here
   ```
   
   Or create a `.env` file in the project root:
   ```bash
   echo "NEMOTRON_API_KEY=your_actual_api_key_here" > .env
   ```

2. **Install dependencies** (if not already installed):
   ```bash
   pip install -r requirements.txt
   ```

## Option 1: Quick Simulated Test (Recommended - Fastest)

This uses mocked web scraping, so it's fast and doesn't require Playwright:

```bash
python3 test_agent_simulated.py
```

**What it does:**
- Uses mock scraped content (no actual web scraping)
- Makes real API calls to Nemotron
- Tests the full agent workflow
- Takes ~30 seconds to 2 minutes

## Option 2: Full Example (Requires Playwright)

This does real web scraping:

```bash
# First install Playwright browsers
playwright install chromium

# Then run the example
python3 examples/agent_workflow_example.py
```

**What it does:**
- Actually scrapes the web for business problems
- Makes real API calls to Nemotron
- Takes 5-10 minutes (depends on scraping speed)

## Option 3: Use in Python Code

```python
import os
os.environ['NEMOTRON_API_KEY'] = 'your_api_key_here'

from src.risk_engine.problem_agent import BusinessProblemAgent

risk_input = {
    "risk_score": 0.73,
    "risk_message": "Your risk message here",
    "profile": {
        "industry": "restaurant",
        "risk_factors": ["high violations", "young age"],
        "business_age_years": 2,
        "total_violations": 5,
        "location": "Mission District"
    }
}

with BusinessProblemAgent() as agent:
    results = agent.analyze_business_risk(risk_input)
    print(results["summary"])
    for problem in results["problems"]:
        print(problem["problem"])
```

## Troubleshooting

**Error: "NEMOTRON_API_KEY environment variable must be set"**
- Make sure you've exported the API key or created a `.env` file
- Check: `echo $NEMOTRON_API_KEY`

**Error: "playwright not found"**
- Install: `pip install playwright && playwright install chromium`
- Or use the simulated test instead

**Error: API connection issues**
- Verify your API key is correct
- Check your internet connection
- Verify the API endpoint is accessible

