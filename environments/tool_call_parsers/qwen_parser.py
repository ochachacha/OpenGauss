"""
Qwen 2.5 tool call parser.

Uses the same <tool_call> format as Gauss.
Registered as a separate parser name for clarity when using --tool-parser=qwen.
"""

from environments.tool_call_parsers import register_parser
from environments.tool_call_parsers.gauss_parser import GaussToolCallParser


@register_parser("qwen")
class QwenToolCallParser(GaussToolCallParser):
    """
    Parser for Qwen 2.5 tool calls.
    Same <tool_call>{"name": ..., "arguments": ...}</tool_call> format as Gauss.
    """

    pass  # Identical format -- inherits everything from Gauss
