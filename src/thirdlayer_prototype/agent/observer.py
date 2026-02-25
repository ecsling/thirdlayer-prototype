"""Observer captures current browser state."""
from playwright.async_api import Page
import time

from thirdlayer_prototype.models.state import BrowserState


class Observer:
    """Observes and captures browser state."""
    
    def __init__(self, page: Page):
        self.page = page
    
    async def observe(self) -> BrowserState:
        """Capture current browser state snapshot.
        
        Returns BrowserState with url, title, timestamp.
        """
        url = self.page.url
        title = await self.page.title()
        
        return BrowserState(
            url=url,
            title=title,
            timestamp=time.time(),
        )
