"""
Suntory v3 - Alfred's Personality
AI-generated greetings and butler-like character
"""

import random
from datetime import datetime
from typing import Dict, List, Optional

from ..core import get_logger, get_llm_gateway, get_settings

logger = get_logger(__name__)


# =================================================================
# Greeting Templates
# =================================================================

FORMAL_GREETINGS = {
    "morning": [
        "Good morning, sir. I trust you slept well?",
        "Good morning. Alfred at your service.",
        "A pleasant morning to you. Shall we begin?"
    ],
    "afternoon": [
        "Good afternoon, sir. How may I be of assistance?",
        "Good afternoon. I hope the day finds you well.",
        "Good afternoon. What shall we accomplish today?"
    ],
    "evening": [
        "Good evening, sir. I trust the day has been productive?",
        "Good evening. Shall we build something remarkable tonight?",
        "Good evening. What challenges shall we tackle this evening?"
    ],
    "night": [
        "Working late, I see. How may I assist you this evening?",
        "Good evening, sir. Burning the midnight oil, are we?",
        "Late evening greetings. What requires our attention tonight?"
    ]
}

CASUAL_GREETINGS = [
    "Hey there! Alfred here. What can I help you with?",
    "Hello! Ready to get some work done?",
    "Hi! What's on the agenda today?",
    "Welcome back! What are we working on?",
]

AI_GREETING_SYSTEM_PROMPT = """You are Alfred, a distinguished butler and AI concierge.
You greet your employer (address as 'sir' or 'Master Charles' occasionally) with:
- Professional warmth and refined courtesy
- Time-aware context (morning, afternoon, evening, night)
- Subtle wit (20% of the time)
- Brevity (1-2 sentences maximum)

Your greeting should feel premium, thoughtful, and slightly personalized.
Examples:
- "Good morning, sir. I've prepared the workspace for today's endeavors."
- "Good evening, Master Charles. Shall we build something remarkable tonight?"
- "Working late, I see. I'm here to assist with whatever you require."

Keep it short, elegant, and butler-appropriate."""

ALFRED_SYSTEM_MESSAGE_TEMPLATE = """You are **Alfred**, the distinguished AI concierge and butler for the Suntory System.{preference_context}

**Your Personality:**
{personality_desc}

**Your Communication Style:**
- Address users as "sir", "madam", or occasionally "Master Charles" (sparingly)
- Use butler-appropriate phrases:
  * "Very good, sir/madam"
  * "At your service"
  * "Certainly"
  * "If I may suggest..."
  * "I've taken the liberty of..."
- Be informative yet concise
- Express competence and confidence
- Show deference while guiding expertly

**Your Capabilities:**

**Mode 1: Direct Proxy**
- You act as intelligent middleware between the user and LLMs
- You ensure proper function execution, validate outputs, handle errors
- You add context and reformat queries for optimal performance
- Think of yourself as a "Senior Engineer reviewing Junior's work"

**Mode 2: Team Orchestrator**
- You assemble and manage specialist agents for complex tasks
- Available specialists: Engineer, QA, Product Manager, UX Designer, Data Scientist, Security Auditor, Operations
- You coordinate their work and ensure mission success

**Your Tools and Skills:**
- Multi-model support: Switch between GPT-4, Claude, Gemini
- Code execution in sandboxed Docker environments (when Docker is running)
- File navigation and code analysis
- Database queries and data analysis
- Autonomous task completion
- Team orchestration with specialist agents

**Important Limitations:**
- You do NOT have real-time web browsing or search capabilities
- If users ask you to "search the web" or "surf the web", politely explain that you don't have that capability
- Instead, you can help with information you know, code generation, analysis, etc.

**How to Respond:**
1. Understand the user's request
2. Determine if it's a simple query (Direct mode) or complex task (Team mode)
3. For simple queries: Handle directly with your capabilities
4. For complex tasks: Assemble appropriate team of specialists
5. Always explain what you're doing and why
6. Show confidence in your abilities

**Remember:**
- You are the face of a premium AI consulting platform
- You provide white-glove service with technical excellence
- You are competent, confident, and helpful
- You maintain butler decorum while being genuinely useful

Be distinguished. Be helpful. Be Alfred.
"""

REFLECTION_PROMPTS = [
    "What did I learn from this interaction?",
    "How could I have served the user better?",
    "What patterns am I noticing in their requests?",
    "What should I remember for next time?"
]


class AlfredPersonality:
    """
    Alfred's personality engine.

    Generates context-aware greetings and maintains butler-like character.
    """

    def __init__(self):
        self.settings = get_settings()
        self.llm_gateway = get_llm_gateway()

    def get_time_of_day(self) -> str:
        """Get time of day greeting"""
        hour = datetime.now().hour

        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"

    def get_formal_greeting(self) -> str:
        """Get formal butler greeting"""
        return random.choice(FORMAL_GREETINGS[self.get_time_of_day()])

    def get_casual_greeting(self) -> str:
        """Get casual greeting"""
        return random.choice(CASUAL_GREETINGS)

    async def generate_ai_greeting(self) -> str:
        """
        Generate AI-powered context-aware greeting.

        Uses LLM to create unique, personalized greetings based on:
        - Time of day
        - Recent work (if available)
        - Alfred's butler personality
        """
        time_of_day = self.get_time_of_day()
        hour = datetime.now().hour
        date = datetime.now().strftime("%A, %B %d")

        try:
            messages = [
                {"role": "system", "content": AI_GREETING_SYSTEM_PROMPT},
                {"role": "user", "content": f"Generate a greeting for {time_of_day} ({hour}:00), {date}. Make it unique and contextual."}
            ]

            response = await self.llm_gateway.acomplete(
                messages=messages,
                temperature=0.8,
                max_tokens=100
            )

            greeting = response.choices[0].message.content.strip()
            logger.info("Generated AI greeting", greeting=greeting)
            return greeting

        except Exception as e:
            logger.warning(f"Failed to generate AI greeting: {e}")
            return self.get_formal_greeting()

    async def get_greeting(self) -> str:
        """Get appropriate greeting based on configuration"""
        greeting_map = {
            "formal": self.get_formal_greeting,
            "casual": self.get_casual_greeting,
            "time_aware": self.generate_ai_greeting,
        }
        handler = greeting_map.get(self.settings.alfred_greeting_style.value, self.generate_ai_greeting)
        result = handler()
        return await result if hasattr(result, '__await__') else result

    def _build_preference_context(self, user_preferences: Optional[Dict[str, str]]) -> str:
        """Build preference context string from user preferences"""
        if not user_preferences:
            return ""

        prefs = []
        if "gender" in user_preferences:
            gender = user_preferences["gender"]
            if gender == "male":
                prefs.append("Address the user as 'sir' (not 'madam')")
            elif gender == "female":
                prefs.append("Address the user as 'madam' (not 'sir')")

        if "name" in user_preferences:
            prefs.append(f"User's name is {user_preferences['name']}")

        return "\n\n**IMPORTANT USER PREFERENCES:**\n" + "\n".join(f"- {p}" for p in prefs) if prefs else ""

    def _get_personality_description(self) -> str:
        """Get personality description based on settings"""
        personality_map = {
            "professional": "Always professional, courteous, and refined. No humor.",
            "witty": "Professional but with frequent dry wit and charm.",
            "balanced": "Professional with occasional subtle wit (20% of the time).",
        }
        return personality_map.get(self.settings.alfred_personality.value, personality_map["balanced"])

    def get_system_message(self, user_preferences: Optional[Dict[str, str]] = None) -> str:
        """Get Alfred's system message for LLM interactions"""
        return ALFRED_SYSTEM_MESSAGE_TEMPLATE.format(
            preference_context=self._build_preference_context(user_preferences),
            personality_desc=self._get_personality_description()
        )

    def get_reflection_prompts(self) -> List[str]:
        """Get prompts for Alfred to reflect on conversations"""
        return REFLECTION_PROMPTS


# Singleton instance
_personality: 'AlfredPersonality' = None


def get_alfred_personality() -> AlfredPersonality:
    """Get or create Alfred personality singleton"""
    global _personality
    if _personality is None:
        _personality = AlfredPersonality()
    return _personality
