from tools.translation_issue_review.review_app import (
    filter_entries,
    scan_translation_data,
    strip_control_codes,
)


def _message(text):
    return {
        "text": text,
        "original_marker": "Message",
        "speaker_id": "NARRATION",
    }


def test_strip_control_codes_removes_easy_rpg_message_codes():
    text = r"\C[10]同\S[2]\V[4]\N[1]\T[2]\.\|\!\>\<\^\$\_"

    assert strip_control_codes(text) == "同"
    assert strip_control_codes("同\n句") == "同\n句"


def test_scan_detects_recall_groups_across_maps_and_control_code_variants():
    data = {
        "MapA": {
            "A": _message("译文 A1"),
            "B": _message("译文 B1"),
        },
        "MapB": {
            r"\C[3]B": _message("译文 B2"),
            r"\S[2]A": _message("译文 A2"),
        },
    }

    entries = scan_translation_data(data)
    recall_entries = filter_entries(entries, status_mode="recall")

    assert [entry.original_key for entry in recall_entries] == [
        "A",
        r"\S[2]A",
        "B",
        r"\C[3]B",
    ]
    assert all(entry.is_recall for entry in recall_entries)


def test_scan_detects_adjacent_continuation_chain_and_ignores_choices():
    data = {
        "MapA": {
            "前缀": _message("第一步"),
            "前缀内容": _message("第二步"),
            "前缀内容更多": _message("第三步"),
            "选择": {
                "text": "选项",
                "original_marker": "Choice",
                "speaker_id": "",
            },
            "独立": _message("独立"),
        },
        "MapB": {
            "另一句": _message("另一句"),
        },
    }

    entries = scan_translation_data(data)
    continuation_entries = filter_entries(entries, status_mode="continuation")

    assert [entry.original_key for entry in continuation_entries] == [
        "前缀",
        "前缀内容",
        "前缀内容更多",
    ]
    assert len({entry.continuation_group_id for entry in continuation_entries}) == 1
    assert all(entry.is_continuation for entry in continuation_entries)
