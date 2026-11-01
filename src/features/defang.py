"""
src/features/defang.py
Safe defanging of URLs and extraction of URLs from raw email bodies.
"""

import re
from typing import List


# URL extraction regex matching http://, https://, or raw domain/path patterns
URL_REGEX = re.compile(
    r'(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]|\((?:[^\s()<>]|(?:\([^\s()<>]+\)))*\))+)'
)


def defang_url(url: str) -> str:
    """
    Safely defangs a URL to prevent accidental clicks or automatic link previews.
    Examples:
      http://evil.com/path -> hxxp://evil[.]com/path
      https://bank-login.net -> hxxps://bank-login[.]net
      ftp://server.org -> fxp://server[.]org
    """
    if not url:
        return ""
    
    # 1. Defang protocol
    defanged = re.sub(r'^https://', 'hxxps://', url, flags=re.IGNORECASE)
    defanged = re.sub(r'^http://', 'hxxp://', defanged, flags=re.IGNORECASE)
    defanged = re.sub(r'^ftp://', 'fxp://', defanged, flags=re.IGNORECASE)
    
    # If no protocol was present but starts with www, defang www
    defanged = re.sub(r'^www\.', 'w[.]w[.]w[.]', defanged, flags=re.IGNORECASE)

    # 2. Defang dots in the hostname portion
    # Split scheme from authority/path
    if '://' in defanged:
        scheme, rest = defanged.split('://', 1)
        if '/' in rest:
            host, path = rest.split('/', 1)
            host = host.replace('.', '[.]')
            defanged = f"{scheme}://{host}/{path}"
        else:
            host = rest.replace('.', '[.]')
            defanged = f"{scheme}://{host}"
    else:
        # If no scheme, split on first slash
        if '/' in defanged:
            host, path = defanged.split('/', 1)
            host = host.replace('.', '[.]')
            defanged = f"{host}/{path}"
        else:
            defanged = defanged.replace('.', '[.]')
            
    return defanged


def extract_urls_from_text(text: str) -> List[str]:
    """
    Extracts all URLs present in an email body or text blob.
    Deduplicates while preserving initial encounter order.
    """
    if not text:
        return []
    
    raw_matches = URL_REGEX.findall(text)
    urls = []
    seen = set()
    for match in raw_matches:
        # Clean trailing punctuation often caught by regex
        cleaned = re.sub(r'[.,;!?"\'>)]+$', '', match).strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            urls.append(cleaned)
    return urls

