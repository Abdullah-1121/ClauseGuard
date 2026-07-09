from app.pipeline.parse import segment


def test_segment_offsets_round_trip():
    text = "First clause here.\n\n  Second clause with leading space.\n\nThird."
    clauses = segment(text)
    assert len(clauses) == 3
    # The core invariant: every clause's offsets recover its exact text.
    for clause in clauses:
        assert text[clause.start : clause.end] == clause.text
    assert clauses[1].text == "Second clause with leading space."


def test_segment_ignores_blank_chunks():
    text = "\n\n\nOnly one real clause.\n\n\n"
    clauses = segment(text)
    assert len(clauses) == 1
    assert clauses[0].text == "Only one real clause."
