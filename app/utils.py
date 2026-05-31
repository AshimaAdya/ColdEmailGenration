import re
import requests
from bs4 import BeautifulSoup

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def scrape_url(url: str, timeout: int = 15) -> tuple[str, str]:
    """
    Fetch page content with browser-like headers.
    Returns (cleaned_text, warning_message).
    warning_message is empty string if scraping was successful.
    Only raises ValueError if the page could not be fetched at all.
    """
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator=" ")
    except requests.RequestException as e:
        raise ValueError(f"Could not fetch the page: {e}")

    cleaned = truncate_text(clean_text(text))

    warning = ""
    if len(cleaned) < 300:
        warning = (
            "Limited content was extracted from this URL (the site may restrict access). "
            "The email will be generated with available information. "
            "For best results, paste the job description directly."
        )

    return cleaned, warning

# ~4 chars/token; 6 000 tokens leaves headroom for the prompt on the 12k TPM tier
_MAX_CHARS = 24_000

def truncate_text(text: str, max_chars: int = _MAX_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_space = truncated.rfind(" ")
    return truncated[:last_space] if last_space > 0 else truncated

def clean_text(text):
    # Remove HTML tags
    text = re.sub(r'<[^>]*?>', '', text)
    # Remove URLs
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    # Remove special characters
    text = re.sub(r'[^a-zA-Z0-9 ]', '', text)
    # Replace multiple spaces with a single space
    text = re.sub(r'\s{2,}', ' ', text)
    # Trim leading and trailing whitespace
    text = text.strip()
    # Remove extra whitespace
    text = ' '.join(text.split())
    return text