"""
Phase E: Policy Engine & Step Generator (Step 6)

Evaluates reconstructed point-in-time resource states against dataset/deletion_rules.csv
and generates finding, remediation, and verification steps according to canonical
operation hierarchy, sorting, and evidence citation contracts.
"""

from typing import Any, Dict, List, Optional, Tuple
from config import PHASE_RANKS, OPERATION_RANKS
from state_reconstructor import ReconstructedResourceState


class PolicyEngine:
    def __init__(self) -> None:
        pass

    def evaluate_case(
        self,
        case_id: str,
        is_deletion: bool,
        resource_states: List[ReconstructedResourceState],
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Evaluate a case and return (deletion_status, steps_list).
        
        deletion_status in ("COMPLETE", "INCOMPLETE", "NOT_APPLICABLE").
        For NOT_APPLICABLE: steps_list is [].
        """
        if not is_deletion:
            return "NOT_APPLICABLE", []

        findings: List[Dict[str, Any]] = []
        remediations: List[Dict[str, Any]] = []
        verifications: List[Dict[str, Any]] = []

        for s in resource_states:
            sys_id = s.system_id
            res_id = s.resource_id
            ev_id = s.evidence_id
            curr_state = s.current_state
            pii_exp = s.pii_exposed

            # 1. Integration Service / Data Flows (Sync / Replication)
            if s.is_flow:
                if curr_state == "ACTIVE":
                    findings.append({
                        "phase": "FINDING",
                        "system_id": sys_id,
                        "resource_id": res_id,
                        "operation": "REPORT_ACTIVE_DATA_FLOW",
                        "state": "ACTIVE",
                        "evidence_id": ev_id,
                    })
                    remediations.append({
                        "phase": "REMEDIATION",
                        "system_id": sys_id,
                        "resource_id": res_id,
                        "operation": "DISABLE_DATA_FLOW",
                        "state": "DISABLED",
                        "evidence_id": "",
                    })
                    verifications.append({
                        "phase": "VERIFICATION",
                        "system_id": sys_id,
                        "resource_id": res_id,
                        "operation": "VERIFY_DATA_FLOW_DISABLED",
                        "state": "DISABLED",
                        "evidence_id": ev_id,
                    })
                else:
                    verifications.append({
                        "phase": "VERIFICATION",
                        "system_id": sys_id,
                        "resource_id": res_id,
                        "operation": "VERIFY_DATA_FLOW_DISABLED",
                        "state": "DISABLED",
                        "evidence_id": ev_id,
                    })

            # 2. Backup Service / Restore Risks (Rule 14)
            elif s.is_backup:
                if curr_state == "ACTIVE":
                    findings.append({
                        "phase": "FINDING",
                        "system_id": sys_id,
                        "resource_id": res_id,
                        "operation": "REPORT_RESTORE_RISK",
                        "state": "ACTIVE",
                        "evidence_id": ev_id,
                    })
                    remediations.append({
                        "phase": "REMEDIATION",
                        "system_id": sys_id,
                        "resource_id": res_id,
                        "operation": "BLOCK_RESTORE",
                        "state": "BLOCKED",
                        "evidence_id": "",
                    })
                    verifications.append({
                        "phase": "VERIFICATION",
                        "system_id": sys_id,
                        "resource_id": res_id,
                        "operation": "VERIFY_RESTORE_BLOCKED",
                        "state": "BLOCKED",
                        "evidence_id": ev_id,
                    })
                else:
                    verifications.append({
                        "phase": "VERIFICATION",
                        "system_id": sys_id,
                        "resource_id": res_id,
                        "operation": "VERIFY_RESTORE_BLOCKED",
                        "state": "BLOCKED",
                        "evidence_id": ev_id,
                    })

            # 3. Retained Security Audit / Legal Hold Records (Rules 12, 13)
            elif s.is_retained:
                verifications.append({
                    "phase": "VERIFICATION",
                    "system_id": sys_id,
                    "resource_id": res_id,
                    "operation": "VERIFY_RECORD_PRESENT",
                    "state": "PRESENT",
                    "evidence_id": ev_id,
                })

            # 4. Identity Service Account Tombstones (Rule 15)
            elif s.is_tombstone:
                if pii_exp or curr_state == "PRESENT":
                    findings.append({
                        "phase": "FINDING",
                        "system_id": sys_id,
                        "resource_id": res_id,
                        "operation": "REPORT_EXPOSED_PII",
                        "state": "PRESENT",
                        "evidence_id": ev_id,
                    })
                    remediations.append({
                        "phase": "REMEDIATION",
                        "system_id": sys_id,
                        "resource_id": res_id,
                        "operation": "REDACT_RECORD",
                        "state": "REDACTED",
                        "evidence_id": "",
                    })
                    verifications.append({
                        "phase": "VERIFICATION",
                        "system_id": sys_id,
                        "resource_id": res_id,
                        "operation": "VERIFY_RECORD_REDACTED",
                        "state": "REDACTED",
                        "evidence_id": ev_id,
                    })
                else:
                    verifications.append({
                        "phase": "VERIFICATION",
                        "system_id": sys_id,
                        "resource_id": res_id,
                        "operation": "VERIFY_RECORD_REDACTED",
                        "state": "REDACTED",
                        "evidence_id": ev_id,
                    })

            # 5. Marketing Profiles (Rule 10) - Always DELETE
            elif s.is_marketing:
                if curr_state != "ABSENT":
                    findings.append({
                        "phase": "FINDING",
                        "system_id": sys_id,
                        "resource_id": res_id,
                        "operation": "REPORT_REMAINING_RECORD",
                        "state": "PRESENT",
                        "evidence_id": ev_id,
                    })
                    remediations.append({
                        "phase": "REMEDIATION",
                        "system_id": sys_id,
                        "resource_id": res_id,
                        "operation": "DELETE_RECORD",
                        "state": "ABSENT",
                        "evidence_id": "",
                    })
                    verifications.append({
                        "phase": "VERIFICATION",
                        "system_id": sys_id,
                        "resource_id": res_id,
                        "operation": "VERIFY_RECORD_ABSENT",
                        "state": "ABSENT",
                        "evidence_id": ev_id,
                    })
                else:
                    verifications.append({
                        "phase": "VERIFICATION",
                        "system_id": sys_id,
                        "resource_id": res_id,
                        "operation": "VERIFY_RECORD_ABSENT",
                        "state": "ABSENT",
                        "evidence_id": ev_id,
                    })

            # 6. Analytics Platform Profiles / Telemetry (Rules 07, 08) - ANONYMIZE
            elif sys_id == "analytics_platform":
                if curr_state == "ABSENT":
                    verifications.append({
                        "phase": "VERIFICATION",
                        "system_id": sys_id,
                        "resource_id": res_id,
                        "operation": "VERIFY_RECORD_ABSENT",
                        "state": "ABSENT",
                        "evidence_id": ev_id,
                    })
                elif pii_exp or curr_state == "PRESENT":
                    findings.append({
                        "phase": "FINDING",
                        "system_id": sys_id,
                        "resource_id": res_id,
                        "operation": "REPORT_EXPOSED_PII",
                        "state": "PRESENT",
                        "evidence_id": ev_id,
                    })
                    remediations.append({
                        "phase": "REMEDIATION",
                        "system_id": sys_id,
                        "resource_id": res_id,
                        "operation": "ANONYMIZE_RECORD",
                        "state": "ANONYMIZED",
                        "evidence_id": "",
                    })
                    verifications.append({
                        "phase": "VERIFICATION",
                        "system_id": sys_id,
                        "resource_id": res_id,
                        "operation": "VERIFY_RECORD_ANONYMIZED",
                        "state": "ANONYMIZED",
                        "evidence_id": ev_id,
                    })
                else:
                    verifications.append({
                        "phase": "VERIFICATION",
                        "system_id": sys_id,
                        "resource_id": res_id,
                        "operation": "VERIFY_RECORD_ANONYMIZED",
                        "state": "ANONYMIZED",
                        "evidence_id": ev_id,
                    })

            # 7. Support Platform (Rules 05, 06)
            elif sys_id == "support_platform":
                if s.is_attachment:
                    # Support Attachment (Rule 06) -> DELETE
                    if curr_state != "ABSENT":
                        findings.append({
                            "phase": "FINDING",
                            "system_id": sys_id,
                            "resource_id": res_id,
                            "operation": "REPORT_REMAINING_RECORD",
                            "state": "PRESENT",
                            "evidence_id": ev_id,
                        })
                        remediations.append({
                            "phase": "REMEDIATION",
                            "system_id": sys_id,
                            "resource_id": res_id,
                            "operation": "DELETE_RECORD",
                            "state": "ABSENT",
                            "evidence_id": "",
                        })
                        verifications.append({
                            "phase": "VERIFICATION",
                            "system_id": sys_id,
                            "resource_id": res_id,
                            "operation": "VERIFY_RECORD_ABSENT",
                            "state": "ABSENT",
                            "evidence_id": ev_id,
                        })
                    else:
                        verifications.append({
                            "phase": "VERIFICATION",
                            "system_id": sys_id,
                            "resource_id": res_id,
                            "operation": "VERIFY_RECORD_ABSENT",
                            "state": "ABSENT",
                            "evidence_id": ev_id,
                        })
                else:
                    # Support Message (Rule 05) -> REDACT
                    if pii_exp or curr_state == "PRESENT":
                        findings.append({
                            "phase": "FINDING",
                            "system_id": sys_id,
                            "resource_id": res_id,
                            "operation": "REPORT_EXPOSED_PII",
                            "state": "PRESENT",
                            "evidence_id": ev_id,
                        })
                        remediations.append({
                            "phase": "REMEDIATION",
                            "system_id": sys_id,
                            "resource_id": res_id,
                            "operation": "REDACT_RECORD",
                            "state": "REDACTED",
                            "evidence_id": "",
                        })
                        verifications.append({
                            "phase": "VERIFICATION",
                            "system_id": sys_id,
                            "resource_id": res_id,
                            "operation": "VERIFY_RECORD_REDACTED",
                            "state": "REDACTED",
                            "evidence_id": ev_id,
                        })
                    else:
                        verifications.append({
                            "phase": "VERIFICATION",
                            "system_id": sys_id,
                            "resource_id": res_id,
                            "operation": "VERIFY_RECORD_REDACTED",
                            "state": "REDACTED",
                            "evidence_id": ev_id,
                        })

            # 8. All other systems (account_service, search_service, export_service) -> DELETE
            else:
                if curr_state != "ABSENT":
                    findings.append({
                        "phase": "FINDING",
                        "system_id": sys_id,
                        "resource_id": res_id,
                        "operation": "REPORT_REMAINING_RECORD",
                        "state": "PRESENT",
                        "evidence_id": ev_id,
                    })
                    remediations.append({
                        "phase": "REMEDIATION",
                        "system_id": sys_id,
                        "resource_id": res_id,
                        "operation": "DELETE_RECORD",
                        "state": "ABSENT",
                        "evidence_id": "",
                    })
                    verifications.append({
                        "phase": "VERIFICATION",
                        "system_id": sys_id,
                        "resource_id": res_id,
                        "operation": "VERIFY_RECORD_ABSENT",
                        "state": "ABSENT",
                        "evidence_id": ev_id,
                    })
                else:
                    verifications.append({
                        "phase": "VERIFICATION",
                        "system_id": sys_id,
                        "resource_id": res_id,
                        "operation": "VERIFY_RECORD_ABSENT",
                        "state": "ABSENT",
                        "evidence_id": ev_id,
                    })

        # Determine deletion_status and apply evidence citation rules
        if findings:
            status = "INCOMPLETE"
            # In INCOMPLETE cases, all proposed remediations and post-remediation verifications have evidence_id: ""
            for v in verifications:
                v["evidence_id"] = ""
            all_steps = findings + remediations + verifications
        else:
            status = "COMPLETE"
            all_steps = verifications

        # Canonical sort
        def step_sort_key(step: Dict[str, Any]) -> Tuple[int, int, str, str]:
            p_rank = PHASE_RANKS[step["phase"]]
            op_rank = OPERATION_RANKS[step["phase"]][step["operation"]]
            return (p_rank, op_rank, step["system_id"], step["resource_id"])

        all_steps.sort(key=step_sort_key)

        # 1-indexed sequential step numbering
        for idx, s in enumerate(all_steps, 1):
            s["step_no"] = idx

        return status, all_steps
