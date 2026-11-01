"""
src/features/lexical.py
Deterministic lexical feature extraction for URL security classification.
Provides:
  - normalize_url(raw_url) -> Tuple[norm_url, host, reg_domain, path_query]
  - extract_lexical_features(norm_url, host, path_query) -> Dict[str, float]
  - batch_extract_features(data) -> pd.DataFrame
  - FEATURE_NAMES -> List[str]
"""

import re
import html
import math
from typing import Dict, List, Any, Tuple, Optional, Union
import pandas as pd
import numpy as np
import tldextract

_extract_tld = tldextract.TLDExtract(suffix_list_urls=None, include_psl_private_domains=True)

SUSPICIOUS_KEYWORDS = [
    'verify', 'login', 'signin', 'update', 'secure', 'account',
    'banking', 'confirm', 'wallet', 'admin', 'service', 'support',
    'password', 'auth', 'token', 'security', 'billing', 'recovery'
]

KW_REGEX = re.compile('|'.join(SUSPICIOUS_KEYWORDS), re.IGNORECASE)
HEX_REGEX = re.compile(r'%[0-9a-fA-F]{2}')
IPV4_REGEX = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')

FEATURE_NAMES = [
    'url_len',
    'host_len',
    'pq_len',
    'num_dots',
    'num_hyphens',
    'num_underscores',
    'num_slashes',
    'num_questionmarks',
    'num_equals',
    'num_at',
    'num_amp',
    'num_percent',
    'num_digits',
    'digit_ratio',
    'letter_ratio',
    'host_num_dots',
    'host_num_hyphens',
    'host_has_ip',
    'subdomain_depth',
    'entropy_url',
    'entropy_host',
    'kw_count',
    'has_hex',
    'punycode',
    'pq_num_digits',
    'pq_digit_ratio'
]


def normalize_url(raw_url: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Normalizes a URL by:
      - HTML unescaping (&amp; -> &)
      - Stripping scheme (http://, https://, etc.)
      - Stripping userinfo (user:pass@)
      - Stripping port (:8080)
      - Stripping leading www. or www[0-9].
      - Stripping fragment (#...)
      - Stripping trailing slash
    Returns:
      (normalized_url, host, registered_domain, path_query)
    """
    if not isinstance(raw_url, str) or not raw_url.strip():
        return None, None, None, None

    u = html.unescape(raw_url.strip())
    # Strip scheme
    u = re.sub(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', '', u)
    # Strip userinfo
    u = re.sub(r'^[^/@]+@', '', u)
    
    # Split host and path/query/fragment
    m = re.match(r'^([^/?#]+)(.*)$', u)
    if not m:
        return None, None, None, None

    host_port, remainder = m.group(1), m.group(2)
    
    # Strip port
    host = re.sub(r':[0-9]+$', '', host_port).lower()
    # Strip leading www
    host = re.sub(r'^www\d*\.', '', host)
    if not host or ('.' not in host and not IPV4_REGEX.match(host)):
        if host != 'localhost':
            return None, None, None, None

    # Clean remainder: strip fragment and trailing slashes
    remainder = re.sub(r'#.*$', '', remainder)
    remainder = remainder.rstrip('/')
    
    norm = (host + remainder).rstrip('/')
    if not norm:
        return None, None, None, None

    tld_res = _extract_tld(host)
    reg_domain = (
        getattr(tld_res, 'top_domain_under_public_suffix', None)
        or tld_res.domain
        or host
    )
    
    return norm, host, reg_domain, remainder


def shannon_entropy(s: str) -> float:
    """Calculates Shannon entropy in bits per character."""
    if not s:
        return 0.0
    length = len(s)
    counts = {}
    for c in s:
        counts[c] = counts.get(c, 0) + 1
    entropy = 0.0
    for count in counts.values():
        p = count / length
        entropy -= p * math.log2(p)
    return entropy


def extract_lexical_features(norm_url: str, host: str, path_query: str) -> Dict[str, float]:
    """
    Deterministic extraction of 26 lexical features for an individual URL.
    """
    url_len = len(norm_url)
    host_len = len(host)
    pq_len = len(path_query)
    
    num_dots = norm_url.count('.')
    num_hyphens = norm_url.count('-')
    num_underscores = norm_url.count('_')
    num_slashes = norm_url.count('/')
    num_questionmarks = norm_url.count('?')
    num_equals = norm_url.count('=')
    num_at = norm_url.count('@')
    num_amp = norm_url.count('&')
    num_percent = norm_url.count('%')
    
    num_digits = sum(c.isdigit() for c in norm_url)
    num_letters = sum(c.isalpha() for c in norm_url)
    digit_ratio = num_digits / max(url_len, 1)
    letter_ratio = num_letters / max(url_len, 1)
    
    host_num_dots = host.count('.')
    host_num_hyphens = host.count('-')
    host_has_ip = 1 if bool(IPV4_REGEX.match(host)) else 0
    subdomain_depth = max(0, host_num_dots - 1) if not host_has_ip else 0
    
    entropy_url = shannon_entropy(norm_url)
    entropy_host = shannon_entropy(host)
    
    kw_count = len(KW_REGEX.findall(norm_url))
    has_hex = 1 if ('%' in norm_url and bool(HEX_REGEX.search(norm_url))) else 0
    punycode = 1 if 'xn--' in host else 0
    
    pq_num_digits = sum(c.isdigit() for c in path_query)
    pq_digit_ratio = pq_num_digits / max(pq_len, 1)
    
    return {
        'url_len': url_len,
        'host_len': host_len,
        'pq_len': pq_len,
        'num_dots': num_dots,
        'num_hyphens': num_hyphens,
        'num_underscores': num_underscores,
        'num_slashes': num_slashes,
        'num_questionmarks': num_questionmarks,
        'num_equals': num_equals,
        'num_at': num_at,
        'num_amp': num_amp,
        'num_percent': num_percent,
        'num_digits': num_digits,
        'digit_ratio': round(digit_ratio, 4),
        'letter_ratio': round(letter_ratio, 4),
        'host_num_dots': host_num_dots,
        'host_num_hyphens': host_num_hyphens,
        'host_has_ip': host_has_ip,
        'subdomain_depth': subdomain_depth,
        'entropy_url': round(entropy_url, 4),
        'entropy_host': round(entropy_host, 4),
        'kw_count': kw_count,
        'has_hex': has_hex,
        'punycode': punycode,
        'pq_num_digits': pq_num_digits,
        'pq_digit_ratio': round(pq_digit_ratio, 4)
    }


def batch_extract_features(data: Union[pd.DataFrame, List[Tuple[str, str, str]]]) -> pd.DataFrame:
    """
    High-performance vector extraction. Accepts either a pandas DataFrame
    with ['norm_url', 'host', 'path_query'] or a list of (norm_url, host, path_query) tuples.
    """
    if isinstance(data, pd.DataFrame):
        urls = data['norm_url'].fillna('').tolist()
        hosts = data['host'].fillna('').tolist()
        pqs = data['path_query'].fillna('').tolist()
    else:
        urls = [item[0] or '' for item in data]
        hosts = [item[1] or '' for item in data]
        pqs = [item[2] or '' for item in data]
    
    res = {}
    res['url_len'] = [len(u) for u in urls]
    res['host_len'] = [len(h) for h in hosts]
    res['pq_len'] = [len(pq) for pq in pqs]
    res['num_dots'] = [u.count('.') for u in urls]
    res['num_hyphens'] = [u.count('-') for u in urls]
    res['num_underscores'] = [u.count('_') for u in urls]
    res['num_slashes'] = [u.count('/') for u in urls]
    res['num_questionmarks'] = [u.count('?') for u in urls]
    res['num_equals'] = [u.count('=') for u in urls]
    res['num_at'] = [u.count('@') for u in urls]
    res['num_amp'] = [u.count('&') for u in urls]
    res['num_percent'] = [u.count('%') for u in urls]
    
    res['num_digits'] = [sum(c.isdigit() for c in u) for u in urls]
    res['digit_ratio'] = [d / max(l, 1) for d, l in zip(res['num_digits'], res['url_len'])]
    res['letter_ratio'] = [sum(c.isalpha() for c in u) / max(l, 1) for u, l in zip(urls, res['url_len'])]
    
    res['host_num_dots'] = [h.count('.') for h in hosts]
    res['host_num_hyphens'] = [h.count('-') for h in hosts]
    res['host_has_ip'] = [1 if bool(IPV4_REGEX.match(h)) else 0 for h in hosts]
    res['subdomain_depth'] = [max(0, d - 1) if not ip else 0 for d, ip in zip(res['host_num_dots'], res['host_has_ip'])]
    
    res['entropy_url'] = [shannon_entropy(u) for u in urls]
    res['entropy_host'] = [shannon_entropy(h) for h in hosts]
    
    res['kw_count'] = [len(KW_REGEX.findall(u)) for u in urls]
    res['has_hex'] = [1 if ('%' in u and bool(HEX_REGEX.search(u))) else 0 for u in urls]
    res['punycode'] = [1 if 'xn--' in h else 0 for h in hosts]
    
    res['pq_num_digits'] = [sum(c.isdigit() for c in pq) for pq in pqs]
    res['pq_digit_ratio'] = [d / max(l, 1) for d, l in zip(res['pq_num_digits'], res['pq_len'])]
    
    return pd.DataFrame(res, columns=FEATURE_NAMES)
