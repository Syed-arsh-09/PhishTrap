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
                                   [ 5. HITL SecOps Review Dashboard (Streamlit) ]
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

# Install dependencies
pip install -r requirements.txt
```

### 3. Run Unit Tests & Quality Check
```powershell
# Run pytest test suite
pytest

# Or use the automated check & push script
.\scripts\check_and_push.ps1 -CommitMessage "your commit message"
```

---

## Repository Structure

```text
├── .coderabbit.yaml          # Automated AI code review instructions
├── requirements.txt          # Python dependencies
├── pytest.ini                # Pytest configuration
├── README.md                 # Project documentation
├── data/
│   └── processed/            # Leakage-free train.csv, val.csv, test.csv + data card
├── models/
│   ├── classifier.pkl        # Serialized hybrid phishing classifier
│   ├── feature_schema.json   # Lexical & n-gram feature schema
│   └── validation_report.json# Empirical metrics & threshold analysis
├── src/
│   ├── features/             # Deterministic URL normalization & lexical extractors
│   ├── storage/              # SQLite DB & audit repositories (Part 3)
│   ├── api/                  # FastAPI REST endpoints (Part 3)
│   └── pipeline/             # Multi-agent orchestrators (Part 4)
├── scripts/
│   ├── part1_prepare_data.py # Dataset normalization and domain hashing
│   ├── part2_train_model.py  # Model training, calibration, and triage evaluation
│   └── check_and_push.ps1    # Pytest + CodeRabbit + GitHub push loop
└── tests/
    └── test_features.py      # Lexical extraction unit tests
```

---

## 🤖 CodeRabbit & CI Integration
Code quality, security checks, and data leakage protection are continuously monitored via `.coderabbit.yaml`. Local changes can be validated using the automated check loop prior to upstream push.

