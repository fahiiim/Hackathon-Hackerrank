"""
Deep Ground-Truth Inspection and Dataset Exploration Script (Step 1)
"""

import csv
import json
from pathlib import Path
from collections import defaultdict, Counter

from config import (
    DELETION_RULES_PATH,
    EVIDENCE_FILES_PATH,
    SAMPLE_DELETION_REQUESTS_PATH,
    SAMPLE_OUTPUT_PATH,
    SYSTEM_ACTIVITY_PATH,
    USER_IDENTITIES_PATH,
    USER_AUDIT_LOG_PATH,
    EVIDENCE_DIR,
)

def run_exploration():
    print("=" * 80)
    print("STEP 1: GROUND-TRUTH & DATASET EXPLORATION")
    print("=" * 80)

    # 1. Inspect deletion_rules.csv
    print("\n--- 1. DELETION RULES (dataset/deletion_rules.csv) ---")
    with open(DELETION_RULES_PATH, mode="r", encoding="utf-8") as f:
        rules = list(csv.DictReader(f))
    print(f"Total rules: {len(rules)}")
    for r in rules:
        print(f"  [{r['rule_id']}] Category: {r['data_category']:<22} Action: {r['required_action']:<10} Condition: {r['condition']}")

    # 2. Inspect evidence_files.csv
    print("\n--- 2. EVIDENCE MANIFEST (dataset/evidence_files.csv) ---")
    with open(EVIDENCE_FILES_PATH, mode="r", encoding="utf-8") as f:
        evidence_files = list(csv.DictReader(f))
    print(f"Total evidence files: {len(evidence_files)}")
    ext_counter = Counter(Path(e["file_path"]).suffix for e in evidence_files)
    origin_counter = Counter(e["origin"] for e in evidence_files)
    print(f"File extensions: {dict(ext_counter)}")
    print(f"Unique origins ({len(origin_counter)} total):")
    for origin, cnt in origin_counter.most_common(10):
        print(f"  - {origin}: {cnt} files")

    # 3. Inspect sample_deletion_requests.csv & sample_output.csv
    print("\n--- 3. SAMPLE CASES & GROUND TRUTH (case_01 to case_32) ---")
    with open(SAMPLE_DELETION_REQUESTS_PATH, mode="r", encoding="utf-8") as f:
        sample_requests = {r["case_id"]: r for r in csv.DictReader(f)}
    with open(SAMPLE_OUTPUT_PATH, mode="r", encoding="utf-8") as f:
        sample_outputs = {r["case_id"]: r for r in csv.DictReader(f)}

    print(f"Sample requests count: {len(sample_requests)}, Sample outputs count: {len(sample_outputs)}")

    status_counts = Counter(o["deletion_status"] for o in sample_outputs.values())
    print(f"Status distribution in sample_output.csv: {dict(status_counts)}")

    # Inspect steps in sample outputs
    all_phases = Counter()
    all_ops = Counter()
    all_systems = Counter()
    evidence_citation_types = Counter()
    incomplete_verif_evidence_ids = Counter()
    complete_verif_evidence_ids = Counter()

    print("\nDetailed Case Breakdown:")
    for cid in sorted(sample_requests.keys()):
        req = sample_requests[cid]
        out = sample_outputs[cid]
        status = out["deletion_status"]
        steps = json.loads(out["steps_json"])
        print(f"\n[{cid}] Status: {status} | Email: {req['email']} | Steps: {len(steps)} | Audit At: {req['audit_at']}")
        
        for s in steps:
            phase = s["phase"]
            op = s["operation"]
            sys_id = s["system_id"]
            res_id = s["resource_id"]
            ev_id = s["evidence_id"]
            state = s["state"]
            all_phases[phase] += 1
            all_ops[op] += 1
            all_systems[sys_id] += 1

            if status == "COMPLETE":
                complete_verif_evidence_ids[ev_id] += 1
            elif status == "INCOMPLETE":
                if phase == "VERIFICATION":
                    incomplete_verif_evidence_ids[ev_id] += 1

            # Check citation type
            if ev_id == "":
                evidence_citation_types["empty"] += 1
            elif ev_id.startswith("evidence_"):
                evidence_citation_types["file_id"] += 1
            elif ev_id.startswith("activity_"):
                evidence_citation_types["activity_id"] += 1
            elif ev_id.startswith("audit_"):
                evidence_citation_types["audit_id"] += 1
            else:
                evidence_citation_types["other"] += 1

            print(f"   Step {s['step_no']:2d}: {phase:<12} | {sys_id:<20} | {res_id:<18} | {op:<26} | State: {state:<10} | Ev: {ev_id}")

    print("\n--- 4. STEP & OPERATION TOTALS ACROSS SAMPLES ---")
    print(f"Phases: {dict(all_phases)}")
    print(f"Operations: {dict(all_ops)}")
    print(f"Systems: {dict(all_systems)}")
    print(f"Evidence citation categories: {dict(evidence_citation_types)}")
    print(f"Verification evidence IDs in COMPLETE cases: {dict(complete_verif_evidence_ids)}")
    print(f"Verification evidence IDs in INCOMPLETE cases: {dict(incomplete_verif_evidence_ids)}")

    # 4. Check system_activity.csv and user_audit_log.csv
    print("\n--- 5. SYSTEM ACTIVITY & AUDIT LOG OVERVIEW ---")
    with open(SYSTEM_ACTIVITY_PATH, mode="r", encoding="utf-8") as f:
        activities = list(csv.DictReader(f))
    print(f"Total system activities: {len(activities)}")
    act_types = Counter(a["event_type"] for a in activities)
    print(f"Activity event types: {dict(act_types)}")

    with open(USER_AUDIT_LOG_PATH, mode="r", encoding="utf-8") as f:
        audit_entries = list(csv.DictReader(f))
    print(f"\nTotal user audit log entries: {len(audit_entries)}")
    fields_mutated = Counter(a["field_name"] for a in audit_entries)
    print(f"Mutated fields: {dict(fields_mutated)}")

    with open(USER_IDENTITIES_PATH, mode="r", encoding="utf-8") as f:
        users = list(csv.DictReader(f))
    print(f"Total user identities: {len(users)}")

    # 5. Check Known Upstream Quirks in case_18 and case_20
    print("\n--- 6. QUIRK CHECK: case_18 and case_20 audit_records ---")
    for check_cid in ["case_18", "case_20"]:
        steps = json.loads(sample_outputs[check_cid]["steps_json"])
        sec_steps = [s for s in steps if s["system_id"] == "security_service"]
        print(f"Security service steps in {check_cid}: {sec_steps}")
        for ss in sec_steps:
            res_id = ss["resource_id"]
            # check if res_id appears in system_activity or user_audit_log or evidence_files
            found_in_act = [a for a in activities if a["resource_id"] == res_id]
            print(f"  Checking {res_id} in system_activity: {len(found_in_act)} matches")

if __name__ == "__main__":
    run_exploration()
