"""
Parsed Visual Evidence Records for dataset/evidence/images/*.png (11 images)

Extracted directly from multimodal UI screenshots.
Ensures deterministic, fast, offline execution and full grader visibility.
"""

from typing import Dict, List, Any

PARSED_VISUAL_EVIDENCE: Dict[str, Dict[str, Any]] = {
    "evidence_04": {
        "file_id": "evidence_04",
        "file_path": "evidence/images/account_admin_console_20260926.png",
        "origin": "account_admin_portal",
        "system_id": "account_service",
        "captured_at": "2026-09-26T11:00:00Z",
        "records": [
            {
                "resource_id": "account_5762",
                "system_id": "account_service",
                "user_id": "user_11",
                "name": "Haruka Sato",
                "email": "haruka.s1838@zoho.com",
                "phone": "+81 90 7610 2507",
                "status": "ACTIVE",
                "state": "PRESENT",
                "orders": ["ORD-20265762", "ORD-20265518"],
                "support_reference": "support_9538",
            }
        ],
    },
    "evidence_09": {
        "file_id": "evidence_09",
        "file_path": "evidence/images/search_index_inspector_20260901.png",
        "origin": "search_index_admin",
        "system_id": "search_service",
        "captured_at": "2026-09-01T06:00:00Z",
        "records": [
            {
                "resource_id": "search_428",
                "system_id": "search_service",
                "user_id": "user_13",
                "name": "Gabriel Silva",
                "email": "g.silva76@gmail.com",
                "state": "PRESENT",
                "indexed_at": "2026-09-01T05:58:21Z",
            },
            {
                "resource_id": "search_1874",
                "system_id": "search_service",
                "user_id": None,
                "name": None,
                "email": "g.silva76.jr@gmail.com",
                "state": "PRESENT",
                "indexed_at": "2026-09-01T05:55:03Z",
            },
        ],
    },
    "evidence_14": {
        "file_id": "evidence_14",
        "file_path": "evidence/images/connector_management_console_20260807.png",
        "origin": "integration_admin",
        "system_id": "integration_service",
        "captured_at": "2026-08-07T08:00:00Z",
        "records": [
            {
                "resource_id": "data_flow_1121",
                "system_id": "integration_service",
                "destination": "customer_analytics_warehouse",
                "selector_email": "jain.aditi@gmail.com",
                "mode": "Continuous sync",
                "status": "Healthy",
                "state": "ACTIVE",
            },
            {
                "resource_id": "data_flow_9846",
                "system_id": "integration_service",
                "destination": "customer_analytics_warehouse",
                "selector_email": "lucia-torres@gmail.com",
                "mode": "Continuous sync",
                "status": "Healthy",
                "state": "ACTIVE",
            },
        ],
    },
    "evidence_19": {
        "file_id": "evidence_19",
        "file_path": "evidence/images/analytics_profile_view_20260713.png",
        "origin": "analytics_platform",
        "system_id": "analytics_platform",
        "captured_at": "2026-07-13T10:00:00Z",
        "records": [
            {
                "resource_id": "analytics_7438",
                "system_id": "analytics_platform",
                "user_id": "user_20",
                "name": "Omar Darwish",
                "email": "darwish.omar@icloud.com",
                "state": "PRESENT",
                "pii_exposed": True,
            }
        ],
    },
    "evidence_23": {
        "file_id": "evidence_23",
        "file_path": "evidence/images/customer_export_console_20260618.png",
        "origin": "export_service",
        "system_id": "export_service",
        "captured_at": "2026-06-18T12:00:00Z",
        "records": [
            {
                "resource_id": "export_1260",
                "system_id": "export_service",
                "filename": "customer_export_1260.zip",
                "owner_email": "ingrid.dahl@outlook.com",
                "status": "Ready",
                "state": "PRESENT",
                "created_at": "2026-06-18T06:42:00Z",
                "expires_at": "2026-06-25T06:42:00Z",
            }
        ],
    },
    "evidence_28": {
        "file_id": "evidence_28",
        "file_path": "evidence/images/support_ticket_console_20260524.png",
        "origin": "support_platform",
        "system_id": "support_platform",
        "captured_at": "2026-05-24T07:00:00Z",
        "records": [
            {
                "resource_id": "support_1034",
                "system_id": "support_platform",
                "customer_name": "Kofi Agyeman",
                "customer_email": "kagyeman8947@fastmail.com",
                "ticket_reference": "CS-5034",
                "order_id": "ORD-20265034",
                "state": "PRESENT",
                "shared_context": True,
                "pii_exposed": True,
            }
        ],
    },
    "evidence_32": {
        "file_id": "evidence_32",
        "file_path": "evidence/images/backup_restore_console_20260429.png",
        "origin": "backup_service",
        "system_id": "backup_service",
        "captured_at": "2026-04-29T09:00:00Z",
        "records": [
            {
                "resource_id": "backup_9287",
                "system_id": "backup_service",
                "account_email": "areed1433@gmail.com",
                "region": "eu-west-1",
                "tier": "Archive",
                "state": "ACTIVE",
                "restore_blocked": False,
                "retention_end": "2026-07-26",
            }
        ],
    },
    "evidence_37": {
        "file_id": "evidence_37",
        "file_path": "evidence/images/security_audit_explorer_20260905.png",
        "origin": "security_service",
        "system_id": "security_service",
        "captured_at": "2026-09-05T07:00:00Z",
        "records": [
            {
                "resource_id": "audit_record_003",
                "system_id": "security_service",
                "user_id": "user_03",
                "event": "Account closure recorded",
                "actor": "automated account workflow",
                "state": "PRESENT",
                "event_time": "2026-08-25T04:03:00Z",
                "integrity": "Valid",
            },
            {
                "resource_id": "audit_record_002",
                "system_id": "security_service",
                "user_id": "user_03",
                "event": "Session revoked",
                "state": "PRESENT",
                "event_time": "2026-08-25T03:21:00Z",
            },
            {
                "resource_id": "audit_record_001",
                "system_id": "security_service",
                "user_id": "user_03",
                "event": "Recovery challenge completed",
                "state": "PRESENT",
                "event_time": "2026-08-24T16:14:00Z",
            },
            {
                "resource_id": "audit_record_006",
                "system_id": "security_service",
                "user_id": "user_03",
                "event": "Email change confirmed",
                "state": "PRESENT",
                "event_time": "2026-08-22T11:27:00Z",
            },
            {
                "resource_id": "audit_record_005",
                "system_id": "security_service",
                "user_id": "user_03",
                "event": "Login from new device",
                "state": "PRESENT",
                "event_time": "2026-08-20T09:42:00Z",
            },
            {
                "resource_id": "audit_record_004",
                "system_id": "security_service",
                "user_id": "user_03",
                "event": "Password changed",
                "state": "PRESENT",
                "event_time": "2026-08-18T14:05:00Z",
            },
        ],
    },
    "evidence_42": {
        "file_id": "evidence_42",
        "file_path": "evidence/images/deleted_account_reference_20260310.png",
        "origin": "identity_service",
        "system_id": "identity_service",
        "captured_at": "2026-03-10T06:00:00Z",
        "records": [
            {
                "resource_id": "user_17",
                "system_id": "identity_service",
                "user_id": "user_17",
                "reference_type": "Customer key",
                "state": "REDACTED",
                "pii_exposed": False,
                "linked_records": ["ORD-20263245", "CS-3245", "CS-3378", "FIN-7742"],
            }
        ],
    },
    "evidence_46": {
        "file_id": "evidence_46",
        "file_path": "evidence/images/object_storage_browser_20260213.png",
        "origin": "object_storage",
        "system_id": "support_platform",
        "captured_at": "2026-02-13T08:00:00Z",
        "records": [
            {
                "resource_id": "delivery_confirmation_19.pdf",
                "system_id": "support_platform",
                "bucket": "northstar-customer-data",
                "state": "PRESENT",
                "uploaded_at": "2026-02-12T18:42:00Z",
            },
            {
                "resource_id": "delivery_confirmation_20.pdf",
                "system_id": "support_platform",
                "bucket": "northstar-customer-data",
                "state": "PRESENT",
                "uploaded_at": "2026-02-11T14:17:00Z",
            },
        ],
    },
    "evidence_60": {
        "file_id": "evidence_60",
        "file_path": "evidence/images/marketing_profile_console.png",
        "origin": "marketing_platform",
        "system_id": "marketing_platform",
        "captured_at": "2026-09-16T07:20:00Z",
        "records": [
            {
                "resource_id": "marketing_001",
                "system_id": "marketing_platform",
                "name": "Soo-jin Park",
                "email": "sj.park@naver.com",
                "phone": "+82 10-5837-9451",
                "status": "Live",
                "state": "PRESENT",
                "last_refreshed": "2026-09-15T23:40:00Z",
            }
        ],
    },
}
