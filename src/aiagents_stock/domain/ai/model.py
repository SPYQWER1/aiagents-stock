"""
AI Domain Models.
"""
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Message:
    """Chat message model."""
    role: str
    content: str
    name: Optional[str] = None

    def to_dict(self) -> dict[str, str]:
        d = {"role": self.role, "content": self.content}
        if self.name:
            d["name"] = self.name
        return d
