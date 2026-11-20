"""
Platform definitions and check logic for username availability.
Includes robust error handling for network issues, timeouts, rate limits, etc.
"""

from typing import Dict, Optional, Tuple
import socket

import requests
from requests.exceptions import (
    ConnectionError,
    HTTPError,
    Timeout,
    SSLError,
    ProxyError,
    RequestException,
    TooManyRedirects,
)


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Default timeout (connect, read)
DEFAULT_TIMEOUT = (5.0, 10.0)


def _safe_text(resp: requests.Response, limit: int = 100_000) -> str:
    """Safely extract text from response, handling encoding errors."""
    try:
        text = resp.text
        return text[:limit].lower() if text else ""
    except Exception:
        try:
            return resp.content[:limit].decode("utf-8", errors="ignore").lower()
        except Exception:
            return ""


def _get(
    url: str,
    session: requests.Session,
    timeout: Tuple[float, float] = DEFAULT_TIMEOUT,
    allow_redirects: bool = True,
) -> Tuple[Optional[requests.Response], str]:
    """
    Safe GET request with detailed error classification.
    Returns (response_or_None, error_message).
    error_message is empty string on success.
    """
    try:
        resp = session.get(
            url,
            headers=DEFAULT_HEADERS,
            timeout=timeout,
            allow_redirects=allow_redirects,
        )
        return resp, ""
    except Timeout:
        return None, "Timeout – server took too long to respond"
    except SSLError:
        return None, "SSL/TLS error – secure connection failed"
    except ProxyError:
        return None, "Proxy error"
    except ConnectionError as e:
        # Distinguish DNS vs connection refused etc.
        msg = str(e).lower()
        if "name or service not known" in msg or "getaddrinfo failed" in msg:
            return None, "DNS resolution failed"
        if "connection refused" in msg:
            return None, "Connection refused"
        return None, "Connection error – network unreachable"
    except TooManyRedirects:
        return None, "Too many redirects"
    except RequestException as e:
        return None, f"Request failed: {type(e).__name__}"
    except Exception as e:
        return None, f"Unexpected error: {type(e).__name__}"


def _handle_status(resp: requests.Response, available_codes=(404,), taken_codes=(200,)) -> Tuple[str, str]:
    """Generic status code handler used by simple checkers."""
    code = resp.status_code
    if code in available_codes:
        return "available", "Username is available"
    if code in taken_codes:
        return "taken", "Profile exists"
    if code in (403, 429):
        return "unknown", f"Blocked or rate-limited (HTTP {code})"
    if code >= 500:
        return "unknown", f"Server error (HTTP {code})"
    return "unknown", f"Unexpected status {code}"


# ---------------------------------------------------------------------------
# Individual platform checkers
# ---------------------------------------------------------------------------

def check_github(username: str, session: requests.Session) -> Tuple[str, str]:
    url = f"https://github.com/{username}"
    resp, err = _get(url, session)
    if resp is None:
        return "unknown", err or "Request failed"
    return _handle_status(resp)


def check_gitlab(username: str, session: requests.Session) -> Tuple[str, str]:
    url = f"https://gitlab.com/{username}"
    resp, err = _get(url, session)
    if resp is None:
        return "unknown", err or "Request failed"
    return _handle_status(resp)


def check_reddit(username: str, session: requests.Session) -> Tuple[str, str]:
    url = f"https://www.reddit.com/user/{username}/about.json"
    resp, err = _get(url, session)
    if resp is None:
        return "unknown", err or "Request failed"

    if resp.status_code == 404:
        return "available", "Username is available"
    if resp.status_code == 200:
        try:
            data = resp.json()
            if isinstance(data, dict) and "data" in data and data["data"].get("name"):
                return "taken", "Profile exists"
            return "taken", "Profile appears to exist"
        except (ValueError, TypeError, KeyError):
            return "taken", "Profile appears to exist (could not parse JSON)"
    if resp.status_code in (403, 429):
        return "unknown", f"Blocked or rate-limited (HTTP {resp.status_code})"
    if resp.status_code >= 500:
        return "unknown", f"Server error (HTTP {resp.status_code})"
    return "unknown", f"Unexpected status {resp.status_code}"


def check_youtube(username: str, session: requests.Session) -> Tuple[str, str]:
    url = f"https://www.youtube.com/@{username}"
    resp, err = _get(url, session)
    if resp is None:
        return "unknown", err or "Request failed"

    if resp.status_code == 404:
        return "available", "Handle appears available"
    if resp.status_code == 200:
        text = _safe_text(resp)
        if any(p in text for p in [
            "this page isn't available",
            "this channel does not exist",
            "404 not found",
        ]):
            return "available", "Handle appears available"
        return "taken", "Channel / handle exists"
    if resp.status_code in (403, 429):
        return "unknown", f"Blocked or rate-limited (HTTP {resp.status_code})"
    return "unknown", f"Unexpected status {resp.status_code}"


def check_tiktok(username: str, session: requests.Session) -> Tuple[str, str]:
    url = f"https://www.tiktok.com/@{username}"
    resp, err = _get(url, session)
    if resp is None:
        return "unknown", err or "Request failed"

    if resp.status_code == 404:
        return "available", "Username appears available"
    if resp.status_code == 200:
        text = _safe_text(resp)
        if any(p in text for p in [
            "couldn't find this account",
            "page not available",
            "user not found",
        ]):
            return "available", "Username appears available"
        return "taken", "Profile appears to exist"
    if resp.status_code in (403, 429):
        return "unknown", f"Blocked or rate-limited (HTTP {resp.status_code})"
    return "unknown", f"Unexpected status {resp.status_code}"


def check_instagram(username: str, session: requests.Session) -> Tuple[str, str]:
    url = f"https://www.instagram.com/{username}/"
    resp, err = _get(url, session)
    if resp is None:
        return "unknown", err or "Request failed / blocked"

    if resp.status_code == 404:
        return "available", "Username appears available"
    if resp.status_code == 200:
        text = _safe_text(resp)
        if any(p in text for p in [
            "sorry, this page isn't available",
            "the link you followed may be broken",
            "page not found",
        ]):
            return "available", "Username appears available"
        if "login" in text and "password" in text and len(text) < 50000:
            return "unknown", "Login wall / anti-bot protection"
        return "taken", "Profile appears to exist"
    if resp.status_code in (429, 403):
        return "unknown", f"Blocked or rate-limited (HTTP {resp.status_code})"
    return "unknown", f"Unexpected status {resp.status_code}"


def check_x(username: str, session: requests.Session) -> Tuple[str, str]:
    url = f"https://x.com/{username}"
    resp, err = _get(url, session, allow_redirects=True)
    if resp is None:
        return "unknown", err or "Request failed"

    if resp.status_code == 404:
        return "available", "Username appears available"
    if resp.status_code == 200:
        text = _safe_text(resp)
        if any(p in text for p in [
            "this account doesn’t exist",
            "this account doesn't exist",
            "account suspended",
            "page doesn’t exist",
            "page doesn't exist",
        ]):
            return "available", "Account does not exist"
        return "unknown", "Could not determine (X protects profiles heavily)"
    if resp.status_code in (403, 429):
        return "unknown", f"Blocked or rate-limited (HTTP {resp.status_code})"
    return "unknown", f"Unexpected status {resp.status_code}"


def check_twitch(username: str, session: requests.Session) -> Tuple[str, str]:
    url = f"https://www.twitch.tv/{username}"
    resp, err = _get(url, session)
    if resp is None:
        return "unknown", err or "Request failed"

    if resp.status_code == 404:
        return "available", "Username appears available"
    if resp.status_code == 200:
        text = _safe_text(resp)
        if any(p in text for p in [
            "sorry. unless you’ve got a time machine",
            "page not found",
            "content unavailable",
        ]):
            return "available", "Username appears available"
        return "taken", "Channel appears to exist"
    if resp.status_code in (403, 429):
        return "unknown", f"Blocked or rate-limited (HTTP {resp.status_code})"
    return "unknown", f"Unexpected status {resp.status_code}"


def check_pinterest(username: str, session: requests.Session) -> Tuple[str, str]:
    url = f"https://www.pinterest.com/{username}/"
    resp, err = _get(url, session)
    if resp is None:
        return "unknown", err or "Request failed"

    if resp.status_code == 404:
        return "available", "Username appears available"
    if resp.status_code == 200:
        text = _safe_text(resp)
        if any(p in text for p in ["page not found", "user not found", "something went wrong"]):
            return "available", "Username appears available"
        return "taken", "Profile appears to exist"
    if resp.status_code in (403, 429):
        return "unknown", f"Blocked or rate-limited (HTTP {resp.status_code})"
    return "unknown", f"Unexpected status {resp.status_code}"


def check_medium(username: str, session: requests.Session) -> Tuple[str, str]:
    url = f"https://medium.com/@{username}"
    resp, err = _get(url, session)
    if resp is None:
        return "unknown", err or "Request failed"

    if resp.status_code == 404:
        return "available", "Username appears available"
    if resp.status_code == 200:
        text = _safe_text(resp)
        if any(p in text for p in ["page not found", "out of nothing", "we couldn’t find", "we couldn't find"]):
            return "available", "Username appears available"
        return "taken", "Profile appears to exist"
    if resp.status_code in (403, 429):
        return "unknown", f"Blocked or rate-limited (HTTP {resp.status_code})"
    return "unknown", f"Unexpected status {resp.status_code}"


def check_devto(username: str, session: requests.Session) -> Tuple[str, str]:
    url = f"https://dev.to/{username}"
    resp, err = _get(url, session)
    if resp is None:
        return "unknown", err or "Request failed"
    return _handle_status(resp)


def check_soundcloud(username: str, session: requests.Session) -> Tuple[str, str]:
    url = f"https://soundcloud.com/{username}"
    resp, err = _get(url, session)
    if resp is None:
        return "unknown", err or "Request failed"

    if resp.status_code == 404:
        return "available", "Username appears available"
    if resp.status_code == 200:
        text = _safe_text(resp)
        if "we can't find that user" in text or "page not found" in text:
            return "available", "Username appears available"
        return "taken", "Profile appears to exist"
    if resp.status_code in (403, 429):
        return "unknown", f"Blocked or rate-limited (HTTP {resp.status_code})"
    return "unknown", f"Unexpected status {resp.status_code}"


def check_telegram(username: str, session: requests.Session) -> Tuple[str, str]:
    url = f"https://t.me/{username}"
    resp, err = _get(url, session)
    if resp is None:
        return "unknown", err or "Request failed"

    if resp.status_code == 404:
        return "available", "Username appears available"
    if resp.status_code == 200:
        text = _safe_text(resp)
        # Telegram often shows a generic page; look for stronger signals
        if "if you have telegram, you can contact" in text and "tgme_page_photo" not in text:
            return "available", "Username appears available"
        if "tgme_page_title" in text or "tgme_username_link" in text:
            return "taken", "Channel / user appears to exist"
        return "taken", "Page exists"
    if resp.status_code in (403, 429):
        return "unknown", f"Blocked or rate-limited (HTTP {resp.status_code})"
    return "unknown", f"Unexpected status {resp.status_code}"


def check_hashnode(username: str, session: requests.Session) -> Tuple[str, str]:
    url = f"https://hashnode.com/@{username}"
    resp, err = _get(url, session)
    if resp is None:
        return "unknown", err or "Request failed"
    return _handle_status(resp)


def check_producthunt(username: str, session: requests.Session) -> Tuple[str, str]:
    url = f"https://www.producthunt.com/@{username}"
    resp, err = _get(url, session)
    if resp is None:
        return "unknown", err or "Request failed"

    if resp.status_code == 404:
        return "available", "Username appears available"
    if resp.status_code == 200:
        text = _safe_text(resp)
        if "page not found" in text or "doesn't exist" in text or "does not exist" in text:
            return "available", "Username appears available"
        return "taken", "Profile appears to exist"
    if resp.status_code in (403, 429):
        return "unknown", f"Blocked or rate-limited (HTTP {resp.status_code})"
    return "unknown", f"Unexpected status {resp.status_code}"


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

PLATFORMS: Dict[str, Dict] = {
    "GitHub": {
        "check": check_github,
        "url_template": "https://github.com/{username}",
        "category": "Developer",
    },
    "GitLab": {
        "check": check_gitlab,
        "url_template": "https://gitlab.com/{username}",
        "category": "Developer",
    },
    "Reddit": {
        "check": check_reddit,
        "url_template": "https://www.reddit.com/user/{username}",
        "category": "Social",
    },
    "YouTube": {
        "check": check_youtube,
        "url_template": "https://www.youtube.com/@{username}",
        "category": "Social",
    },
    "TikTok": {
        "check": check_tiktok,
        "url_template": "https://www.tiktok.com/@{username}",
        "category": "Social",
    },
    "Instagram": {
        "check": check_instagram,
        "url_template": "https://www.instagram.com/{username}/",
        "category": "Social",
    },
    "X (Twitter)": {
        "check": check_x,
        "url_template": "https://x.com/{username}",
        "category": "Social",
    },
    "Twitch": {
        "check": check_twitch,
        "url_template": "https://www.twitch.tv/{username}",
        "category": "Social",
    },
    "Pinterest": {
        "check": check_pinterest,
        "url_template": "https://www.pinterest.com/{username}/",
        "category": "Social",
    },
    "Telegram": {
        "check": check_telegram,
        "url_template": "https://t.me/{username}",
        "category": "Social",
    },
    "Medium": {
        "check": check_medium,
        "url_template": "https://medium.com/@{username}",
        "category": "Creator",
    },
    "Dev.to": {
        "check": check_devto,
        "url_template": "https://dev.to/{username}",
        "category": "Creator",
    },
    "Hashnode": {
        "check": check_hashnode,
        "url_template": "https://hashnode.com/@{username}",
        "category": "Creator",
    },
    "SoundCloud": {
        "check": check_soundcloud,
        "url_template": "https://soundcloud.com/{username}",
        "category": "Creator",
    },
    "Product Hunt": {
        "check": check_producthunt,
        "url_template": "https://www.producthunt.com/@{username}",
        "category": "Creator",
    },
}
