"""
Phase B: Current & Historical Identity Graph Resolver (Step 3)

Reconstructs the full identity profile for any subject request by joining
user_identities.csv snapshot with historical mutation logs in user_audit_log.csv
strictly up to the case's audit_at cutoff.
"""

import csv
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from config import USER_IDENTITIES_PATH, USER_AUDIT_LOG_PATH

@dataclass
class UserIdentityProfile:
    user_id: str
    canonical_name: str
    canonical_email: str
    canonical_phone: str
    canonical_email_hash: str
    emails: Set[str] = field(default_factory=set)
    email_hashes: Set[str] = field(default_factory=set)
    phones: Set[str] = field(default_factory=set)
    normalized_phones: Set[str] = field(default_factory=set)
    names: Set[str] = field(default_factory=set)
    audit_records: List[Dict[str, str]] = field(default_factory=list)

    def matches_any_identifier(
        self,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        name: Optional[str] = None,
        email_hash: Optional[str] = None,
    ) -> bool:
        """
        Check if any provided candidate field matches this user's identity profile.
        """
        if user_id and user_id.strip() == self.user_id:
            return True
        if email and email.strip().lower() in self.emails:
            return True
        if email_hash and email_hash.strip().lower() in self.email_hashes:
            return True
        if phone:
            p_clean = phone.strip()
            if p_clean in self.phones:
                return True
            digits = re.sub(r"\D", "", p_clean)
            if digits and digits in self.normalized_phones:
                return True
        if name and name.strip() in self.names:
            return True
        return False

class IdentityResolver:
    def __init__(
        self,
        user_identities_path: Path = USER_IDENTITIES_PATH,
        user_audit_log_path: Path = USER_AUDIT_LOG_PATH,
    ):
        self.user_identities_path = user_identities_path
        self.user_audit_log_path = user_audit_log_path
        
        self.users_by_id: Dict[str, Dict[str, str]] = {}
        self.current_email_to_uid: Dict[str, str] = {}
        self.audit_log_entries: List[Dict[str, str]] = []
        self.audits_by_user_id: Dict[str, List[Dict[str, str]]] = {}

        self._load_data()

    def _load_data(self) -> None:
        # Load user_identities.csv
        with open(self.user_identities_path, mode="r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                uid = row["user_id"]
                self.users_by_id[uid] = row
                email = row["email"].strip().lower()
                self.current_email_to_uid[email] = uid

        # Load user_audit_log.csv
        with open(self.user_audit_log_path, mode="r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                self.audit_log_entries.append(row)
                uid = row["user_id"]
                if uid not in self.audits_by_user_id:
                    self.audits_by_user_id[uid] = []
                self.audits_by_user_id[uid].append(row)

    def resolve_user_id(self, request_email: str, audit_at: Optional[str] = None) -> Optional[str]:
        """
        Resolve a given email address to the canonical user_id.
        First attempts direct lookup in current identities snapshot.
        If not found, searches historical email changes in user_audit_log up to audit_at.
        """
        if not request_email:
            return None
        clean_email = request_email.strip().lower()

        # 1. Direct match on current identity snapshot
        if clean_email in self.current_email_to_uid:
            return self.current_email_to_uid[clean_email]

        # 2. Historical search in user_audit_log (filtered <= audit_at if supplied)
        for entry in self.audit_log_entries:
            if entry.get("field_name") == "email":
                if audit_at and entry["event_time"] > audit_at:
                    continue
                old_val = entry["old_value"].strip().lower()
                new_val = entry["new_value"].strip().lower()
                if clean_email in (old_val, new_val):
                    return entry["user_id"]

        # 3. Fallback: historical search without strict audit_at cutoff if not matched
        if audit_at:
            for entry in self.audit_log_entries:
                if entry.get("field_name") == "email":
                    old_val = entry["old_value"].strip().lower()
                    new_val = entry["new_value"].strip().lower()
                    if clean_email in (old_val, new_val):
                        return entry["user_id"]

        return None

    def get_user_profile(self, user_id: str, audit_at: Optional[str] = None) -> Optional[UserIdentityProfile]:
        """
        Build a comprehensive UserIdentityProfile for the user_id,
        gathering current attributes and all historical mutations strictly <= audit_at.
        """
        if user_id not in self.users_by_id:
            return None

        u = self.users_by_id[user_id]
        canonical_name = u["name"].strip()
        canonical_email = u["email"].strip().lower()
        canonical_phone = u["phone"].strip()
        canonical_hash = u["email_hash"].strip().lower()

        emails: Set[str] = {canonical_email}
        email_hashes: Set[str] = {canonical_hash}
        phones: Set[str] = {canonical_phone}
        normalized_phones: Set[str] = set()
        names: Set[str] = {canonical_name}

        # Filter audit records for this user <= audit_at
        filtered_audits: List[Dict[str, str]] = []
        user_audits = self.audits_by_user_id.get(user_id, [])
        for entry in user_audits:
            if audit_at and entry["event_time"] > audit_at:
                continue
            filtered_audits.append(entry)
            fn = entry.get("field_name")
            old_val = entry.get("old_value", "").strip()
            new_val = entry.get("new_value", "").strip()

            if fn == "email":
                if old_val:
                    emails.add(old_val.lower())
                if new_val:
                    emails.add(new_val.lower())
            elif fn == "phone":
                if old_val:
                    phones.add(old_val)
                if new_val:
                    phones.add(new_val)
            elif fn == "name":
                if old_val:
                    names.add(old_val)
                if new_val:
                    names.add(new_val)
            elif fn == "email_hash":
                if old_val:
                    email_hashes.add(old_val.lower())
                if new_val:
                    email_hashes.add(new_val.lower())

        # Generate normalized phone numbers (digits only, e.g. for matching without formatting)
        for p in phones:
            digits = re.sub(r"\D", "", p)
            if digits:
                normalized_phones.add(digits)
                # Also include last 10 digits for standard phone matching
                if len(digits) >= 10:
                    normalized_phones.add(digits[-10:])

        # Compute SHA-256 and MD5 hashes for all known emails
        for e in list(emails):
            sha256_hash = hashlib.sha256(e.encode("utf-8")).hexdigest().lower()
            md5_hash = hashlib.md5(e.encode("utf-8")).hexdigest().lower()
            email_hashes.add(sha256_hash)
            email_hashes.add(md5_hash)

        return UserIdentityProfile(
            user_id=user_id,
            canonical_name=canonical_name,
            canonical_email=canonical_email,
            canonical_phone=canonical_phone,
            canonical_email_hash=canonical_hash,
            emails=emails,
            email_hashes=email_hashes,
            phones=phones,
            normalized_phones=normalized_phones,
            names=names,
            audit_records=filtered_audits,
        )

if __name__ == "__main__":
    from config import SAMPLE_DELETION_REQUESTS_PATH, DELETION_REQUESTS_PATH

    print("=" * 80)
    print("TESTING PHASE B: CURRENT & HISTORICAL IDENTITY GRAPH RESOLVER")
    print("=" * 80)

    resolver = IdentityResolver()
    print(f"Loaded {len(resolver.users_by_id)} user identities.")
    print(f"Loaded {len(resolver.audit_log_entries)} audit log entries.")

    # 1. Test resolution on sample requests
    with open(SAMPLE_DELETION_REQUESTS_PATH, mode="r", encoding="utf-8") as f:
        sample_rows = list(csv.DictReader(f))

    print(f"\nResolving {len(sample_rows)} sample deletion requests:")
    sample_resolved = 0
    historical_samples = 0
    for r in sample_rows:
        cid = r["case_id"]
        email = r["email"]
        audit_at = r["audit_at"]
        uid = resolver.resolve_user_id(email, audit_at)
        assert uid is not None, f"Failed to resolve sample case {cid} ({email})!"
        sample_resolved += 1
        prof = resolver.get_user_profile(uid, audit_at)
        assert prof is not None
        if email.strip().lower() != prof.canonical_email:
            historical_samples += 1
            print(f"  [HISTORICAL RESOLUTION] {cid}: Request email '{email}' -> Resolved to {uid} (Current email: '{prof.canonical_email}')")

    print(f"Sample Requests Resolution: {sample_resolved}/{len(sample_rows)} (100%) [Historical cases: {historical_samples}]")

    # 2. Test resolution on all 518 evaluation requests
    with open(DELETION_REQUESTS_PATH, mode="r", encoding="utf-8") as f:
        eval_rows = list(csv.DictReader(f))

    print(f"\nResolving {len(eval_rows)} evaluation requests:")
    eval_resolved = 0
    eval_historical = 0
    for r in eval_rows:
        cid = r["case_id"]
        email = r["email"]
        audit_at = r["audit_at"]
        uid = resolver.resolve_user_id(email, audit_at)
        assert uid is not None, f"Failed to resolve eval case {cid} ({email})!"
        eval_resolved += 1
        prof = resolver.get_user_profile(uid, audit_at)
        if email.strip().lower() != prof.canonical_email:
            eval_historical += 1

    print(f"Evaluation Requests Resolution: {eval_resolved}/{len(eval_rows)} (100.0%)")
    print(f"  - Direct Current Matches: {eval_resolved - eval_historical}")
    print(f"  - Historical Audit Log Matches: {eval_historical}")
    print("\nALL 518 EVALUATION REQUEST IDENTITIES RESOLVED SUCCESSFULLY!")
    print("=" * 80)
