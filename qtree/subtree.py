"""Builds the textual description of a k-level sub-tree rooted at an
arbitrary node, for one "chunk" call in CT9's chunked traversal (see
qtree/runner.py). The model is given the full decision logic for the next
k layers (which question each active node asks, and where each possible
answer leads) and must trace it itself, using the form's answers, to land
on the correct destination k steps away -- exactly like handing a human a
small flowchart excerpt and asking them to follow it.

Also handles the semantic-vs-opaque folder-labeling axis (k=10 only, see
methodology.md §13): internal node ids (e.g. "n3_2") are always shown
as-is regardless of labeling, since they're already opaque-looking with no
semantic content to leak. Only the 5 terminal FOLDER ids get relabeled.
"""

from __future__ import annotations

from harness.constants import sub_rng
from qtree.questions import SPECIAL_BY_ID, STANDARD_BY_ID, _MULTIWAY_CUTS
from qtree.tree import FOLDERS, TREE, Node

LABELING_SCHEMES = ("semantic", "opaque")


def semantic_folder_display() -> dict[str, str]:
    return {f: f for f in FOLDERS}


def opaque_folder_display() -> dict[str, str]:
    """Distinct random-character ids per folder, seeded once so they're
    stable across the whole benchmark run -- same principle as
    rubrics/conditions.py's Condition B for CT1-8."""
    from rubrics.rng_util import distinct_opaque_ids

    rng = sub_rng("qtree_opaque_folder_ids")
    ids = distinct_opaque_ids(rng, len(FOLDERS), length=6)
    return dict(zip(FOLDERS, ids))


def folder_display_mapping(labeling: str) -> dict[str, str]:
    if labeling == "semantic":
        return semantic_folder_display()
    if labeling == "opaque":
        return opaque_folder_display()
    raise ValueError(f"unknown labeling scheme {labeling!r}")


def subtree_layers(start_id: str, k: int) -> list[set[str]]:
    """layers[0] = {start_id}; layers[i] = set of ids reachable from
    start_id in exactly i steps, for i = 1..k. layers[k] is the
    destination set (may contain folder ids if this chunk reaches the
    tree's final layer)."""
    layers = [{start_id}]
    current = {start_id}
    for _ in range(k):
        nxt: set[str] = set()
        for nid in current:
            node = TREE.get(nid)
            if node is None:
                continue  # nid is already a folder; shouldn't occur given correct k usage
            nxt.update(node.outcomes.values())
        layers.append(nxt)
        current = nxt
    return layers


def _question_text(question_id: str) -> str:
    if question_id in STANDARD_BY_ID:
        return STANDARD_BY_ID[question_id].text
    return SPECIAL_BY_ID[question_id].text


def _standard_outcome_description(question_id: str, value: bool) -> str:
    if question_id in _MULTIWAY_CUTS:
        cuts = _MULTIWAY_CUTS[question_id]
        matching = [opt for opt, v in cuts.items() if v == value]
        return f"the answer is one of {matching}"
    return f"the answer is {'YES' if value else 'NO'}"


def _special_outcome_description(outcome_key: str) -> str:
    compliant = outcome_key.startswith("compliant")
    correct = outcome_key.endswith("correct")
    compliance_text = (
        "complies with the length instruction (3 sentences or less)"
        if compliant
        else "does NOT comply with the length instruction (i.e. is 4+ sentences)"
    )
    correctness_text = "is factually correct" if correct else "is factually incorrect/wrong"
    return f"the answer {compliance_text} AND {correctness_text}"


def _describe_outcome(node: Node, outcome_key) -> str:
    if node.is_special:
        return f"If {_special_outcome_description(outcome_key)}"
    return f"If {_standard_outcome_description(node.question_id, outcome_key)}"


def describe_subtree(start_id: str, k: int, folder_display: dict[str, str]) -> tuple[str, list[str]]:
    """Returns (description_text, sorted list of destination display ids)."""
    layers = subtree_layers(start_id, k)
    active_node_ids = {nid for layer in layers[:-1] for nid in layer if nid in TREE}

    lines = [
        f"You are currently at decision position `{start_id}`. Below is the decision logic for "
        f"the next {k} step(s) from this position. Using the form's answers above, trace through "
        f"this logic step by step to determine exactly where you end up after {k} step(s)."
    ]
    for nid in sorted(active_node_ids, key=lambda x: (TREE[x].layer, x)):
        node = TREE[nid]
        lines.append(f'\nAt position `{nid}`, the question is: "{_question_text(node.question_id)}"')
        for outcome_key, target in node.outcomes.items():
            target_display = folder_display.get(target, target)
            lines.append(f"  - {_describe_outcome(node, outcome_key)} -> go to `{target_display}`")

    destinations = sorted({folder_display.get(t, t) for t in layers[-1]})
    lines.append(
        f"\nAfter tracing exactly {k} step(s) from `{start_id}`, you must land on exactly one of "
        f"these positions: {destinations}. Choose which one."
    )
    return "\n".join(lines), destinations
