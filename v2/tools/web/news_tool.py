"""
Yamazaki v2 - News Search Tool

Provides news search capabilities using NewsAPI.org (requires free API key).
Fallback to web search if no API key is available.
"""

import httpx
import os
from typing import Optional
from datetime import datetime

from ...core.base_tool import BaseTool, ToolResult, ToolCategory


class NewsSearchTool(BaseTool):
    """
    News search tool using NewsAPI.org or web search fallback.

    Requires NEWS_API_KEY environment variable for best results,
    but will fall back to web search if not available.
    """

    NAME = "web.news"
    DESCRIPTION = "Search for recent news articles on any topic"
    CATEGORY = ToolCategory.WEB
    VERSION = "1.0.0"
    REQUIRES_SECURITY_VALIDATION = False

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("NEWS_API_KEY")

    async def execute(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        max_results: int = 5
    ) -> ToolResult:
        """
        Search for news articles.

        Args:
            query: Search query (optional if category is provided)
            category: News category: business, entertainment, general, health, science, sports, technology
            max_results: Maximum number of results to return (default: 5, max: 10)

        Returns:
            ToolResult with news articles
        """
        try:
            max_results = min(max_results, 10)

            if self.api_key:
                return await self._search_with_newsapi(query, category, max_results)
            else:
                return await self._search_with_web(query, category, max_results)

        except Exception as e:
            return ToolResult.error(f"Failed to search news: {str(e)}")

    async def _search_with_newsapi(
        self,
        query: Optional[str],
        category: Optional[str],
        max_results: int
    ) -> ToolResult:
        """Search using NewsAPI.org"""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                if query:
                    # Search for specific query
                    url = "https://newsapi.org/v2/everything"
                    params = {
                        "q": query,
                        "apiKey": self.api_key,
                        "pageSize": max_results,
                        "sortBy": "publishedAt",
                        "language": "en"
                    }
                else:
                    # Get top headlines by category
                    url = "https://newsapi.org/v2/top-headlines"
                    params = {
                        "apiKey": self.api_key,
                        "pageSize": max_results,
                        "country": "us",
                        "language": "en"
                    }
                    if category:
                        params["category"] = category

                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                if data.get("status") != "ok":
                    return ToolResult.error(f"NewsAPI error: {data.get('message', 'Unknown error')}")

                articles = data.get("articles", [])
                if not articles:
                    return ToolResult.error("No news articles found")

                results = [
                    {
                        "title": article.get("title", "No title"),
                        "source": article.get("source", {}).get("name", "Unknown"),
                        "author": article.get("author", "Unknown"),
                        "url": article.get("url", ""),
                        "published_at": article.get("publishedAt", ""),
                        "description": article.get("description", "")
                    }
                    for article in articles
                ]

                formatted_results = self._format_results(query or f"{category} news", results)

                return ToolResult.ok({
                    "query": query or category,
                    "results": results,
                    "count": len(results),
                    "source": "NewsAPI",
                    "formatted": formatted_results
                })

        except httpx.HTTPError as e:
            return ToolResult.error(f"HTTP error: {str(e)}")

    async def _search_with_web(
        self,
        query: Optional[str],
        category: Optional[str],
        max_results: int
    ) -> ToolResult:
        """Fallback to web search for news"""
        search_query = query or f"{category or 'today'} news"
        search_query = f"{search_query} site:news.google.com OR site:reuters.com OR site:bbc.com"

        # Use web search tool
        from .search_tool import WebSearchTool
        search_tool = WebSearchTool()

        result = await search_tool.execute(query=search_query, max_results=max_results)

        if result.success:
            # Reformat as news results
            web_results = result.data.get("results", [])
            news_results = [
                {
                    "title": r["title"],
                    "source": "Web Search",
                    "author": "Unknown",
                    "url": r["url"],
                    "published_at": datetime.now().isoformat(),
                    "description": r["snippet"]
                }
                for r in web_results
            ]

            formatted_results = self._format_results(query or category or "news", news_results)

            return ToolResult.ok({
                "query": query or category,
                "results": news_results,
                "count": len(news_results),
                "source": "Web Search (fallback)",
                "formatted": formatted_results,
                "note": "Using web search fallback. Set NEWS_API_KEY for better news results."
            })

        return result

    def _format_results(self, query: str, results: list) -> str:
        """Format news results for display"""
        lines = [f"**Latest news for:** {query}\n"]

        for i, article in enumerate(results, 1):
            lines.append(f"{i}. **{article['title']}**")
            lines.append(f"   Source: {article['source']}")
            if article.get('published_at'):
                try:
                    pub_date = datetime.fromisoformat(article['published_at'].replace('Z', '+00:00'))
                    lines.append(f"   Published: {pub_date.strftime('%Y-%m-%d %H:%M')}")
                except:
                    pass
            lines.append(f"   {article['url']}")
            if article.get('description'):
                lines.append(f"   {article['description']}\n")
            else:
                lines.append("")

        return "\n".join(lines)

    def validate_params(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate parameters"""
        query = kwargs.get("query")
        category = kwargs.get("category")

        if not query and not category:
            return False, "either query or category is required"

        if query and not isinstance(query, str):
            return False, "query must be a string"

        if query and len(query) > 500:
            return False, "query is too long (max 500 characters)"

        valid_categories = [
            "business", "entertainment", "general", "health",
            "science", "sports", "technology"
        ]
        if category and category not in valid_categories:
            return False, f"category must be one of: {', '.join(valid_categories)}"

        max_results = kwargs.get("max_results", 5)
        if not isinstance(max_results, int) or max_results < 1 or max_results > 10:
            return False, "max_results must be an integer between 1 and 10"

        return True, None

    def _get_parameters_schema(self) -> dict:
        """Get parameters schema"""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for news articles",
                    "maxLength": 500,
                },
                "category": {
                    "type": "string",
                    "description": "News category",
                    "enum": [
                        "business", "entertainment", "general", "health",
                        "science", "sports", "technology"
                    ],
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 5, max: 10)",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 10,
                },
            },
        }
