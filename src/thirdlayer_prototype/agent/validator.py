"""Validator filters unsafe/invalid actions before execution."""
from dataclasses import dataclass
from typing import Any
from playwright.async_api import Page

from thirdlayer_prototype.models.action import Action


DENYLIST_PATTERNS = [
    "logout",
    "log-out",
    "sign-out",
    "signout",
    "delete",
    "remove",
    "submit",
    "purchase",
    "buy",
    "payment",
    "checkout",
    "account",
    "settings",
    "preferences",
]


@dataclass
class ValidationResult:
    """Result of action validation."""
    
    valid: bool
    reason: str
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {"valid": self.valid, "reason": self.reason}


class Validator:
    """Validates actions before execution."""
    
    def __init__(self, page: Page):
        self.page = page
    
    async def validate(self, action: Action) -> ValidationResult:
        """Validate action for safety and feasibility.
        
        Checks:
        1. Denylist patterns (destructive actions)
        2. Selector existence (when relevant)
        """
        if action.type in ["click", "type", "wait_for", "extract"]:
            if not action.selector:
                return ValidationResult(
                    valid=False,
                    reason=f"missing_selector_for_{action.type}",
                )
            
            if self._is_denylisted(action.selector):
                return ValidationResult(
                    valid=False,
                    reason=f"selector_matches_denylist_pattern",
                )
            
            exists = await self._selector_exists(action.selector)
            if not exists:
                return ValidationResult(
                    valid=False,
                    reason=f"selector_not_found_{action.selector}",
                )
        
        if action.type == "navigate":
            if not action.url:
                return ValidationResult(
                    valid=False,
                    reason="missing_url_for_navigate",
                )
        
        if action.type == "press":
            if not action.key:
                return ValidationResult(
                    valid=False,
                    reason="missing_key_for_press",
                )
        
        return ValidationResult(valid=True, reason="passed_all_checks")
    
    def _is_denylisted(self, selector: str) -> bool:
        """Check if selector contains denylist patterns."""
        selector_lower = selector.lower()
        return any(pattern in selector_lower for pattern in DENYLIST_PATTERNS)
    
    async def _selector_exists(self, selector: str, timeout: int = 2000) -> bool:
        """Check if selector exists on page.
        
        Uses short timeout to avoid blocking.
        """
        try:
            count = await self.page.locator(selector).count()
            return count > 0
        except Exception:
            return False
