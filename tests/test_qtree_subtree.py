from qtree.subtree import (
    describe_subtree,
    folder_display_mapping,
    opaque_folder_display,
    semantic_folder_display,
    subtree_layers,
)
from qtree.tree import FOLDERS, ROOT_ID


def test_semantic_folder_display_is_identity():
    mapping = semantic_folder_display()
    for f in FOLDERS:
        assert mapping[f] == f


def test_opaque_folder_display_distinct_and_stable():
    a = opaque_folder_display()
    b = opaque_folder_display()
    assert a == b  # seeded, reproducible
    assert len(set(a.values())) == len(FOLDERS)  # all distinct
    for f in FOLDERS:
        assert a[f] != f  # genuinely opaque, not accidentally identity


def test_folder_display_mapping_dispatches():
    assert folder_display_mapping("semantic") == semantic_folder_display()
    assert folder_display_mapping("opaque") == opaque_folder_display()


def test_subtree_layers_length_and_growth():
    layers = subtree_layers(ROOT_ID, 3)
    assert len(layers) == 4  # layers[0..3]
    assert layers[0] == {ROOT_ID}
    for prev, cur in zip(layers, layers[1:]):
        assert len(cur) >= 1


def test_subtree_layers_k10_destination_is_all_folders_reachable():
    layers = subtree_layers(ROOT_ID, 10)
    # destination set after 10 steps from root should be a subset of FOLDERS
    assert layers[-1] <= set(FOLDERS)


def test_describe_subtree_destinations_match_subtree_layers():
    fd = semantic_folder_display()
    _, destinations = describe_subtree(ROOT_ID, 2, fd)
    layers = subtree_layers(ROOT_ID, 2)
    expected = sorted({fd.get(t, t) for t in layers[-1]})
    assert destinations == expected


def test_describe_subtree_opaque_labels_do_not_leak_semantic_names():
    fd = opaque_folder_display()
    text, destinations = describe_subtree(ROOT_ID, 10, fd)
    for f in FOLDERS:
        assert f not in text
        assert f not in destinations


def test_describe_subtree_mentions_every_active_node():
    fd = semantic_folder_display()
    text, _ = describe_subtree(ROOT_ID, 5, fd)
    layers = subtree_layers(ROOT_ID, 5)
    active_ids = {nid for layer in layers[:-1] for nid in layer}
    for nid in active_ids:
        assert f"`{nid}`" in text
