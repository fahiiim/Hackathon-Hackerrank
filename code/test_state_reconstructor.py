import csv
import json
from identity_resolver import IdentityResolver
from evidence_indexer import EvidenceIndexer
from state_reconstructor import StateReconstructor

resolver = IdentityResolver()
indexer = EvidenceIndexer()
reconstructor = StateReconstructor(indexer, resolver)

with open('dataset/sample_deletion_requests.csv', 'r', encoding='utf-8') as f:
    sample_reqs = list(csv.DictReader(f))

with open('dataset/sample_output.csv', 'r', encoding='utf-8') as f:
    sample_out = {r['case_id']: (r['deletion_status'], json.loads(r['steps_json'])) for r in csv.DictReader(f)}

print("=" * 100)
print("COMPREHENSIVE TEST: STATE RECONSTRUCTOR ON 32 SAMPLE REQUESTS")
print("=" * 100)

exact_res_count = 0
total_cases = len(sample_reqs)

for req in sample_reqs:
    cid = req['case_id']
    email = req['email']
    req_at = req['requested_at']
    rep_at = req['reported_at']
    audit_at = req['audit_at']
    
    uid = resolver.resolve_user_id(email, audit_at)
    prof = resolver.get_user_profile(uid, audit_at)

    gt_status, gt_steps = sample_out[cid]
    gt_res_set = set((s['system_id'], s['resource_id']) for s in gt_steps)

    recon_states = reconstructor.reconstruct_user_state(
        case_id=cid,
        user_profile=prof,
        requested_at=req_at,
        reported_at=rep_at,
        audit_at=audit_at,
    )
    recon_res_set = set((s.system_id, s.resource_id) for s in recon_states)

    overlap = recon_res_set.intersection(gt_res_set)
    missing = gt_res_set - recon_res_set
    extra = recon_res_set - gt_res_set

    if overlap == gt_res_set and not extra:
        exact_res_count += 1
        status_str = "EXACT MATCH"
    else:
        status_str = f"Overlap: {len(overlap)}/{len(gt_res_set)}"

    print(f"[{cid}] {uid:<9} | {gt_status:<11} | GT: {len(gt_res_set):2d} | Recon: {len(recon_res_set):2d} | {status_str}")
    if missing:
        print(f"       MISSING: {sorted(list(missing))}")
    if extra:
        print(f"       EXTRA:   {sorted(list(extra))}")

print("=" * 100)
print(f"Summary: Exact Resource Set Matches: {exact_res_count}/{total_cases}")
print("=" * 100)
