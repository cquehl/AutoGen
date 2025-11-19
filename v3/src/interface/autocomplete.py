"""
Suntory v3 - Command Autocomplete System
Fish-shell style autocomplete with fuzzy matching
"""

from typing import Iterable, List, Optional

from prompt_toolkit.completion import (
    CompleteEvent,
    Completer,
    Completion,
    FuzzyCompleter,
)
from prompt_toolkit.document import Document


class SuntoryCompleter(Completer):
    """
    Custom completer for Suntory commands with fuzzy matching.

    Features:
    - Command autocomplete (/help, /model, etc.)
    - Agent name autocomplete
    - Model name autocomplete
    - Inline suggestions (Fish-style)
    - Fuzzy matching for typos
    """

    # Available commands with descriptions
    COMMANDS = {
        "/help": "Show all available commands and usage",
        "/model": "Show or switch LLM model",
        "/agent": "List or switch between agents",
        "/team": "Force team orchestration mode",
        "/cost": "Show cost summary and breakdown",
        "/budget": "View or set budget limits",
        "/mode": "Show current operating mode",
        "/history": "Show conversation history",
        "/clear": "Clear conversation history",
        "exit": "Exit Alfred gracefully",
        "quit": "Exit Alfred gracefully",
    }

    # Available models
    MODELS = [
        "gpt-4o",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo",
        "claude-3-5-sonnet-20241022",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
        "gemini-pro",
        "gemini-1.5-pro",
        "gemini-ultra",
    ]

    # Available agents (specialist + Magentic-One)
    AGENTS = {
        "engineer": "Senior Software Engineer - architecture, coding, debugging",
        "qa": "QA Engineer - testing, quality assurance",
        "product": "Product Manager - requirements, prioritization",
        "ux": "UX Designer - user experience, accessibility",
        "data": "Data Scientist - analytics, ETL, ML",
        "security": "Security Auditor - vulnerabilities, compliance",
        "ops": "Operations Engineer - DevOps, infrastructure",
        "web_surfer": "Web Research - autonomous web browsing",
        "file_surfer": "File Navigation - codebase exploration",
        "coder": "Code Generator - autonomous coding",
        "terminal": "Terminal Executor - sandboxed commands",
    }

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        """
        Generate completions for current input.

        Args:
            document: Current document state
            complete_event: Completion event

        Yields:
            Completion objects
        """
        text = document.text_before_cursor
        word = text.split()[-1] if text else ""

        # Command completions
        if text.startswith("/") or not text:
            for cmd, desc in self.COMMANDS.items():
                if cmd.startswith(word.lower()):
                    yield Completion(
                        cmd,
                        start_position=-len(word),
                        display=cmd,
                        display_meta=desc,
                    )

        # Model name completions after /model
        elif text.startswith("/model "):
            model_input = text[7:].strip()
            for model in self.MODELS:
                if model_input.lower() in model.lower():
                    yield Completion(
                        model,
                        start_position=-len(model_input),
                        display=model,
                        display_meta=self._get_model_meta(model),
                    )

        # Agent completions after /agent
        elif text.startswith("/agent "):
            agent_input = text[7:].strip()
            for agent, desc in self.AGENTS.items():
                if agent_input.lower() in agent.lower():
                    yield Completion(
                        agent,
                        start_position=-len(agent_input),
                        display=agent,
                        display_meta=desc,
                    )

        # Budget completions
        elif text.startswith("/budget "):
            parts = text[8:].strip().split()
            if len(parts) == 0 or (len(parts) == 1 and not text.endswith(" ")):
                for period in ["daily", "monthly"]:
                    if not parts or period.startswith(parts[0].lower()):
                        yield Completion(
                            period,
                            start_position=-len(parts[0]) if parts else 0,
                            display=period,
                            display_meta="Set budget period",
                        )

    def _get_model_meta(self, model: str) -> str:
        """Get metadata description for model"""
        if "gpt-4o" in model:
            return "Fast and capable - OpenAI"
        elif "gpt-4" in model:
            return "Most capable - OpenAI"
        elif "gpt-3.5" in model:
            return "Fast and economical - OpenAI"
        elif "claude-3-5-sonnet" in model:
            return "Best reasoning - Anthropic"
        elif "claude-3-opus" in model:
            return "Most capable - Anthropic"
        elif "claude-3-sonnet" in model:
            return "Balanced - Anthropic"
        elif "claude-3-haiku" in model:
            return "Fast and economical - Anthropic"
        elif "gemini-pro" in model:
            return "Cost-effective - Google"
        elif "gemini-1.5" in model:
            return "Long context - Google"
        elif "gemini-ultra" in model:
            return "Most capable - Google"
        return ""


def create_fuzzy_completer() -> FuzzyCompleter:
    """
    Create fuzzy completer for typo tolerance.

    Returns:
        FuzzyCompleter wrapping SuntoryCompleter
    """
    return FuzzyCompleter(SuntoryCompleter(), WORD=True)


# Example completions for help display
EXAMPLE_COMMANDS = [
    ("Ask a question", "What are Python decorators?"),
    ("Build something", "Create a REST API with JWT authentication"),
    ("Switch models", "/model claude-3-5-sonnet-20241022"),
    ("Use team mode", "/team Design a data pipeline"),
    ("Check costs", "/cost"),
    ("Set budget", "/budget daily 10.00"),
    ("Get help", "/help"),
]
