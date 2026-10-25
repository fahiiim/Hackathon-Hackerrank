"""
Test suite for Phase E: Policy Engine & Step Generator (Step 6)
"""

import csv
import json
import os
import sys

# Ensure local code directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DATASET_DIR
from evidence_indexer import EvidenceIndexer
from identity_resolver import IdentityResolver
from intent_classifier import is_deletion_request
from policy_engine import PolicyEngine
from state_reconstructor import StateReconstructor


def main() -> None:
    print("=" * 80)
    print("RUNNING POLICY ENGINE VALIDATION (Step 6)")
    print("=" * 80)

    resolver = IdentityResolver()
    indexer = EvidenceIndexer()
    reconstructor = StateReconstructor(indexer, resolver)
    engine = PolicyEngine()

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
    exact_step_matches = 0

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

    print(f"Loaded {total_cases} sample cases for validation.\n")

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

        # 2. Identity & State Reconstruction
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

        # Accuracy checks
        s_match = pred_status == gt_status
        if s_match:
            status_matches += 1

        steps_match = pred_steps == gt_steps
        if s_match and steps_match:
            exact_step_matches += 1
            res_str = "[OK] EXACT MATCH"
        elif s_match:
            res_str = f"[~] Status MATCH ({pred_status}) | Steps: Pred {len(pred_steps)} vs GT {len(gt_steps)}"
        else:
            res_str = f"[X] Status MISMATCH: Pred {pred_status} vs GT {gt_status}"

        print(f"[{cid}] {res_str}")

        # Accumulate metrics
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

        # Field-level comparison on zip
        for p_step, g_step in zip(pred_steps, gt_steps):
            field_totals += 1
            for k in field_matches:
                if p_step.get(k) == g_step.get(k):
                    field_matches[k] += 1

    precision = matched_step_tuples / total_pred_steps if total_pred_steps else 0.0
    recall = matched_step_tuples / total_gt_steps if total_gt_steps else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    print("\n" + "=" * 80)
    print("STEP 6 EVALUATION SUMMARY:")
    print("=" * 80)
    print(f"Case-Level Status Accuracy:     {status_matches}/{total_cases} ({(status_matches/total_cases)*100:.2f}%)")
    print(f"Exact Sequence Match Accuracy:  {exact_step_matches}/{total_cases} ({(exact_step_matches/total_cases)*100:.2f}%)")
    print(f"Step Precision:                 {precision:.4f} ({matched_step_tuples}/{total_pred_steps})")
    print(f"Step Recall:                    {recall:.4f} ({matched_step_tuples}/{total_gt_steps})")
    print(f"Step F1 Score:                  {f1:.4f}")
    if field_totals > 0:
        print("\nField-Level Accuracies:")
        for k, v in field_matches.items():
            print(f"  - {k:<15}: {v}/{field_totals} ({(v/field_totals)*100:.2f}%)")
    print("=" * 80)


if __name__ == "__main__":
    main()
