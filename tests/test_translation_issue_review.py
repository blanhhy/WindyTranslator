from tools.translation_issue_review.review_app import (
    filter_entries,
    scan_translation_data,
    strip_control_codes,
    update_translation_consistency,
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


def test_filter_can_exclude_the_selected_status_category():
    data = {
        "MapA": {
            "重复": _message("译文 1"),
            r"\C[3]重复": _message("译文 2"),
            "普通": _message("译文 3"),
        }
    }

    entries = scan_translation_data(data)
    excluded = filter_entries(entries, status_mode="recall", exclude_status=True)

    assert [entry.original_key for entry in excluded] == ["普通"]


def test_filter_can_exclude_each_text_filter_independently():
    data = {
        "MapA": {
            "甲": {**_message("译文 甲"), "speaker_id": "Alice"},
            "乙": {**_message("译文 乙"), "speaker_id": "Bob"},
        },
        "MapB": {
            "丙": {**_message("译文 丙"), "speaker_id": "Alice"},
        },
    }

    entries = scan_translation_data(data)
    excluded_map = filter_entries(
        entries,
        status_mode="all",
        exclude_map=True,
        map_filter="mapa",
    )
    excluded_speaker = filter_entries(
        entries,
        status_mode="all",
        exclude_speaker=True,
        speaker_filter="alice",
    )
    excluded_keyword = filter_entries(
        entries,
        status_mode="all",
        exclude_keyword=True,
        keyword_filter="甲",
    )

    assert [entry.original_key for entry in excluded_map] == ["丙"]
    assert [entry.original_key for entry in excluded_speaker] == ["乙"]
    assert [entry.original_key for entry in excluded_keyword] == ["乙", "丙"]


def test_recall_translation_mismatch_marks_the_whole_group_only_in_status():
    data = {
        "MapA": {"重复": _message("相同")},
        "MapB": {r"\C[3]重复": _message("不同")},
    }

    entries = scan_translation_data(data)

    assert all(entry.is_inconsistent for entry in entries)
    assert all("不统一" in entry.status_label for entry in entries)
    assert all("不统一" not in entry.issue_label for entry in entries)
    assert filter_entries(entries, status_mode="inconsistent") == entries


def test_translation_control_code_differences_are_ignored_for_consistency():
    data = {
        "MapA": {
            "重复": _message(r"\C[1]同一句"),
            r"\S[2]重复": _message(r"\V[3]同一句"),
        }
    }

    entries = scan_translation_data(data)

    assert all(not entry.is_inconsistent for entry in entries)


def test_continuation_translation_mismatch_marks_only_the_broken_pair():
    data = {
        "MapA": {
            "甲": _message("a"),
            "甲乙": _message("x"),
            "甲乙丙": _message("xy"),
        }
    }

    entries = scan_translation_data(data)

    assert [entry.is_inconsistent for entry in entries] == [True, True, False]

    entries[1].update_text("a")
    entries[2].update_text("ab")
    update_translation_consistency(entries)

    assert [entry.is_inconsistent for entry in entries] == [False, False, False]
