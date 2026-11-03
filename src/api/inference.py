"""
src/api/inference.py
Deterministic model loading, scoring, and explainability for URL analysis.
"""

import os
import pickle
import numpy as np
from typing import List, Dict, Any, Tuple
from scipy.sparse import hstack
import tldextract

from src.features.lexical import normalize_url, batch_extract_features, FEATURE_NAMES
from src.features.defang import defang_url

_extractor = tldextract.TLDExtract(suffix_list_urls=None, include_psl_private_domains=True)

MODEL_PATH = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
    "models",
    "classifier.pkl"
)

DEFAULT_T_LOW = 0.05
DEFAULT_T_HIGH = 0.85

_MODEL_ARTIFACT = None


def get_model_artifact(model_path: str = None) -> dict:
    """
    Loads and caches the trained hybrid classifier artifact.
    """
    global _MODEL_ARTIFACT
    if _MODEL_ARTIFACT is not None and model_path is None:
        return _MODEL_ARTIFACT

    path = model_path or os.getenv("PHISHTRAP_MODEL_PATH", MODEL_PATH)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Model artifact not found at {path}. Run scripts/part2_train_model.py first.")

    with open(path, "rb") as f:
        artifact = pickle.load(f)

    if model_path is None:
        _MODEL_ARTIFACT = artifact
    return artifact


def explain_url_features(
    feature_values: np.ndarray,
    scaled_features: np.ndarray,
    lex_coefs: np.ndarray,
    feature_names: List[str],
    top_k: int = 3
) -> List[str]:
    """
    Identifies the top contributing lexical features using linear model weights.
    Contribution = scaled_feature_value * coefficient.
    """
    contributions = scaled_features * lex_coefs
    # Sort descending by positive contribution to phishing probability
    sorted_indices = np.argsort(-contributions)
    
    explanations = []
    for idx in sorted_indices[:top_k]:
        feat_name = feature_names[idx]
        raw_val = feature_values[idx]
        contrib = contributions[idx]
        
        # Format neatly
        if isinstance(raw_val, float):
            val_str = f"{raw_val:.2f}"
        else:
            val_str = str(int(raw_val))
            
        sign = "+" if contrib >= 0 else ""
        explanations.append(f"{feat_name}={val_str} ({sign}{contrib:.2f})")
        
    return explanations


def score_urls(raw_urls: List[str], model_artifact: dict = None) -> Tuple[List[Dict[str, Any]], float, str]:
    """
    Scores a collection of raw URLs and computes message-level triage decision.
    
    Returns:
      (urls_scored, max_score, decision)
    """
    if not raw_urls:
        return [], 0.0, "ALLOW"

    artifact = model_artifact or get_model_artifact()
    scaler = artifact["scaler"]
    tfidf = artifact["tfidf"]
    model = artifact["model"]
    t_low = artifact.get("t_low", DEFAULT_T_LOW)
    t_high = artifact.get("t_high", DEFAULT_T_HIGH)
    feature_names = artifact.get("feature_names", FEATURE_NAMES)

    # 1. Normalise URLs
    normalized_list = []
    hosts = []
    reg_domains = []
    path_queries = []

    for raw_u in raw_urls:
        norm_u, host, reg_dom, pq = normalize_url(raw_u)
        if norm_u is None:
            # Fallback for irregular strings
            norm_u = raw_u.strip()
            ext = _extractor(norm_u)
            host = ext.fqdn or "unknown"
            reg_dom = ext.registered_domain or host
            pq = ""
        normalized_list.append(norm_u)
        hosts.append(host)
        reg_domains.append(reg_dom)
        path_queries.append(pq or "")

    # 2. Extract lexical features & scale
    tuple_data = list(zip(normalized_list, hosts, path_queries))
    df_lex = batch_extract_features(tuple_data)
    X_lex = df_lex.values
    X_lex_scaled = scaler.transform(df_lex)

    # 3. Transform character n-grams TF-IDF
    X_tfidf = tfidf.transform(normalized_list)

    # 4. Combine representations and predict probabilities
    X_comb = hstack([X_lex_scaled, X_tfidf])
    probs = model.predict_proba(X_comb)[:, 1]

    # Model coefficients for lexical part
    lex_coefs = model.coef_[0][:len(feature_names)]

    scored_records = []
    for i, raw_u in enumerate(raw_urls):
        score = float(round(probs[i], 4))
        top_features = explain_url_features(
            feature_values=X_lex[i],
            scaled_features=X_lex_scaled[i],
            lex_coefs=lex_coefs,
            feature_names=feature_names,
            top_k=3
        )

        scored_records.append({
            "raw_url": raw_u,
            "defanged_url": defang_url(raw_u),
            "normalized_url": normalized_list[i],
            "registered_domain": reg_domains[i],
            "score": score,
            "top_features": top_features
        })

    max_score = max(r["score"] for r in scored_records) if scored_records else 0.0

    # Strict Dual-Threshold Triage Policy
    if max_score >= t_high:
        decision = "QUARANTINE"
    elif max_score < t_low:
        decision = "ALLOW"
    else:
        decision = "HUMAN_REVIEW"

    return scored_records, max_score, decision
