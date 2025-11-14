"""
WebSurfer Agent - Specialized agent for web navigation and content extraction

Can browse websites, search the web, extract content, and gather information.
"""

from autogen_core.models import ChatCompletionClient
from autogen_core.tools import FunctionTool
from .base import BaseMagneticAgent
from .tools.web_tools import (
    navigate_to_url,
    search_google,
    extract_text_content,
    extract_links,
    get_page_title,
    download_page
)


class WebSurferAgent(BaseMagneticAgent):
    """
    WebSurfer agent for web browsing and research.

    Capabilities:
    - Navigate to URLs
    - Search Google/DuckDuckGo
    - Extract page content and text
    - Extract links from pages
    - Download pages
    - Get page titles

    Example:
        web_agent = WebSurferAgent(model_client=client)

        # Agent can now:
        # - "Browse to https://example.com and summarize the content"
        # - "Search for 'AI frameworks 2024' and list the top 5 results"
        # - "Extract all article links from https://news.ycombinator.com"
    """

    def __init__(
        self,
        model_client: ChatCompletionClient,
        name: str = "WebSurfer",
        **kwargs
    ):
        """
        Initialize WebSurfer agent.

        Args:
            model_client: ChatCompletionClient instance
            name: Agent name (default: "WebSurfer")
            **kwargs: Additional arguments passed to BaseMagneticAgent
        """
        system_message = """
        You are **WebSurfer**, an expert web browsing and research agent.

        **Your Capabilities:**
        - Navigate to any URL and retrieve content
        - Search the web using Google/DuckDuckGo
        - Extract text content from web pages
        - Extract links from pages
        - Download pages for offline viewing
        - Get page titles and metadata

        **Your Tools:**
        1. `navigate_to_url(url)` - Visit a URL and get the page content
        2. `search_google(query, num_results)` - Search the web
        3. `extract_text_content(url, max_length)` - Get cleaned text from a page
        4. `extract_links(url, filter_pattern)` - Get all links from a page
        5. `get_page_title(url)` - Get the title of a page
        6. `download_page(url, output_path)` - Save a page to file

        **Your Approach:**
        1. **Understand the task** - What information is needed?
        2. **Plan your search** - Which sites or search queries?
        3. **Execute efficiently** - Use the right tools in the right order
        4. **Extract key information** - Focus on relevant content
        5. **Summarize clearly** - Present findings in organized format

        **Best Practices:**
        - Use `extract_text_content` instead of `navigate_to_url` when you need readable text
        - Use `search_google` to find relevant pages before browsing
        - Extract links when you need to find specific resources on a page
        - Handle errors gracefully (sites may be down, blocked, or changed)
        - Be concise - summarize long pages, don't dump raw HTML

        **Example Workflows:**

        *Research Task:*
        1. Search Google for the topic
        2. Visit top 3 results
        3. Extract key points from each
        4. Compile summary

        *Link Gathering:*
        1. Navigate to the page
        2. Extract all links
        3. Filter for relevant ones
        4. Return organized list

        *Content Extraction:*
        1. Use extract_text_content
        2. Summarize main points
        3. Include key quotes or data

        Always provide **structured, actionable results** to the user or orchestrator.
        """

        # Initialize with web tools
        tools = [
            FunctionTool(navigate_to_url, description="Navigate to a URL and retrieve the page content. Returns HTML and metadata."),
            FunctionTool(search_google, description="Search Google/DuckDuckGo for a query. Returns list of results with titles, URLs, and snippets."),
            FunctionTool(extract_text_content, description="Extract cleaned text content from a webpage. Removes scripts, navigation, etc. Good for reading articles."),
            FunctionTool(extract_links, description="Extract all links from a webpage. Can filter by regex pattern. Useful for finding specific resources."),
            FunctionTool(get_page_title, description="Get the title of a webpage. Quick way to verify page identity."),
            FunctionTool(download_page, description="Download and save a webpage to a file. Useful for archiving or offline access."),
        ]

        super().__init__(
            name=name,
            model_client=model_client,
            system_message=system_message,
            tools=tools,
            **kwargs
        )


def create_web_surfer(model_client: ChatCompletionClient, **kwargs) -> WebSurferAgent:
    """
    Factory function to create a WebSurfer agent.

    Args:
        model_client: ChatCompletionClient instance
        **kwargs: Additional arguments passed to WebSurferAgent

    Returns:
        Configured WebSurferAgent

    Example:
        client = ChatCompletionClient.load_component(config)
        web_agent = create_web_surfer(client)
    """
    return WebSurferAgent(model_client=model_client, **kwargs)
