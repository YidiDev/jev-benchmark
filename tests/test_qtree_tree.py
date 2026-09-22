from qtree.questions import sample_form_answers
from qtree.tree import FOLDERS, LAYER_WIDTHS, ROOT_ID, TREE, true_folder, walk


def test_all_nodes_reachable_from_root():
    reachable = {ROOT_ID}
    frontier = {ROOT_ID}
    while frontier:
        nxt = set()
        for nid in frontier:
            node = TREE.get(nid)
            if node is None:
                continue
            for target in node.outcomes.values():
                if target not in reachable:
                    nxt.add(target)
        reachable |= nxt
        frontier = nxt
    all_node_ids = set(TREE.keys())
    assert all_node_ids <= reachable


def test_all_folders_reachable():
    reachable_folders = set()
    for node in TREE.values():
        for target in node.outcomes.values():
            if target in FOLDERS:
                reachable_folders.add(target)
    assert reachable_folders == set(FOLDERS)


def test_every_root_to_leaf_path_is_exactly_10_edges():
    # Every node id encodes its layer as "n{layer}_{i}"; walking any node's
    # outcomes should only ever point to the next layer or (from the last
    # layer) a folder.
    n_layers = len(LAYER_WIDTHS)
    for node in TREE.values():
        for target in node.outcomes.values():
            if target in FOLDERS:
                assert node.layer == n_layers
            else:
                target_layer = TREE[target].layer
                assert target_layer == node.layer + 1


def test_tree_size_matches_layer_widths():
    assert len(TREE) == sum(LAYER_WIDTHS)


def test_true_folder_always_lands_on_a_folder():
    for form_id in ("qt_test_a", "qt_test_b", "qt_test_c"):
        answers = sample_form_answers(form_id)
        folder = true_folder(answers)
        assert folder in FOLDERS


def test_true_folder_deterministic():
    answers = sample_form_answers("qt_test_determinism")
    assert true_folder(answers) == true_folder(answers)


def test_walk_partial_steps_lands_on_correct_layer():
    # steps in (1, 2, 5) never reach layer 11 (folders) from root (layer 1),
    # so landing should always still be an internal node at layer 1+steps.
    answers = sample_form_answers("qt_test_partial")
    for steps in (1, 2, 5):
        landing = walk(answers, start=ROOT_ID, steps=steps)
        assert landing in TREE
        assert TREE[landing].layer == steps + 1


def test_walk_from_arbitrary_node_matches_manual_trace():
    from qtree.tree import evaluate_node

    answers = sample_form_answers("qt_test_manual")
    node = TREE[ROOT_ID]
    outcome = evaluate_node(node, answers)
    expected_next = node.outcomes[outcome]
    actual = walk(answers, start=ROOT_ID, steps=1)
    assert actual == expected_next


def test_balance_across_simulated_forms():
    import random

    from qtree.questions import sample_special_answers, sample_standard_answers

    rng = random.Random(12345)  # independent, not part of real corpus seed stream
    counts = {f: 0 for f in FOLDERS}
    n = 2000
    for _ in range(n):
        answers = {"standard": sample_standard_answers(rng), "special": sample_special_answers(rng)}
        counts[true_folder(answers)] += 1
    # No folder should be wildly dominant or absent -- loose bounds since
    # this is a smaller/faster sample than the 20k exploratory check done
    # during design (see methodology.md §13).
    for folder, count in counts.items():
        assert count > 0, f"{folder} never reached in {n} simulated forms"
        assert count / n < 0.5, f"{folder} dominates at {count/n:.2%}"
