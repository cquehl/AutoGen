# 🧲 Magentic-One Multi-Agent System

**Web Research. Data Gathering. Automated Workflows. All Powered by AI.**

Magentic-One is your orchestrator-driven multi-agent system for complex web tasks. Perfect for:
- Morning news briefings from multiple sources
- Competitive research and analysis
- Market intelligence gathering
- Content aggregation
- Automated reporting

## 🚀 Quick Start

```bash
# Launch Magentic-One team
./cli.py --team magentic

# Single-shot web research
./cli.py --team magentic "Research Tesla's latest product announcements"

# With memory (remembers preferences)
./cli.py --team magentic -r "Create my morning briefing"
```

## 🤖 Meet the Agents

### 1. **Orchestrator** - The Brain
- Plans complex tasks
- Breaks them into subtasks
- Coordinates other agents
- Aggregates results

### 2. **WebSurfer** - The Researcher
- Browse any website
- Search Google/DuckDuckGo
- Extract text content
- Gather links
- Download pages

### 3. **FileWriter** - The Documenter
- Save results to files
- Create markdown reports
- Generate CSV data
- Organize output

## 💡 What Can You Do?

### Web Research

```bash
You: Research the top 3 AI agent frameworks in 2024

Orchestrator: Breaking down the task...
1. Search for "best AI agent frameworks 2024"
2. Visit top result pages
3. Extract key information
4. Compile comparison

WebSurfer: Searching Google for "best AI agent frameworks 2024"...
WebSurfer: Found 10 results. Visiting top 3...
WebSurfer: Extracting content from each page...

Orchestrator: Compiling results...

Here's what I found:
1. **AutoGen** - Microsoft's framework for multi-agent systems
   - Link: https://microsoft.github.io/autogen
   - Key features: Multi-agent chat, tool use, human-in-loop

2. **LangGraph** - LangChain's agent framework
   - Link: https://langchain-ai.github.io/langgraph
   - Key features: State machines, cycles, persistence

3. **CrewAI** - Role-based agent teams
   - Link: https://www.crewai.com
   - Key features: Role assignment, task delegation, workflows
```

### Morning Briefing

```bash
You: Create my morning briefing from TechCrunch and Hacker News

Orchestrator: Planning briefing workflow...

WebSurfer: Navigating to TechCrunch...
WebSurfer: Extracting top 5 articles...

WebSurfer: Navigating to Hacker News...
WebSurfer: Extracting top discussions...

FileWriter: Creating briefing file...
FileWriter: Saved to ~/briefings/morning_2024-11-14.md

Done! Your briefing is ready at ~/briefings/morning_2024-11-14.md

Contents:
# Morning Briefing - November 14, 2024

## TechCrunch Top Stories
1. [Article title] - [summary]
2. [Article title] - [summary]
...

## Hacker News Trending
1. [Discussion] - [key points]
2. [Discussion] - [key points]
...
```

### Competitive Intelligence

```bash
You: Research my competitors: CompanyA, CompanyB, CompanyC
Find: latest product launches, pricing changes, news

Orchestrator: Multi-company research plan...
1. Research each company separately
2. Extract recent news
3. Check for pricing updates
4. Compile comparison table

WebSurfer: Researching CompanyA...
WebSurfer: Found 3 recent announcements...

[Process repeats for B and C]

FileWriter: Creating comparison report...
FileWriter: Saved to ./competitor_analysis_2024-11-14.md
```

### Content Aggregation

```bash
You: Find all blog posts about "Magentic-One" from the last month
Extract titles, URLs, and summaries

WebSurfer: Searching for "Magentic-One blog posts"...
WebSurfer: Found 15 results
WebSurfer: Extracting content from each...

FileWriter: Creating CSV with results...
FileWriter: Saved to ./magentic_one_posts.csv

Columns: Title, URL, Published Date, Summary
Rows: 15
```

## 🎯 Your Exact Use Case: Morning Briefing

**Goal**: Daily briefing from WSJ, Facebook Marketplace, Auto Trader

Here's how to set it up:

### Step 1: Configure Sources

```bash
./cli.py --team magentic -r

You: /remember My morning briefing sources:
- Wall Street Journal (subscription required)
- Facebook Marketplace (local car listings)
- Auto Trader (industry news)

You: /remember I want briefings saved to ~/briefings/YYYY-MM-DD.md

You: /remember I'm interested in: electric vehicles, auto industry, market trends
```

### Step 2: Create the Briefing

```bash
You: Create my morning briefing

Orchestrator: Morning briefing workflow:
1. WSJ: Extract top business/tech stories
2. Facebook Marketplace: Check new car listings
3. Auto Trader: Get industry news
4. Compile into ~/briefings/2024-11-14.md

WebSurfer: Note - WSJ requires login. I'll extract from public sections.
WebSurfer: Navigating to wsj.com...
[Extracts available content]

WebSurfer: Checking Facebook Marketplace...
[Note: May need auth - will get what's publicly visible]

WebSurfer: Getting Auto Trader news...
[Extracts industry updates]

FileWriter: Compiling briefing...
FileWriter: Saved to ~/briefings/2024-11-14.md

Your briefing is ready!
```

### Step 3: Review Output

```markdown
# Morning Briefing - November 14, 2024

## Wall Street Journal
- Markets Rally on Fed Comments
- Tech Sector Shows Strong Q4
- ...

## New Listings (Facebook Marketplace)
- 2023 Tesla Model 3 - $35,000 (City)
- 2024 Hyundai Ioniq 5 - $42,000 (Nearby)
- ...

## Auto Industry News (Auto Trader)
- EV Sales Up 45% Year-Over-Year
- New EPA Emissions Standards Announced
- ...

---
Generated: 2024-11-14 07:00 AM
```

## 🔐 Handling Authentication

### For Subscription Sites (WSJ)

**Option 1: Public Content Only**
```bash
# Magentic-One will extract publicly available content
# No login needed, but limited access
```

**Option 2: Cookie-Based Auth** (Advanced)
```bash
# Export cookies from your browser
# Use navigate_to_url with cookies parameter
# (Requires custom tool enhancement)
```

**Option 3: API Integration**
```bash
# Many news sites have APIs
# Add custom tool for API access
# More reliable than scraping
```

### For Social Sites (Facebook)

**Challenges:**
- Facebook heavily protects against scraping
- Requires login for most content
- Frequent changes to structure

**Alternatives:**
- Use public Facebook pages (don't require login)
- Use Facebook Graph API (if available)
- Use RSS feeds if provided
- Check if Marketplace has public listings

## 🛠️ Advanced Usage

### Custom Web Tools

Add your own web tools to WebSurfer:

```python
# In agents/magentic_one/tools/custom_tools.py

async def scrape_specific_site(url: str) -> dict:
    """Custom scraper for a specific site structure"""
    # Your site-specific logic
    pass

# Add to WebSurfer
web_surfer.add_tool(scrape_specific_site, "Scrape XYZ site")
```

### Automated Scheduling

Run briefings automatically:

**Option 1: Cron Job**
```bash
# Add to crontab
0 7 * * * cd /path/to/AutoGen && ./cli.py --team magentic "Create morning briefing" >> /var/log/briefing.log 2>&1
```

**Option 2: Python Script**
```python
# briefing_scheduler.py
import asyncio
import schedule
from agents.magentic_one import create_magentic_team
from config.settings import get_llm_config

async def run_briefing():
    llm_config = get_llm_config()
    team = await create_magentic_team(llm_config)
    await team.run(task="Create my morning briefing")

schedule.every().day.at("07:00").do(lambda: asyncio.run(run_briefing()))

while True:
    schedule.run_pending()
    time.sleep(60)
```

### Workflow Templates

Create reusable workflows:

```python
# workflows/morning_briefing.py

async def morning_briefing_workflow(sources: List[str], output_path: str):
    """
    Automated morning briefing workflow.

    Args:
        sources: List of URLs to check
        output_path: Where to save the briefing
    """
    orchestrator = create_orchestrator(client)

    task = f"""
    Create a morning briefing from these sources:
    {', '.join(sources)}

    Extract:
    - Top 3 stories from each source
    - Key quotes and data points
    - Links to full articles

    Format as markdown and save to {output_path}
    """

    result = await orchestrator.run(task)
    return result
```

## 📊 Integration with Other Teams

### Combine with Data Team

```bash
# Research online + analyze database
You: Research competitor pricing online,
     then compare with our sales data from the database

# Magentic team gathers web data
# Switch to data team for analysis
You: /team data
You: Analyze the competitor data I just gathered
```

### Combine with Memory

```bash
# Day 1: Research
./cli.py --team magentic
You: Research AI frameworks
You: /remember AutoGen is best for multi-agent systems

# Day 2: Build on it
./cli.py --team magentic -r
You: Based on my previous research, find AutoGen tutorials
# Agent remembers your preference for AutoGen
```

## 🎛️ Web Tools Reference

### navigate_to_url(url, use_cache)
```python
# Visit a webpage
result = await navigate_to_url("https://example.com")
# Returns: HTML, status, headers, content
```

### search_google(query, num_results)
```python
# Search the web
results = await search_google("AI agents 2024", num_results=10)
# Returns: List of {title, url, snippet}
```

### extract_text_content(url, max_length)
```python
# Get clean text from page
content = await extract_text_content("https://example.com/article")
# Returns: Cleaned text, title, length
```

### extract_links(url, filter_pattern)
```python
# Get all links from a page
links = await extract_links("https://news.site", filter_pattern="article")
# Returns: List of {url, text, title}
```

### get_page_title(url)
```python
# Quick title check
title = await get_page_title("https://example.com")
# Returns: Page title
```

### download_page(url, output_path)
```python
# Save page for offline viewing
await download_page("https://example.com", "./pages/example.html")
# Returns: Confirmation with file path
```

## 💡 Tips & Best Practices

### 1. **Start Simple**
```bash
# Don't start with complex multi-source briefings
# Test with one site first
./cli.py --team magentic "Get top 3 articles from TechCrunch"
```

### 2. **Use Memory for Preferences**
```bash
# Save your preferences so agents remember
You: /remember I prefer summaries under 100 words
You: /remember I want results as bulleted lists
You: /remember My local area is Cincinnati, OH
```

### 3. **Be Specific**
```bash
# Good: "Find electric vehicle news from Auto Trader, extract titles and URLs"
# Bad: "Get car stuff"
```

### 4. **Handle Failures Gracefully**
```bash
# Sites may be down, blocked, or changed
# Orchestrator will adapt and provide partial results
# Check what was successfully gathered
```

### 5. **Respect Rate Limits**
```bash
# Don't hammer sites with requests
# Use caching (navigate_to_url caches automatically)
# Spread out requests for multiple sources
```

### 6. **Verify Output**
```bash
# Always check generated briefings
# Web scraping can be fragile
# Structure changes may break extraction
```

## 🚨 Limitations & Considerations

### What Magentic-One CAN Do:
- ✅ Browse public websites
- ✅ Search Google/DuckDuckGo
- ✅ Extract visible text content
- ✅ Navigate simple page structures
- ✅ Save results to files

### What It CANNOT (Yet) Do:
- ❌ Bypass login walls easily (needs auth setup)
- ❌ Interact with JavaScript-heavy React apps perfectly
- ❌ Fill complex forms automatically
- ❌ Solve CAPTCHAs
- ❌ Access pages that require browser fingerprints

### For Sites That Require Login:
1. **Use RSS feeds** if available
2. **Use official APIs** instead of scraping
3. **Extract cookies** from browser and pass manually
4. **Use public sections** only
5. **Consider browser automation** (Playwright/Selenium) as enhancement

## 🔮 Future Enhancements

Want to make Magentic-One even better? Here's what's possible:

1. **Browser Automation** - Add Playwright for JavaScript sites
2. **RSS Feed Reader** - Parse RSS/Atom feeds
3. **API Integrations** - Official APIs for news sources
4. **Image Extraction** - Download and analyze images
5. **Screenshot Capability** - Visual verification
6. **Auth Manager** - Secure credential storage
7. **Retry Logic** - Exponential backoff for failed requests
8. **Content Deduplication** - Avoid duplicate articles

## 📚 Examples

See the examples in action:

```bash
# Tech news aggregation
./cli.py --team magentic "Aggregate top tech news from HN, TechCrunch, and Verge"

# Product research
./cli.py --team magentic "Research iPhone 15 Pro reviews and pricing"

# Competitive analysis
./cli.py --team magentic "Compare features of top 3 project management tools"

# Market research
./cli.py --team magentic "Find recent YC-funded startups in AI space"

# Content discovery
./cli.py --team magentic "Find all articles about Rust programming from last week"
```

## 🆘 Troubleshooting

### "Site returned 403 Forbidden"
- Site blocks automated access
- Try adding User-Agent headers
- Consider using official API
- Check robots.txt

### "Could not extract content"
- Site structure may have changed
- JavaScript-heavy site
- Content behind login
- Try different extraction approach

### "Search returned no results"
- Check search query
- Try different search engine
- Verify internet connection
- Site may be blocking searches

### "File not saved"
- Check file path permissions
- Verify parent directory exists
- Check disk space
- Review error message

## 🎉 Get Started!

```bash
# Install beautifulsoup4 if not already
pip install beautifulsoup4

# Try your first web research
./cli.py --team magentic "Search for 'AutoGen framework' and summarize the top result"

# Create your morning briefing
./cli.py --team magentic "Create a briefing from TechCrunch and HackerNews"

# Save it to file
./cli.py --team magentic "Research Tesla news and save to ~/tesla_news.md"
```

**Welcome to automated web research! 🚀**

---

For more examples and advanced usage, see the examples directory or ask the design team:
```bash
./cli.py --team design "How can I enhance Magentic-One for [MY USE CASE]?"
```
