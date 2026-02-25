"""State representation for browser context."""
from dataclasses import dataclass
from typing import Any


@dataclass
class BrowserState:
    """Current browser state snapshot."""
    
    url: str
    title: str
    timestamp: float
    metadata: dict[str, Any] | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "title": self.title,
            "timestamp": self.timestamp,
            "metadata": self.metadata or {},
        }
