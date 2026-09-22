import random

from rubrics.rng_util import derangement, distinct_opaque_ids, random_opaque_id


def test_derangement_no_fixed_points():
    rng = random.Random(1)
    for trial in range(200):
        items = ["a", "b", "c"] if trial % 2 == 0 else ["x", "y"]
        d = derangement(items, rng)
        for k, v in d.items():
            assert k != v
        assert sorted(d.values()) == sorted(items)


def test_derangement_requires_at_least_two():
    rng = random.Random(1)
    try:
        derangement(["only"], rng)
        assert False, "should have raised"
    except ValueError:
        pass


def test_random_opaque_id_shape():
    rng = random.Random(2)
    oid = random_opaque_id(rng, length=6)
    assert len(oid) == 6
    assert oid.isalnum()
    assert oid == oid.lower()


def test_distinct_opaque_ids_are_unique():
    rng = random.Random(3)
    ids = distinct_opaque_ids(rng, 10, length=4)
    assert len(ids) == len(set(ids)) == 10
