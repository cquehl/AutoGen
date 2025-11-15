# logger.py
import logging
import sys

# pyautogen uses the standard Python logging module.
# You can configure the root logger or get the specific "autogen" logger.
# The old EVENT_LOGGER_NAME constant is no longer part of the public API.

# Example: Configure the logger for the autogen library
autogen_logger = logging.getLogger("autogen")
autogen_logger.setLevel(logging.INFO)

# Ensure the logger has a handler to output messages.
if not autogen_logger.handlers:
    stream_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    stream_handler.setFormatter(formatter)
    autogen_logger.addHandler(stream_handler)

# You can also configure the root logger for broader logging
# logging.basicConfig(level=logging.INFO, stream=sys.stdout)
