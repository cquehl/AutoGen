"""
Suntory v3 - Agents Module
Specialist and Magentic One agents
"""

from .specialist import (
    create_engineer_agent,
    create_qa_agent,
    create_product_agent,
    create_ux_agent,
    create_data_scientist_agent,
    create_security_agent,
    create_ops_agent,
)

from .magentic import (
    create_web_surfer_agent,
    create_file_surfer_agent,
    create_coder_agent,
    create_terminal_agent,
)

__all__ = [
    # Specialist Agents
    "create_engineer_agent",
    "create_qa_agent",
    "create_product_agent",
    "create_ux_agent",
    "create_data_scientist_agent",
    "create_security_agent",
    "create_ops_agent",
    # Magentic One Agents
    "create_web_surfer_agent",
    "create_file_surfer_agent",
    "create_coder_agent",
    "create_terminal_agent",
]
