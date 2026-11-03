from portal.engine.protocol import STEP_RANGES, decode, encode, overall_pct


def test_ranges_cover_0_to_100_in_order():
    spans = list(STEP_RANGES.values())
    assert spans[0][0] == 0 and spans[-1][1] == 100
    assert all(a[1] == b[0] for a, b in zip(spans, spans[1:]))


def test_overall_pct():
    assert overall_pct("compile", 0.5) == 67.5
    assert overall_pct("generate", 0) == 0
    assert overall_pct("package", 1) == 100


def test_overall_pct_clamps_fraction():
    assert overall_pct("buildings", 1.7) == 45
    assert overall_pct("buildings", -1) == 15


def test_decode_ignores_non_json():
    assert decode("wrote 854 .tbx files") is None
    assert decode("") is None
    assert decode("[1, 2]") is None


def test_round_trip():
    e = {"event": "progress", "step": "compile", "pct": 50.0, "message": "cells 3/25"}
    assert decode(encode(e)) == e
