"""
scripts/retrain_from_overrides.py
Active Learning Retraining Feedback Loop.
Extracts verified SecOps analyst overrides from SQLite, constructs an active learning
feedback dataset, fine-tunes the hybrid classifier with sample weighting, and produces
a candidate model artifact models/classifier_v2_active_learned.pkl.
"""

import os
import sys
import json
import time
import pickle
import numpy as np
import pandas as pd
from scipy.sparse import hstack, vstack
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score

# Ensure project root is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.features.lexical import batch_extract_features, FEATURE_NAMES
from src.storage.db import get_db_context
from src.storage.repositories import AuditRepository, MessageRepository


def extract_override_training_samples():
    """
    Extracts all analyst override decisions from SQLite and maps them to binary labels:
      - CONFIRMED_PHISH -> 1 (Phishing)
      - RELEASED        -> 0 (Benign)
      - RELABELED       -> Inferred from reason/context or defaulted based on override
    """
    labeled_urls = []
    
    with get_db_context() as conn:
        cursor = conn.execute("""
            SELECT o.id, o.message_id, o.reviewer_id, o.previous_status, o.new_status, o.reason, o.timestamp,
                   u.raw_url, u.normalized_url, u.registered_domain
            FROM overrides o
            JOIN extracted_urls u ON o.message_id = u.message_id
            ORDER BY o.timestamp ASC
        """)
        rows = cursor.fetchall()

    for r in rows:
        new_status = r["new_status"]
        if new_status == "CONFIRMED_PHISH":
            label = 1
        elif new_status == "RELEASED":
            label = 0
        elif new_status == "RELABELED":
            # If reason contains benign/clean/fp -> 0, else 1
            reason_lower = r["reason"].lower()
            if any(w in reason_lower for w in ["benign", "false positive", "legit", "clean", "safe"]):
                label = 0
            else:
                label = 1
        else:
            continue
            
        labeled_urls.append({
            "override_id": r["id"],
            "message_id": r["message_id"],
            "url": r["normalized_url"] or r["raw_url"],
            "host": r["registered_domain"],
            "label_binary": label,
            "reviewer": r["reviewer_id"],
            "reason": r["reason"]
        })
        
    return labeled_urls


def retrain_with_active_learning():
    print("=================================================================")
    print("     PHISHTRAP ACTIVE LEARNING RETRAINING FEEDBACK LOOP          ")
    print("=================================================================")
    
    # 1. Check for overrides in SQLite
    override_samples = extract_override_training_samples()
    print(f"[*] Extracted {len(override_samples)} verified human-in-the-loop override samples from SQLite.")

    # 2. Load existing base model and validation data
    base_model_path = os.path.join("models", "classifier.pkl")
    train_path = os.path.join("data", "processed", "train.csv")
    val_path = os.path.join("data", "processed", "val.csv")

    if not os.path.exists(base_model_path):
        raise FileNotFoundError(f"Base classifier artifact not found at {base_model_path}")
    if not os.path.exists(val_path):
        raise FileNotFoundError(f"Validation dataset not found at {val_path}")

    with open(base_model_path, "rb") as f:
        base_artifact = pickle.load(f)

    scaler = base_artifact["scaler"]
    tfidf = base_artifact["tfidf"]
    base_model = base_artifact["model"]

    val_df = pd.read_csv(val_path)
    val_y = val_df["label_binary"].values

    # Transform validation features
    print("[*] Generating validation features...")
    val_lex = batch_extract_features(val_df)
    val_lex_scaled = scaler.transform(val_lex)
    val_tfidf = tfidf.transform(val_df["norm_url"].tolist())
    X_val = hstack([val_lex_scaled, val_tfidf])

    # Base performance
    base_probs = base_model.predict_proba(X_val)[:, 1]
    base_auc = roc_auc_score(val_y, base_probs)
    base_f1 = f1_score(val_y, (base_probs >= 0.5).astype(int))
    print(f"    Base Model Validation Performance: ROC-AUC = {base_auc:.4f} | F1 = {base_f1:.4f}")

    if not override_samples:
        print("\n[!] No active overrides found in database yet.")
        print("    Submit overrides via the SOC console or API to feed the active learning loop.")
        return

    # 3. Process override samples
    override_df = pd.DataFrame(override_samples)
    override_df["norm_url"] = override_df["url"]
    override_df["path_query"] = ""
    print(f"[*] Processing {len(override_df)} human override samples:")
    print(f"    - Benign Overrides (False Positive Corrections): {int(np.sum(override_df['label_binary'] == 0))}")
    print(f"    - Threat Overrides (False Negative Corrections): {int(np.sum(override_df['label_binary'] == 1))}")

    ov_lex = batch_extract_features(override_df)
    ov_lex_scaled = scaler.transform(ov_lex)
    ov_tfidf = tfidf.transform(override_df["url"].tolist())
    X_ov = hstack([ov_lex_scaled, ov_tfidf])
    y_ov = override_df["label_binary"].values

    # 4. Load a subset of base training data to prevent catastrophic forgetting
    print("[*] Combining base training anchors with weighted human override corrections...")
    train_df = pd.read_csv(train_path).sample(n=min(25000, len(pd.read_csv(train_path))), random_state=42)
    tr_lex = batch_extract_features(train_df)
    tr_lex_scaled = scaler.transform(tr_lex)
    tr_tfidf = tfidf.transform(train_df["norm_url"].tolist())
    X_base = hstack([tr_lex_scaled, tr_tfidf])
    y_base = train_df["label_binary"].values

    # Stack datasets
    X_combined = vstack([X_base, X_ov])
    y_combined = np.concatenate([y_base, y_ov])

    # Sample weights: give human overrides 5x priority weight
    OVERRIDE_WEIGHT_MULTIPLIER = 5.0
    weights = np.concatenate([
        np.ones(len(y_base)),
        np.full(len(y_ov), OVERRIDE_WEIGHT_MULTIPLIER)
    ])

    # 5. Fit Active-Learned Retrained Model
    print("[*] Fitting active-learned candidate model with weighted overrides...")
    retrained_model = LogisticRegression(
        C=1.0,
        solver='lbfgs',
        max_iter=500,
        random_state=42
    )
    retrained_model.fit(X_combined, y_combined, sample_weight=weights)

    # 6. Evaluate Retrained Model on Validation Data
    new_probs = retrained_model.predict_proba(X_val)[:, 1]
    new_auc = float(roc_auc_score(val_y, new_probs))
    new_f1 = float(f1_score(val_y, (new_probs >= 0.5).astype(int)))
    new_prec = float(precision_score(val_y, (new_probs >= 0.5).astype(int)))
    new_rec = float(recall_score(val_y, (new_probs >= 0.5).astype(int)))

    print("\n-----------------------------------------------------------------")
    print("         ACTIVE LEARNING RETRAINING PERFORMANCE SUMMARY          ")
    print("-----------------------------------------------------------------")
    print(f"  Base Model ROC-AUC      : {base_auc:.4f}  --> Retrained: {new_auc:.4f} (Delta: {new_auc - base_auc:+.4f})")
    print(f"  Base Model F1 Score     : {base_f1:.4f}  --> Retrained: {new_f1:.4f} (Delta: {new_f1 - base_f1:+.4f})")
    print(f"  Retrained Precision     : {new_prec:.4f}")
    print(f"  Retrained Recall        : {new_rec:.4f}")

    # 7. Save Retrained Candidate Artifact
    v2_artifact = {
        "version": "2.0.0-active-learned",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "base_version": base_artifact.get("version", "1.0.0"),
        "override_samples_incorporated": len(override_samples),
        "scaler": scaler,
        "tfidf": tfidf,
        "model": retrained_model,
        "t_low": base_artifact.get("t_low", 0.05),
        "t_high": base_artifact.get("t_high", 0.85),
        "feature_names": FEATURE_NAMES
    }
    candidate_path = os.path.join("models", "classifier_v2_active_learned.pkl")
    with open(candidate_path, "wb") as f:
        pickle.dump(v2_artifact, f)

    report_path = os.path.join("models", "retraining_report.json")
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "override_samples_count": len(override_samples),
        "base_model": {
            "roc_auc": round(base_auc, 4),
            "f1": round(base_f1, 4)
        },
        "retrained_candidate": {
            "version": "2.0.0-active-learned",
            "artifact_path": candidate_path,
            "roc_auc": round(new_auc, 4),
            "f1": round(new_f1, 4),
            "precision": round(new_prec, 4),
            "recall": round(new_rec, 4),
            "delta_roc_auc": round(new_auc - base_auc, 4),
            "delta_f1": round(new_f1 - base_f1, 4)
        }
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\n[+] Active learning cycle complete!")
    print(f"    - Candidate model saved to: {candidate_path}")
    print(f"    - Retraining report saved to: {report_path}")


if __name__ == "__main__":
    retrain_with_active_learning()
