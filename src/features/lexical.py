"""
src/features/lexical.py
Deterministic lexical feature extraction for URL security classification.
Provides:
  - extract_lexical_features(norm_url, host, path_query) -> Dict[str, float]
  - batch_extract_features(df) -> pd.DataFrame
  - FEATURE_NAMES -> List[str]
"""

import re
import math
from collections import Counter
from typing import Dict, List, Any
import pandas as pd
import numpy as np

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


def shannon_entropy(s: str) -> float:
    """Calculates Shannon entropy in bits per character."""
    if not s:
        return 0.0
    counts = Counter(s)
    total = len(s)
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


def extract_lexical_features(norm_url: str, host: str, path_query: str = "") -> Dict[str, Any]:
    """
    Extracts a dictionary of 26 lexical, structural, and information-theoretic features.
    """
    norm_url = norm_url or ""
    host = host or ""
    path_query = path_query or ""
    
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


def batch_extract_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    High-performance vector extraction for pandas DataFrames.
    """
    urls = df['norm_url'].fillna('').tolist()
    hosts = df['host'].fillna('').tolist()
    pqs = df['path_query'].fillna('').tolist()
    
    data = {}
    data['url_len'] = [len(u) for u in urls]
    data['host_len'] = [len(h) for h in hosts]
    data['pq_len'] = [len(pq) for pq in pqs]
    data['num_dots'] = [u.count('.') for u in urls]
    data['num_hyphens'] = [u.count('-') for u in urls]
    data['num_underscores'] = [u.count('_') for u in urls]
    data['num_slashes'] = [u.count('/') for u in urls]
    data['num_questionmarks'] = [u.count('?') for u in urls]
    data['num_equals'] = [u.count('=') for u in urls]
    data['num_at'] = [u.count('@') for u in urls]
    data['num_amp'] = [u.count('&') for u in urls]
    data['num_percent'] = [u.count('%') for u in urls]
    
    data['num_digits'] = [sum(c.isdigit() for c in u) for u in urls]
    data['digit_ratio'] = [d / max(l, 1) for d, l in zip(data['num_digits'], data['url_len'])]
    data['letter_ratio'] = [sum(c.isalpha() for c in u) / max(l, 1) for u, l in zip(urls, data['url_len'])]
    
    data['host_num_dots'] = [h.count('.') for h in hosts]
    data['host_num_hyphens'] = [h.count('-') for h in hosts]
    data['host_has_ip'] = [1 if bool(IPV4_REGEX.match(h)) else 0 for h in hosts]
    data['subdomain_depth'] = [max(0, d - 1) if not ip else 0 for d, ip in zip(data['host_num_dots'], data['host_has_ip'])]
    
    data['entropy_url'] = [shannon_entropy(u) for u in urls]
    data['entropy_host'] = [shannon_entropy(h) for h in hosts]
    
    data['kw_count'] = [len(KW_REGEX.findall(u)) for u in urls]
    data['has_hex'] = [1 if ('%' in u and bool(HEX_REGEX.search(u))) else 0 for u in urls]
    data['punycode'] = [1 if 'xn--' in h else 0 for h in hosts]
    
    data['pq_num_digits'] = [sum(c.isdigit() for c in pq) for pq in pqs]
    data['pq_digit_ratio'] = [d / max(l, 1) for d, l in zip(data['pq_num_digits'], data['pq_len'])]
    
    return pd.DataFrame(data, columns=FEATURE_NAMES)

