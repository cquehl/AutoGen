"""
Suntory v3 - Onboarding System
Interactive tutorial for first-time users
"""

from typing import List, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from ..core import get_logger

logger = get_logger(__name__)


class OnboardingTutorial:
    """
    Interactive onboarding tutorial for new users.

    Guides users through:
    - System capabilities
    - Example tasks
    - Command discovery
    - Best practices
    """

    def __init__(self, console: Console):
        self.console = console
        self.skipped = False

    def should_run(self) -> bool:
        """Check if user wants to run tutorial"""
        self.console.print()
        self.console.print(
            "[bold cyan]👋 Welcome to Suntory System v3![/bold cyan]"
        )
        self.console.print()
        self.console.print(
            "[dim]This appears to be your first time. Would you like a quick tutorial?[/dim]"
        )
        self.console.print(
            "[dim](You can skip this and type /help anytime)[/dim]"
        )
        self.console.print()

        return Confirm.ask("Run tutorial?", default=True)

    def run(self):
        """Run the full onboarding tutorial"""
        if not self.should_run():
            self.skipped = True
            self.console.print()
            self.console.print(
                "[green]No problem! Type /help anytime for guidance.[/green]"
            )
            self.console.print()
            return

        logger.info("Starting onboarding tutorial")

        self._step_welcome()
        self._step_modes()
        self._step_commands()
        self._step_examples()
        self._step_tips()
        self._step_complete()

    def _step_welcome(self):
        """Welcome step"""
        self.console.clear()
        self.console.print()

        welcome = Panel(
            """**Alfred is your AI concierge for the Suntory System**

He operates in two modes:
• **Direct Mode**: Quick queries and conversations
• **Team Mode**: Complex tasks with specialist agents

Alfred automatically chooses the best mode for your task.""",
            title="[bold]What is Alfred?[/bold]",
            border_style="cyan",
            padding=(1, 2)
        )

        self.console.print(welcome)
        self.console.print()

        Prompt.ask("[dim]Press Enter to continue[/dim]", default="")

    def _step_modes(self):
        """Explain modes"""
        self.console.clear()
        self.console.print()

        # Create table
        table = Table(
            title="Alfred's Two Modes",
            show_header=True,
            header_style="bold cyan"
        )
        table.add_column("Mode", style="cyan", width=15)
        table.add_column("When Used", width=30)
        table.add_column("Example", style="italic", width=35)

        table.add_row(
            "Direct",
            "Quick queries, Q&A",
            '"Explain Python decorators"'
        )
        table.add_row(
            "Team",
            "Complex, multi-step tasks",
            '"Build a REST API for authentication"'
        )

        self.console.print(table)
        self.console.print()

        self.console.print(
            "[green]💡 Tip:[/green] Alfred detects complexity automatically!\n"
            "   You don't need to specify the mode."
        )
        self.console.print()

        Prompt.ask("[dim]Press Enter to continue[/dim]", default="")

    def _step_commands(self):
        """Show key commands"""
        self.console.clear()
        self.console.print()

        commands = Panel(
            """**Essential Commands:**

`/help` - Show all commands
`/model` - Show or switch LLM model
`/model claude-3-5-sonnet-20241022` - Switch to Claude
`/team <task>` - Force team mode
`/history` - View conversation history
`/cost` - Show cost summary
`/clear` - Clear conversation
`exit` or `quit` - Leave Alfred

**Example:**
```
[alfred] > /model
Current model: claude-3-5-sonnet-20241022

[alfred] > /model gpt-4o
Switched to gpt-4o
```
""",
            title="[bold]Essential Commands[/bold]",
            border_style="cyan",
            padding=(1, 2)
        )

        self.console.print(commands)
        self.console.print()

        Prompt.ask("[dim]Press Enter to continue[/dim]", default="")

    def _step_examples(self):
        """Show example tasks"""
        self.console.clear()
        self.console.print()

        examples = Panel(
            """**Try These Examples:**

**Simple Queries** (Direct Mode):
• "What are Python context managers?"
• "Explain the difference between SQL and NoSQL"
• "Show me how to use async/await in JavaScript"

**Complex Tasks** (Team Mode - Automatic):
• "Build a CI/CD pipeline for a Python project"
• "Create a secure REST API with JWT authentication"
• "Design a data pipeline for processing CSV files"
• "Review this code for security vulnerabilities"

**Force Team Mode:**
• "/team Create a dashboard for monitoring API performance"
• "/team Build a recommendation system for e-commerce"
""",
            title="[bold]Example Tasks to Try[/bold]",
            border_style="cyan",
            padding=(1, 2)
        )

        self.console.print(examples)
        self.console.print()

        Prompt.ask("[dim]Press Enter to continue[/dim]", default="")

    def _step_tips(self):
        """Show tips and best practices"""
        self.console.clear()
        self.console.print()

        tips = Panel(
            """**Pro Tips for Best Results:**

🎯 **Be Specific**
   Instead of: "Help with database"
   Try: "Design a PostgreSQL schema for user authentication"

🔄 **Switch Models for Different Tasks**
   • Claude: Best for complex reasoning and analysis
   • GPT-4: Excellent for code generation
   • Gemini: Fast and cost-effective

💰 **Track Your Costs**
   Use `/cost` to see token usage and estimated costs

📊 **View Your Work**
   Use `/history` to review past conversations

🛡️ **Docker Sandbox**
   Code executes in isolated Docker containers for security

⚡ **Streaming Responses**
   See Alfred's thoughts in real-time as he formulates answers
""",
            title="[bold]Pro Tips[/bold]",
            border_style="cyan",
            padding=(1, 2)
        )

        self.console.print(tips)
        self.console.print()

        Prompt.ask("[dim]Press Enter to continue[/dim]", default="")

    def _step_complete(self):
        """Tutorial complete"""
        self.console.clear()
        self.console.print()

        complete = Panel(
            """**You're all set! 🚀**

Alfred is ready to assist you.

**Quick Reminders:**
• Type naturally - Alfred understands context
• Use `/help` anytime for command reference
• Use `/cost` to monitor spending
• Use `/model` to switch between AI models
• Type `exit` or `quit` to leave

**Ready to start?**

Try asking Alfred something like:
"What can you help me with today?"
""",
            title="[bold green]Tutorial Complete![/bold green]",
            border_style="green",
            padding=(1, 2)
        )

        self.console.print(complete)
        self.console.print()

        logger.info("Onboarding tutorial completed")


class QuickStartGuide:
    """Quick reference guide for existing users"""

    def __init__(self, console: Console):
        self.console = console

    def show(self):
        """Show quick start guide"""
        self.console.print()

        guide = """**Quick Start Guide**

**Direct Mode** (automatic for simple queries):
Just ask your question naturally.

**Team Mode** (automatic for complex tasks):
Alfred assembles specialists to handle your request.

**Force Team Mode:**
`/team <your task>`

**Switch Models:**
`/model gpt-4o` or `/model claude-3-5-sonnet-20241022`

**View Costs:**
`/cost` - See token usage and cost breakdown

**Help:**
`/help` - Full command list

**Exit:**
Type `exit` or `quit`
"""

        self.console.print(Markdown(guide))
        self.console.print()


def run_onboarding(console: Console, force: bool = False) -> bool:
    """
    Run onboarding tutorial if needed.

    Args:
        console: Rich console
        force: Force tutorial even if user has seen it

    Returns:
        True if tutorial was run, False if skipped
    """
    # In production, check if user has completed tutorial before
    # For now, always offer on first run

    tutorial = OnboardingTutorial(console)

    if force:
        tutorial.run()
        return not tutorial.skipped
    else:
        # Check if first run (could check for marker file)
        import os
        marker_file = os.path.expanduser("~/.suntory_tutorial_completed")

        if not os.path.exists(marker_file):
            tutorial.run()

            if not tutorial.skipped:
                # Mark tutorial as completed
                try:
                    with open(marker_file, 'w') as f:
                        f.write("completed")
                except (OSError, IOError) as e:
                    # Ignore file errors - tutorial completion marker is non-critical
                    pass

            return not tutorial.skipped

    return False


def show_quick_start(console: Console):
    """Show quick start guide"""
    guide = QuickStartGuide(console)
    guide.show()
