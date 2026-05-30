"""Generate drift gold dataset fixtures."""
import json
import os

gold_dir = "tests/fixtures/drift_gold"

cases = [
    {
        "case_id": "case_001",
        "character_name": "Viktor",
        "chapter_summary": "Viktor, who has always been cautious and methodical, suddenly charges into battle without any tactical planning, screaming war cries.",
        "canon_anchor": {"character_id": "viktor", "stable_traits": ["cautious", "methodical", "analytical"], "values": ["strategic thinking", "self-preservation"], "taboos": ["reckless endangerment"]},
        "expected_positive": True,
        "expected_drift_type": "ooc_behavior",
        "expected_severity": "creative_review",
    },
    {
        "case_id": "case_002",
        "character_name": "Elena",
        "chapter_summary": "Elena, who has always valued honesty above all, deliberately lies to her closest friend to protect a minor secret. She shows no guilt.",
        "canon_anchor": {"character_id": "elena", "stable_traits": ["honest", "loyal", "empathetic"], "values": ["truth", "loyalty", "compassion"], "taboos": ["deception of friends"]},
        "expected_positive": True,
        "expected_drift_type": "value_violation",
        "expected_severity": "hard_pause",
    },
    {
        "case_id": "case_003",
        "character_name": "Marcus",
        "chapter_summary": "Marcus, who speaks in formal academic prose, suddenly uses modern slang and internet abbreviations in his dialogue with the queen.",
        "canon_anchor": {"character_id": "marcus", "stable_traits": ["scholarly", "formal", "reserved"], "voice_markers": ["academic vocabulary", "complete sentences"], "taboos": []},
        "expected_positive": True,
        "expected_drift_type": "voice_drift",
        "expected_severity": "soft_warning",
    },
    {
        "case_id": "case_004",
        "character_name": "Aria",
        "chapter_summary": "Aria casually mentions details about the enemy spy network that she has no way of knowing. She was never briefed on intelligence matters.",
        "canon_anchor": {"character_id": "aria", "stable_traits": ["brave", "naive", "trusting"], "values": ["family", "honor"], "taboos": ["betrayal"], "knowledge_boundary": ["no intelligence access"]},
        "expected_positive": True,
        "expected_drift_type": "knowledge_boundary_violation",
        "expected_severity": "hard_pause",
    },
    {
        "case_id": "case_005",
        "character_name": "Thorne",
        "chapter_summary": "Thorne, a gentle healer, suddenly displays expert sword fighting skills and kills three armed soldiers without any prior combat training.",
        "canon_anchor": {"character_id": "thorne", "stable_traits": ["gentle", "nurturing", "conflict-averse"], "values": ["life preservation", "healing"], "taboos": ["unnecessary violence"]},
        "expected_positive": True,
        "expected_drift_type": "ooc_behavior",
        "expected_severity": "creative_review",
    },
    {
        "case_id": "case_006",
        "character_name": "Lena",
        "chapter_summary": "Lena reflects on her past mistakes and decides to be more cautious in future negotiations. She practices new techniques with her mentor.",
        "canon_anchor": {"character_id": "lena", "stable_traits": ["adaptable", "introspective", "growth-oriented"], "values": ["self-improvement", "learning"], "taboos": []},
        "expected_positive": False,
        "expected_drift_type": "",
        "expected_severity": "none",
    },
    {
        "case_id": "case_007",
        "character_name": "Kai",
        "chapter_summary": "Kai shows sadness and vulnerability after losing his companion. He withdraws but eventually accepts support from friends.",
        "canon_anchor": {"character_id": "kai", "stable_traits": ["resilient", "emotional", "caring"], "values": ["friendship", "emotional authenticity"], "taboos": []},
        "expected_positive": False,
        "expected_drift_type": "",
        "expected_severity": "none",
    },
    {
        "case_id": "case_008",
        "character_name": "Sophia",
        "chapter_summary": "Sophia decides to challenge her prejudice against northern tribes after witnessing their culture. She acknowledges her narrow-mindedness.",
        "canon_anchor": {"character_id": "sophia", "stable_traits": ["open-minded", "curious", "adaptable"], "values": ["truth-seeking", "growth"], "taboos": []},
        "expected_positive": False,
        "expected_drift_type": "",
        "expected_severity": "none",
    },
]

os.makedirs(f"{gold_dir}/cases", exist_ok=True)

manifest_cases = []
for case in cases:
    case_id = case["case_id"]
    case_dir = f"{gold_dir}/cases/{case_id}"
    os.makedirs(case_dir, exist_ok=True)

    with open(f"{case_dir}/input_summary.json", "w") as f:
        json.dump({"chapter_id": f"ch_{case_id[-3:]}", "arc_id": "arc_001", "content": case["chapter_summary"]}, f, indent=2)

    with open(f"{case_dir}/canon_anchor.json", "w") as f:
        json.dump(case["canon_anchor"], f, indent=2)

    with open(f"{case_dir}/expected.json", "w") as f:
        json.dump({
            "expected_positive": case["expected_positive"],
            "expected_drift_type": case["expected_drift_type"],
            "expected_severity": case["expected_severity"],
        }, f, indent=2)

    manifest_cases.append({"case_id": case_id, "character_name": case["character_name"]})

manifest = {
    "schema_version": "1.0",
    "dataset_version": 1,
    "case_count": len(cases),
    "positive_cases": sum(1 for c in cases if c["expected_positive"]),
    "negative_cases": sum(1 for c in cases if not c["expected_positive"]),
    "cases": manifest_cases,
    "generated_by": "manual",
}
with open(f"{gold_dir}/gold_manifest.json", "w") as f:
    json.dump(manifest, f, indent=2)

print(f"Generated {len(cases)} gold cases ({sum(1 for c in cases if c['expected_positive'])} positive, {sum(1 for c in cases if not c['expected_positive'])} negative)")
