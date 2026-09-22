"""The CT9 decision DAG: 10 layers of decision nodes, every root-to-leaf
path exactly 10 edges long, with convergence (multiple edges/nodes merging
onto shared downstream nodes), terminating in one of 5 folders.

Construction is a "coverage pass" (every node in layer i+1 gets at least
one incoming edge from layer i, guaranteeing full reachability) followed by
a "random pass" (remaining outgoing edge budget distributed randomly across
layer i+1, which is exactly where convergence comes from -- multiple edges
landing on the same target). Both passes use harness.constants.sub_rng, so
the whole tree is deterministic and reproducible from MASTER_SEED alone.

Layer widths: [1,2,3,3,4,4,3,3,2,3] (28 decision nodes total). 3 of those
28 are "special" 4-way nodes (one each in layers 4, 7, 9) using the special
questions from qtree/questions.py; the remaining 25 are standard binary
nodes drawn from the 27-question standard bank (2 go unused -- the bank
doesn't need to be exhaustively placed). The last layer is deliberately
width-3 rather than width-2: 2 binary nodes emit only 4 total edges, which
cannot cover all 5 terminal folders -- width-3 (6 edges) leaves room for
full folder coverage plus one convergence.
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass, field

from harness.constants import sub_rng
from qtree.questions import (
    SPECIAL_OUTCOMES,
    SPECIAL_QUESTIONS,
    STANDARD_QUESTIONS,
    binary_value,
    special_outcome,
)

LAYER_WIDTHS = [1, 2, 3, 3, 4, 4, 3, 3, 2, 3]  # layers 1..10
N_LAYERS = len(LAYER_WIDTHS)
SPECIAL_LAYERS = {4, 7, 9}  # one special node placed in each of these layers
FOLDERS = ["F_auto_approve", "F_manual_review_minor", "F_manual_review_major", "F_auto_reject", "F_escalate_compliance"]


@dataclass
class Node:
    id: str
    layer: int
    question_id: str
    is_special: bool
    outcomes: dict[object, str] = field(default_factory=dict)  # outcome_key -> next node id or folder id


def _layer_node_ids(layer: int) -> list[str]:
    return [f"n{layer}_{i}" for i in range(LAYER_WIDTHS[layer - 1])]


def build_tree() -> dict[str, Node]:
    rng = sub_rng("qtree_tree_structure")

    # 1. Assign questions to node slots.
    standard_pool = [q.id for q in STANDARD_QUESTIONS]
    rng.shuffle(standard_pool)
    special_pool = [q.id for q in SPECIAL_QUESTIONS]
    rng.shuffle(special_pool)

    nodes: dict[str, Node] = {}
    standard_idx = 0
    special_idx = 0
    for layer in range(1, N_LAYERS + 1):
        for node_id in _layer_node_ids(layer):
            if layer in SPECIAL_LAYERS and special_idx < len(special_pool) and not any(
                n.is_special and n.layer == layer for n in nodes.values()
            ):
                nodes[node_id] = Node(node_id, layer, special_pool[special_idx], is_special=True)
                special_idx += 1
            else:
                nodes[node_id] = Node(node_id, layer, standard_pool[standard_idx], is_special=False)
                standard_idx += 1

    # 2. Wire edges layer by layer: coverage pass then random convergence pass.
    for layer in range(1, N_LAYERS + 1):
        this_layer_ids = _layer_node_ids(layer)
        if layer < N_LAYERS:
            targets = _layer_node_ids(layer + 1)
        else:
            targets = list(FOLDERS)

        for node_id in this_layer_ids:
            node = nodes[node_id]
            outcome_keys = list(SPECIAL_OUTCOMES) if node.is_special else [True, False]
            # Coverage-biased random assignment: shuffle targets, cycle to
            # guarantee spread, but allow (indeed expect) repeats when
            # outcome_keys > len(targets) or by chance -- that's convergence.
            assigned = []
            pool = targets[:]
            rng.shuffle(pool)
            for i, _key in enumerate(outcome_keys):
                assigned.append(pool[i % len(pool)])
            # Shuffle again so which outcome gets which target isn't
            # positionally predictable.
            rng.shuffle(assigned)
            for key, target in zip(outcome_keys, assigned):
                node.outcomes[key] = target

    # 3. Reachability guarantee pass: reassign edges so every target has
    # >=1 incoming edge. Recomputes incoming counts fresh before each fix
    # (not a stale snapshot) and only reassigns edges whose *current*
    # target has spare/redundant coverage (>1 incoming), so fixing one
    # orphan can never silently create a new one by overwriting the only
    # edge keeping some other target covered.
    def _ensure_coverage(source_ids: list[str], target_ids: list[str]) -> None:
        def incoming_counts() -> dict[str, int]:
            counts: dict[str, int] = defaultdict(int)
            for sid in source_ids:
                for t in nodes[sid].outcomes.values():
                    counts[t] += 1
            return counts

        for target in target_ids:
            if incoming_counts()[target] > 0:
                continue
            counts = incoming_counts()
            candidates = [
                (sid, key)
                for sid in source_ids
                for key, cur_target in nodes[sid].outcomes.items()
                if counts[cur_target] > 1
            ]
            if not candidates:
                candidates = [(sid, key) for sid in source_ids for key in nodes[sid].outcomes]
            sid, key = rng.choice(candidates)
            nodes[sid].outcomes[key] = target

    for layer in range(1, N_LAYERS):
        _ensure_coverage(_layer_node_ids(layer), _layer_node_ids(layer + 1))
    _ensure_coverage(_layer_node_ids(N_LAYERS), list(FOLDERS))

    return nodes


TREE: dict[str, Node] = build_tree()
ROOT_ID = "n1_0"


def evaluate_node(node: Node, answers: dict) -> str:
    """The outcome key this node resolves to, given full structured
    answers for a form (as produced by qtree.questions.sample_form_answers)."""
    if node.is_special:
        bits = answers["special"][node.question_id]
        return special_outcome(bits["content_correct"], bits["length_compliant"])
    value = answers["standard"][node.question_id]
    return binary_value(node.question_id, value)


def walk(answers: dict, start: str = ROOT_ID, steps: int | None = None) -> str:
    """Walk the tree from `start` for `steps` layers (None = walk to
    completion, i.e. until a folder is reached). Returns the landing node
    id or folder id."""
    current = start
    taken = 0
    while current in TREE:
        if steps is not None and taken >= steps:
            break
        node = TREE[current]
        outcome = evaluate_node(node, answers)
        current = node.outcomes[outcome]
        taken += 1
    return current


def true_folder(answers: dict) -> str:
    """The ground-truth terminal folder for a form -- always computed from
    structured answers only, walking the full 10-layer path from the root."""
    result = walk(answers, start=ROOT_ID, steps=None)
    assert result in FOLDERS, f"walk did not terminate at a folder: {result}"
    return result
