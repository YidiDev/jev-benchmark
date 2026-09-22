from rubrics.clause_specs import CLAUSE_SPECS
from rubrics.conditions import misleading_mapping, opaque_mapping, semantic_mapping
from rubrics.shuffle_control import clause_permutation, shuffle_mapping


def test_semantic_mapping_is_identity():
    for ct in CLAUSE_SPECS:
        m = semantic_mapping(ct)
        for canonical, display in m.items():
            assert canonical == display


def test_opaque_mapping_has_no_semantic_leakage_and_is_unique():
    for ct in CLAUSE_SPECS:
        folders = CLAUSE_SPECS[ct].folders
        m = opaque_mapping(ct)
        assert set(m.keys()) == set(folders)
        assert len(set(m.values())) == len(folders)  # all distinct
        for canonical, display in m.items():
            assert display != canonical
            assert display.isalnum() and display == display.lower()


def test_misleading_mapping_is_a_derangement():
    for ct in CLAUSE_SPECS:
        folders = CLAUSE_SPECS[ct].folders
        m = misleading_mapping(ct)
        assert set(m.values()) == set(folders)  # relabels using the *same* name set
        for canonical, display in m.items():
            assert display != canonical, f"ct{ct}: {canonical} mapped to itself"


def test_mappings_are_reproducible_across_calls():
    for ct in CLAUSE_SPECS:
        assert opaque_mapping(ct) == opaque_mapping(ct)
        assert misleading_mapping(ct) == misleading_mapping(ct)


def test_shuffle_control_uses_same_opaque_ids_as_condition_b():
    for ct in CLAUSE_SPECS:
        b_ids = set(opaque_mapping(ct).values())
        shuffle_ids = set(shuffle_mapping(ct).values())
        assert b_ids == shuffle_ids, "shuffle control must reuse Condition B's opaque id set"


def test_shuffle_control_permutation_is_a_derangement_and_reproducible():
    for ct in CLAUSE_SPECS:
        pi = clause_permutation(ct)
        for canonical, permuted in pi.items():
            assert canonical != permuted
        assert clause_permutation(ct) == pi  # same seeded stream, reproducible


def test_shuffle_and_misleading_use_independent_seed_streams():
    # "shuffle_control::ctN" and "misleading::ctN" must hash to different
    # sub-seeds, so the two derangements are independent draws even though,
    # for small n, they may coincidentally produce the same permutation
    # (n=3 has only 2 possible derangements -- a 50% coincidence rate is
    # expected and is not a bug). Check seed independence directly instead
    # of asserting the outputs differ.
    from harness.constants import sub_rng

    for ct in CLAUSE_SPECS:
        shuffle_seed = sub_rng(f"shuffle_control::ct{ct}").random()
        misleading_seed = sub_rng(f"misleading::ct{ct}").random()
        assert shuffle_seed != misleading_seed  # different streams, not aliased
