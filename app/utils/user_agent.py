# app/utils/user_agent.py
from user_agents import parse

def extract_browser(user_agent_string: str | None) -> str:
    """
    Extracts a clean browser name from a raw user agent string.
    
    "Mozilla/5.0 ... Chrome/120.0.0.0 ..." → "Chrome"
    """
    if not user_agent_string:
        return "Unknown"
    
    ua = parse(user_agent_string)

    if ua.is_bot:
        return "Bot"

    # ua.browser.family gives us "Chrome", "Firefox", "Safari" etc.
    return ua.browser.family or "Unknown"


def extract_os(user_agent_string: str | None) -> str:
    """
    Extracts operating system from user agent string.
    
    "Mozilla/5.0 (Macintosh; Intel Mac OS X ...)" → "Mac OS X"
    """
    if not user_agent_string:
        return "Unknown"
    
    ua = parse(user_agent_string)
    return ua.os.family or "Unknown"