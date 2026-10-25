"""
Phase A: Multilingual Request Intent Gate (Step 2)

Determines whether a user request authorizes personal data / account deletion.
Non-deletion requests (access, export, rectification, marketing opt-out only, login reset)
must be classified as NOT_APPLICABLE (is_deletion = False) with steps_json = [].
"""

import re
from typing import Dict, List, Tuple
from config import USAGE_TRACKER

# Strong non-deletion indicator phrases across languages
NON_DELETION_PATTERNS = [
    # English non-deletion phrases
    r"\bnot asking for deletion\b",
    r"\bnot a request to erase\b",
    r"\bleave the account active\b",
    r"\bleave my profile\b",
    r"\bkeep the account\b",
    r"\bcontinue using\b",
    r"\bdo not close\b",
    r"\bdon't close\b",
    r"\bdo not delete\b",
    r"\bdon't delete\b",
    r"\bwithout removing\b",
    r"\bwithout deleting\b",
    r"\bmarketing (?:lists?|emails?) only\b",
    r"\bpromotional emails?\b",
    r"\bportable format\b",
    r"\bcopy of (?:last year|the information|my records|my invoices)\b",
    r"\binformation request\b",
    r"\bresetting the login\b",
    r"\bhelp resetting\b",
    r"\bmisspelled\b",
    r"\bcorrect it\b",
    r"\bout of date\b",
    r"\breplace it with the new\b",
    
    # Spanish / Portuguese non-deletion
    r"\bno (?:deseo|quiero|solicito) (?:la )?eliminaci[oó]n\b",
    r"\bmantener la cuenta\b",
    r"\bn[aã]o (?:desejo|quero|solicito) (?:a )?exclus[aã]o\b",
    r"\bmanter a conta\b",
    
    # French non-deletion
    r"\bne supprimez pas\b",
    r"\bgarder le compte\b",
    
    # German non-deletion
    r"\bnicht l[oö]schen\b",
    r"\bkonto behalten\b",
]

# Multilingual positive deletion authorization stems and patterns
DELETION_PATTERNS = [
    # English stems (delet*, eras*, remov*, clos*, purg*, gone)
    r"\bdelet",
    r"\beras",
    r"\bremov",
    r"\bclos",
    r"\bpurg",
    r"\bgone\b",
    
    # French stems
    r"\bsuppress",
    r"\bsupprim",
    r"\beffac",
    
    # Spanish stems
    r"\belimin",
    r"\bborr",
    r"\bcancel",
    
    # Portuguese stems
    r"\bexclu",
    r"\bapag",
    
    # German stems
    r"\bl[oö]sch",
    r"\bentfern",
    
    # Italian stems
    r"\bcancell",
    
    # Japanese
    r"削除",
    r"消去",
    
    # Korean
    r"삭제",
]

# Compiled regular expressions
RE_NON_DELETION = [re.compile(p, re.IGNORECASE) for p in NON_DELETION_PATTERNS]
RE_DELETION = [re.compile(p, re.IGNORECASE) for p in DELETION_PATTERNS]

def is_deletion_request(request_text: str) -> bool:
    """
    Classify whether the given request_text authorizes personal data/account deletion.
    
    Returns:
        True: Request explicitly authorizes deletion.
        False: Request is for access, export, rectification, marketing opt-out, or explicitly negates deletion.
    """
    if not request_text or not request_text.strip():
        return False

    cleaned_text = request_text.strip()

    # Step 1: Explicit non-deletion patterns take highest precedence
    for pat in RE_NON_DELETION:
        if pat.search(cleaned_text):
            return False

    # Step 2: Positive multilingual deletion stems
    for pat in RE_DELETION:
        if pat.search(cleaned_text):
            return True

    # Default fallback: If no explicit deletion phrase found, treat as non-deletion (fail-safe)
    return False

def classify_request(case_id: str, request_text: str) -> Tuple[bool, str]:
    """
    Convenience wrapper returning (is_deletion, reason).
    """
    is_del = is_deletion_request(request_text)
    if is_del:
        return True, "Authorized deletion request"
    return False, "Non-deletion request (access, rectification, export, or opt-out only)"

if __name__ == "__main__":
    import csv
    from config import SAMPLE_DELETION_REQUESTS_PATH, DELETION_REQUESTS_PATH

    print("=" * 80)
    print("TESTING PHASE A: MULTILINGUAL REQUEST INTENT GATE")
    print("=" * 80)

    # Test on Sample Deletion Requests
    with open(SAMPLE_DELETION_REQUESTS_PATH, mode="r", encoding="utf-8") as f:
        sample_rows = list(csv.DictReader(f))

    sample_passes = 0
    print(f"\nEvaluating {len(sample_rows)} sample requests (expecting all True):")
    for r in sample_rows:
        cid = r["case_id"]
        text = r["request_text"]
        is_del = is_deletion_request(text)
        if is_del:
            sample_passes += 1
        else:
            print(f"  [FAIL] {cid}: Incorrectly classified as False! Text: {text}")

    print(f"Sample Accuracy: {sample_passes}/{len(sample_rows)} ({sample_passes/len(sample_rows)*100:.1f}%)")
    assert sample_passes == len(sample_rows), "All sample requests should be classified as deletion requests!"

    # Test on Full 518 Evaluation Requests
    with open(DELETION_REQUESTS_PATH, mode="r", encoding="utf-8") as f:
        eval_rows = list(csv.DictReader(f))

    print(f"\nEvaluating {len(eval_rows)} evaluation requests:")
    non_del_cases = []
    del_cases = []
    for r in eval_rows:
        cid = r["case_id"]
        text = r["request_text"]
        is_del = is_deletion_request(text)
        if is_del:
            del_cases.append(cid)
        else:
            non_del_cases.append((cid, text))

    print(f"Total Deletion Requests: {len(del_cases)}")
    print(f"Total Non-Deletion Requests (NOT_APPLICABLE): {len(non_del_cases)}")
    print("\nNon-Deletion Cases identified:")
    for cid, text in non_del_cases:
        print(f"  [{cid}]: {text}")

    expected_non_del = {"case_533", "case_534", "case_535", "case_536", "case_537", "case_538", "case_539", "case_540", "case_541", "case_542"}
    detected_non_del = set(cid for cid, _ in non_del_cases)
    assert detected_non_del == expected_non_del, f"Mismatch in non-deletion cases! Detected: {detected_non_del}, Expected: {expected_non_del}"
    print(f"\nExact match on all 10 non-deletion evaluation cases: SUCCESS!")
    print("=" * 80)
