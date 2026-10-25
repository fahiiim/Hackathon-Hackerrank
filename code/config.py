"""
Configuration, constants, paths, and token/cost tracker for the Ghost Data Still Exists deletion-audit agent.
"""

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Dict, List, Optional

# Base paths
CODE_DIR = Path(__file__).resolve().parent
REPO_ROOT = CODE_DIR.parent
DATASET_DIR = REPO_ROOT / "dataset"
EVIDENCE_DIR = DATASET_DIR / "evidence"

# Dataset file paths
DELETION_REQUESTS_PATH = DATASET_DIR / "deletion_requests.csv"
SAMPLE_DELETION_REQUESTS_PATH = DATASET_DIR / "sample_deletion_requests.csv"
SAMPLE_OUTPUT_PATH = DATASET_DIR / "sample_output.csv"
USER_IDENTITIES_PATH = DATASET_DIR / "user_identities.csv"
USER_AUDIT_LOG_PATH = DATASET_DIR / "user_audit_log.csv"
SYSTEM_ACTIVITY_PATH = DATASET_DIR / "system_activity.csv"
DELETION_RULES_PATH = DATASET_DIR / "deletion_rules.csv"
EVIDENCE_FILES_PATH = DATASET_DIR / "evidence_files.csv"
OUTPUT_CSV_PATH = REPO_ROOT / "output.csv"

# Canonical Phase Ranks
PHASE_RANKS: Dict[str, int] = {
    "FINDING": 1,
    "REMEDIATION": 2,
    "VERIFICATION": 3,
}

# Canonical Operation Ranks within Phase
OPERATION_RANKS: Dict[str, Dict[str, int]] = {
    "FINDING": {
        "REPORT_REMAINING_RECORD": 1,
        "REPORT_EXPOSED_PII": 2,
        "REPORT_ACTIVE_DATA_FLOW": 3,
        "REPORT_RESTORE_RISK": 4,
    },
    "REMEDIATION": {
        "DISABLE_DATA_FLOW": 1,
        "BLOCK_RESTORE": 2,
        "DELETE_RECORD": 3,
        "REDACT_RECORD": 4,
        "ANONYMIZE_RECORD": 5,
    },
    "VERIFICATION": {
        "VERIFY_RECORD_ABSENT": 1,
        "VERIFY_RECORD_PRESENT": 2,
        "VERIFY_RECORD_REDACTED": 3,
        "VERIFY_RECORD_ANONYMIZED": 4,
        "VERIFY_DATA_FLOW_DISABLED": 5,
        "VERIFY_RESTORE_BLOCKED": 6,
    },
}

# Allowed Operation -> State mapping
OPERATION_STATE_MAP: Dict[str, str] = {
    "REPORT_REMAINING_RECORD": "PRESENT",
    "REPORT_EXPOSED_PII": "PRESENT",
    "REPORT_ACTIVE_DATA_FLOW": "ACTIVE",
    "REPORT_RESTORE_RISK": "ACTIVE",
    "DISABLE_DATA_FLOW": "DISABLED",
    "BLOCK_RESTORE": "BLOCKED",
    "DELETE_RECORD": "ABSENT",
    "REDACT_RECORD": "REDACTED",
    "ANONYMIZE_RECORD": "ANONYMIZED",
    "VERIFY_RECORD_ABSENT": "ABSENT",
    "VERIFY_RECORD_PRESENT": "PRESENT",
    "VERIFY_RECORD_REDACTED": "REDACTED",
    "VERIFY_RECORD_ANONYMIZED": "ANONYMIZED",
    "VERIFY_DATA_FLOW_DISABLED": "DISABLED",
    "VERIFY_RESTORE_BLOCKED": "BLOCKED",
}

# Allowed Deletion Statuses
ALLOWED_STATUSES = {"COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"}

# Pricing constants for usage report (USD per 1M tokens)
# Gemini 3.8 Flash benchmark pricing
INPUT_COST_PER_MILLION = 0.075
OUTPUT_COST_PER_MILLION = 0.30

@dataclass
class UsageTracker:
    model_provider: str = "Google"
    model_name: str = "Gemini 3.8 Flash (High)"
    model_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    requests_processed: int = 0

    def add_call(self, input_toks: int, output_toks: int) -> None:
        self.model_calls += 1
        self.input_tokens += input_toks
        self.output_tokens += output_toks

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def total_cost_usd(self) -> float:
        input_cost = (self.input_tokens / 1_000_000.0) * INPUT_COST_PER_MILLION
        output_cost = (self.output_tokens / 1_000_000.0) * OUTPUT_COST_PER_MILLION
        return input_cost + output_cost

    @property
    def avg_tokens_per_request(self) -> float:
        if self.requests_processed == 0:
            return 0.0
        return self.total_tokens / float(self.requests_processed)

    @property
    def avg_cost_per_request_usd(self) -> float:
        if self.requests_processed == 0:
            return 0.0
        return self.total_cost_usd / float(self.requests_processed)

# Global tracker instance
USAGE_TRACKER = UsageTracker()
