from urllib.parse import urlparse
import requests


def validate_url(url: str) -> tuple[bool, str]:
    if not url or not url.strip():
        return False, "Please enter a URL."
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return False, "Could not parse the URL."
    if parsed.scheme not in ("http", "https"):
        return False, "URL must start with http:// or https://"
    if not parsed.netloc:
        return False, "URL is missing a domain name."
    return True, ""


def check_url_accessible(url: str, timeout: int = 8) -> tuple[bool, str]:
    try:
        response = requests.head(url.strip(), timeout=timeout, allow_redirects=True)
        if response.status_code >= 400:
            return False, f"URL returned status {response.status_code} — check the link and try again."
        return True, ""
    except requests.exceptions.ConnectionError:
        return False, "Could not connect to the URL. Check your internet connection or the link."
    except requests.exceptions.Timeout:
        return False, "URL took too long to respond. Try again or use a different link."
    except Exception as e:
        return False, f"Could not reach URL: {e}"
