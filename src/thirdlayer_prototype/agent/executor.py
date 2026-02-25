"""Executor performs browser actions using Playwright."""
from dataclasses import dataclass
from typing import Any
from playwright.async_api import Page

from thirdlayer_prototype.models.action import Action


@dataclass
class ExecutionResult:
    """Result of action execution."""
    
    success: bool
    error: str | None = None
    extracted_text: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "error": self.error,
            "extracted_text": self.extracted_text,
        }


class Executor:
    """Executes browser actions using Playwright."""
    
    def __init__(self, page: Page, timeout: int = 10000):
        self.page = page
        self.timeout = timeout
    
    async def execute(self, action: Action) -> ExecutionResult:
        """Execute action on browser page.
        
        Returns ExecutionResult with success status and optional error/data.
        """
        try:
            if action.type == "navigate":
                await self.page.goto(action.url, timeout=self.timeout)
                return ExecutionResult(success=True)
            
            elif action.type == "click":
                await self.page.click(action.selector, timeout=self.timeout)
                return ExecutionResult(success=True)
            
            elif action.type == "type":
                await self.page.fill(action.selector, action.text, timeout=self.timeout)
                return ExecutionResult(success=True)
            
            elif action.type == "press":
                await self.page.keyboard.press(action.key)
                return ExecutionResult(success=True)
            
            elif action.type == "wait_for":
                await self.page.wait_for_selector(action.selector, timeout=self.timeout)
                return ExecutionResult(success=True)
            
            elif action.type == "extract":
                element = self.page.locator(action.selector).first
                text = await element.text_content()
                return ExecutionResult(success=True, extracted_text=text)
            
            else:
                return ExecutionResult(
                    success=False,
                    error=f"unknown_action_type_{action.type}",
                )
        
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=f"{type(e).__name__}_{str(e)[:100]}",
            )
