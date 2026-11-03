"""
part1_prepare_data.py
Script to acquire, clean, normalize, group, split, and profile the phishing dataset.
Produces:
  - data/processed/train.csv
  - data/processed/val.csv
  - data/processed/test.csv
  - data/processed/data_card.json
"""

import os
import sys
import json
import hashlib
import time
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score, f1_score, precision_score, recall_score

# Ensure project root is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.features.lexical import normalize_url


def get_split(domain: str) -> str:
    """
    Hashes the registered domain to assign to train (70%), val (15%), test (15%).
    Ensures zero domain overlap between splits.
    """
    h = int(hashlib.sha256(domain.encode('utf-8')).hexdigest(), 16) % 100
    if h < 70:
        return 'train'
    elif h < 85:
        return 'val'
    else:
        return 'test'


def main():
    start_time = time.time()
    input_csv = 'merged_urls_dataset.csv'
    if not os.path.exists(input_csv):
        input_csv = os.path.join('data', 'raw', 'merged_urls_dataset.csv')
    
    if not os.path.exists(input_csv):
        raise FileNotFoundError(f"Cannot find {input_csv}. Please ensure merged_urls_dataset.csv is in the workspace root or data/raw/.")

    print(f"[*] Reading dataset from: {input_csv}")
    
    # Track metrics for data card
    data_card = {
        "dataset_name": "Merged URLs Dataset (Option B+)",
        "source_file": input_csv,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "raw_counts": {},
        "cleaning_stats": {},
        "split_stats": {},
        "shortcut_probes": {}
    }

    # Step 1: Read and count raw labels
    raw_labels = {}
    valid_rows = []
    
    chunk_size = 100000
    total_raw_rows = 0
    
    for chunk in pd.read_csv(input_csv, chunksize=chunk_size, usecols=['url', 'label']):
        total_raw_rows += len(chunk)
        for lbl, count in chunk['label'].value_counts().items():
            raw_labels[str(lbl)] = raw_labels.get(str(lbl), 0) + int(count)
        
        # Keep only benign and phish
        filtered = chunk[chunk['label'].isin(['benign', 'phish'])].copy()
        if not filtered.empty:
            valid_rows.append(filtered)
            
    data_card["raw_counts"] = {
        "total_rows": total_raw_rows,
        "labels": raw_labels
    }
    print(f"[*] Raw labels encountered: {raw_labels}")
    
    df = pd.concat(valid_rows, ignore_index=True)
    initial_filtered_count = len(df)
    print(f"[*] Filtered for benign & phish: {initial_filtered_count} rows")
    
    # Step 2: Normalize URLs
    print("[*] Normalizing URLs and extracting domains...")
    norm_urls = []
    hosts = []
    domains = []
    path_queries = []
    valid_mask = []
    
    for u in df['url']:
        n, h, d, pq = normalize_url(u)
        if n is not None:
            norm_urls.append(n)
            hosts.append(h)
            domains.append(d)
            path_queries.append(pq if pq else '')
            valid_mask.append(True)
        else:
            norm_urls.append(None)
            hosts.append(None)
            domains.append(None)
            path_queries.append(None)
            valid_mask.append(False)
            
    df['norm_url'] = norm_urls
    df['host'] = hosts
    df['reg_domain'] = domains
    df['path_query'] = path_queries
    
    # Drop rows that failed normalization
    dropped_no_host = (~np.array(valid_mask)).sum()
    df = df[valid_mask].copy()
    print(f"[*] Dropped rows with invalid/missing host: {dropped_no_host}")
    
    # Map label to binary (0 = benign, 1 = phish)
    df['label_binary'] = df['label'].map({'benign': 0, 'phish': 1}).astype(int)
    
    # Step 3: Handle conflicting labels and deduplicate
    print("[*] Checking for label conflicts...")
    conflicts = df.groupby('norm_url')['label_binary'].nunique()
    conflict_urls = set(conflicts[conflicts > 1].index)
    dropped_conflicts = df['norm_url'].isin(conflict_urls).sum()
    if conflict_urls:
        print(f"[*] Dropping {len(conflict_urls)} conflicting URLs ({dropped_conflicts} rows)")
        df = df[~df['norm_url'].isin(conflict_urls)].copy()
        
    before_dedup = len(df)
    df = df.drop_duplicates(subset=['norm_url']).copy()
    dropped_duplicates = before_dedup - len(df)
    print(f"[*] Deduplicated on normalized URL: removed {dropped_duplicates} duplicates, remaining {len(df)}")
    
    # Step 4: Cap rows per registered domain group at 500
    print("[*] Capping maximum 500 URLs per registered domain...")
    before_cap = len(df)
    # Fast vectorized shuffle and capping per group
    df = df.sample(frac=1.0, random_state=42).reset_index(drop=True)
    df['row_in_group'] = df.groupby('reg_domain').cumcount()
    df = df[df['row_in_group'] < 500].drop(columns=['row_in_group']).reset_index(drop=True)
    dropped_by_capping = before_cap - len(df)
    print(f"[*] Dropped by domain capping: {dropped_by_capping} rows, remaining {len(df)}")
    
    data_card["cleaning_stats"] = {
        "initial_benign_and_phish": initial_filtered_count,
        "dropped_no_host": int(dropped_no_host),
        "conflicting_urls_count": len(conflict_urls),
        "dropped_conflict_rows": int(dropped_conflicts),
        "dropped_duplicates": int(dropped_duplicates),
        "dropped_by_domain_capping": int(dropped_by_capping),
        "clean_rows": len(df),
        "unique_registered_domains": int(df['reg_domain'].nunique())
    }

    # Step 5: Domain-Grouped Split
    print("[*] Performing domain-grouped split (70% train / 15% val / 15% test)...")
    df['split'] = df['reg_domain'].map(get_split)
    
    train_df = df[df['split'] == 'train'].reset_index(drop=True)
    val_df = df[df['split'] == 'val'].reset_index(drop=True)
    test_df = df[df['split'] == 'test'].reset_index(drop=True)
    
    # Verification of zero domain leakage
    train_domains = set(train_df['reg_domain'])
    val_domains = set(val_df['reg_domain'])
    test_domains = set(test_df['reg_domain'])
    
    overlap_train_val = len(train_domains & val_domains)
    overlap_train_test = len(train_domains & test_domains)
    overlap_val_test = len(val_domains & test_domains)
    
    assert overlap_train_val == 0, f"Domain overlap between train and val: {overlap_train_val}"
    assert overlap_train_test == 0, f"Domain overlap between train and test: {overlap_train_test}"
    assert overlap_val_test == 0, f"Domain overlap between val and test: {overlap_val_test}"
    print("[+] Verified: 0 domain overlap across all three splits!")
    
    data_card["split_stats"] = {
        "train": {
            "total_urls": len(train_df),
            "phish_count": int(train_df['label_binary'].sum()),
            "benign_count": int((train_df['label_binary'] == 0).sum()),
            "unique_domains": len(train_domains),
            "phish_ratio": round(float(train_df['label_binary'].mean()), 4)
        },
        "val": {
            "total_urls": len(val_df),
            "phish_count": int(val_df['label_binary'].sum()),
            "benign_count": int((val_df['label_binary'] == 0).sum()),
            "unique_domains": len(val_domains),
            "phish_ratio": round(float(val_df['label_binary'].mean()), 4)
        },
        "test": {
            "total_urls": len(test_df),
            "phish_count": int(test_df['label_binary'].sum()),
            "benign_count": int((test_df['label_binary'] == 0).sum()),
            "unique_domains": len(test_domains),
            "phish_ratio": round(float(test_df['label_binary'].mean()), 4)
        }
    }
    print("[*] Split counts:")
    for split_name, stats in data_card["split_stats"].items():
        print(f"    - {split_name.upper()}: {stats['total_urls']} URLs ({stats['unique_domains']} domains) | Phish: {stats['phish_count']} | Benign: {stats['benign_count']} (Phish ratio: {stats['phish_ratio']:.1%})")

    # Step 6: Shortcut Probes
    print("\n[*] Evaluating Shortcut Probes...")
    
    # Probe A: Host-only char n-gram model
    print("  -> Training Probe A (Host-only char 3-5 n-grams)...")
    host_vec = TfidfVectorizer(analyzer='char', ngram_range=(3, 5), max_features=10000)
    X_train_host = host_vec.fit_transform(train_df['host'])
    X_val_host = host_vec.transform(val_df['host'])
    
    clf_host = LogisticRegression(max_iter=1000, random_state=42)
    clf_host.fit(X_train_host, train_df['label_binary'])
    val_preds_host = clf_host.predict_proba(X_val_host)[:, 1]
    val_pred_labels_host = (val_preds_host >= 0.5).astype(int)
    
    probe_host_metrics = {
        "roc_auc": round(float(roc_auc_score(val_df['label_binary'], val_preds_host)), 4),
        "pr_auc": round(float(average_precision_score(val_df['label_binary'], val_preds_host)), 4),
        "f1": round(float(f1_score(val_df['label_binary'], val_pred_labels_host)), 4),
        "precision": round(float(precision_score(val_df['label_binary'], val_pred_labels_host)), 4),
        "recall": round(float(recall_score(val_df['label_binary'], val_pred_labels_host)), 4)
    }
    print(f"  [+] Host Probe Results (Val): ROC-AUC={probe_host_metrics['roc_auc']}, PR-AUC={probe_host_metrics['pr_auc']}, F1={probe_host_metrics['f1']}")

    # Probe B: Path/Query-only char n-gram model
    print("  -> Training Probe B (Path/Query-only char 3-5 n-grams)...")
    pq_vec = TfidfVectorizer(analyzer='char', ngram_range=(3, 5), max_features=10000)
    X_train_pq = pq_vec.fit_transform(train_df['path_query'])
    X_val_pq = pq_vec.transform(val_df['path_query'])
    
    clf_pq = LogisticRegression(max_iter=1000, random_state=42)
    clf_pq.fit(X_train_pq, train_df['label_binary'])
    val_preds_pq = clf_pq.predict_proba(X_val_pq)[:, 1]
    val_pred_labels_pq = (val_preds_pq >= 0.5).astype(int)
    
    probe_pq_metrics = {
        "roc_auc": round(float(roc_auc_score(val_df['label_binary'], val_preds_pq)), 4),
        "pr_auc": round(float(average_precision_score(val_df['label_binary'], val_preds_pq)), 4),
        "f1": round(float(f1_score(val_df['label_binary'], val_pred_labels_pq)), 4),
        "precision": round(float(precision_score(val_df['label_binary'], val_pred_labels_pq)), 4),
        "recall": round(float(recall_score(val_df['label_binary'], val_pred_labels_pq)), 4)
    }
    print(f"  [+] Path/Query Probe Results (Val): ROC-AUC={probe_pq_metrics['roc_auc']}, PR-AUC={probe_pq_metrics['pr_auc']}, F1={probe_pq_metrics['f1']}")

    data_card["shortcut_probes"] = {
        "probe_a_host_only": probe_host_metrics,
        "probe_b_path_query_only": probe_pq_metrics
    }

    # Step 7: Save Processed Partitions and Data Card
    os.makedirs(os.path.join('data', 'processed'), exist_ok=True)
    
    train_path = os.path.join('data', 'processed', 'train.csv')
    val_path = os.path.join('data', 'processed', 'val.csv')
    test_path = os.path.join('data', 'processed', 'test.csv')
    card_path = os.path.join('data', 'processed', 'data_card.json')
    
    print("[*] Saving CSV files...")
    cols_to_save = ['norm_url', 'host', 'reg_domain', 'path_query', 'label_binary']
    train_df[cols_to_save].to_csv(train_path, index=False)
    val_df[cols_to_save].to_csv(val_path, index=False)
    test_df[cols_to_save].to_csv(test_path, index=False)
    
    data_card["execution_time_seconds"] = round(time.time() - start_time, 2)
    with open(card_path, 'w', encoding='utf-8') as f:
        json.dump(data_card, f, indent=2)
        
    print(f"[+] All deliverables saved successfully in {data_card['execution_time_seconds']}s:")
    print(f"    - {train_path}")
    print(f"    - {val_path}")
    print(f"    - {test_path}")
    print(f"    - {card_path}")


if __name__ == '__main__':
    main()
