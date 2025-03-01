from typing import Any, Optional
import traceback

class APIError(Exception):
    def __init__(self, message: str, response: Optional[Any] = None, body: Optional[str] = None):
        super().__init__(message)
        self.response = response
        self.body = body

def get_error_details(error: Exception) -> str:
    if not isinstance(error, Exception):
        raise TypeError("Input must be an exception")

    stack_lines = []
    for frame in traceback.extract_tb(error.__traceback__):
        stack_lines.append(
            f"  File '{frame.filename}', line {frame.lineno}, in {frame.name}\n"
            f"    {frame.line}"
        )

    error_type = error.__class__.__name__
    error_msg = str(error)
    
    return (
        f"{error_type}: {error_msg}\n"
        f"Stack trace (most recent call last):\n"
        f"{chr(10).join(stack_lines)}"
    )