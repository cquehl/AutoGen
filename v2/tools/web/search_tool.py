"""
Yamazaki v2 - Web Search Tool

Provides web search capabilities using DuckDuckGo (no API key needed).
"""

import httpx
from typing import Optional
from bs4 import BeautifulSoup

from ...core.base_tool import BaseTool, ToolResult, ToolCategory


class WebSearchTool(BaseTool):
    """
    Web search tool using DuckDuckGo HTML search.

    Provides web search without requiring API keys.
    """

    NAME = "web.search"
    DESCRIPTION = "Search the web using DuckDuckGo and return relevant results with snippets"
    CATEGORY = ToolCategory.WEB
    VERSION = "1.0.0"
    REQUIRES_SECURITY_VALIDATION = False

    async def execute(self, query: str, max_results: int = 5) -> ToolResult:
        """
        Search the web.

        Args:
            query: Search query
            max_results: Maximum number of results to return (default: 5, max: 10)

        Returns:
            ToolResult with search results
        """
        try:
            # Limit max_results
            max_results = min(max_results, 10)

            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                # DuckDuckGo HTML search
                url = "https://html.duckduckgo.com/html/"
                data = {"q": query}
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                }

                response = await client.post(url, data=data, headers=headers)
                response.raise_for_status()

                # Parse HTML
                soup = BeautifulSoup(response.text, 'html.parser')

                results = []
                for result_div in soup.find_all('div', class_='result', limit=max_results):
                    try:
                        # Extract title link
                        title_link = result_div.find('a', class_='result__a')
                        if not title_link:
                            continue

                        title = title_link.get_text(strip=True)
                        link = title_link.get('href', '')

                        # Extract snippet
                        snippet_div = result_div.find('a', class_='result__snippet')
                        snippet = snippet_div.get_text(strip=True) if snippet_div else ""

                        results.append({
                            "title": title,
                            "url": link,
                            "snippet": snippet
                        })

                    except Exception as e:
                        # Skip malformed results
                        continue

                if not results:
                    return ToolResult.error("No search results found")

                # Format results
                formatted_results = self._format_results(query, results)

                return ToolResult.ok({
                    "query": query,
                    "results": results,
                    "count": len(results),
                    "formatted": formatted_results
                })

        except httpx.HTTPError as e:
            return ToolResult.error(f"HTTP error during search: {str(e)}")
        except Exception as e:
            return ToolResult.error(f"Failed to search web: {str(e)}")

    def _format_results(self, query: str, results: list) -> str:
        """Format search results for display"""
        lines = [f"**Web search results for:** {query}\n"]

        for i, result in enumerate(results, 1):
            lines.append(f"{i}. **{result['title']}**")
            lines.append(f"   {result['url']}")
            if result['snippet']:
                lines.append(f"   {result['snippet']}\n")
            else:
                lines.append("")

        return "\n".join(lines)

    def validate_params(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate parameters"""
        query = kwargs.get("query")

        if not query:
            return False, "query is required"

        if not isinstance(query, str):
            return False, "query must be a string"

        if len(query) > 500:
            return False, "query is too long (max 500 characters)"

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
                    "description": "Search query",
                    "maxLength": 500,
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 5, max: 10)",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 10,
                },
            },
            "required": ["query"],
        }
