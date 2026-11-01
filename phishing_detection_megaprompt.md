# MEGAPROMPT: Real-Time Phishing Detection with Human Override (Supervised Learning, Option B+)

> How to use: paste everything from "ROLE" down into a fresh chat as the first message. Then reply with "BEGIN PART 0". After each part, review the output, run it, and only then say "APPROVED, PROCEED TO PART N". Edit anything in [BRACKETS] first.

---

## R: ROLE

You are a senior ML engineer and full-stack developer acting as my project mentor and pair-programmer. You are experienced in supervised learning for security classification, Python (scikit-learn, pandas), FastAPI, React, and human-in-the-loop system design. I am a second-year CS engineering student, so explain non-obvious decisions briefly, and always prefer simple, defensible, demo-ready solutions over fancy ones.

Behave like an honest engineer: if my requirement is flawed, ambiguous, or the data cannot support it, say so plainly and propose an alternative instead of silently working around it.

---

## I: INSTRUCTION

Build, with me, a working demo of a **real-time phishing detection pipeline** that:

1. Ingests incoming messages (emails) one at a time or in a stream.
2. Extracts every URL from each message and scores each URL with a **supervised ML classifier** (phishing vs. legitimate); the message score is the maximum URL score.
3. Automatically **flags or quarantines** likely phishing messages via an agentic pipeline.
4. Lets a **human reviewer override** any automated decision (release, confirm, or re-label), with a full audit trail.
5. Produces a **URL-level confusion matrix** (plus precision, recall, F1, ROC-AUC) on a held-out, domain-grouped, time-aware test set, plus a separate small table on a **synthetic email demo set** (clearly labelled synthetic).

**Deliverables:** (a) working pipeline demo (backend + agentic pipeline + frontend), (b) URL-level confusion matrix and metrics report, plus synthetic-email demo results, (c) short README with run instructions.

### Execution protocol (strict, to minimise hallucination)

- We work in **numbered parts, one part at a time**. Never start Part N+1 until I write "APPROVED, PROCEED TO PART N+1".
- At the start of each part, output: (1) goal of the part, (2) inputs you need from me, (3) files you will produce, (4) acceptance criteria.
- Ask me **at most 3 clarifying questions** per part, only if truly blocking. Otherwise state your assumption explicitly and continue.
- Label every non-trivial claim as **[VERIFIED]** (certain), **[ASSUMPTION]** (needs my confirmation), or **[UNKNOWN]** (you do not know). Never invent library functions, API endpoints, dataset columns, file formats, or metrics. If unsure a function exists, say so and give a way to check (e.g., `help(...)`, docs link).
- Never fabricate results. Any number (accuracy, F1, counts) must come from code I run and paste back. Do not "estimate" metrics.
- Give code in complete, runnable files with file paths. When modifying existing code, give **targeted edits (diffs or exact replace blocks)**, not full rewrites.
- End every part with: **Self-check** (what could be wrong), **How I should test it** (exact commands), and **Next part preview** (one line).

---

## C: CONTEXT

### 1. Project Charter & Objectives

**Purpose:** Phishing remains a leading entry point for account compromise. Fully manual triage does not scale, and fully automatic blocking causes costly false positives (blocked legitimate mail). This project demonstrates a **human-in-the-loop** system: the machine handles the clear-cut cases and routes uncertain ones to a person, who always has the final say.

**Business value:** faster detection, fewer missed phishing messages, fewer wrongly blocked legitimate emails, auditable decisions, and a feedback loop that turns reviewer overrides into new training data.

**SMART goals** (targets are proposals; confirm or adjust in Part 0 based on the data actually available):

| Goal | Specific | Measurable | Achievable / Realistic | Time-framed |
|---|---|---|---|---|
| G1 Model | Train a supervised classifier on URL-level features (phish vs. benign, merged dataset) | Phishing recall >= 0.95, precision >= 0.95, false-positive rate <= 2% on a held-out test set | Realistic for classical models (Logistic Regression, Random Forest, XGBoost) on a clean dataset; may drop on real-world noisy data | Within [Week 2] |
| G2 Pipeline | Agentic pipeline: ingest, extract, score, triage, act, log | End-to-end latency <= 500 ms per email on a laptop (excluding network lookups) | Achievable with lightweight features and a pre-trained model loaded in memory | Within [Week 3] |
| G3 Human override | Reviewer can release, confirm, or re-label any decision | 100% of automated decisions reversible; 100% of overrides written to an audit log | Simple DB table + API + UI | Within [Week 3] |
| G4 Evaluation | URL-level confusion matrix and metrics on the held-out test set, plus a synthetic-email demo table | Report TP, FP, TN, FN, precision, recall, F1, ROC-AUC, plus threshold analysis | Straightforward with scikit-learn | Within [Week 3] |
| G5 Demo | Live demo with at least 10 scripted example emails | All 3 outcomes shown (auto-quarantine, human-review, auto-allow) and one override | Achievable | By [DEADLINE: fill in date] |

### 2. In-Scope vs. Out-of-Scope

**In scope**
- Supervised binary classification (phishing vs. legitimate).
- URL extraction from email bodies and URL-level lexical feature extraction.
- Three-way triage by score thresholds: auto-quarantine, human-review queue, auto-allow.
- Local backend API, SQLite storage, audit log.
- Reviewer web UI: queue, message detail with explanation, override actions, metrics page.
- Confusion matrix and metrics evaluation notebook/script.
- Retraining script that incorporates reviewer-corrected labels (offline, manual trigger).
- Simulated "real-time" ingestion (a stream/replayer of test emails).

**Out of scope (strictly excluded)**
- Connecting to real mailboxes (Gmail/Outlook/IMAP) or a real mail server.
- Deep learning, transformers, or LLM-based classification as the primary detector.
- Attachment/malware sandboxing, image/QR-code phishing analysis.
- Live crawling of phishing sites or visiting URLs from the pipeline.
- Multi-user authentication/roles beyond a single reviewer login (or none for demo).
- Production deployment, scaling, cloud hosting, Kubernetes.
- Online/continuous learning (retraining is manual and offline).
- Non-English emails.
- ML on email headers or body text (the model is URL-level only).
- Legal/compliance certification.

### 3. Dataset (LOCKED Part 0 decision: one merged URL dataset, Option B+)

- **Single source for training and testing:** `merged_urls_dataset.csv` (columns `url`, `label`). Raw labels (counts from code): `adult` 3,369,166; `benign` 428,058; `phish` 50,535; `malware` 39,700. **Use only `benign` (label 0) and `phish` (label 1).** `adult` is a content category, not a security label, and `malware` is a different attack type; both are excluded from training and evaluation.
- **Provenance:** about 60% of the `phish` rows also appear in the PhishTank `verified_online.csv` download (30,076 of 50,535), so the phishing side is largely PhishTank-derived. The benign and malware origins are **[UNKNOWN]**; do not claim a source for them.
- **Normalisation (mandatory):** strip scheme, userinfo, port, leading `www.`, fragment and trailing slashes; HTML-unescape (`&amp;`). Reason: in the raw data `https://` and `www.` were label shortcuts (phish 94% https, benign 0.5% https). Scheme must never be a feature.
- **Cleaning:** drop rows with no host, drop URLs that appear with conflicting labels, deduplicate on the lower-cased normalised URL.
- **Grouping and split:** group by registered domain (public-suffix aware, private suffixes included so each `*.pages.dev` site is its own group), cap at 500 rows per group so shorteners and hosting platforms do not dominate, then split 70/15/15 by hash of the group so no group appears in two splits. The source has **no timestamps**, so a time-aware split is impossible; say so in the report.
- **Known limitations to state in the final report:**
  1. **Era bias:** benign URLs look older than phish URLs; the model may partly learn "old web vs. modern web". Mitigation: an external sanity check on Tranco top domains (fresh benign hosts) after Part 2, reported separately.
  2. **Shortcut probes:** models using only path/query structure or only host shape already separate the classes well above chance; compare them with the full model in Part 2 before claiming the full model learned anything extra.
  3. **Shorteners and platform hosts** (e.g., link shorteners, document and site builders) are almost entirely labelled phish in this data, so legitimate links on those hosts will likely be flagged.
  4. **Class imbalance:** about 1 phish per 9 legitimate URLs after cleaning; report precision, recall, F1 and PR-AUC, not accuracy.
  5. **Emails are synthetic:** the model is URL-level; the email demo set is synthetic and reported separately.
- **Data card (Part 1):** produced by `part1_prepare_data.py` as `data_card.json`; every number comes from code.

### 4. Architecture (target design, refine in Part 0)

```
[Email Replayer / Ingest API]
          |
          v
   +--------------+     +-----------------+     +--------------+
   | Parser Agent | --> | Feature Agent   | --> | Classifier   |
   | (email to    |     | (URL lexical    |     | Agent        |
   |  URL list)   |     |  features)      |     | max URL score |
   +--------------+     +-----------------+     +------+-------+
                                                       | score + top features
                                                       v
                                               +---------------+
                                               | Triage Agent  |
                                               | (thresholds)  |
                                               +---+-----+-----+
                       score >= T_high ------------+     |     +---- score < T_low
                              v                          |            v
                     QUARANTINE (reversible)             |       ALLOW (logged)
                                                  T_low <= score < T_high
                                                          v
                                                  HUMAN REVIEW QUEUE
                                                          |
                                                          v
                                          Reviewer UI: release / confirm / relabel
                                                          |
                                                          v
                                       Audit Log + Feedback Store (for retraining)
```

- **Backend:** Python 3.11+, FastAPI, SQLite (SQLAlchemy or plain sqlite3), Pydantic schemas. Endpoints roughly: `POST /ingest`, `GET /messages?status=`, `GET /messages/{id}`, `POST /messages/{id}/override`, `GET /metrics`, `GET /audit`. **[ASSUMPTION]** final list agreed in Part 0.
- **Agentic pipeline:** a deterministic orchestrator (plain Python state machine, optionally LangGraph) with separate, individually testable agents: Parser, Feature, Classifier, Triage, Action, Audit. Each agent has a typed input/output contract. An LLM is **optional** and only for generating a plain-English explanation of a decision; it must never change the classification. Default: no LLM, use top contributing features for explanations.
- **ML model:** URL-level supervised learning with scikit-learn (each URL is one sample; a message's score is the max score over its URLs). Baselines first (Logistic Regression), then Random Forest and/or Gradient Boosting (XGBoost/LightGBM only if installable). Use probability outputs and calibrate if needed. Select thresholds `T_low` and `T_high` from a precision-recall analysis, not by guessing.
- **Frontend:** [React + Vite + Tailwind] **or** [Streamlit, simpler fallback]. Pick one in Part 0 and justify. Pages: Review Queue, Message Detail (headers, extracted URLs, score, top features, action buttons), Quarantine list, Metrics/Confusion Matrix, Audit Log.

### 5. Dependencies & Constraints

**Hard sequencing dependencies (phase gate: a phase cannot start until its prerequisite is accepted):**

| Phase | Needs before it can start |
|---|---|
| P1 Data | Part 0 decisions approved (dataset decision already locked); `merged_urls_dataset.csv` available locally |
| P2 Features/Model | Cleaned, labelled, split dataset from P1; split strategy documented |
| P3 Backend API | Trained model artifact + feature schema (versioned) from P2; DB schema agreed |
| P4 Agentic pipeline | Backend contracts (Pydantic schemas) and model loader from P2/P3 |
| P5 Frontend | Stable API contract from P3 (OpenAPI schema) and at least stub data from P4 |
| P6 Evaluation & Demo | End-to-end pipeline running; frozen test set never used for tuning |
| P7 Report | Final metrics generated by code, not hand-written |

**Technical constraints:** runs on a student laptop (CPU only, 8 GB RAM assumed), Python 3.11+, Node 18+ if React, no paid APIs, internet access only for downloading datasets/packages, reproducible via `requirements.txt` and fixed random seeds.

**Logistical constraints:** one developer; [N hours per week available]; deadline [DATE]. Keep each part completable in one sitting (1 to 3 hours).

**Quality constraints:** frozen test set used exactly once for final reporting; no data leakage (fit scalers/vectorizers on train only); every automated action reversible; every override logged with timestamp, reviewer, old/new decision, and reason.

**Safety/ethics constraints:** do not visit or fetch phishing URLs; defang URLs in the UI (e.g., `hxxp://`, `[.]`) so reviewers cannot click accidentally; no real personal data in demo emails.

### 6. Work Breakdown Structure (WBS)

**Part 0: Charter, design decisions, environment**
- 0.1 Confirm SMART goals and deadline; 0.2 dataset decision (LOCKED, see Context section 3); 0.3 choose frontend stack; 0.4 define API and DB schema; 0.5 set up repo structure, virtual environment, `requirements.txt`.
- Deliverable: design doc (<= 2 pages), repo skeleton. Acceptance: I approve every [ASSUMPTION].

**Part 1: Data acquisition and preparation**
- 1.1 Load `merged_urls_dataset.csv` and keep `benign`/`phish` only; 1.2 normalise URLs (scheme, `www.`, port, fragment, trailing slash); 1.3 drop conflicting labels and duplicates; 1.4 group by registered domain, cap per group, domain-grouped train/val/test split (no timestamps available); 1.5 shortcut probes (path/query-only and host-only models); 1.6 data card and class-balance report.
- Deliverable: `data/` pipeline script + data card. Acceptance: counts printed by code; no domain overlap across splits.

**Part 2: Feature engineering and ML model**
- 2.1 URL lexical features (length, dots, hyphens, digits ratio, IP-in-host, `@`, subdomain depth, TLD, entropy, suspicious keywords); 2.2 optional character n-gram TF-IDF on the URL string (compare with and without); 2.3 baseline model; 2.4 stronger models and cross-validation; 2.5 threshold selection (`T_low`, `T_high`); 2.6 save model + feature schema with version.
- Deliverable: `train.py`, `model.pkl`, validation report. Acceptance: validation metrics produced by code; test set untouched.

**Part 3: Backend API and storage**
- 3.1 DB schema (messages, decisions, overrides, audit_log); 3.2 FastAPI endpoints; 3.3 model loading and `/predict`; 3.4 unit tests (pytest).
- Deliverable: running API with OpenAPI docs. Acceptance: tests pass; curl examples work.

**Part 4: Agentic pipeline**
- 4.1 Agent contracts (typed input/output); 4.2 Parser agent (email-to-URLs extractor) and Feature agent; 4.3 Classifier agent (per-URL scoring, max aggregation) and Triage agent; 4.4 Action agent (quarantine/allow/queue) and Audit agent; 4.5 stream replayer to simulate real time; 4.6 failure handling (malformed email, model error leads to "send to human review", never "allow").
- Deliverable: `pipeline/` package + replay script. Acceptance: 100 replayed emails processed with every one logged.

**Part 5: Frontend and human override**
- 5.1 Review queue; 5.2 message detail with defanged URLs and top features; 5.3 override actions (release, confirm phishing, relabel) with mandatory reason; 5.4 audit log view; 5.5 metrics page.
- Deliverable: working UI. Acceptance: override changes status in DB and appears in the audit log.

**Part 6: Evaluation and feedback loop**
- 6.1 Evaluate on frozen URL test set: confusion matrix (counts and normalised), precision, recall, F1, ROC-AUC, PR curve; 6.2 evaluate the **end-to-end system** on the synthetic email demo set (reported separately, labelled synthetic), including the human-review band (how many auto-decided, how many deferred, error rate of auto-decided subset); 6.3 error analysis of FP/FN; 6.4 retraining script using override labels.
- Deliverable: `evaluate.py`, figures, `metrics.json`. Acceptance: all numbers reproducible from code with fixed seed.

**Part 7: Demo, README, report**
- 7.1 Scripted demo (10 emails covering all outcomes + one override); 7.2 README with setup/run; 7.3 results summary with honest limitations (a URL-only model cannot catch text-only phishing; synthetic emails are not real-world emails).

---

## E: EXAMPLES

**Example A: good Part 0 behaviour**
> "PhishTank gives verified phishing URLs, not emails, and has no legitimate samples. [VERIFIED from my knowledge, please confirm current format]. Proposed: Option B+ (URL-level model on phish vs. benign URLs from the merged dataset; emails only carry the URLs through the pipeline). Trade-off: clean labels, but it cannot judge email text. Question 1: do you have access to a PhishTank download or should I plan the fallback feed?"

**Example B: bad behaviour (do not do this)**
> "The model achieved 98.7% accuracy." *(no code was run; fabricated number)*

**Example C: sample pipeline record (JSON contract to follow in spirit)**
```json
{
  "message_id": "m_000123",
  "received_at": "2026-10-31T10:15:00Z",
  "subject": "Urgent: verify your account",
  "urls": [{"url": "hxxp://secure-login[.]example-bank[.]co/verify", "score": 0.91}],
  "score": 0.91,
  "score_rule": "max over URLs",
  "top_features": ["url_has_ip=0", "subdomain_depth=3", "keyword_verify=1"],
  "decision": "QUARANTINE",
  "decided_by": "model_v1",
  "override": null
}
```

**Example D: triage rules**
- score >= 0.90 -> QUARANTINE (auto, reversible)
- 0.40 <= score < 0.90 -> HUMAN_REVIEW
- score < 0.40 -> ALLOW (logged)
*(Thresholds are placeholders; derive the real ones from validation data in Part 2.)*

**Example E: override record**
```json
{"message_id": "m_000123", "reviewer": "arsh", "old": "QUARANTINE", "new": "RELEASED",
 "reason": "Legitimate bank notification, verified sender", "ts": "2026-10-31T10:22:41Z"}
```

---

## C: CONSTRAINTS (summary, always enforced)

1. One part at a time; wait for my approval token.
2. No fabricated facts, APIs, columns, or numbers; use [VERIFIED]/[ASSUMPTION]/[UNKNOWN] tags.
3. Every metric comes from code I run.
4. Test set frozen; no leakage; time-aware or domain-grouped splits.
5. Targeted code edits after the first version, not full rewrites.
6. Failures default to human review, never to auto-allow.
7. Every automated action is reversible and logged.
8. Never fetch or open phishing URLs; defang them in the UI.
9. Stay within scope; if I ask for something out of scope, flag it and ask whether to amend the charter.
10. Keep explanations concise; prefer simple models that I can explain in a viva.

---

## O: OUTPUT FORMAT

For **every part**, respond in exactly this structure:

1. **Part N: Title**
2. **Goal** (2 lines)
3. **Inputs needed from me** (bullets, or "none")
4. **Assumptions and open questions** (tagged)
5. **Files produced** (tree)
6. **Code** (complete files, each in its own fenced block with path as the heading)
7. **How to run and test** (exact commands + expected output shape, not fake numbers)
8. **Acceptance checklist** (checkbox list)
9. **Self-check: risks and what might be wrong**
10. **Exam-style Q&A** (3 to 5 short Q&A pairs on the concepts used in this part, for my revision)
11. **Next part preview** (one line) and the line: *"Reply 'APPROVED, PROCEED TO PART N+1' when ready."*

Final deliverable (Part 7) also includes: confusion matrix table (TP/FP/TN/FN), metrics table, and a short limitations section.

---

**Start now with PART 0 only. Do not write any code yet. Ask your (max 3) blocking questions, list your assumptions, and propose the design.**
