import csv
import json

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
