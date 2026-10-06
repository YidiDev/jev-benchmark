"""Exercise the real SDK serialization/parser over a local mock transport."""
import json

import httpx2 as httpx
import pytest

from scripts.run_api_arm import _build_arm as build_document
from qtree.runner import _build_arm as build_tree
from examgrade.runner import _build_arm as build_exam
from examgrade.questions import EXAM_QUESTIONS
from harness.scoring import ALL_KNOWN_ARMS, CALIBRATION_ARMS, ARMS_SYNTHESIZE_SHUFFLE_FROM_B
from rubrics.clauses import build_rubric


@pytest.mark.parametrize("name", ["cygnet", "winnow", "strands"])
@pytest.mark.parametrize("suite", ["document", "tree", "exam"])
def test_sdk_contract_and_accounting(name, suite, monkeypatch):
    import arms.hosted_decision as hosted
    import qtree.arms as tree
    import examgrade.arms as exam

    monkeypatch.setenv(f"{name.upper()}_BASE_URL", "http://localhost:1")
    spends = []
    for module in (hosted, tree, exam):
        monkeypatch.setattr(module, "record_spend", lambda **kw: spends.append(kw))
    arm = {"document": build_document, "tree": build_tree, "exam": build_exam}[suite](name)
    client = arm._arm._client if suite == "tree" else arm._client
    seen = []

    def respond(request):
        payload = json.loads(request.content)
        seen.append(payload)
        answers = {}
        for qid, question in payload["questions"].items():
            if question["type"] == "choice":
                keys = list(question["criteria"])
                probs = {k: (1.0 if i == 0 else 0.0) for i, k in enumerate(keys)}
                answers[qid] = {"type": "choice", "choice": keys[0], "probabilities": probs, "confidence": 1.0}
            else:
                levels = question["criteria"]
                answers[qid] = {"type": "score", "score": 1.0, "legend": {str(i): v for i, v in enumerate(levels)},
                                "probabilities": {str(i): float(i == 1) for i in range(len(levels))}, "confidence": 0.8}
        return httpx.Response(200, json={"model": payload["model"], "answers": answers,
                                        "usage": {"input_tokens": 123, "output_tokens": 1}})

    # Install the transport on the SDK's existing httpx client, retaining its parser.
    client._http_client.close()
    client._http_client = httpx.Client(transport=httpx.MockTransport(respond), base_url="http://localhost:1")
    try:
        if suite == "document":
            rubric = build_rubric(1, "SHUFFLE")
            result = arm.predict("unaltered state", rubric)
            assert seen[0]["questions"]["folder"]["criteria"] == rubric.criteria
            assert result.folder in rubric.folders
        elif suite == "tree":
            result = arm.predict_chunk("unaltered state", "tree logic", ["one", "two"])
            assert result.chosen == "one"
            assert "tree logic" in seen[0]["questions"]["destination"]["instructions"]
        else:
            result = arm.grade_exam("unaltered state", with_key=True)
            assert set(result.grades) == {q.id for q in EXAM_QUESTIONS}
            assert all(g.score == 1 for g in result.grades.values())
        assert seen[0]["state"] == "unaltered state"
        if name == "winnow":
            # The native server rejects the lowercase alias with HTTP 400.
            assert seen[0]["model"] == "Winnow-12B"
        assert result.input_tokens == 123
        assert spends[0]["input_tokens"] == 123
        assert spends[0]["source"] == f"{name}_arm" + ({"document": "", "tree": "_ct9", "exam": "_ct10"}[suite])
        assert name in ALL_KNOWN_ARMS and name in CALIBRATION_ARMS
        assert name not in ARMS_SYNTHESIZE_SHUFFLE_FROM_B
    finally:
        arm.close()
