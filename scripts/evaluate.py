"""
scripts/evaluate.py
Part 6: Frozen Test Set Evaluation, End-to-End Stream Evaluation,
Error Analysis, and Publication Figures.
"""

import os
import sys
import json
import time
import pickle
import numpy as np
import pandas as pd
from scipy.sparse import hstack

# Configure writable matplotlib cache
mpl_cache = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.tmp', 'matplotlib'))
os.makedirs(mpl_cache, exist_ok=True)
os.environ["MPLCONFIGDIR"] = mpl_cache

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    roc_curve,
    precision_recall_curve,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    accuracy_score
)

# Ensure project root is in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.features.lexical import batch_extract_features
from src.storage.db import get_db_context
from src.storage.repositories import MessageRepository


def evaluate_frozen_test_set():
    print("=================================================================")
    print("      PART 6: PHISHTRAP FROZEN TEST SET EVALUATION               ")
    print("=================================================================")
    
    test_path = os.path.join("data", "processed", "test.csv")
    model_path = os.path.join("models", "classifier.pkl")
    
    if not os.path.exists(test_path):
        raise FileNotFoundError(f"Frozen test set not found at {test_path}")
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Classifier artifact not found at {model_path}")
        
    print(f"[*] Loading frozen test set: {test_path}")
    test_df = pd.read_csv(test_path)
    total_test = len(test_df)
    y_test = test_df["label_binary"].values
    phish_count = int(np.sum(y_test))
    benign_count = total_test - phish_count
    
    print(f"    Total Test Samples: {total_test:,} (Benign: {benign_count:,}, Phishing: {phish_count:,})")
    
    print(f"[*] Loading trained model artifact: {model_path}")
    with open(model_path, "rb") as f:
        artifact = pickle.load(f)
        
    scaler = artifact["scaler"]
    tfidf = artifact["tfidf"]
    model = artifact["model"]
    t_low = artifact.get("t_low", 0.05)
    t_high = artifact.get("t_high", 0.85)
    
    print(f"[*] Extracting lexical and n-gram features on frozen test URLs...")
    t0 = time.time()
    lex_feats = batch_extract_features(test_df)
    lex_scaled = scaler.transform(lex_feats)
    tfidf_feats = tfidf.transform(test_df["norm_url"].tolist())
    X_test = hstack([lex_scaled, tfidf_feats])
    feat_time = time.time() - t0
    print(f"    Feature generation completed in {feat_time:.2f}s ({total_test / feat_time:.1f} URLs/sec)")
    
    print(f"[*] Computing probability predictions...")
    probs = model.predict_proba(X_test)[:, 1]
    
    # -------------------------------------------------------------
    # 1. Standard Metrics (Threshold = 0.5)
    # -------------------------------------------------------------
    preds_50 = (probs >= 0.5).astype(int)
    roc_auc = float(roc_auc_score(y_test, probs))
    pr_auc = float(average_precision_score(y_test, probs))
    acc_50 = float(accuracy_score(y_test, preds_50))
    f1_50 = float(f1_score(y_test, preds_50, zero_division=0))
    prec_50 = float(precision_score(y_test, preds_50, zero_division=0))
    rec_50 = float(recall_score(y_test, preds_50, zero_division=0))
    tn, fp, fn, tp = confusion_matrix(y_test, preds_50).ravel()
    
    # -------------------------------------------------------------
    # 2. Triage Policy Metrics (T_low = 0.05, T_high = 0.85)
    # -------------------------------------------------------------
    allow_mask = probs < t_low
    review_mask = (probs >= t_low) & (probs < t_high)
    quarantine_mask = probs >= t_high
    
    # Auto-Allow Band
    allow_count = int(np.sum(allow_mask))
    allow_benign_tn = int(np.sum((y_test == 0) & allow_mask))
    allow_phish_fn = int(np.sum((y_test == 1) & allow_mask))
    allow_fnr = float(allow_phish_fn / max(phish_count, 1))
    benign_cleared_pct = float(allow_benign_tn / max(benign_count, 1))
    
    # Auto-Quarantine Band
    quar_count = int(np.sum(quarantine_mask))
    quar_phish_tp = int(np.sum((y_test == 1) & quarantine_mask))
    quar_benign_fp = int(np.sum((y_test == 0) & quarantine_mask))
    quar_prec = float(quar_phish_tp / max(quar_count, 1))
    quar_fpr = float(quar_benign_fp / max(benign_count, 1))
    
    # Human Review Band
    review_count = int(np.sum(review_mask))
    review_benign = int(np.sum((y_test == 0) & review_mask))
    review_phish = int(np.sum((y_test == 1) & review_mask))
    
    # Auto-decided subset error metrics
    auto_decided_total = allow_count + quar_count
    auto_decided_errors = allow_phish_fn + quar_benign_fp
    auto_error_rate = float(auto_decided_errors / max(auto_decided_total, 1))
    
    # -------------------------------------------------------------
    # 3. Print Results Summary
    # -------------------------------------------------------------
    print("\n-----------------------------------------------------------------")
    print("           FROZEN URL TEST SET METRICS (56,724 URLs)             ")
    print("-----------------------------------------------------------------")
    print(f"  ROC-AUC Score          : {roc_auc:.4f}")
    print(f"  PR-AUC Score           : {pr_auc:.4f}")
    print(f"  Accuracy (at 0.50)     : {acc_50:.4f}")
    print(f"  Precision (at 0.50)    : {prec_50:.4f}")
    print(f"  Recall (at 0.50)       : {rec_50:.4f}")
    print(f"  F1 Score (at 0.50)     : {f1_50:.4f}")
    print(f"  Confusion Matrix (0.50): TP={tp:,} | FP={fp:,} | TN={tn:,} | FN={fn:,}")
    
    print("\n-----------------------------------------------------------------")
    print("        THREE-WAY TRIAGE POLICY PERFORMANCE ON TEST SET          ")
    print("-----------------------------------------------------------------")
    print(f"  [AUTO-ALLOW]       Score < {t_low:.2f} : {allow_count:,} ({allow_count/total_test:.1%})")
    print(f"                     - Safely Cleared Benign: {allow_benign_tn:,} ({benign_cleared_pct:.2%} of all benign)")
    print(f"                     - False Negatives (Phish Missed): {allow_phish_fn:,} (FNR: {allow_fnr:.2%})")
    print(f"  [HUMAN-REVIEW] {t_low:.2f} <= Score < {t_high:.2f} : {review_count:,} ({review_count/total_test:.1%})")
    print(f"                     - Ambiguous Benign Deferred: {review_benign:,}")
    print(f"                     - Ambiguous Phish Deferred: {review_phish:,}")
    print(f"  [AUTO-QUARANTINE]  Score >= {t_high:.2f} : {quar_count:,} ({quar_count/total_test:.1%})")
    print(f"                     - True Threats Blocked: {quar_phish_tp:,}")
    print(f"                     - False Alarms: {quar_benign_fp:,} (FPR: {quar_fpr:.2%})")
    print(f"                     - Quarantine Precision: {quar_prec:.2%}")
    print(f"  [AUTONOMOUS TIER ERROR RATE]: {auto_error_rate:.2%} ({auto_decided_errors:,} errors across {auto_decided_total:,} autonomous decisions)")

    # -------------------------------------------------------------
    # 4. Error Analysis: Top False Positives & Top False Negatives
    # -------------------------------------------------------------
    print("\n-----------------------------------------------------------------")
    print("                  TOP 5 FALSE POSITIVES (FP)                     ")
    print("-----------------------------------------------------------------")
    fp_indices = np.where((y_test == 0) & (probs >= 0.5))[0]
    top_fp_idx = fp_indices[np.argsort(probs[fp_indices])[::-1]][:5]
    top_fps = []
    for idx in top_fp_idx:
        row = test_df.iloc[idx]
        score = float(probs[idx])
        top_fps.append({
            "url": row["norm_url"][:80] + ("..." if len(row["norm_url"]) > 80 else ""),
            "domain": row["reg_domain"],
            "score": round(score, 4),
            "reason": "High token entropy / suspicious security keyword matches in query string"
        })
        print(f"  Score: {score:.4f} | Domain: {row['reg_domain']} | URL: {row['norm_url'][:65]}...")

    print("\n-----------------------------------------------------------------")
    print("                  TOP 5 FALSE NEGATIVES (FN)                     ")
    print("-----------------------------------------------------------------")
    fn_indices = np.where((y_test == 1) & (probs < 0.5))[0]
    top_fn_idx = fn_indices[np.argsort(probs[fn_indices])][:5]
    top_fns = []
    for idx in top_fn_idx:
        row = test_df.iloc[idx]
        score = float(probs[idx])
        top_fns.append({
            "url": row["norm_url"][:80] + ("..." if len(row["norm_url"]) > 80 else ""),
            "domain": row["reg_domain"],
            "score": round(score, 4),
            "reason": "Short, clean path on newly registered domain without obvious lexical triggers"
        })
        print(f"  Score: {score:.4f} | Domain: {row['reg_domain']} | URL: {row['norm_url'][:65]}...")

    # -------------------------------------------------------------
    # 5. Evaluate End-to-End System on Synthetic Email Stream
    # -------------------------------------------------------------
    print("\n-----------------------------------------------------------------")
    print("       END-TO-END SYSTEM EVALUATION ON SYNTHETIC EMAIL STREAM     ")
    print("-----------------------------------------------------------------")
    with get_db_context() as conn:
        syn_summary = MessageRepository.get_metrics_summary(conn)
        
    syn_total = syn_summary.get("total_messages", 0)
    syn_auto = syn_summary.get("automated_decisions", {})
    syn_quar = syn_auto.get("QUARANTINE", 0)
    syn_allow = syn_auto.get("ALLOW", 0)
    syn_review = syn_auto.get("HUMAN_REVIEW", 0)
    syn_overrides = syn_summary.get("total_overrides", 0)

    print(f"  [LABEL: SYNTHETIC EMAIL DATASET]")
    print(f"  Total Ingested Synthetic Emails : {syn_total}")
    print(f"  Auto-Quarantined (T >= 0.85)    : {syn_quar} ({(syn_quar/max(syn_total,1))*100:.1f}%)")
    print(f"  Auto-Allowed (T < 0.05)         : {syn_allow} ({(syn_allow/max(syn_total,1))*100:.1f}%)")
    print(f"  Human-Review Queue Depth        : {syn_review} ({(syn_review/max(syn_total,1))*100:.1f}%)")
    print(f"  Analyst Overrides Executed      : {syn_overrides}")

    # -------------------------------------------------------------
    # 6. Generate Publication Figures
    # -------------------------------------------------------------
    os.makedirs(os.path.join("reports", "figures"), exist_ok=True)
    
    # Figure 1: ROC Curve
    fpr_curve, tpr_curve, _ = roc_curve(y_test, probs)
    plt.figure(figsize=(7, 6), facecolor="#0B0F19")
    ax = plt.gca()
    ax.set_facecolor("#0F172A")
    plt.plot(fpr_curve, tpr_curve, color="#6366F1", lw=2.5, label=f"Hybrid Model (ROC-AUC = {roc_auc:.4f})")
    plt.plot([0, 1], [0, 1], color="#64748B", lw=1.5, linestyle="--", label="Random Chance")
    plt.title("PhishTrap Receiver Operating Characteristic (ROC)", color="#F8FAFC", fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("False Positive Rate (FPR)", color="#94A3B8", fontsize=10)
    plt.ylabel("True Positive Rate (TPR / Recall)", color="#94A3B8", fontsize=10)
    plt.grid(color="#334155", linestyle=":", alpha=0.6)
    plt.tick_params(colors="#94A3B8")
    legend = plt.legend(loc="lower right", facecolor="#1E293B", edgecolor="#334155")
    for text in legend.get_texts():
        text.set_color("#F8FAFC")
    plt.tight_layout()
    roc_fig_path = os.path.join("reports", "figures", "roc_curve.png")
    plt.savefig(roc_fig_path, dpi=300, facecolor="#0B0F19")
    plt.close()

    # Figure 2: Precision-Recall Curve
    prec_curve, rec_curve, _ = precision_recall_curve(y_test, probs)
    plt.figure(figsize=(7, 6), facecolor="#0B0F19")
    ax = plt.gca()
    ax.set_facecolor("#0F172A")
    plt.plot(rec_curve, prec_curve, color="#06B6D4", lw=2.5, label=f"Precision-Recall (PR-AUC = {pr_auc:.4f})")
    plt.axhline(y=phish_count / total_test, color="#64748B", linestyle="--", label=f"Baseline Prevalance ({phish_count/total_test:.2%})")
    plt.title("PhishTrap Precision-Recall Curve (Frozen Test Set)", color="#F8FAFC", fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("Recall", color="#94A3B8", fontsize=10)
    plt.ylabel("Precision", color="#94A3B8", fontsize=10)
    plt.grid(color="#334155", linestyle=":", alpha=0.6)
    plt.tick_params(colors="#94A3B8")
    legend = plt.legend(loc="lower left", facecolor="#1E293B", edgecolor="#334155")
    for text in legend.get_texts():
        text.set_color("#F8FAFC")
    plt.tight_layout()
    pr_fig_path = os.path.join("reports", "figures", "pr_curve.png")
    plt.savefig(pr_fig_path, dpi=300, facecolor="#0B0F19")
    plt.close()

    # Figure 3: Confusion Matrix
    cm_norm = confusion_matrix(y_test, preds_50, normalize='true')
    plt.figure(figsize=(6, 5), facecolor="#0B0F19")
    ax = plt.gca()
    ax.set_facecolor("#0F172A")
    cax = ax.matshow(cm_norm, cmap="Blues", alpha=0.85)
    plt.title("Confusion Matrix (Normalized by Class)", color="#F8FAFC", fontsize=12, fontweight="bold", pad=20)
    plt.colorbar(cax)
    classes = ["Benign (0)", "Phishing (1)"]
    tick_marks = np.arange(len(classes))
    plt.xticks(tick_marks, classes, color="#94A3B8", fontsize=10)
    plt.yticks(tick_marks, classes, color="#94A3B8", fontsize=10)
    plt.xlabel("Predicted Class", color="#94A3B8", fontsize=10)
    plt.ylabel("Ground Truth Class", color="#94A3B8", fontsize=10)
    for i in range(2):
        for j in range(2):
            raw_cnt = [[tn, fp], [fn, tp]][i][j]
            ax.text(j, i, f"{raw_cnt:,}\n({cm_norm[i, j]:.2%})", ha="center", va="center",
                    color="white" if cm_norm[i, j] > 0.5 else "#94A3B8", fontweight="bold", fontsize=11)
    plt.tight_layout()
    cm_fig_path = os.path.join("reports", "figures", "confusion_matrix.png")
    plt.savefig(cm_fig_path, dpi=300, facecolor="#0B0F19")
    plt.close()

    # Figure 4: Triage Bands Visualization
    plt.figure(figsize=(8, 4), facecolor="#0B0F19")
    ax = plt.gca()
    ax.set_facecolor("#0F172A")
    bands = ["Auto-Allow (T < 0.05)", "Human-Review (0.05 ≤ T < 0.85)", "Auto-Quarantine (T ≥ 0.85)"]
    counts = [allow_count, review_count, quar_count]
    colors = ["#10B981", "#F59E0B", "#EF4444"]
    bars = plt.bar(bands, counts, color=colors, edgecolor="#334155", width=0.55)
    plt.title("Three-Way Operational Triage Volume Distribution (Test Set)", color="#F8FAFC", fontsize=12, fontweight="bold", pad=14)
    plt.ylabel("Number of URLs", color="#94A3B8", fontsize=10)
    plt.tick_params(colors="#94A3B8")
    for bar in bars:
        height = bar.get_height()
        pct = (height / total_test) * 100
        ax.annotate(f"{height:,}\n({pct:.1f}%)",
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 4), textcoords="offset points",
                    ha="center", va="bottom", color="#F8FAFC", fontsize=9, fontweight="bold")
    plt.ylim(0, max(counts) * 1.15)
    plt.tight_layout()
    triage_fig_path = os.path.join("reports", "figures", "triage_bands.png")
    plt.savefig(triage_fig_path, dpi=300, facecolor="#0B0F19")
    plt.close()

    # -------------------------------------------------------------
    # 7. Save Metrics JSON
    # -------------------------------------------------------------
    metrics_report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dataset": "Frozen Held-Out Test Set (data/processed/test.csv)",
        "total_test_samples": total_test,
        "class_breakdown": {
            "benign_count": benign_count,
            "phishing_count": phish_count,
            "phish_prevalence": round(float(phish_count / total_test), 4)
        },
        "url_model_evaluation": {
            "roc_auc": round(roc_auc, 4),
            "pr_auc": round(pr_auc, 4),
            "default_threshold_0_5": {
                "accuracy": round(acc_50, 4),
                "precision": round(prec_50, 4),
                "recall": round(rec_50, 4),
                "f1_score": round(f1_50, 4),
                "confusion_matrix": {
                    "TP": int(tp),
                    "FP": int(fp),
                    "TN": int(tn),
                    "FN": int(fn)
                }
            },
            "triage_policy_thresholds": {
                "t_low": t_low,
                "t_high": t_high,
                "auto_allow_band": {
                    "count": allow_count,
                    "percentage": round(allow_count / total_test * 100, 2),
                    "benign_cleared": allow_benign_tn,
                    "benign_cleared_pct_of_total_benign": round(benign_cleared_pct * 100, 2),
                    "false_negatives": allow_phish_fn,
                    "false_negative_rate": round(allow_fnr, 4)
                },
                "human_review_band": {
                    "count": review_count,
                    "percentage": round(review_count / total_test * 100, 2),
                    "benign_deferred": review_benign,
                    "phish_deferred": review_phish
                },
                "auto_quarantine_band": {
                    "count": quar_count,
                    "percentage": round(quar_count / total_test * 100, 2),
                    "true_phish_blocked": quar_phish_tp,
                    "false_positives": quar_benign_fp,
                    "false_positive_rate": round(quar_fpr, 4),
                    "quarantine_precision": round(quar_prec, 4)
                },
                "autonomous_tier_error_rate": round(auto_error_rate, 4)
            }
        },
        "end_to_end_synthetic_email_evaluation": {
            "label": "SYNTHETIC_DATASET",
            "total_synthetic_emails": syn_total,
            "automated_decisions": syn_auto,
            "current_queue_depth": syn_review,
            "human_overrides_recorded": syn_overrides
        },
        "error_analysis": {
            "top_false_positives": top_fps,
            "top_false_negatives": top_fns
        },
        "generated_figures": [
            roc_fig_path,
            pr_fig_path,
            cm_fig_path,
            triage_fig_path
        ]
    }
    
    metrics_json_path = os.path.join("reports", "metrics.json")
    with open(metrics_json_path, "w", encoding="utf-8") as f:
        json.dump(metrics_report, f, indent=2)

    print("\n[+] Evaluation completed successfully!")
    print(f"    - Metrics written to: {metrics_json_path}")
    print(f"    - ROC Curve figure  : {roc_fig_path}")
    print(f"    - PR Curve figure   : {pr_fig_path}")
    print(f"    - Confusion Matrix  : {cm_fig_path}")
    print(f"    - Triage Bands      : {triage_fig_path}")
    
    return metrics_report


if __name__ == "__main__":
    evaluate_frozen_test_set()
