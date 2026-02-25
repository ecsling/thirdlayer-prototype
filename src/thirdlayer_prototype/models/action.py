"""Action abstraction for browser automation.

Defines composable action grammar with stable serialization.
"""
from dataclasses import dataclass
from typing import Any, Literal
import json


ActionType = Literal["navigate", "click", "type", "press", "wait_for", "extract"]


@dataclass
class Action:
    """Composable browser action with stable signature."""
    
    type: ActionType
    selector: str | None = None
    text: str | None = None
    url: str | None = None
    key: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with only non-None fields."""
        d = {"type": self.type}
        if self.selector is not None:
            d["selector"] = self.selector
        if self.text is not None:
            d["text"] = self.text
        if self.url is not None:
            d["url"] = self.url
        if self.key is not None:
            d["key"] = self.key
        return d
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), sort_keys=True)
    
    def signature(self) -> str:
        """Generate canonical signature for Markov transitions.
        
        Uses sorted JSON to ensure stable keys regardless of field order.
        """
        return self.to_json()
    
    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Action":
        """Create Action from dictionary."""
        return cls(
            type=d["type"],
            selector=d.get("selector"),
            text=d.get("text"),
            url=d.get("url"),
            key=d.get("key"),
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "Action":
        """Create Action from JSON string."""
        return cls.from_dict(json.loads(json_str))
    
    def __str__(self) -> str:
        """Human-readable representation."""
        parts = [self.type]
        if self.url:
            parts.append(f"url={self.url}")
        if self.selector:
            parts.append(f"sel={self.selector}")
        if self.text:
            parts.append(f"text={self.text[:20]}...")
        if self.key:
            parts.append(f"key={self.key}")
        return f"Action({', '.join(parts)})"


def navigate(url: str) -> Action:
    """Navigate to URL."""
    return Action(type="navigate", url=url)


def click(selector: str) -> Action:
    """Click element matching selector."""
    return Action(type="click", selector=selector)


def type_text(selector: str, text: str) -> Action:
    """Type text into element matching selector."""
    return Action(type="type", selector=selector, text=text)


def press(key: str) -> Action:
    """Press keyboard key."""
    return Action(type="press", key=key)


def wait_for(selector: str) -> Action:
    """Wait for element matching selector."""
    return Action(type="wait_for", selector=selector)


def extract(selector: str) -> Action:
    """Extract text from element matching selector."""
    return Action(type="extract", selector=selector)
