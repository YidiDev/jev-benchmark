from qtree.predictions import ChunkRecord, group_traces


def _rec(**kw) -> ChunkRecord:
    base = dict(
        arm="jev",
        form_id="qt_te_001",
        split="test",
        k=5,
        repeat=1,
        labeling="semantic",
        chunk_index=0,
        start_node="n1_0",
        destinations=["n6_0", "n6_1"],
        chosen_display="n6_0",
        chosen_canonical="n6_0",
        true_local_destination="n6_0",
        local_correct=True,
    )
    base.update(kw)
    return ChunkRecord(**base)


def test_group_traces_groups_by_form_k_repeat_labeling():
    a = _rec(chunk_index=0)
    b = _rec(chunk_index=1, start_node="n6_0")
    other_trace = _rec(form_id="qt_te_002", chunk_index=0)
    groups = group_traces([a, b, other_trace])
    assert len(groups) == 2
    key = ("qt_te_001", 5, 1, "semantic")
    assert key in groups
    assert [c.chunk_index for c in groups[key]] == [0, 1]


def test_group_traces_sorts_by_chunk_index_even_if_out_of_order():
    b = _rec(chunk_index=1, start_node="n6_0")
    a = _rec(chunk_index=0)
    groups = group_traces([b, a])
    key = ("qt_te_001", 5, 1, "semantic")
    assert [c.chunk_index for c in groups[key]] == [0, 1]
