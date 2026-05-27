# Deferred Scope

## P1 Deferred
- Checkpoint resume (arc_contract.checkpoint_chapters field exists, NovelFlow integration partial)
- Source-layered RAG (RAG index not implemented, context built from direct file reads)
- Relationship ledger (schema defined, MVP uses timeline/knowledge/foreshadowing only)
- Emotion arc ledger (schema defined, MVP uses timeline/knowledge/foreshadowing only)

## P2 Deferred
- Full CrewAI Flow restoration (currently using function-based orchestration due to Pydantic state serialization issues)
- Plugin runtime (directory structure exists, runtime disabled)
- Multi-process lock (single-process LockManager implemented, file-based lock for production)
- Schema migration (single version supported, unknown version rejected)
- Unicode/case path hardening (MVP uses ASCII-only paths)
