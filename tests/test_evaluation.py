"""
tests/test_evaluation.py
Tests for Part 6: Evaluation Metrics, Figures, and Active Learning Retraining Loop.
"""

import os
import json
import pickle


def test_metrics_json_integrity():
    metrics_path = os.path.join("reports", "metrics.json")
    assert os.path.exists(metrics_path), "reports/metrics.json does not exist"
    
    with open(metrics_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    assert "url_model_evaluation" in data
    eval_data = data["url_model_evaluation"]
    assert eval_data["roc_auc"] >= 0.95
    assert eval_data["pr_auc"] >= 0.85
    
    cm = eval_data["default_threshold_0_5"]["confusion_matrix"]
    total_eval = cm["TP"] + cm["FP"] + cm["TN"] + cm["FN"]
    assert total_eval == data["total_test_samples"]
    
    triage = eval_data["triage_policy_thresholds"]
    assert triage["t_low"] == 0.05
    assert triage["t_high"] == 0.85
    assert triage["auto_quarantine_band"]["quarantine_precision"] >= 0.95


def test_evaluation_figures_exist_and_non_empty():
    figures = [
        "roc_curve.png",
        "pr_curve.png",
        "confusion_matrix.png",
        "triage_bands.png"
    ]
    for fig_name in figures:
        p = os.path.join("reports", "figures", fig_name)
        assert os.path.exists(p), f"Figure {fig_name} missing"
        assert os.path.getsize(p) > 10000, f"Figure {fig_name} is corrupted or too small"


def test_active_learning_retrained_artifact():
    artifact_path = os.path.join("models", "classifier_v2_active_learned.pkl")
    assert os.path.exists(artifact_path), "Retrained model artifact does not exist"
    
    with open(artifact_path, "rb") as f:
        artifact = pickle.load(f)
        
    assert artifact["version"] == "2.0.0-active-learned"
    assert "scaler" in artifact
    assert "tfidf" in artifact
    assert "model" in artifact
    assert hasattr(artifact["model"], "predict_proba")
