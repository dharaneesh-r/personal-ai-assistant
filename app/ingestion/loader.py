from pathlib import Path

import requests
from bs4 import BeautifulSoup


def load_txt(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def load_pdf(path: str) -> str:
    from PyPDF2 import PdfReader
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def load_docx(path: str) -> str:
    from docx import Document
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

_BLOCKED_HINTS = {
    "login", "signin", "sign-in", "auth", "authenticate",
    "access denied", "forbidden", "bot detected", "captcha",
    "cloudflare", "please enable javascript",
}


def load_url(url: str) -> str:
    try:
        response = requests.get(url, timeout=15, headers=_BROWSER_HEADERS)
    except requests.exceptions.ConnectionError:
        raise ValueError(f"Could not connect to {url}. Check the URL and your internet connection.")
    except requests.exceptions.Timeout:
        raise ValueError(f"Request timed out after 15 seconds for {url}.")

    if response.status_code == 401:
        raise ValueError(
            f"This URL requires login (401 Unauthorized). "
            "Copy the page text manually and use the Text tab instead."
        )
    if response.status_code == 403:
        raise ValueError(
            f"Access denied (403 Forbidden) — {url} blocks automated scrapers. "
            "Common causes: Cloudflare protection, login required, or JavaScript-only rendering. "
            "Tip: copy the page content manually and paste it in the Text tab."
        )
    if response.status_code == 404:
        raise ValueError(f"Page not found (404) — {url}")

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)

    # Detect pages that rendered a login wall or JS-only shell — try Jina Reader fallback
    text_lower = text.lower()
    if len(text) < 200 or any(h in text_lower for h in _BLOCKED_HINTS):
        return _load_url_via_jina(url)

    return text


def _load_url_via_jina(url: str) -> str:
    """Fallback scraper using Jina Reader (r.jina.ai) — handles JS-rendered pages."""
    jina_url = f"https://r.jina.ai/{url}"
    try:
        response = requests.get(jina_url, timeout=20, headers={"Accept": "text/plain"})
    except Exception as e:
        raise ValueError(
            f"Could not fetch {url} directly or via Jina Reader. "
            "The page may require a login. Copy the content manually and paste it in the Text tab."
        )

    if response.status_code != 200:
        raise ValueError(
            f"The page at {url} could not be read (tried direct scraping and Jina Reader). "
            "Copy the content manually and paste it in the Text tab."
        )

    text = response.text.strip()
    if len(text) < 200:
        raise ValueError(
            f"The page at {url} returned almost no readable text even via Jina Reader. "
            "It may require a login. Copy the content manually and paste it in the Text tab."
        )
    return text


def load_file(path: str) -> str:
    suffix = Path(path).suffix.lower()
    loaders = {".txt": load_txt, ".pdf": load_pdf, ".docx": load_docx}
    if suffix not in loaders:
        raise ValueError(f"Unsupported file type: {suffix}. Supported: .txt, .pdf, .docx")
    return loaders[suffix](path)
