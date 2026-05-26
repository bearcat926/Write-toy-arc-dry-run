from novel_workflow.schemas.ledgers import (
    TimelineEvent,
    CharacterKnowledgeEntry,
    ForeshadowEntry,
)


def test_timeline_event():
    e = TimelineEvent(event_id="evt_001", time_marker="day_01", summary="A arrives")
    assert e.schema_version == "1.0"


def test_character_knowledge():
    k = CharacterKnowledgeEntry(
        character_id="char_a",
        knowledge="B's real identity",
        knowledge_source="saw",
        certainty="confirmed",
    )
    assert k.knowledge_source == "saw"


def test_foreshadow_entry():
    f = ForeshadowEntry(foreshadow_id="fs_001", summary="The broken sword")
    assert f.status == "introduced"
