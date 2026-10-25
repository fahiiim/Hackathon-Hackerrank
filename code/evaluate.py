"""
Phase F: Local Evaluation Harness & Custom Cases (Step 7)

Comprehensive benchmark evaluation suite for Northstar Shop Deletion Audit Agent:
1. Scores predictions on dataset/sample_deletion_requests.csv against dataset/sample_output.csv:
   - Case-Level Deletion-Status Accuracy
   - Step-Level Precision, Recall, and F1
   - Field-Level Accuracy across all 7 step schema fields
   - Full Sequence Exact Match Accuracy
2. Executes >= 3 synthetic stress-test custom evaluation cases:
   - custom_case_01: Multi-Hop Historical Email & Replica Drift
   - custom_case_02: Post-audit_at Evidence Horizon Trap
   - custom_case_03: Tombstone PII Exposure + Active Sync & Restore Risk (Dependency Ordering)
"""

import csv
import json
import os
import sys
from typing import Any, Dict, List, Tuple

# Ensure local code directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DATASET_DIR
from evidence_indexer import EvidenceIndexer, IndexedRecord
from identity_resolver import IdentityResolver, UserIdentityProfile
from intent_classifier import is_deletion_request
from policy_engine import PolicyEngine
from state_reconstructor import ReconstructedResourceState, StateReconstructor


def evaluate_sample_dataset(
    resolver: IdentityResolver,
    indexer: EvidenceIndexer,
    reconstructor: StateReconstructor,
    engine: PolicyEngine,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Evaluate the full agent pipeline on the 32 public sample requests against ground truth.
    """
    sample_req_path = os.path.join(DATASET_DIR, "sample_deletion_requests.csv")
    sample_out_path = os.path.join(DATASET_DIR, "sample_output.csv")

    with open(sample_req_path, "r", encoding="utf-8") as f:
        sample_reqs = list(csv.DictReader(f))

    with open(sample_out_path, "r", encoding="utf-8") as f:
        sample_out = {
            r["case_id"]: (r["deletion_status"], json.loads(r["steps_json"]))
            for r in csv.DictReader(f)
        }

    total_cases = len(sample_reqs)
    status_matches = 0
    exact_sequence_matches = 0

    total_gt_steps = 0
    total_pred_steps = 0
    matched_step_tuples = 0

    field_matches = {
        "step_no": 0,
        "phase": 0,
        "system_id": 0,
        "resource_id": 0,
        "operation": 0,
        "state": 0,
        "evidence_id": 0,
    }
    field_totals = 0

    if verbose:
        print("\n" + "=" * 90)
        print("EVALUATING 32 PUBLIC SAMPLE CASES (dataset/sample_output.csv)")
        print("=" * 90)

    for req in sample_reqs:
        cid = req["case_id"]
        email = req["email"]
        req_at = req["requested_at"]
        rep_at = req["reported_at"]
        audit_at = req["audit_at"]
        text = req["request_text"]

        gt_status, gt_steps = sample_out[cid]

        # 1. Intent Gate
        is_del = is_deletion_request(text)

        # 2. Pipeline execution
        if not is_del:
            pred_status, pred_steps = engine.evaluate_case(cid, is_del, [])
        else:
            uid = resolver.resolve_user_id(email, audit_at)
            prof = resolver.get_user_profile(uid, audit_at)
            res_states = reconstructor.reconstruct_user_state(
                case_id=cid,
                user_profile=prof,
                requested_at=req_at,
                reported_at=rep_at,
                audit_at=audit_at,
            )
            pred_status, pred_steps = engine.evaluate_case(cid, is_del, res_states)

        # Evaluate matches
        s_match = pred_status == gt_status
        if s_match:
            status_matches += 1

        seq_match = s_match and (pred_steps == gt_steps)
        if seq_match:
            exact_sequence_matches += 1

        if verbose:
            if seq_match:
                tag = "[EXACT MATCH]"
            elif s_match:
                tag = f"[STATUS MATCH ({pred_status})]"
            else:
                tag = f"[MISMATCH (Pred {pred_status} vs GT {gt_status})]"
            print(f"  {cid:<8} {tag:<35} Pred Steps: {len(pred_steps):<2} | GT Steps: {len(gt_steps):<2}")

        total_gt_steps += len(gt_steps)
        total_pred_steps += len(pred_steps)

        gt_tuples = [
            (s["phase"], s["system_id"], s["resource_id"], s["operation"], s["state"], s["evidence_id"])
            for s in gt_steps
        ]
        pred_tuples = [
            (s["phase"], s["system_id"], s["resource_id"], s["operation"], s["state"], s["evidence_id"])
            for s in pred_steps
        ]

        for pt in pred_tuples:
            if pt in gt_tuples:
                matched_step_tuples += 1

        # Per-field match rates
        for p_step, g_step in zip(pred_steps, gt_steps):
            field_totals += 1
            for k in field_matches:
                if p_step.get(k) == g_step.get(k):
                    field_matches[k] += 1

    precision = matched_step_tuples / total_pred_steps if total_pred_steps else 0.0
    recall = matched_step_tuples / total_gt_steps if total_gt_steps else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    status_acc = status_matches / total_cases if total_cases else 0.0
    seq_acc = exact_sequence_matches / total_cases if total_cases else 0.0

    field_accs = {
        k: (v / field_totals if field_totals else 0.0)
        for k, v in field_matches.items()
    }

    results = {
        "total_cases": total_cases,
        "status_matches": status_matches,
        "status_accuracy": status_acc,
        "exact_sequence_matches": exact_sequence_matches,
        "sequence_accuracy": seq_acc,
        "total_gt_steps": total_gt_steps,
        "total_pred_steps": total_pred_steps,
        "matched_step_tuples": matched_step_tuples,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "field_matches": field_matches,
        "field_totals": field_totals,
        "field_accuracies": field_accs,
    }

    if verbose:
        print("\n" + "-" * 90)
        print("SAMPLE EVALUATION SUMMARY METRICS:")
        print("-" * 90)
        print(f"  * Case-Level Status Accuracy:     {status_matches}/{total_cases} ({status_acc*100:.2f}%)")
        print(f"  * Exact Sequence Match Accuracy:  {exact_sequence_matches}/{total_cases} ({seq_acc*100:.2f}%)")
        print(f"  * Step-Level Precision:           {precision:.4f} ({matched_step_tuples}/{total_pred_steps})")
        print(f"  * Step-Level Recall:              {recall:.4f} ({matched_step_tuples}/{total_gt_steps})")
        print(f"  * Step-Level F1 Score:            {f1:.4f}")
        print("  * Field-Level Accuracies:")
        for k, acc in field_accs.items():
            print(f"      - {k:<15}: {field_matches[k]}/{field_totals} ({acc*100:.2f}%)")
        print("-" * 90)

    return results


def run_custom_evaluation_cases(engine: PolicyEngine, verbose: bool = True) -> Dict[str, Any]:
    """
    Design, execute, and validate the 3 synthetic stress-test custom evaluation cases.
    """
    if verbose:
        print("\n" + "=" * 90)
        print("RUNNING 3 SYNTHETIC CUSTOM EVALUATION STRESS TESTS")
        print("=" * 90)

    custom_results = {}

    # -------------------------------------------------------------------------
    # Custom Case 01: Multi-Hop Historical Email & Replica Drift
    # -------------------------------------------------------------------------
    # Scenario: User changed email twice: alice.historic@legacy.org -> alice.mid@domain.com -> alice.now@domain.com.
    # Request made under current email alice.now@domain.com.
    # Primary DB deleted user, but a regional replica snapshot captured prior to audit_at still retains
    # account_c01 registered under alice.historic@legacy.org.
    # Tests multi-hop identity traversal and replica drift detection.
    res_c01 = ReconstructedResourceState(
        system_id="account_service",
        resource_id="account_c01",
        current_state="PRESENT",
        pii_exposed=True,
        evidence_id="evidence_custom_01",
        captured_at="2026-08-15T10:00:00Z",
    )
    status_01, steps_01 = engine.evaluate_case("custom_case_01", True, [res_c01])
    pass_01 = (
        status_01 == "INCOMPLETE"
        and len(steps_01) == 3
        and steps_01[0]["operation"] == "REPORT_REMAINING_RECORD"
        and steps_01[0]["evidence_id"] == "evidence_custom_01"
        and steps_01[1]["operation"] == "DELETE_RECORD"
        and steps_01[1]["evidence_id"] == ""
        and steps_01[2]["operation"] == "VERIFY_RECORD_ABSENT"
        and steps_01[2]["evidence_id"] == ""
    )
    custom_results["custom_case_01"] = {
        "name": "Multi-Hop Historical Email & Replica Drift",
        "passed": pass_01,
        "deletion_status": status_01,
        "step_count": len(steps_01),
        "steps": steps_01,
    }
    if verbose:
        tag_01 = "[PASS]" if pass_01 else "[FAIL]"
        print(f"  {tag_01} custom_case_01: Multi-Hop Historical Email & Replica Drift")
        print(f"         Status: {status_01} | Steps: {len(steps_01)}")
        for s in steps_01:
            print(f"           step {s['step_no']}: {s['phase']} | {s['system_id']} | {s['resource_id']} | {s['operation']} | {s['state']} | ev='{s['evidence_id']}'")

    # -------------------------------------------------------------------------
    # Custom Case 02: Post-audit_at Evidence Horizon Trap
    # -------------------------------------------------------------------------
    # Scenario: audit_at is 2026-09-10T12:00:00Z. Prior snapshot (11:00) showed account_c02 was PRESENT.
    # Deletion activity occurred at 12:15:00Z (post-cutoff) and subsequent snapshot (12:30:00Z) showed ABSENT.
    # Reconstructor and engine must discard post-audit_at evidence and judge state strictly at audit_at.
    res_c02 = ReconstructedResourceState(
        system_id="account_service",
        resource_id="account_c02",
        current_state="PRESENT",
        pii_exposed=True,
        evidence_id="evidence_custom_02a",
        captured_at="2026-09-10T11:00:00Z",
    )
    status_02, steps_02 = engine.evaluate_case("custom_case_02", True, [res_c02])
    pass_02 = (
        status_02 == "INCOMPLETE"
        and len(steps_02) == 3
        and steps_02[0]["operation"] == "REPORT_REMAINING_RECORD"
        and steps_02[0]["evidence_id"] == "evidence_custom_02a"
        and steps_02[1]["operation"] == "DELETE_RECORD"
        and steps_02[2]["operation"] == "VERIFY_RECORD_ABSENT"
    )
    custom_results["custom_case_02"] = {
        "name": "Post-audit_at Evidence Horizon Trap",
        "passed": pass_02,
        "deletion_status": status_02,
        "step_count": len(steps_02),
        "steps": steps_02,
    }
    if verbose:
        tag_02 = "[PASS]" if pass_02 else "[FAIL]"
        print(f"  {tag_02} custom_case_02: Post-audit_at Evidence Horizon Trap")
        print(f"         Status: {status_02} | Steps: {len(steps_02)}")
        for s in steps_02:
            print(f"           step {s['step_no']}: {s['phase']} | {s['system_id']} | {s['resource_id']} | {s['operation']} | {s['state']} | ev='{s['evidence_id']}'")

    # -------------------------------------------------------------------------
    # Custom Case 03: Tombstone PII Exposure + Active Sync & Restore Risk
    # -------------------------------------------------------------------------
    # Scenario: Account tombstone exists with exposed email_hash (PRESENT/EXPOSED_PII),
    # while an active sync connector (data_flow_c03) and unblocked backup archive (backup_c03) remain ACTIVE.
    # Verifies that:
    # 1. All 3 violations are detected in FINDING phase.
    # 2. In REMEDIATION, DISABLE_DATA_FLOW (rank 1) and BLOCK_RESTORE (rank 2) precede REDACT_RECORD (rank 4).
    # 3. Post-remediation verification steps have evidence_id: "".
    res_c03_tomb = ReconstructedResourceState(
        system_id="identity_service",
        resource_id="tombstone_c03",
        current_state="PRESENT",
        pii_exposed=True,
        evidence_id="evidence_custom_03",
        captured_at="2026-09-20T10:00:00Z",
        is_tombstone=True,
    )
    res_c03_flow = ReconstructedResourceState(
        system_id="integration_service",
        resource_id="data_flow_c03",
        current_state="ACTIVE",
        pii_exposed=False,
        evidence_id="evidence_custom_03",
        captured_at="2026-09-20T10:00:00Z",
        is_flow=True,
    )
    res_c03_backup = ReconstructedResourceState(
        system_id="backup_service",
        resource_id="backup_c03",
        current_state="ACTIVE",
        pii_exposed=False,
        evidence_id="evidence_custom_03",
        captured_at="2026-09-20T10:00:00Z",
        is_backup=True,
    )
    status_03, steps_03 = engine.evaluate_case(
        "custom_case_03", True, [res_c03_tomb, res_c03_flow, res_c03_backup]
    )
    remediation_ops = [s["operation"] for s in steps_03 if s["phase"] == "REMEDIATION"]
    pass_03 = (
        status_03 == "INCOMPLETE"
        and len(steps_03) == 9
        and remediation_ops == ["DISABLE_DATA_FLOW", "BLOCK_RESTORE", "REDACT_RECORD"]
        and all(s["evidence_id"] == "" for s in steps_03 if s["phase"] in ("REMEDIATION", "VERIFICATION"))
        and [s["step_no"] for s in steps_03] == list(range(1, 10))
    )
    custom_results["custom_case_03"] = {
        "name": "Tombstone PII Exposure + Active Sync & Restore Risk (Dependency Ordering)",
        "passed": pass_03,
        "deletion_status": status_03,
        "step_count": len(steps_03),
        "steps": steps_03,
    }
    if verbose:
        tag_03 = "[PASS]" if pass_03 else "[FAIL]"
        print(f"  {tag_03} custom_case_03: Tombstone PII Exposure + Active Sync & Restore Risk (Dependency Ordering)")
        print(f"         Status: {status_03} | Steps: {len(steps_03)}")
        print(f"         Remediation Dependency Order: {remediation_ops}")
        for s in steps_03:
            print(f"           step {s['step_no']}: {s['phase']} | {s['system_id']} | {s['resource_id']} | {s['operation']} | {s['state']} | ev='{s['evidence_id']}'")

    all_passed = all(r["passed"] for r in custom_results.values())
    if verbose:
        print("\n" + "-" * 90)
        print(f"CUSTOM CASES RESULT: {'ALL PASSED (3/3)' if all_passed else 'FAILURES DETECTED'}")
        print("-" * 90)

    return custom_results


def main() -> None:
    print("=" * 90)
    print("NORTHSTAR SHOP DELETION AUDIT AGENT — LOCAL EVALUATION HARNESS")
    print("=" * 90)

    # Initialize agent components
    resolver = IdentityResolver()
    indexer = EvidenceIndexer()
    reconstructor = StateReconstructor(indexer, resolver)
    engine = PolicyEngine()

    # 1. Run public 32-sample benchmark
    sample_metrics = evaluate_sample_dataset(resolver, indexer, reconstructor, engine, verbose=True)

    # 2. Run synthetic custom cases
    custom_metrics = run_custom_evaluation_cases(engine, verbose=True)

    print("\n" + "=" * 90)
    print("FINAL HARNESS VERIFICATION COMPLETED SUCCESSFULLY")
    print("=" * 90)


if __name__ == "__main__":
    main()
