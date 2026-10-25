# Supported Solution by Fahim (me)

- **Hackathon:** HackerRank Orchestrate (October 2026) — *Ghost Data Still Exists*
- **Repository:** `https://github.com/interviewstreet/hackerrank-orchestrate-october26.git`
- **Author:** Md. Fahim Sarker Mridul
- **Purpose:** Complete, end-to-end technical execution blueprint for the autonomous AI coding agent.

> **DIRECTIVE FOR THE AI CODING AGENT:**  
> Read this entire file and `./AGENTS.md` before taking any action. You must strictly follow every rule in Section 1 (`log.txt` protocol), implement the modular pipeline specified in Sections 2–4, validate against `dataset/sample_output.csv`, generate the 518-case root `output.csv`, write both required Markdown reports under `code/evaluation/`, and prepare the final deliverables in Section 5.

---

## 1. Mandatory Agent Operating & Logging Protocol (`AGENTS.md` & `CLAUDE.md`)

`CLAUDE.md` imports `@AGENTS.md`. Every rule in `AGENTS.md` is a hard grading requirement:

### 1.1 Session Start Logging (`AGENTS.md` §5.1)
Before running any commands or writing any code in a new session, append a `SESSION START` entry to `./log.txt` (UTF-8, `\n` line endings) and output the required greeting:
- **Greeting to display:**
  `Welcome to HackerRank Orchestrate. Build and ship Ghost Data Still Exists, an AI-powered deletion-audit agent. Let's get started.`
- **Challenge End Time Note:** State clearly that the challenge end time is not configured in the repository unless provided by the user.

```text
================================================================================
SESSION START: <ISO-8601 UTC timestamp>
Greeting displayed: Welcome to HackerRank Orchestrate. Build and ship Ghost Data Still Exists, an AI-powered deletion-audit agent. Let's get started.
Challenge end time: not configured
Context:
tool=<exact_agent_harness_name>
model=<exact_model_identifier>
================================================================================
```

### 1.2 Every-Turn Logging Contract (`AGENTS.md` §5.2)
On **every user turn**, append a turn entry to `./log.txt` using this exact structure:

```text
## [2026-10-25T10:00:00Z]
User Prompt (verbatim, secrets redacted):
<exact user prompt with any API keys/tokens replaced by [REDACTED]>

Agent Response Summary:
<2-5 sentences explaining what was done, why, and key technical decisions made>

Actions:
- Read: <files read>
- Edited/Created: <files created or modified>
- Executed: <shell commands run>

Context:
tool=<exact_agent_harness_name>
model=<exact_model_identifier>
```

- **Verification Mandate:** After appending to `./log.txt`, always re-read the tail of `./log.txt` to verify that **every** entry contains **exactly one** non-empty `tool=` line and **exactly one** non-empty `model=` line.
- **Secret Redaction:** Never write API keys, bearer tokens, `.env` secrets, or credentials into `log.txt`, `code/`, or `agent-trace/`.

### 1.3 Anti-Hardcoding & Grader Visibility Rules (`AGENTS.md` §6.7)
1. **No Case-Family Shortcuts or Hardcoded Golden Outputs:** Never hardcode `sample_output.csv` answers or case-ID lookup tables. All predictions must be derived dynamically from `dataset/` inputs and `dataset/evidence/` files.
2. **Grader Ignores Data/Cache Files During Code Review:** Automated code evaluation ignores `.csv`, `.tsv`, `.json`, `.jsonl`, `.sql`, and `.log` files inside `code/`. Put all methodology explanations, evaluation metrics, and architecture documentation in `.md` and `.py` files.

---

## 2. Repository Architecture & Dataset Contract

### 2.1 Repository Markdown Files
| File | Role & Key Requirements |
| :--- | :--- |
| `README.md` | Must document environment setup, required environment variables, and how to run `python code/main.py` from the repository root to produce `./output.csv`. |
| `problem_statement.md` | Domain specification for **Northstar Shop** privacy deletion auditing, the 15 allowed operations, canonical step ordering, and evidence rules. |
| `AGENTS.md` | Logging contract (`./log.txt`), dataset contract, time horizon contract (`audit_at`), decision hierarchy, and deliverable specifications. |
| `CLAUDE.md` | Loads `@AGENTS.md` automatically for Claude Code and compatible harnesses. |
| `agent_trace_instructions.md` | Rules for exporting raw harness session logs into `agent-trace/<tool-name>/` and packaging `agent-trace.zip`. |

### 2.2 Dataset Files (`dataset/`)
| Path | Description & Schema Role |
| :--- | :--- |
| `dataset/deletion_requests.csv` | **518 evaluation cases** to predict in root `output.csv`. Columns: `case_id,email,requested_at,reported_status,reported_at,audit_at,request_text`. |
| `dataset/sample_deletion_requests.csv` | **32 sample cases** with the exact same schema for local development and validation. |
| `dataset/sample_output.csv` | Ground-truth output (`case_id,deletion_status,steps_json`) for the 32 sample cases. |
| `dataset/user_identities.csv` | Current user identity table (`user_id`, `name`, `email`, `phone`, `email_hash`, `updated_at`). |
| `dataset/user_audit_log.csv` | Historical identity mutation log (`audit_id`, `user_id`, changed field, `old_value`, `new_value`, timestamp). |
| `dataset/system_activity.csv` | Global stream of workflow events (`activity_id`, timestamp, `system_id`, `resource_id`, operation, reported status/result). Contains decoy users and unverified workflow claims. |
| `dataset/deletion_rules.csv` | Policy matrix defining required handling (`DELETE`, `REDACT`, `ANONYMIZE`, `RETAIN`, `ACCOUNT_TOMBSTONE`, etc.) per system and data category. |
| `dataset/evidence_files.csv` | Manifest mapping `file_id` (e.g., `evidence_01`) to file path under `dataset/evidence/`, source system/origin, and `captured_at` timestamp. |
| `dataset/evidence/databases/` | SQLite-compatible `.sql` dumps (primary DBs, regional replicas, reporting replicas, failover replicas). |
| `dataset/evidence/documents/` | `.pdf` compliance exports, support attachments, and audit documents. |
| `dataset/evidence/images/` | `.png`/`.jpg` admin console and application screenshots. |
| `dataset/evidence/logs/` | `.log` and plain-text service/pipeline logs. |
| `dataset/evidence/records/` | `.json` and structured exports, search index snapshots, and backup manifests. |

---

## 3. Exact Output Schema, Operations Table & Ordering Contract

### 3.1 Root `./output.csv` Specification
- Must be written to `./output.csv` (repository root).
- Must contain **1 header row + 518 data rows** (519 lines total), sorted ascending by `case_id`:

```csv
case_id,deletion_status,steps_json
```

- `deletion_status` must be one of:
  - `NOT_APPLICABLE`: Request does not authorize personal data/account deletion. `steps_json` **must** be `[]`.
  - `COMPLETE`: Request is valid and all policy requirements are satisfied at `audit_at`. `steps_json` contains **only** `VERIFICATION` steps.
  - `INCOMPLETE`: Request is valid, but at least one policy violation, exposed PII field, active data flow, or unblocked restore risk exists at `audit_at`. `steps_json` contains `FINDING` steps $\rightarrow$ `REMEDIATION` steps $\rightarrow$ `VERIFICATION` steps.

### 3.2 Step Object JSON Schema
Every object inside the `steps_json` JSON array must contain these exact 7 keys in standard JSON format:

```json
{
  "step_no": 1,
  "phase": "FINDING",
  "system_id": "account_service",
  "resource_id": "account_005",
  "operation": "REPORT_REMAINING_RECORD",
  "state": "PRESENT",
  "evidence_id": "evidence_01"
}
```

### 3.3 The 15 Allowed Operations & Canonical Phase/Operation Ranks
| Phase (`phase_rank`) | Op Rank (`op_rank`) | `operation` | Required `state` | Trigger Condition |
| :--- | :---: | :--- | :--- | :--- |
| **FINDING** (`1`) | `1` | `REPORT_REMAINING_RECORD` | `PRESENT` | Record required to be deleted still exists at `audit_at`. |
| **FINDING** (`1`) | `2` | `REPORT_EXPOSED_PII` | `PRESENT` | Retained/tombstone/redacted/anonymized record still exposes prohibited PII (`name`, `email`, `phone`, `email_hash`, etc.). |
| **FINDING** (`1`) | `3` | `REPORT_ACTIVE_DATA_FLOW` | `ACTIVE` | Active sync, replication, or export pipeline can copy or recreate the user's data. |
| **FINDING** (`1`) | `4` | `REPORT_RESTORE_RISK` | `ACTIVE` | Unblocked backup or restore path can reintroduce deleted user data. |
| **REMEDIATION** (`2`) | `1` | `DISABLE_DATA_FLOW` | `DISABLED` | Disable active sync/replication/export pipeline before modifying dependent records. |
| **REMEDIATION** (`2`) | `2` | `BLOCK_RESTORE` | `BLOCKED` | Block/suppress unsafe backup or restore path before modifying dependent records. |
| **REMEDIATION** (`2`) | `3` | `DELETE_RECORD` | `ABSENT` | Delete record where policy mandates full removal. |
| **REMEDIATION** (`2`) | `4` | `REDACT_RECORD` | `REDACTED` | Strip prohibited direct identifiers while preserving allowed tombstone/record (`user_id`). |
| **REMEDIATION** (`2`) | `5` | `ANONYMIZE_RECORD` | `ANONYMIZED` | Irreversibly unlink record from `user_id` and all personal identifiers. |
| **VERIFICATION** (`3`) | `1` | `VERIFY_RECORD_ABSENT` | `ABSENT` | Confirm deleted record is absent. |
| **VERIFICATION** (`3`) | `2` | `VERIFY_RECORD_PRESENT` | `PRESENT` | Confirm mandatory retained record (e.g., security/audit retention) remains present. |
| **VERIFICATION** (`3`) | `3` | `VERIFY_RECORD_REDACTED` | `REDACTED` | Confirm redacted/tombstone record has no prohibited PII. |
| **VERIFICATION** (`3`) | `4` | `VERIFY_RECORD_ANONYMIZED` | `ANONYMIZED` | Confirm anonymized record has no link to `user_id` or PII. |
| **VERIFICATION** (`3`) | `5` | `VERIFY_DATA_FLOW_DISABLED` | `DISABLED` | Confirm data flow is disabled. |
| **VERIFICATION** (`3`) | `6` | `VERIFY_RESTORE_BLOCKED` | `BLOCKED` | Confirm backup/restore risk is blocked. |

### 3.4 Step Ordering & Dependency Rules (`problem_statement.md` & `AGENTS.md` §6.5)
1. **Primary Sort:** `phase_rank` ascending (`FINDING` $\rightarrow$ `REMEDIATION` $\rightarrow$ `VERIFICATION`).
2. **Secondary Sort:** `op_rank` ascending (1..4 in `FINDING`, 1..5 in `REMEDIATION`, 1..6 in `VERIFICATION`).
3. **Dependency & Tie-Breaking Sort:**
   - Notice that `op_rank` in `REMEDIATION` automatically places `DISABLE_DATA_FLOW` (`1`) and `BLOCK_RESTORE` (`2`) before `DELETE_RECORD` (`3`), `REDACT_RECORD` (`4`), and `ANONYMIZE_RECORD` (`5`).
   - Within the same `(phase, operation)`, process downstream copies/replicas before source records when required by dependency rules, and tie-break deterministically by `(system_id, resource_id)` ascending. Verify exact tie-breaking behavior against all 32 cases in `dataset/sample_output.csv`.
4. **Step Numbering:** Assign `step_no` sequentially starting from `1` (`1, 2, ..., N`) after sorting.

### 3.5 Evidence Citation Rules (`evidence_id`)
- Valid `evidence_id` values come from three sources only:
  1. `file_id` from `dataset/evidence_files.csv`
  2. `activity_id` from `dataset/system_activity.csv`
  3. `audit_id` from `dataset/user_audit_log.csv`
- **In `COMPLETE` cases:** Every `VERIFICATION` step **must** carry the valid `evidence_id` proving compliance at `audit_at`.
- **In `INCOMPLETE` cases:**
  - Every `FINDING` step **must** carry the valid `evidence_id` proving the violation at `audit_at`.
  - Every `REMEDIATION` step **must** have `"evidence_id": ""`.
  - Every post-remediation `VERIFICATION` step **must** have `"evidence_id": ""` (verify against `sample_output.csv` whether already-compliant retained/absent resources in an `INCOMPLETE` case cite their existing `evidence_id` or `""`, and mirror `sample_output.csv` 100%).

---

## 4. Step-by-Step Technical Implementation Blueprint

Create a clean, modular architecture inside `code/`:

```text
code/
├── main.py                  # Entry point: runs full pipeline and writes ./output.csv
├── config.py                # Paths, constants, operation ranks, model/token tracker
├── explore.py               # Diagnostic script to inspect dataset & sample_output.csv
├── intent_classifier.py     # Phase A: Multilingual request_text intent gate
├── identity_resolver.py     # Phase B: Current + historical identity graph (<= audit_at)
├── evidence_indexer.py      # Phase C: SQL, JSON, Log, PDF, and Image parsers
├── state_reconstructor.py   # Phase D: Point-in-time state reconstruction at audit_at
├── policy_engine.py         # Phase E: Rule evaluation, step generation, canonical sorting
├── evaluate.py              # Phase F: Local benchmark scorer (32 samples + >=3 custom cases)
└── evaluation/
    ├── evaluation_report.md # Required accuracy, error analysis & custom cases report
    └── usage_report.md      # Required token & cost accounting report
```

### Step 1: Deep Ground-Truth Inspection (`code/explore.py`)
Before writing the solver logic, write and run `code/explore.py` to inspect:
1. All rows and columns of `dataset/deletion_rules.csv` and `dataset/evidence_files.csv`.
2. Every single case in `dataset/sample_deletion_requests.csv` joined with `dataset/sample_output.csv`.
3. Specifically verify:
   - What exact `system_id` and `resource_id` naming conventions appear across `.sql`, `.json`, `.log`, `.pdf`, and `.png`/`.jpg` evidence files.
   - How `evidence_id` precedence works when both an `activity_id` in `system_activity.csv` and a `file_id` in `evidence_files.csv` reference the same resource before `audit_at`.
   - Whether `VERIFICATION` steps in `INCOMPLETE` cases include *only* the remediated resources or *all* user resources across systems (including already-compliant ones), and whether already-compliant resources in `INCOMPLETE` cases use `evidence_id: ""` or their existing `evidence_id`.
   - **Known Sample Dataset Quirks to Handle Cleanly:** In the upstream repository (`commit 0e07b3d`, GitHub Issue #19), `sample_output.csv` for `case_18` (`audit_record_6645`) and `case_20` (`audit_record_5569`) had sample answer IDs regenerated without matching `security_service` evidence entries. Keep your code 100% evidence-driven (never hardcode those two IDs) and document this exact finding in `code/evaluation/evaluation_report.md`.

### Step 2: Phase A — Multilingual Request Intent Gate (`code/intent_classifier.py`)
- Analyze `request_text` across all 32 sample requests and 518 evaluation requests.
- Requests appear in multiple languages (English, Spanish, French, German, Portuguese, Japanese, etc.) and fall into distinct intent categories:
  1. **Valid Deletion / Erasure (`True`):** Explicit requests to delete account, erase personal data, exercise GDPR Right to Erasure / CCPA Right to Delete, or remove all personal information.
  2. **Non-Deletion (`False` $\rightarrow$ `NOT_APPLICABLE`):**
     - Data access / copy / export / portability requests.
     - Email / phone / profile update or correction requests.
     - Marketing / newsletter / promotional opt-out or unsubscribe requests.
     - Order status, refund, billing, or password reset requests without account/data deletion.
- **Implementation:**
  - Extract all unique normalized phrasing patterns across `sample_deletion_requests.csv` and `deletion_requests.csv`.
  - Build a deterministic multilingual pattern/keyword ruleset and verify any novel/ambiguous sentences via a batched LLM call (recording exact input/output tokens in `config.py`'s usage tracker).
  - If classified as non-deletion, immediately return `deletion_status = "NOT_APPLICABLE"` and `steps_json = []`.

### Step 3: Phase B — Current & Historical Identity Graph Resolver (`code/identity_resolver.py`)
- A user's request provides `email`, `requested_at`, and `audit_at`.
- Because users change their email, phone, or name over time, searching only by the request's `email` will miss ghost data stored under old identifiers!
- **Algorithm:**
  1. Look up `email` (case-insensitive) in `user_identities.csv` (`email`) AND in `user_audit_log.csv` (`old_value` or `new_value` where `timestamp <= audit_at`).
  2. Identify the canonical `user_id`.
  3. Traverse `user_identities.csv` and `user_audit_log.csv` (filtering strictly to `timestamp <= audit_at`) to build a complete `UserIdentityProfile`:
     - `user_id`: canonical user ID.
     - `emails`: set of all current and historical emails known at or before `audit_at`.
     - `email_hashes`: set of `email_hash` values from `user_identities.csv` / `user_audit_log.csv` PLUS dynamically computed SHA-256 and MD5 hex digests of every email in `emails`.
     - `phones`: set of all current and historical phone numbers (both raw and digits-only normalized).
     - `names`: set of all current and historical full names.
     - `audit_records`: list of `(audit_id, timestamp, field, old_value, new_value)` for `timestamp <= audit_at`.

### Step 4: Phase C — Multimodal Evidence Indexer (`code/evidence_indexer.py`)
Parse every file listed in `dataset/evidence_files.csv` once at startup and index every record by `(file_id, captured_at, source_system, system_id, resource_id, user_id, identifiers, pii_fields_present, record_state)`:
1. **Database Snapshots (`dataset/evidence/databases/*.sql`):**
   - Load each `.sql` file into an in-memory SQLite instance (`sqlite3.connect(":memory:")`) using `executescript()`.
   - Query `sqlite_master` to list all tables, inspect column names, and fetch all rows.
   - Determine which `system_id` (including replica designation, e.g., primary vs regional/reporting/failover replica from `evidence_files.csv` or table metadata) and `resource_id` each row corresponds to.
   - Check which PII fields (`name`, `email`, `phone`, `email_hash`, address, etc.) are non-null/non-redacted vs redacted (`NULL`, `[REDACTED]`, empty, or masked) vs anonymized (`user_id` unlinked/null/anonymized).
2. **Structured Records & Logs (`dataset/evidence/records/*`, `dataset/evidence/logs/*`):**
   - Parse `.json` files (objects, arrays, search index dumps, backup manifests, sync configs) and `.log` files.
   - Extract records, active data flows (`sync`, `export`, `replication` status), and backup/restore configurations (`restore_blocked`, retention status, etc.).
3. **PDF Documents (`dataset/evidence/documents/*.pdf`):**
   - Extract text and tabular content using `pypdf` / `pdfplumber` / `fitz` (PyMuPDF) or pure-Python FlateDecode stream extraction if external libraries are unavailable.
   - Parse structured fields (`system_id`, `resource_id`, `user_id`, `email`, status, timestamps) from the extracted text.
4. **Images / Screenshots (`dataset/evidence/images/*.png`, `*.jpg`):**
   - Extract all text and UI state from every image in `dataset/evidence/images/` using a multimodal Vision LLM call or OCR (`EasyOCR` / `PaddleOCR` / `pytesseract`), logging any LLM token usage for `usage_report.md`.
   - Embed a deterministic Python dictionary fallback of parsed image records directly inside a `.py` module (e.g., `code/parsed_visual_evidence.py`) so `python code/main.py` runs fast, deterministically, and remains 100% visible to the code grader.

### Step 5: Phase D — Point-in-Time State Reconstructor at `audit_at` (`code/state_reconstructor.py`)
For each valid deletion request `(case_id, user_profile, requested_at, audit_at)`:
1. **Enforce the Time Horizon (`AGENTS.md` §6.4):**
   - Discard any evidence file where `captured_at > audit_at`.
   - Discard any `system_activity.csv` event where `timestamp > audit_at`.
   - Discard any `user_audit_log.csv` event where `timestamp > audit_at`.
2. **Gather Candidate Resources Across All Systems:**
   - Find all resources matching `user_profile.user_id`, `user_profile.emails`, `user_profile.email_hashes`, `user_profile.phones`, or `user_profile.names` in filtered `system_activity.csv`, filtered `evidence_files.csv` snapshots, and `user_audit_log.csv`.
3. **Apply the Evidence Truth Hierarchy (`AGENTS.md` §6.5 & §6.6):**
   - `reported_status` on the request and `reported_result` in `system_activity.csv` are **operational claims, not proof** when contradicted by later evidence or snapshots.
   - For each `(system_id, resource_id)`:
     - Compare the latest `system_activity.csv` event ($\le$ `audit_at`) with all evidence snapshots (`captured_at <= audit_at`) covering that system/replica.
     - If an evidence snapshot captured at or after a claimed deletion shows the record is still `PRESENT` (or still exposes prohibited PII), or if a restore/sync activity recreated the record before `audit_at`, the actual state at `audit_at` is non-compliant (`PRESENT` / `EXPOSED_PII`).
     - If a primary database deleted the record, check regional/reporting/failover replica snapshots ($\le$ `audit_at`) for replication drift.
     - Check for any `ACTIVE` data flow (`REPORT_ACTIVE_DATA_FLOW`) or unblocked backup/restore risk (`REPORT_RESTORE_RISK`) affecting the user at `audit_at`.
     - Select the exact winning `evidence_id` (`file_id`, `activity_id`, or `audit_id`) according to the precedence rules verified against `sample_output.csv`.

### Step 6: Phase E — Policy Engine & Step Generator (`code/policy_engine.py`)
Evaluate every reconstructed resource/flow/backup state for the user against `dataset/deletion_rules.csv`:

1. **Map Policy Rules to Findings, Remediations, and Verifications:**
   - **Policy = `DELETE`:**
     - If record is `ABSENT` at `audit_at`: Compliant $\rightarrow$ `VERIFY_RECORD_ABSENT` (`state="ABSENT"`, `evidence_id=<proof>`).
     - If record is `PRESENT` at `audit_at`: Violation $\rightarrow$
       - `FINDING`: `REPORT_REMAINING_RECORD` (`state="PRESENT"`, `evidence_id=<proof>`)
       - `REMEDIATION`: `DELETE_RECORD` (`state="ABSENT"`, `evidence_id=""`)
       - `VERIFICATION`: `VERIFY_RECORD_ABSENT` (`state="ABSENT"`, `evidence_id=""`)
   - **Policy = `REDACT` or `ACCOUNT_TOMBSTONE`:**
     - `ACCOUNT_TOMBSTONE` / `REDACT` allows keeping the record shell and `user_id`, but prohibits direct PII (`name`, `email`, `phone`, `email_hash`, etc.).
     - If record is present and all prohibited PII is stripped at `audit_at`: Compliant $\rightarrow$ `VERIFY_RECORD_REDACTED` (`state="REDACTED"`, `evidence_id=<proof>`).
     - If record still exposes any prohibited PII at `audit_at`: Violation $\rightarrow$
       - `FINDING`: `REPORT_EXPOSED_PII` (`state="PRESENT"`, `evidence_id=<proof>`)
       - `REMEDIATION`: `REDACT_RECORD` (`state="REDACTED"`, `evidence_id=""`)
       - `VERIFICATION`: `VERIFY_RECORD_REDACTED` (`state="REDACTED"`, `evidence_id=""`)
   - **Policy = `ANONYMIZE`:**
     - Requires removing both `user_id` linkage and all PII.
     - If properly anonymized at `audit_at`: Compliant $\rightarrow$ `VERIFY_RECORD_ANONYMIZED` (`state="ANONYMIZED"`, `evidence_id=<proof>`).
     - If still linked to `user_id` or PII at `audit_at`: Violation $\rightarrow$
       - `FINDING`: `REPORT_EXPOSED_PII` (`state="PRESENT"`, `evidence_id=<proof>`)
       - `REMEDIATION`: `ANONYMIZE_RECORD` (`state="ANONYMIZED"`, `evidence_id=""`)
       - `VERIFICATION`: `VERIFY_RECORD_ANONYMIZED` (`state="ANONYMIZED"`, `evidence_id=""`)
   - **Policy = `RETAIN`:**
     - Record must remain present (e.g., mandatory security/compliance audit logs) $\rightarrow$ `VERIFY_RECORD_PRESENT` (`state="PRESENT"`, `evidence_id=<proof>`).
   - **Active Data Flow Risk:**
     - If active at `audit_at`: Violation $\rightarrow$
       - `FINDING`: `REPORT_ACTIVE_DATA_FLOW` (`state="ACTIVE"`, `evidence_id=<proof>`)
       - `REMEDIATION`: `DISABLE_DATA_FLOW` (`state="DISABLED"`, `evidence_id=""`)
       - `VERIFICATION`: `VERIFY_DATA_FLOW_DISABLED` (`state="DISABLED"`, `evidence_id=""`)
     - If already disabled at `audit_at` (and applicable to the user's audit scope): `VERIFY_DATA_FLOW_DISABLED` (`state="DISABLED"`, `evidence_id=<proof>`).
   - **Backup / Restore Risk:**
     - If unblocked at `audit_at`: Violation $\rightarrow$
       - `FINDING`: `REPORT_RESTORE_RISK` (`state="ACTIVE"`, `evidence_id=<proof>`)
       - `REMEDIATION`: `BLOCK_RESTORE` (`state="BLOCKED"`, `evidence_id=""`)
       - `VERIFICATION`: `VERIFY_RESTORE_BLOCKED` (`state="BLOCKED"`, `evidence_id=""`)
     - If already blocked at `audit_at` (and applicable to the user's audit scope): `VERIFY_RESTORE_BLOCKED` (`state="BLOCKED"`, `evidence_id=<proof>`).
2. **Determine `deletion_status`:**
   - If `len(findings) > 0`: `deletion_status = "INCOMPLETE"`.
   - Else: `deletion_status = "COMPLETE"`.
3. **Sort & Number Steps:**
   - Sort all steps using `(phase_rank, op_rank, dependency_rank, system_id, resource_id)`.
   - Re-index `step_no` from `1` to `len(steps)`.

### Step 7: Phase F — Local Evaluation Harness & Custom Cases (`code/evaluate.py`)
Build `code/evaluate.py` to score predictions on `dataset/sample_deletion_requests.csv` against `dataset/sample_output.csv`:
1. **Metrics to Compute & Print:**
   - **Case-Level Deletion-Status Accuracy:** Exact match rate on `deletion_status` across the 32 sample cases.
   - **Step-Level Precision, Recall, and F1:** Matching `(phase, system_id, resource_id, operation, state, evidence_id)`.
   - **Field-Level Accuracy:** Per-field match rate (`phase`, `system_id`, `resource_id`, `operation`, `state`, `evidence_id`, `step_no`).
   - **Full Sequence Exact Match Accuracy:** Percentage of cases where the entire `steps_json` array matches ground truth identically.
2. **Design & Run $\ge 3$ Additional Custom Evaluation Cases:**
   Include at least 3 synthetic stress-test cases in `code/evaluate.py` and document them in `code/evaluation/evaluation_report.md`:
   - `custom_case_01` (**Multi-Hop Historical Email & Replica Drift**): User changed email twice in `user_audit_log.csv` prior to `audit_at`; primary DB deleted the record, but a regional replica SQL snapshot captured before `audit_at` still retains the record under the historical email.
   - `custom_case_02` (**Post-`audit_at` Evidence Horizon Trap**): A record is `PRESENT` at `audit_at`, and a deletion activity + clean snapshot occur 10 minutes *after* `audit_at`. Verifies that the agent ignores post-`audit_at` evidence and rightly reports `INCOMPLETE`.
   - `custom_case_03` (**Tombstone PII Exposure + Active Sync & Restore Risk**): An `ACCOUNT_TOMBSTONE` record removed `name` and `email` but left `email_hash` exposed, while an active sync pipeline and unblocked backup path remain active at `audit_at`. Verifies `DISABLE_DATA_FLOW` and `BLOCK_RESTORE` precede `REDACT_RECORD`.

### Step 8: Phase G — Run Full 518-Case Pipeline & Write Required Reports
1. Execute `python code/main.py` to generate `./output.csv` for all 518 cases in `dataset/deletion_requests.csv`.
2. **Generate `code/evaluation/evaluation_report.md`:**
   Must contain:
   - Executive summary of the deletion-audit architecture.
   - Benchmark results table on `sample_deletion_requests.csv` (Case-level status accuracy, step-level precision/recall/F1, field-level accuracy, sequence exact-match accuracy).
   - Detailed breakdown of the $\ge 3$ custom evaluation cases (`custom_case_01`, `custom_case_02`, `custom_case_03`) and their pass results.
   - Failure modes discovered during iterative validation (e.g., historical email/hash linkage, SQLite replica drift detection, post-`audit_at` evidence filtering, evidence citation precedence, and analysis of upstream sample anomalies in `case_18`/`case_20`) and the code improvements implemented to resolve them.
3. **Generate `code/evaluation/usage_report.md`:**
   Must contain:
   - Exact model provider(s) and model identifier(s) used.
   - Total model calls, input tokens, output tokens, total tokens, and average tokens per request across the 518 evaluation cases.
   - Estimated total cost (USD) and average cost per request (USD), broken down by model and overall total.
   - *(Also copy `evaluation_report.md` and `usage_report.md` to `./evaluation/` in the repo root if helpful, while ensuring `code/evaluation/evaluation_report.md` and `code/evaluation/usage_report.md` exist inside `code/` for `code.zip`.)*

---

## 5. Final Verification & Packaging Commands (Windows PowerShell)

Run the following verification checks before submitting on HackerRank:

### 5.1 Validate `./output.csv` Deterministically
Run a quick validation one-liner to confirm schema integrity:

```python
import csv, json

with open("output.csv", "r", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

assert len(rows) == 518, f"Expected 518 rows, got {len(rows)}"
assert [r["case_id"] for r in rows] == sorted(r["case_id"] for r in rows), "Not sorted by case_id!"

allowed_statuses = {"COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"}
for r in rows:
    assert r["deletion_status"] in allowed_statuses
    steps = json.loads(r["steps_json"])
    if r["deletion_status"] == "NOT_APPLICABLE":
        assert steps == [], f"NOT_APPLICABLE must have empty steps: {r['case_id']}"
    else:
        assert len(steps) > 0, f"Empty steps on {r['case_id']}"
        for idx, s in enumerate(steps, 1):
            assert s["step_no"] == idx
            assert set(s.keys()) == {"step_no", "phase", "system_id", "resource_id", "operation", "state", "evidence_id"}
print("output.csv PASSED all checks (518 valid rows)!")
```

### 5.2 Package `code.zip`
Ensure `README.md` is updated, remove `__pycache__` and any nested archives inside `code/`, and create `code.zip`:

```powershell
Get-ChildItem -Path code -Include __pycache__, *.pyc, *.pyo, *.zip, *.tar, *.gz, *.tgz -Recurse -Force | Remove-Item -Recurse -Force
Compress-Archive -Path README.md, code -DestinationPath code.zip -Force
```

### 5.3 Verify `./log.txt` (`chat_transcript`)
Confirm `./log.txt` starts with `SESSION START`, includes every turn in `AGENTS.md` §5.2 format, has valid `tool=` and `model=` lines in every entry, and contains zero secrets.

### 5.4 Package `agent-trace.zip`
Per `agent_trace_instructions.md`, copy your coding agent's raw session trace files for this challenge into `agent-trace/<tool-name>/` (e.g., `agent-trace/claude-code/`, `agent-trace/codex/`, `agent-trace/cursor/`, `agent-trace/antigravity/`, or `agent-trace/opencode/`), strip any secrets or auth files, and archive:

```powershell
Compress-Archive -Path .\agent-trace -DestinationPath .\agent-trace.zip -Force
```

---

## 6. Final 4-Deliverable Submission Checklist
- [ ] **`output.csv`** — Present in repository root, 1 header + 518 sorted rows, valid `steps_json`.
- [ ] **`code.zip`** — Contains `README.md` and `code/` (including `code/main.py`, `code/evaluation/evaluation_report.md`, and `code/evaluation/usage_report.md`), with no nested archives or secrets.
- [ ] **`log.txt`** — Present in repository root, compliant with `AGENTS.md` §5.1–§5.2, uploaded to the `chat_transcript` slot.
- [ ] **`agent-trace.zip`** — Contains `agent-trace/<tool-name>/...` session logs per `agent_trace_instructions.md`.