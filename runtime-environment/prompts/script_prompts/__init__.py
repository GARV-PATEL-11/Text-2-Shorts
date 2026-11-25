"""Script-generation prompts: the topic list (req_modifier) and the outline of every approach (approach_outline)."""

from .approach_outline import outline_system
from .req_modifier import REQ_MODIFIER_SYSTEM

__all__ = ["REQ_MODIFIER_SYSTEM", "outline_system"]
