# fix-mvp-s-blocking Proof Matrix

Each DoD (Definition of Done) mapped to specific test file and test function.

## Group 2: system_script Full-Path Guard Coverage

| DoD | Test File | Test Function |
|-----|-----------|---------------|
| arc_contract write guarded in flow.py | `tests/test_path_safety.py` | `test_system_script_arc_contract_succeeds` |
| canon_manuscript_copy guarded in canonicalizer.py | `tests/test_path_safety.py` | `test_system_script_canon_manuscript_copy_succeeds` |
| canon_character_update guarded in atomic_apply_manager.py | `tests/test_path_safety.py` | `test_system_script_canon_character_update_succeeds` |
| progress.jsonl write guarded in flow.py | `tests/test_path_safety.py` | `test_system_script_can_write_progress` |
| ledger_diff write guarded in flow.py | `tests/test_path_safety.py` | `test_system_script_can_write_ledgers` |
| dashboard_report write guarded in flow.py | `tests/test_path_safety.py` | `test_system_script_known_types_succeed_unknown_rejected` |
| apply_record write guarded in atomic_apply_manager.py | `tests/test_path_safety.py` | `test_system_script_known_types_succeed_unknown_rejected` |
| consumed_hashes write guarded in atomic_apply_manager.py | `tests/test_path_safety.py` | `test_system_script_known_types_succeed_unknown_rejected` |
| ledger_diff apply guarded in atomic_apply_manager.py | `tests/test_path_safety.py` | `test_system_script_can_write_ledgers` |
| All known artifact types accepted, unknown rejected | `tests/test_path_safety.py` | `test_system_script_known_types_succeed_unknown_rejected` |

## Group 3: rollback_snapshot + inverse_diff Alignment

| DoD | Test File | Test Function |
|-----|-----------|---------------|
| inverse_diff path accepted | `tests/test_path_safety.py` | `test_system_script_inverse_diff_succeeds` |
| inverse_diff wrong path rejected | `tests/test_path_safety.py` | `test_system_script_inverse_diff_wrong_path_rejected` |
| rollback_snapshot still points to archive/snapshot_* | `src/novel_workflow/guards/path_safety.py` | Entry in `_SYSTEM_SCRIPT_ALLOWED` (no test change needed - unchanged regex) |

## Group 4: Rejected Gate Apply Order

| DoD | Test File | Test Function |
|-----|-----------|---------------|
| Rejected gate evidence required | `tests/test_e2e_failure_paths.py` | `test_rejected_gate_evidence_required` |
| Rejected gate with evidence accepted | `tests/test_e2e_failure_paths.py` | `test_rejected_gate_with_evidence_accepted` |
| Rejected gate triggers hard_pause not apply | `tests/test_e2e_failure_paths.py` | `test_rejected_gate_blocks_apply` |
| Gate validator enforces rejected evidence | `tests/test_e2e_failure_paths.py` | `test_rejected_gate_evidence_required` |

## Group 5: Pause Taxonomy Alignment

| DoD | Test File | Test Function |
|-----|-----------|---------------|
| CANON_DIRECT_CONFLICT is hard_pause | `tests/test_pause_routing.py` | `TestRouteFailureHardPause::test_canon_conflict_is_hard_pause` |
| AWS_CANON_CONFLICT remains creative_review | `tests/test_pause_routing.py` | `TestRouteFailureCreativeReview::test_aws_canon_conflict_is_creative_review` |
| AUDIT_BLOCKING remains creative_review | `tests/test_pause_routing.py` | `TestRouteFailureCreativeReview::test_audit_blocking_is_creative_review` |
| Hard pause author options include Fix/Archive | `tests/test_pause_detector.py` | `test_pause_report_has_author_options` |

## Group 7: Dry-Run Artifact Verification

| DoD | Test File | Test Function |
|-----|-----------|---------------|
| apply_record checks non-empty diff_hash | `verify_llm_dry_run.py` | `verify_dry_run()` - checks `ledger_diff_hash` is non-empty |
| ledgers entries > 0 verified | `verify_llm_dry_run.py` | `verify_dry_run()` - checks `len(entries) == 0` |
| arc_working_state entries > 0 verified | `verify_llm_dry_run.py` | `verify_dry_run()` - checks `len(entries) == 0` |
