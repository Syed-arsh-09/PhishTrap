# PhishTrap 
### Real-Time Phishing Detection Pipeline with Human-in-the-Loop (HITL) Override

PhishTrap is an enterprise-grade phishing detection and triage pipeline. It combines deterministic feature engineering, a calibrated machine learning classifier, an automated triaging agent, and a Human-in-the-Loop (HITL) review dashboard with tamper-evident audit logging.

---

## System Architecture

```text
[ Incoming Email Stream ]
          │
          ▼
[ 1. Ingestion & Extraction Agent ] ── Strip schemes/credentials, parse registered domains (tldextract)
          │
          ▼
[ 2. Feature Extraction Agent ]    ── 26 Lexical signals + Character 3-5 n-gram TF-IDF
          │
          ▼
[ 3. Classifier Agent ]            ── Calibrated Hybrid Classifier (HistGradientBoosting + SGD/TF-IDF)
          │                           Produces calibrated probability score p ∈ [0, 1]
          │
          ▼
[ 4. Triage Agent ]                ── Strict Dual-Threshold Routing:
          ├─► p ≥ 0.85 (T_high)    ── AUTO_QUARANTINE (98.1% Precision, 0.07% FPR on benign)
          ├─► p < 0.05 (T_low)     ── AUTO_ALLOW (clears 84.6% of benign traffic safely)
          └─► 0.05 ≤ p < 0.85      ── HUMAN_REVIEW (routed to SecOps triage queue)
                                              │
                                              ▼
                                   [ 5. HITL SecOps Review Dashboard (React SPA) ]
                                              │  - Defanged URL inspection
                                              │  - Feature impact explainability
                                              │  - Override action (RELEASE / CONFIRM_PHISH / RELABEL)
                                              │  - Mandatory justification logging
                                              ▼
                                   [ 6. Tamper-Evident Audit Trail (SQLite) ]
```

---

## Dataset & Leakage-Free Splitting

The pipeline is trained and validated on a curated dataset of **378,849 clean URLs** derived from verified sources:
- **No Domain Overlap**: Splits are strictly partitioned by the SHA-256 hash of the registered domain (handling public suffix providers like `.pages.dev`, `.github.io`, etc.). Domain overlap across train, val, and test is strictly **0.00%**.
- **Data Format**: Stored completely in `.csv` format across all splits.
  - `data/processed/train.csv`: 262,665 URLs (90,294 registered domains)
  - `data/processed/val.csv`: 59,462 URLs (19,356 registered domains)
  - `data/processed/test.csv`: 56,722 URLs (19,330 registered domains — held out & frozen)

---

## Classifier Performance (Validation Set)

| Metric | Baseline Logistic Reg | HistGradientBoosting (Lexical) | Combined Hybrid Model |
| :--- | :---: | :---: | :---: |
| **ROC-AUC** | 0.8676 | 0.9456 | **0.9821** |
| **PR-AUC** | 0.4658 | 0.6906 | **0.8848** |
| **F1 Score** | 0.3110 | 0.5573 | **0.7725** |
| **FPR @ High Recall** | 5.21% | 2.14% | **0.62%** |

### Triage Thresholds
- **$T_{\text{high}} = 0.85$**: Auto-Quarantine achieves **98.13% precision** and **0.07% FPR** (only 43 false alarms on 55,099 benign validation URLs).
- **$T_{\text{low}} = 0.05$**: Auto-Allow clears **84.6% of safe traffic** with a **0.46% False Negative Rate**.
- **Human Queue**: Only **11.5%** of traffic enters the SecOps review queue, containing over 43% of all edge-case phishing attacks.

---

## Quickstart & Setup

### 1. Prerequisites
- Python 3.10+ (Tested on Python 3.12)
- Node.js 18+ (for building frontend assets, if modifying frontend)
- Virtual environment recommended

### 2. Installation
```powershell
# Clone the repository
git clone https://github.com/Syed-arsh-09/PhishTrap.git
cd PhishTrap

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1   # On Windows
# source venv/bin/activate    # On Linux / macOS

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Launch Web Console & REST API
```powershell
# Start FastAPI backend (serves REST API and precompiled React SPA at http://localhost:8000)
uvicorn src.api.app:app --host 0.0.0.0 --port 8000
```
Open [http://localhost:8000](http://localhost:8000) in your browser to view the SecOps console.

### 4. Run Simulated Multi-Agent Demo Stream
```powershell
# Replays 100 realistic synthetic emails through the 6-agent pipeline and persists to SQLite
python scripts/run_demo_stream.py
```

### 5. Run Unit Tests & Quality Check
```powershell
# Run pytest test suite
pytest

# Or use the automated check & push script
.\scripts\check_and_push.ps1 -CommitMessage "your commit message"
```

### 6. Frozen Test Set Evaluation & Active Learning
```powershell
# Evaluate frozen test set (56,722 URLs) and update publication figures
python scripts/evaluate.py

# Run active learning retraining feedback loop from SecOps analyst overrides
python scripts/retrain_from_overrides.py
```

---

## Repository Structure

```text
├── .coderabbit.yaml             # Automated AI code review instructions
├── requirements.txt             # Python dependencies
├── pytest.ini                   # Pytest configuration
├── README.md                    # Project documentation
├── data/
│   └── processed/               # Leakage-free train.csv, val.csv, test.csv + data card
├── frontend/
│   ├── dist/                    # Precompiled production bundle mounted by FastAPI
│   ├── src/                     # React + Tailwind SPA source code
│   ├── package.json             # Frontend dependencies
│   └── vite.config.js           # Vite build configuration
├── models/
│   ├── classifier.pkl           # Serialized hybrid phishing classifier
│   ├── feature_schema.json      # Lexical & n-gram feature schema
│   ├── validation_report.json   # Empirical metrics & threshold analysis
│   └── retraining_report.json   # Active learning retraining telemetry
├── reports/
│   ├── metrics.json             # Frozen test set performance metrics
│   └── figures/                 # Confusion matrix, ROC, PR, and triage band curves
├── src/
│   ├── features/                # Deterministic URL normalization & lexical extractors
│   ├── storage/                 # SQLite DB schema & repository access layer
│   ├── api/                     # FastAPI REST endpoints, schemas, and inference
│   └── pipeline/                # Deterministic multi-agent pipeline and contracts
├── scripts/
│   ├── part1_prepare_data.py    # Dataset normalization and domain hashing
│   ├── part2_train_model.py     # Model training, calibration, and triage evaluation
│   ├── run_demo_stream.py       # Simulated 100-email multi-agent stream replayer
│   ├── evaluate.py              # Frozen test set evaluation and figure generation
│   ├── retrain_from_overrides.py# Active learning feedback loop
│   └── check_and_push.ps1       # Automated test suite and git push loop
└── tests/
    ├── test_api.py              # FastAPI endpoints and repository tests
    ├── test_evaluation.py       # Metrics, figures, and active learning tests
    ├── test_features.py         # Lexical feature extraction tests
    └── test_pipeline.py         # Multi-agent contracts and safety invariant tests
```

---

## 🤖 CodeRabbit & CI Integration
Code quality, security checks, and data leakage protection are continuously monitored via `.coderabbit.yaml`. Local changes can be validated using the automated check loop prior to upstream push.
