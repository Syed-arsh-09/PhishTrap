"""
tests/test_features.py
Unit tests for lexical feature extraction and model inference consistency.
"""

import os
import pickle
from src.features.lexical import extract_lexical_features, shannon_entropy, FEATURE_NAMES


def test_shannon_entropy():
    # Constant string has 0 entropy
    assert shannon_entropy("aaaaa") == 0.0
    # Empty string has 0 entropy
    assert shannon_entropy("") == 0.0
    # Higher diversity has higher entropy
    assert shannon_entropy("abcdef") > shannon_entropy("aabbaa")


def test_extract_lexical_features_structure():
    url = "secure-login.pages.dev/banking/update?id=123"
    host = "secure-login.pages.dev"
    pq = "/banking/update?id=123"
    
    feats = extract_lexical_features(url, host, pq)
    
    assert isinstance(feats, dict)
    assert len(feats) == len(FEATURE_NAMES)
    for name in FEATURE_NAMES:
        assert name in feats, f"Missing feature {name}"
        assert isinstance(feats[name], (int, float)), f"Feature {name} is not numeric"
        
    # Check expected specific values
    assert feats['url_len'] == len(url)
    assert feats['host_len'] == len(host)
    assert feats['pq_len'] == len(pq)
    assert feats['kw_count'] >= 3  # secure, login, update, banking
    assert feats['host_has_ip'] == 0


def test_extract_ip_in_host():
    feats = extract_lexical_features("192.168.1.1/login", "192.168.1.1", "/login")
    assert feats['host_has_ip'] == 1
    assert feats['subdomain_depth'] == 0


def test_model_artifact_loading():
    model_path = os.path.join("models", "classifier.pkl")
    assert os.path.exists(model_path), "Model artifact does not exist"
    
    with open(model_path, "rb") as f:
        artifact = pickle.load(f)
        
    assert "model" in artifact
    assert "scaler" in artifact
    assert "tfidf" in artifact
    assert "t_low" in artifact
    assert "t_high" in artifact
    assert artifact["t_low"] < artifact["t_high"]

