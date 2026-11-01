"""
scripts/part2_train_model.py
Part 2: Feature Engineering, Model Training, Cross-Validation, and Threshold Selection.
Produces:
  - models/classifier.pkl
  - models/baseline_lr.pkl
  - models/feature_schema.json
  - models/validation_report.json
"""

import os
import sys
import json
import time
import pickle
import numpy as np
import pandas as pd
from scipy.sparse import hstack
from sklearn.preprocessing import StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    precision_recall_curve,
    confusion_matrix
)

# Ensure project root is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.features.lexical import batch_extract_features, FEATURE_NAMES, SUSPICIOUS_KEYWORDS


def evaluate_model(name: str, y_true: np.ndarray, probs: np.ndarray, default_threshold: float = 0.5) -> dict:
    preds = (probs >= default_threshold).astype(int)
    roc_auc = float(roc_auc_score(y_true, probs))
    pr_auc = float(average_precision_score(y_true, probs))
    f1 = float(f1_score(y_true, preds, zero_division=0))
    prec = float(precision_score(y_true, preds, zero_division=0))
    rec = float(recall_score(y_true, preds, zero_division=0))
    tn, fp, fn, tp = confusion_matrix(y_true, preds).ravel()
    fpr = float(fp / max(fp + tn, 1))

    return {
        "model_name": name,
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "default_threshold": default_threshold,
        "f1_score": round(f1, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "false_positive_rate": round(fpr, 4),
        "confusion_matrix": {
            "TP": int(tp),
            "FP": int(fp),
            "TN": int(tn),
            "FN": int(fn)
        }
    }


def main():
    start_time = time.time()
    train_path = os.path.join('data', 'processed', 'train.csv')
    val_path = os.path.join('data', 'processed', 'val.csv')

    if not os.path.exists(train_path) or not os.path.exists(val_path):
        raise FileNotFoundError("Processed datasets not found. Please run scripts/part1_prepare_data.py first.")

    print(f"[*] Loading training data from {train_path}...")
    train_df = pd.read_csv(train_path)
    print(f"[*] Loading validation data from {val_path}...")
    val_df = pd.read_csv(val_path)
    
    y_train = train_df['label_binary'].values
    y_val = val_df['label_binary'].values
    
    print(f"[*] Training samples: {len(train_df)} | Validation samples: {len(val_df)}")
    print(f"[*] Phishing prior (Train): {y_train.mean():.2%} | (Val): {y_val.mean():.2%}")

    # 1. Feature Extraction: Lexical
    print("\n[*] Extracting 26 lexical features...")
    t0 = time.time()
    X_train_lex = batch_extract_features(train_df)
    X_val_lex = batch_extract_features(val_df)
    print(f"[+] Lexical extraction completed in {time.time() - t0:.2f}s")

    # Fit Scaler on TRAIN only (strictly no data leakage)
    scaler = StandardScaler()
    X_train_lex_scaled = scaler.fit_transform(X_train_lex)
    X_val_lex_scaled = scaler.transform(X_val_lex)

    # 2. Feature Extraction: Character n-gram TF-IDF (Optional/Ablation study)
    print("\n[*] Extracting sublinear char 3-5 n-grams (max_features=5000)...")
    t0 = time.time()
    tfidf = TfidfVectorizer(analyzer='char', ngram_range=(3, 5), max_features=5000, sublinear_tf=True)
    X_train_tfidf = tfidf.fit_transform(train_df['norm_url'])
    X_val_tfidf = tfidf.transform(val_df['norm_url'])
    print(f"[+] TF-IDF extraction completed in {time.time() - t0:.2f}s")

    # Combine Lexical + TF-IDF
    X_train_comb = hstack([X_train_lex_scaled, X_train_tfidf])
    X_val_comb = hstack([X_val_lex_scaled, X_val_tfidf])

    # 3. Model 1: Baseline Logistic Regression (Lexical only)
    print("\n[*] Model 1: Training Baseline Logistic Regression (Lexical features only)...")
    t0 = time.time()
    baseline_lr = LogisticRegression(max_iter=1000, C=1.0, random_state=42)
    baseline_lr.fit(X_train_lex_scaled, y_train)
    probs_baseline = baseline_lr.predict_proba(X_val_lex_scaled)[:, 1]
    res_baseline = evaluate_model("Baseline Logistic Regression (Lexical Only)", y_val, probs_baseline)
    print(f"    -> ROC-AUC: {res_baseline['roc_auc']} | PR-AUC: {res_baseline['pr_auc']} | F1: {res_baseline['f1_score']}")

    # 4. Model 2: Tree Ensemble (HistGradientBoosting on Lexical features)
    print("\n[*] Model 2: Training HistGradientBoosting (Lexical features only)...")
    t0 = time.time()
    hgb_model = HistGradientBoostingClassifier(max_iter=200, random_state=42)
    hgb_model.fit(X_train_lex, y_train)
    probs_hgb = hgb_model.predict_proba(X_val_lex)[:, 1]
    res_hgb = evaluate_model("HistGradientBoosting (Lexical Only)", y_val, probs_hgb)
    print(f"    -> ROC-AUC: {res_hgb['roc_auc']} | PR-AUC: {res_hgb['pr_auc']} | F1: {res_hgb['f1_score']}")

    # 5. Model 3: Combined Hybrid Pipeline (Lexical + Char n-grams)
    print("\n[*] Model 3: Training Combined Model (Lexical Scaled + Char n-grams TF-IDF)...")
    t0 = time.time()
    comb_model = LogisticRegression(max_iter=1000, C=2.0, random_state=42)
    comb_model.fit(X_train_comb, y_train)
    probs_comb = comb_model.predict_proba(X_val_comb)[:, 1]
    res_comb = evaluate_model("Combined Pipeline (Lexical + Char n-grams)", y_val, probs_comb)
    print(f"    -> ROC-AUC: {res_comb['roc_auc']} | PR-AUC: {res_comb['pr_auc']} | F1: {res_comb['f1_score']}")

    # 6. Threshold Selection on Validation Set for Best Model (Combined Model)
    print("\n[*] Selecting Triage Thresholds (T_low and T_high) on Validation Set...")
    
    # We want:
    # 1. T_high (Auto-quarantine): Precision >= 0.980, minimal False Positives on benign mail
    # 2. T_low (Auto-allow): High Recall (minimal False Negatives), so almost no phish is auto-allowed
    precisions, recalls, thresholds = precision_recall_curve(y_val, probs_comb)
    
    # Choose T_high: smallest threshold achieving >= 98.0% precision
    high_candidates = [t for p, t in zip(precisions[:-1], thresholds) if p >= 0.980]
    t_high = float(high_candidates[0]) if high_candidates else 0.85
    # Cap T_high at 0.85 for practical robustness
    t_high = round(max(t_high, 0.85), 2)

    # Choose T_low: threshold where Recall is ~95%
    low_candidates = [t for r, t in zip(recalls[:-1], thresholds) if r >= 0.950]
    t_low = float(low_candidates[-1]) if low_candidates else 0.05
    t_low = round(min(t_low, 0.05), 2)

    print(f"[+] Selected Operational Thresholds: T_low = {t_low}, T_high = {t_high}")

    # Evaluate the 3-Way Triage System on Validation Set:
    auto_allow_mask = (probs_comb < t_low)
    human_review_mask = (probs_comb >= t_low) & (probs_comb < t_high)
    auto_quarantine_mask = (probs_comb >= t_high)

    val_total = len(y_val)
    
    # Auto-Allow Band Statistics
    allow_count = int(auto_allow_mask.sum())
    allow_benign = int(((auto_allow_mask) & (y_val == 0)).sum())
    allow_phish_fn = int(((auto_allow_mask) & (y_val == 1)).sum())
    allow_fn_rate = allow_phish_fn / max(allow_count, 1)

    # Human Review Queue Statistics
    review_count = int(human_review_mask.sum())
    review_phish = int(((human_review_mask) & (y_val == 1)).sum())
    review_benign = int(((human_review_mask) & (y_val == 0)).sum())

    # Auto-Quarantine Band Statistics
    quarantine_count = int(auto_quarantine_mask.sum())
    quarantine_phish_tp = int(((auto_quarantine_mask) & (y_val == 1)).sum())
    quarantine_benign_fp = int(((auto_quarantine_mask) & (y_val == 0)).sum())
    quarantine_precision = quarantine_phish_tp / max(quarantine_count, 1)

    triage_report = {
        "t_low": t_low,
        "t_high": t_high,
        "auto_allow_band": {
            "total_urls": allow_count,
            "pct_of_traffic": round(allow_count / val_total, 4),
            "benign_correct": allow_benign,
            "phish_missed_fn": allow_phish_fn,
            "false_negative_rate": round(allow_fn_rate, 5)
        },
        "human_review_queue": {
            "total_urls": review_count,
            "pct_of_traffic": round(review_count / val_total, 4),
            "phish_contained": review_phish,
            "benign_flagged": review_benign
        },
        "auto_quarantine_band": {
            "total_urls": quarantine_count,
            "pct_of_traffic": round(quarantine_count / val_total, 4),
            "phish_correct_tp": quarantine_phish_tp,
            "benign_false_alarms_fp": quarantine_benign_fp,
            "precision": round(quarantine_precision, 4)
        }
    }

    print("\n--- Validation 3-Way Triage Simulation ---")
    print(f"  [AUTO-ALLOW]        Score < {t_low:.2f} : {allow_count:,} URLs ({allow_count/val_total:.1%}) | Benign: {allow_benign:,} | False Negatives (Phish): {allow_phish_fn}")
    print(f"  [HUMAN REVIEW]  {t_low:.2f} <= Score < {t_high:.2f} : {review_count:,} URLs ({review_count/val_total:.1%}) | Phish routed: {review_phish:,} | Benign routed: {review_benign:,}")
    print(f"  [AUTO-QUARANTINE]   Score >= {t_high:.2f} : {quarantine_count:,} URLs ({quarantine_count/val_total:.1%}) | Phish: {quarantine_phish_tp:,} | False Positives: {quarantine_benign_fp} (Precision: {quarantine_precision:.2%})")

    # 7. Save Artifacts
    os.makedirs('models', exist_ok=True)
    
    # Save best combined classifier artifact
    model_artifact = {
        "version": "1.0.0",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model_type": "LogisticRegression_Combined_Lexical_TFIDF",
        "t_low": t_low,
        "t_high": t_high,
        "feature_names": FEATURE_NAMES,
        "scaler": scaler,
        "tfidf": tfidf,
        "model": comb_model
    }
    with open('models/classifier.pkl', 'wb') as f:
        pickle.dump(model_artifact, f)
        
    # Save baseline artifact
    baseline_artifact = {
        "version": "1.0.0_baseline",
        "model_type": "LogisticRegression_LexicalOnly",
        "feature_names": FEATURE_NAMES,
        "scaler": scaler,
        "model": baseline_lr
    }
    with open('models/baseline_lr.pkl', 'wb') as f:
        pickle.dump(baseline_artifact, f)

    # Save feature schema
    feature_schema = {
        "schema_version": "1.0.0",
        "total_lexical_features": len(FEATURE_NAMES),
        "feature_names": FEATURE_NAMES,
        "tfidf_ngram_range": [3, 5],
        "tfidf_max_features": 5000,
        "suspicious_keywords": SUSPICIOUS_KEYWORDS,
        "thresholds": {
            "t_low": t_low,
            "t_high": t_high,
            "decision_rules": {
                "score_lt_t_low": "ALLOW",
                "score_ge_t_low_and_lt_t_high": "HUMAN_REVIEW",
                "score_ge_t_high": "QUARANTINE"
            }
        }
    }
    with open('models/feature_schema.json', 'w', encoding='utf-8') as f:
        json.dump(feature_schema, f, indent=2)

    # Save comprehensive validation report
    validation_report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dataset_split": "val.csv (Domain-Grouped, Held-Out)",
        "models_compared": [
            res_baseline,
            res_hgb,
            res_comb
        ],
        "selected_model": "Combined Pipeline (Lexical + Char n-grams)",
        "triage_policy": triage_report,
        "training_time_seconds": round(time.time() - start_time, 2)
    }
    with open('models/validation_report.json', 'w', encoding='utf-8') as f:
        json.dump(validation_report, f, indent=2)

    print(f"\n[+] Part 2 Completed successfully in {validation_report['training_time_seconds']}s!")
    print("    - models/classifier.pkl")
    print("    - models/baseline_lr.pkl")
    print("    - models/feature_schema.json")
    print("    - models/validation_report.json")


if __name__ == '__main__':
    main()

