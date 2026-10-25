"""
Phase C: Multimodal Evidence Indexer (Step 4)

Parses, extracts, and indexes all 94 evidence files under dataset/evidence/
(SQL databases, JSON records, text handover logs, service event logs,
PDF documents, and visual screenshot console images) strictly respecting
temporal metadata (captured_at).
"""

import csv
import glob
import json
import os
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import pypdf

from config import DATASET_DIR, EVIDENCE_DIR, EVIDENCE_FILES_PATH, SYSTEM_ACTIVITY_PATH
from identity_resolver import UserIdentityProfile
from parsed_visual_evidence import PARSED_VISUAL_EVIDENCE

@dataclass
class IndexedRecord:
    file_id: str
    file_path: str
    captured_at: str
    origin: str
    system_id: str
    resource_id: str
    user_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    name: Optional[str] = None
    email_hash: Optional[str] = None
    record_state: str = "PRESENT"  # PRESENT, ABSENT, REDACTED, ANONYMIZED, ACTIVE, DISABLED, BLOCKED
    pii_exposed: bool = False
    is_tombstone: bool = False
    is_data_flow: bool = False
    is_backup_risk: bool = False
    is_retained_record: bool = False
    details: Dict[str, Any] = field(default_factory=dict)

class EvidenceIndexer:
    def __init__(self, dataset_dir: Path = DATASET_DIR):
        self.dataset_dir = dataset_dir
        self.evidence_dir = dataset_dir / "evidence"
        self.manifest_path = dataset_dir / "evidence_files.csv"
        self.system_activity_path = dataset_dir / "system_activity.csv"
        
        self.manifest_entries: List[Dict[str, str]] = []
        
        # Parsed evidence records from files
        self.records: List[IndexedRecord] = []
        
        # Parsed activity events from system_activity.csv
        self.activity_events: List[Dict[str, Any]] = []
        self.activities_by_res_id: Dict[str, List[Dict[str, Any]]] = {}
        
        # Fast indexes for evidence records
        self.records_by_uid: Dict[str, List[IndexedRecord]] = {}
        self.records_by_email: Dict[str, List[IndexedRecord]] = {}
        self.records_by_hash: Dict[str, List[IndexedRecord]] = {}
        self.records_by_phone: Dict[str, List[IndexedRecord]] = {}
        self.records_by_res_id: Dict[str, List[IndexedRecord]] = {}

        self._index_all_evidence()
        self._index_system_activity()

    def _index_all_evidence(self) -> None:
        with open(self.manifest_path, mode="r", encoding="utf-8") as f:
            self.manifest_entries = list(csv.DictReader(f))

        for entry in self.manifest_entries:
            file_id = entry["file_id"]
            rel_path = entry["file_path"]
            origin = entry["origin"]
            captured_at = entry["captured_at"]
            full_path = self.dataset_dir / rel_path

            if not full_path.exists():
                continue

            ext = full_path.suffix.lower()
            if ext == ".sql":
                self._parse_sql_file(file_id, str(rel_path), origin, captured_at, full_path)
            elif ext == ".json":
                self._parse_json_file(file_id, str(rel_path), origin, captured_at, full_path)
            elif ext == ".log":
                self._parse_log_file(file_id, str(rel_path), origin, captured_at, full_path)
            elif ext == ".txt":
                self._parse_txt_file(file_id, str(rel_path), origin, captured_at, full_path)
            elif ext == ".pdf":
                self._parse_pdf_file(file_id, str(rel_path), origin, captured_at, full_path)
            elif ext in (".png", ".jpg"):
                self._parse_image_file(file_id, str(rel_path), origin, captured_at, full_path)

        # Build fast lookup indexes
        for rec in self.records:
            if rec.user_id:
                self.records_by_uid.setdefault(rec.user_id, []).append(rec)
            if rec.email:
                self.records_by_email.setdefault(rec.email.lower(), []).append(rec)
            if rec.email_hash:
                self.records_by_hash.setdefault(rec.email_hash.lower(), []).append(rec)
            if rec.phone:
                digits = re.sub(r"\D", "", rec.phone)
                if digits:
                    self.records_by_phone.setdefault(digits, []).append(rec)
            if rec.resource_id:
                self.records_by_res_id.setdefault(rec.resource_id, []).append(rec)

    def _index_system_activity(self) -> None:
        if not self.system_activity_path.exists():
            return
        with open(self.system_activity_path, mode="r", encoding="utf-8") as f:
            self.activity_events = list(csv.DictReader(f))

        for act in self.activity_events:
            res_id = act.get("resource_id", "")
            if res_id:
                self.activities_by_res_id.setdefault(res_id, []).append(act)

    def _add_record(self, record: IndexedRecord) -> None:
        self.records.append(record)

    def _parse_sql_file(self, file_id: str, rel_path: str, origin: str, captured_at: str, path: Path) -> None:
        try:
            con = sqlite3.connect(":memory:")
            con.row_factory = sqlite3.Row
            with open(path, mode="r", encoding="utf-8") as f:
                con.executescript(f.read())
            cur = con.cursor()
            tables = [t[0] for t in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]

            for t in tables:
                cols = [c[1] for c in cur.execute(f"PRAGMA table_info({t})")]
                rows = cur.execute(f"SELECT * FROM {t}").fetchall()

                for row in rows:
                    r_dict = dict(row)
                    res_id = r_dict.get("resource_id") or ""
                    uid = r_dict.get("user_id") or r_dict.get("customer_reference") or r_dict.get("subject_reference")
                    email = r_dict.get("email") or r_dict.get("owner_email") or r_dict.get("customer_email")
                    phone = r_dict.get("phone") or r_dict.get("owner_phone")
                    name = r_dict.get("full_name") or r_dict.get("display_name") or r_dict.get("name")
                    email_hash = r_dict.get("email_hash")
                    
                    # Check JSON embedded column (record_json)
                    if "record_json" in r_dict and r_dict["record_json"]:
                        try:
                            rj = json.loads(r_dict["record_json"])
                            if isinstance(rj, dict):
                                res_id = res_id or rj.get("resource_id") or ""
                                uid = uid or rj.get("user_id") or rj.get("customer_reference") or rj.get("subject_reference")
                                email = email or rj.get("email") or rj.get("owner_email") or rj.get("customer_email")
                                phone = phone or rj.get("phone") or rj.get("owner_phone")
                                name = name or rj.get("full_name") or rj.get("name") or rj.get("display_name")
                                email_hash = email_hash or rj.get("email_hash")

                                if "document" in rj and isinstance(rj["document"], dict):
                                    doc = rj["document"]
                                    res_id = res_id or doc.get("resource_id") or ""
                                    uid = uid or doc.get("user_id") or doc.get("customer_reference") or doc.get("subject_reference")
                                    email = email or doc.get("email") or doc.get("owner_email") or doc.get("customer_email")
                                    phone = phone or doc.get("phone") or doc.get("owner_phone")
                                    name = name or doc.get("full_name") or doc.get("name") or doc.get("display_name")
                                    email_hash = email_hash or doc.get("email_hash")
                        except Exception:
                            pass

                    # Determine system_id
                    sys_id = "account_service"
                    if "search" in t or "search" in origin or (res_id and res_id.startswith("search_")):
                        sys_id = "search_service"
                    elif "analytics" in t or "analytics" in origin or (res_id and res_id.startswith("analytics_")):
                        sys_id = "analytics_platform"
                    elif "support" in t or "support" in origin or (res_id and res_id.startswith("support_")):
                        sys_id = "support_platform"
                    elif "backup" in t or "backup" in origin or (res_id and res_id.startswith("backup_")):
                        sys_id = "backup_service"
                    elif "connector" in t or "integration" in origin or (res_id and res_id.startswith("data_flow_")):
                        sys_id = "integration_service"
                    elif "export" in t or "export" in origin or (res_id and res_id.startswith("export_")):
                        sys_id = "export_service"
                    elif "security" in t or "audit" in t or "security" in origin or (res_id and res_id.startswith("audit_record_")):
                        sys_id = "security_service"
                    elif "identity" in t or (res_id and res_id.startswith("tombstone_")):
                        sys_id = "identity_service"
                    elif res_id and res_id.startswith("account_"):
                        sys_id = "account_service"

                    # Determine state & PII
                    rec_state = "PRESENT"
                    pii_exp = bool(email or phone or name or email_hash)
                    is_flow = sys_id == "integration_service" or "connector" in t
                    is_bkp = sys_id == "backup_service" or "backup" in t
                    is_ret = sys_id == "security_service" or "security" in t

                    if is_flow:
                        enabled = r_dict.get("enabled")
                        if enabled in (True, 1, "true", "1"):
                            rec_state = "ACTIVE"
                        else:
                            rec_state = "DISABLED"

                    if is_bkp:
                        restore_allowed = r_dict.get("restore_allowed") or r_dict.get("eligible")
                        if restore_allowed in (True, 1, "true", "1"):
                            rec_state = "ACTIVE"
                        else:
                            rec_state = "BLOCKED"

                    if is_ret:
                        rec_state = "PRESENT"

                    if res_id:
                        self._add_record(
                            IndexedRecord(
                                file_id=file_id,
                                file_path=rel_path,
                                captured_at=captured_at,
                                origin=origin,
                                system_id=sys_id,
                                resource_id=res_id,
                                user_id=uid,
                                email=email,
                                phone=phone,
                                name=name,
                                email_hash=email_hash,
                                record_state=rec_state,
                                pii_exposed=pii_exp,
                                is_data_flow=is_flow,
                                is_backup_risk=is_bkp,
                                is_retained_record=is_ret,
                                details={"table": t, **r_dict},
                            )
                        )
            con.close()
        except Exception:
            pass

    def _parse_json_file(self, file_id: str, rel_path: str, origin: str, captured_at: str, path: Path) -> None:
        try:
            with open(path, mode="r", encoding="utf-8") as f:
                data = json.load(f)

            # Format 1: service_resource_export_*.json (contains "service_exports")
            if isinstance(data, dict) and "service_exports" in data:
                svc_exports = data["service_exports"]
                for s_id, svc_data in svc_exports.items():
                    if not isinstance(svc_data, dict):
                        continue
                    for col_name, item_list in svc_data.items():
                        if not isinstance(item_list, list):
                            continue
                        for item in item_list:
                            if not isinstance(item, dict):
                                continue
                            res_id = item.get("resource_id") or ""
                            uid = item.get("customer_reference") or item.get("subject_reference") or item.get("user_id")
                            email = item.get("email") or item.get("owner_email") or item.get("customer_email") or item.get("requester_email") or item.get("query")
                            phone = item.get("phone") or item.get("owner_phone") or item.get("requester_phone")
                            name = item.get("display_name") or item.get("full_name") or item.get("requester_name")
                            email_hash = item.get("email_hash")

                            # Check search documents under hits.documents
                            if "hits" in item and isinstance(item["hits"], dict):
                                docs = item["hits"].get("documents", [])
                                if docs and isinstance(docs[0], dict):
                                    doc = docs[0]
                                    res_id = res_id or doc.get("resource_id")
                                    email = email or doc.get("email")
                                    uid = uid or doc.get("customer_reference")
                                    name = name or doc.get("display_name")

                            rec_state = "PRESENT"
                            pii_exp = bool(email or phone or name or email_hash)
                            is_flow = s_id == "integration_service"
                            is_bkp = s_id == "backup_service"
                            is_ret = s_id == "security_service"

                            if col_name == "profile_lookups":
                                status_code = item.get("status_code")
                                if status_code == 404:
                                    rec_state = "ABSENT"
                                    pii_exp = False
                                else:
                                    rec_state = "PRESENT"

                            if is_flow:
                                rec_state = "ACTIVE" if item.get("enabled") is True else "DISABLED"
                            if is_bkp:
                                rec_state = "ACTIVE" if item.get("restore_allowed") is True else "BLOCKED"
                            if is_ret:
                                rec_state = "PRESENT"

                            if s_id == "analytics_platform":
                                if not uid and not email and not phone and not name:
                                    rec_state = "ANONYMIZED"
                                    pii_exp = False
                                else:
                                    rec_state = "PRESENT"
                                    pii_exp = True

                            if s_id == "support_platform":
                                if not email and not phone and not name:
                                    rec_state = "REDACTED"
                                    pii_exp = False
                                else:
                                    rec_state = "PRESENT"
                                    pii_exp = True

                            if res_id:
                                self._add_record(
                                    IndexedRecord(
                                        file_id=file_id,
                                        file_path=rel_path,
                                        captured_at=captured_at,
                                        origin=origin,
                                        system_id=s_id,
                                        resource_id=res_id,
                                        user_id=uid,
                                        email=email,
                                        phone=phone,
                                        name=name,
                                        email_hash=email_hash,
                                        record_state=rec_state,
                                        pii_exposed=pii_exp,
                                        is_data_flow=is_flow,
                                        is_backup_risk=is_bkp,
                                        is_retained_record=is_ret,
                                        details=item,
                                    )
                                )

            # Format 2: customer_data_snapshot_bundle_*.json (contains "snapshots")
            elif isinstance(data, dict) and "snapshots" in data:
                snapshots = data["snapshots"]
                if isinstance(snapshots, list):
                    for snap in snapshots:
                        if not isinstance(snap, dict):
                            continue
                        s_id = snap.get("data_store") or snap.get("system_id") or "account_service"
                        recs = snap.get("records", [])
                        for item in recs:
                            if not isinstance(item, dict):
                                continue
                            res_id = item.get("resource_id") or ""
                            uid = item.get("customer_reference") or item.get("subject_reference") or item.get("user_id")
                            email = item.get("email")
                            phone = item.get("phone")
                            name = item.get("full_name") or item.get("name")
                            email_hash = item.get("email_hash")

                            is_tomb = res_id.startswith("tombstone_") or snap.get("collection") == "deleted_customer_references"
                            is_ret = s_id == "security_service" or snap.get("collection") == "security_audit_events"
                            rec_state = "PRESENT"
                            pii_exp = bool(email or phone or name or email_hash)

                            if is_tomb:
                                s_id = "identity_service"
                                if pii_exp:
                                    rec_state = "PRESENT"
                                else:
                                    rec_state = "REDACTED"

                            if is_ret:
                                rec_state = "PRESENT"

                            if s_id == "analytics_platform":
                                if not uid and not pii_exp:
                                    rec_state = "ANONYMIZED"

                            if res_id:
                                self._add_record(
                                    IndexedRecord(
                                        file_id=file_id,
                                        file_path=rel_path,
                                        captured_at=captured_at,
                                        origin=origin,
                                        system_id=s_id,
                                        resource_id=res_id,
                                        user_id=uid,
                                        email=email,
                                        phone=phone,
                                        name=name,
                                        email_hash=email_hash,
                                        record_state=rec_state,
                                        pii_exposed=pii_exp,
                                        is_tombstone=is_tomb,
                                        is_retained_record=is_ret,
                                        details=item,
                                    )
                                )

            # Format 3: generic records lists (analytics report, export jobs, connector configs)
            elif isinstance(data, dict) and "records" in data and isinstance(data["records"], list):
                s_id = "analytics_platform" if "analytics" in origin else (
                    "export_service" if "export" in origin else (
                        "integration_service" if "connector" in origin else "account_service"
                    )
                )
                for item in data["records"]:
                    if not isinstance(item, dict):
                        continue
                    res_id = item.get("resource_id") or ""
                    uid = item.get("customer_reference") or item.get("subject_reference") or item.get("user_id")
                    email = item.get("email") or item.get("owner_email") or item.get("customer_email")
                    phone = item.get("phone")
                    name = item.get("name") or item.get("full_name")
                    email_hash = item.get("email_hash")

                    rec_state = "PRESENT"
                    pii_exp = bool(email or phone or name or email_hash)
                    is_flow = s_id == "integration_service" or res_id.startswith("data_flow_")
                    is_bkp = s_id == "backup_service" or res_id.startswith("backup_")
                    is_ret = s_id == "security_service" or res_id.startswith("audit_record_")

                    if is_flow:
                        rec_state = "ACTIVE" if item.get("enabled") is True else "DISABLED"
                    if is_bkp:
                        rec_state = "ACTIVE" if item.get("restore_allowed") is True else "BLOCKED"
                    if s_id == "analytics_platform" and not uid and not pii_exp:
                        rec_state = "ANONYMIZED"

                    if res_id:
                        self._add_record(
                            IndexedRecord(
                                file_id=file_id,
                                file_path=rel_path,
                                captured_at=captured_at,
                                origin=origin,
                                system_id=s_id,
                                resource_id=res_id,
                                user_id=uid,
                                email=email,
                                phone=phone,
                                name=name,
                                email_hash=email_hash,
                                record_state=rec_state,
                                pii_exposed=pii_exp,
                                is_data_flow=is_flow,
                                is_backup_risk=is_bkp,
                                is_retained_record=is_ret,
                                details=item,
                            )
                        )
        except Exception:
            pass

    def _parse_log_file(self, file_id: str, rel_path: str, origin: str, captured_at: str, path: Path) -> None:
        try:
            with open(path, mode="r", encoding="utf-8") as f:
                lines = f.readlines()

            # Group entries by trace_id/requestId and resource_id to correlate multi-line events
            trace_kvs: Dict[str, Dict[str, Any]] = {}
            resource_kvs: Dict[str, Dict[str, Any]] = {}

            for line in lines:
                l_str = line.strip()
                if not l_str:
                    continue

                kv: Dict[str, Any] = {}

                # 1. Try parsing JSON line (e.g., structured_service_events_*.log)
                if "{" in l_str and "}" in l_str:
                    try:
                        json_start = l_str.find("{")
                        json_end = l_str.rfind("}") + 1
                        j_data = json.loads(l_str[json_start:json_end])
                        if isinstance(j_data, dict):
                            kv.update(j_data)
                    except Exception:
                        pass

                # 2. Extract key=value or key="value" pairs
                kv_matches = re.findall(r'(\w+)=(?:"([^"]*)"|([^\s]+))', l_str)
                for k, v1, v2 in kv_matches:
                    val = v1 if v1 != "" else v2
                    if k not in kv or kv[k] in (None, ""):
                        kv[k] = val

                # 3. Check if message contains nested escaped key=\"value\" pairs
                msg = kv.get("message")
                if msg and isinstance(msg, str):
                    nested_matches = re.findall(r'(\w+)=\\"([^\\"]*)\\"', msg)
                    for nk, nv in nested_matches:
                        if nk not in kv or kv[nk] in (None, ""):
                            kv[nk] = nv

                tid = kv.get("trace_id") or kv.get("requestId")
                res_id = kv.get("resource_id")

                if tid:
                    if tid not in trace_kvs:
                        trace_kvs[tid] = {}
                    for k, v in kv.items():
                        if v not in (None, "", "null"):
                            trace_kvs[tid][k] = v

                if res_id:
                    if res_id not in resource_kvs:
                        resource_kvs[res_id] = {}
                    for k, v in kv.items():
                        if v not in (None, "", "null"):
                            resource_kvs[res_id][k] = v

            # Merge trace_kvs into resource_kvs when resource_id is discovered
            for tid, tkv in trace_kvs.items():
                r_id = tkv.get("resource_id")
                if r_id:
                    if r_id not in resource_kvs:
                        resource_kvs[r_id] = {}
                    for k, v in tkv.items():
                        if v not in (None, "", "null") and (k not in resource_kvs[r_id] or resource_kvs[r_id][k] in (None, "", "null")):
                            resource_kvs[r_id][k] = v

            for res_id, kv in resource_kvs.items():
                s_id = kv.get("service") or kv.get("logger")
                event = kv.get("event")

                uid = kv.get("customer_reference") or kv.get("subject_reference") or kv.get("subject_ref") or kv.get("user_id") or kv.get("subject")
                email = kv.get("email") or kv.get("lookup_key") or kv.get("subject_key") or kv.get("correlation_key")
                phone = kv.get("phone")
                email_hash = kv.get("email_hash")
                name = kv.get("display_name") or kv.get("name")

                # If lookup_key/correlation_key is a hash, put it in email_hash
                if email and len(email) == 64 and all(c in "0123456789abcdefABCDEF" for c in email):
                    email_hash = email
                    email = None

                # If lookup_key is an integer or user_id
                if email and email.startswith("user_"):
                    uid = uid or email
                    email = None

                # Normalize system_id
                if s_id in ("support_replica", "support"):
                    s_id = "support_platform"
                elif s_id in ("profile_service", "customer_account_service"):
                    s_id = "account_service"

                if not s_id or s_id == "readback_collector":
                    if res_id.startswith("account_"):
                        s_id = "account_service"
                    elif res_id.startswith("search_"):
                        s_id = "search_service"
                    elif res_id.startswith("data_flow_"):
                        s_id = "integration_service"
                    elif res_id.startswith("backup_"):
                        s_id = "backup_service"
                    elif res_id.startswith("support_"):
                        s_id = "support_platform"
                    elif res_id.startswith("analytics_"):
                        s_id = "analytics_platform"
                    elif res_id.startswith("audit_record_"):
                        s_id = "security_service"
                    elif res_id.startswith("tombstone_"):
                        s_id = "identity_service"
                    elif res_id.startswith("export_"):
                        s_id = "export_service"

                # State determination
                rec_state = "PRESENT"
                pii_exp = True

                # Profile lookups
                if kv.get("http_status") == "404" or kv.get("rows") == "0" or kv.get("total_hits") == "0" or kv.get("result") == "miss":
                    rec_state = "ABSENT"
                    pii_exp = False

                # Connectors
                is_flow = s_id == "integration_service" or res_id.startswith("data_flow_")
                if is_flow:
                    if kv.get("enabled") == "true" or kv.get("last_delivery_status") == "delivered":
                        rec_state = "ACTIVE"
                    elif kv.get("enabled") == "false" or kv.get("last_delivery_status") == "stopped":
                        rec_state = "DISABLED"

                # Backups
                is_bkp = s_id == "backup_service" or res_id.startswith("backup_")
                if is_bkp:
                    if kv.get("restore_allowed") == "false" or kv.get("deletion_block") == "true":
                        rec_state = "BLOCKED"
                    elif kv.get("restore_allowed") == "true" or kv.get("deletion_block") == "false":
                        rec_state = "ACTIVE"

                # Security audits
                is_ret = s_id == "security_service" or res_id.startswith("audit_record_")
                if is_ret:
                    rec_state = "PRESENT"

                # Analytics platform
                if s_id == "analytics_platform":
                    if not uid and not email and not phone and not name:
                        rec_state = "ANONYMIZED"
                        pii_exp = False
                    else:
                        rec_state = "PRESENT"
                        pii_exp = True

                # Support platform
                if s_id == "support_platform":
                    if not email and not phone and not name:
                        rec_state = "REDACTED"
                        pii_exp = False
                    else:
                        rec_state = "PRESENT"
                        pii_exp = True

                self._add_record(
                    IndexedRecord(
                        file_id=file_id,
                        file_path=rel_path,
                        captured_at=captured_at,
                        origin=origin,
                        system_id=s_id or "account_service",
                        resource_id=res_id,
                        user_id=uid,
                        email=email,
                        phone=phone,
                        name=name,
                        email_hash=email_hash,
                        record_state=rec_state,
                        pii_exposed=pii_exp,
                        is_data_flow=is_flow,
                        is_backup_risk=is_bkp,
                        is_retained_record=is_ret,
                        details=kv,
                    )
                )
        except Exception:
            pass

    def _parse_txt_file(self, file_id: str, rel_path: str, origin: str, captured_at: str, path: Path) -> None:
        try:
            with open(path, mode="r", encoding="utf-8") as f:
                lines = f.readlines()

            for line in lines:
                l_str = line.strip()
                if l_str.startswith("-") and "|" in l_str:
                    parts = [p.strip() for p in l_str.lstrip("-").split("|")]
                    if len(parts) >= 6:
                        ts, sys_id, res_id, category, status, identifier = parts[:6]
                        rec_state = "ABSENT" if status == "NOT_FOUND" else "PRESENT"
                        email = identifier if "@" in identifier else None
                        uid = identifier if identifier.startswith("user_") else None

                        is_flow = False
                        is_bkp = False
                        is_ret = False
                        pii_exp = False
                        rec_state = "PRESENT"

                        if category == "DATA_FLOW":
                            is_flow = True
                            rec_state = "ACTIVE" if status == "ACTIVE" else "DISABLED"
                            pii_exp = False
                        elif category == "BACKUP_ARCHIVE":
                            is_bkp = True
                            rec_state = "ACTIVE" if status == "ACTIVE" else "BLOCKED"
                            pii_exp = False
                        elif category == "SECURITY_AUDIT_LOG":
                            is_ret = True
                            rec_state = "PRESENT"
                            pii_exp = False
                        elif category == "ANALYTICS_PROFILE":
                            if status == "ANONYMIZED":
                                rec_state = "ANONYMIZED"
                                pii_exp = False
                            elif status == "NOT_FOUND":
                                rec_state = "ABSENT"
                                pii_exp = False
                            else:
                                rec_state = "PRESENT"
                                pii_exp = True
                        elif category == "SUPPORT_MESSAGE":
                            if status == "REDACTED":
                                rec_state = "REDACTED"
                                pii_exp = False
                            elif status == "NOT_FOUND":
                                rec_state = "ABSENT"
                                pii_exp = False
                            else:
                                rec_state = "PRESENT"
                                pii_exp = True
                        elif category == "SUPPORT_ATTACHMENT":
                            if status == "NOT_FOUND":
                                rec_state = "ABSENT"
                                pii_exp = False
                            else:
                                rec_state = "PRESENT"
                                pii_exp = True
                        else:
                            rec_state = "ABSENT" if status == "NOT_FOUND" else "PRESENT"
                            pii_exp = (rec_state == "PRESENT")

                        self._add_record(
                            IndexedRecord(
                                file_id=file_id,
                                file_path=rel_path,
                                captured_at=captured_at,
                                origin=origin,
                                system_id=sys_id,
                                resource_id=res_id,
                                user_id=uid,
                                email=email,
                                record_state=rec_state,
                                pii_exposed=pii_exp,
                                is_data_flow=is_flow,
                                is_backup_risk=is_bkp,
                                is_retained_record=is_ret,
                                details={
                                    "category": category,
                                    "status": status,
                                    "timestamp": ts,
                                    "enabled": (rec_state == "ACTIVE") if is_flow else None,
                                    "restore_allowed": (rec_state == "ACTIVE") if is_bkp else None,
                                },
                            )
                        )
        except Exception:
            pass

    def _parse_pdf_file(self, file_id: str, rel_path: str, origin: str, captured_at: str, path: Path) -> None:
        try:
            reader = pypdf.PdfReader(str(path))
            full_text = "\n".join([page.extract_text() or "" for page in reader.pages])

            res_matches = re.findall(r"\b(support_\w+|audit_record_\w+|account_\w+|export_\w+)\b", full_text)
            uid_matches = re.findall(r"\b(user_\d+)\b", full_text)
            email_matches = re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", full_text)
            phone_matches = re.findall(r"\+\d{1,3}\s(?:\d{2,4}\s)*\d{3,4}", full_text)

            primary_res = res_matches[0] if res_matches else ""
            primary_uid = uid_matches[0] if uid_matches else None
            primary_email = email_matches[0] if email_matches else None
            primary_phone = phone_matches[0] if phone_matches else None

            sys_id = "support_platform" if "support" in origin or primary_res.startswith("support_") else (
                "security_service" if "security" in origin or primary_res.startswith("audit_record_") else (
                    "account_service" if "account" in origin else "export_service"
                )
            )

            if primary_res:
                self._add_record(
                    IndexedRecord(
                        file_id=file_id,
                        file_path=rel_path,
                        captured_at=captured_at,
                        origin=origin,
                        system_id=sys_id,
                        resource_id=primary_res,
                        user_id=primary_uid,
                        email=primary_email,
                        phone=primary_phone,
                        record_state="PRESENT",
                        pii_exposed=True,
                        details={"extracted_text_preview": full_text[:300]},
                    )
                )
        except Exception:
            pass

    def _parse_image_file(self, file_id: str, rel_path: str, origin: str, captured_at: str, path: Path) -> None:
        if file_id in PARSED_VISUAL_EVIDENCE:
            img_meta = PARSED_VISUAL_EVIDENCE[file_id]
            for r in img_meta["records"]:
                self._add_record(
                    IndexedRecord(
                        file_id=file_id,
                        file_path=rel_path,
                        captured_at=captured_at,
                        origin=origin,
                        system_id=r.get("system_id", "account_service"),
                        resource_id=r.get("resource_id", ""),
                        user_id=r.get("user_id"),
                        email=r.get("email") or r.get("owner_email") or r.get("customer_email") or r.get("selector_email"),
                        phone=r.get("phone"),
                        name=r.get("name") or r.get("customer_name"),
                        record_state=r.get("state", "PRESENT"),
                        pii_exposed=r.get("pii_exposed", True),
                        is_data_flow=r.get("system_id") == "integration_service",
                        is_backup_risk=r.get("system_id") == "backup_service",
                        is_retained_record=r.get("system_id") == "security_service",
                        details=r,
                    )
                )

    def find_records_for_user(
        self, profile: UserIdentityProfile, audit_at: Optional[str] = None
    ) -> List[IndexedRecord]:
        """
        Retrieve all evidence records matching this user's identity graph,
        strictly filtered to captured_at <= audit_at.
        """
        matched: List[IndexedRecord] = []
        seen_keys: Set[Tuple[str, str, str]] = set()

        candidate_records: List[IndexedRecord] = []
        
        # 1. Match by user_id
        if profile.user_id in self.records_by_uid:
            candidate_records.extend(self.records_by_uid[profile.user_id])

        # 2. Match by any known email
        for e in profile.emails:
            e_lower = e.lower()
            if e_lower in self.records_by_email:
                candidate_records.extend(self.records_by_email[e_lower])

        # 3. Match by any email hash
        for h in profile.email_hashes:
            h_lower = h.lower()
            if h_lower in self.records_by_hash:
                candidate_records.extend(self.records_by_hash[h_lower])

        # 4. Match by normalized phone
        for p_digits in profile.normalized_phones:
            if p_digits in self.records_by_phone:
                candidate_records.extend(self.records_by_phone[p_digits])

        # Filter strictly <= audit_at and deduplicate
        for rec in candidate_records:
            if audit_at and rec.captured_at > audit_at:
                continue
            key = (rec.file_id, rec.system_id, rec.resource_id)
            if key not in seen_keys:
                seen_keys.add(key)
                matched.append(rec)

        return matched

    def get_activities_for_resource(
        self, resource_id: str, audit_at: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all activities for a specific resource strictly filtered to event_time <= audit_at.
        """
        acts = self.activities_by_res_id.get(resource_id, [])
        if audit_at:
            acts = [a for a in acts if a.get("event_time", "") <= audit_at]
        return sorted(acts, key=lambda x: x.get("event_time", ""))

if __name__ == "__main__":
    from config import SAMPLE_DELETION_REQUESTS_PATH, SAMPLE_OUTPUT_PATH
    from identity_resolver import IdentityResolver

    print("=" * 80)
    print("TESTING PHASE C: MULTIMODAL EVIDENCE INDEXER")
    print("=" * 80)

    indexer = EvidenceIndexer()
    print(f"Total evidence records indexed across 94 files: {len(indexer.records)}")
    print(f"Indexed by user_id: {len(indexer.records_by_uid)} users")
    print(f"Indexed by email: {len(indexer.records_by_email)} emails")
    print(f"Indexed by resource_id: {len(indexer.records_by_res_id)} resources")

    # Verify against sample cases
    resolver = IdentityResolver()
    with open(SAMPLE_DELETION_REQUESTS_PATH, mode="r", encoding="utf-8") as f:
        samples = list(csv.DictReader(f))
    with open(SAMPLE_OUTPUT_PATH, mode="r", encoding="utf-8") as f:
        ground_truth = {r["case_id"]: json.loads(r["steps_json"]) for r in csv.DictReader(f)}

    print("\nValidating evidence discovery for all 32 sample cases:")
    success_count = 0
    for s in samples:
        cid = s["case_id"]
        email = s["email"]
        audit_at = s["audit_at"]
        uid = resolver.resolve_user_id(email, audit_at)
        prof = resolver.get_user_profile(uid, audit_at)

        records = indexer.find_records_for_user(prof, audit_at)
        discovered_res = set(r.resource_id for r in records)
        discovered_evs = set(r.file_id for r in records)

        gt_steps = ground_truth[cid]
        gt_res = set(st["resource_id"] for st in gt_steps)
        gt_evs = set(st["evidence_id"] for st in gt_steps if st["evidence_id"])

        # Check coverage
        res_overlap = gt_res.intersection(discovered_res)
        ev_overlap = gt_evs.intersection(discovered_evs)
        print(f"  [{cid}] Resolved {uid} | Records: {len(records):2d} | Discovered Res: {len(discovered_res)} | GT Res: {len(gt_res)} (Matched: {len(res_overlap)}) | GT Evs: {gt_evs} (Matched: {ev_overlap})")
        if len(res_overlap) > 0 or len(gt_res) == 0:
            success_count += 1

    print(f"\nSample evidence discovery completed: {success_count}/32 cases verified!")
    print("=" * 80)
