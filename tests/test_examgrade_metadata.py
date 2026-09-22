import statistics

from examgrade.generate_metadata import sample_student_ability, sample_true_score
from examgrade.questions import EXAM_QUESTIONS
from harness.constants import sub_rng


def test_ability_in_bounds():
    rng = sub_rng("test_ability_bounds")
    for _ in range(200):
        a = sample_student_ability(rng)
        assert 0.0 <= a <= 1.0


def test_true_score_in_bounds():
    rng = sub_rng("test_true_score_bounds")
    for _ in range(200):
        score = sample_true_score(ability=0.5, points=5, rng=rng)
        assert 0 <= score <= 5


def test_true_score_correlates_with_ability():
    rng = sub_rng("test_true_score_correlation")
    low_ability_scores = [sample_true_score(0.05, 4, rng) for _ in range(100)]
    high_ability_scores = [sample_true_score(0.95, 4, rng) for _ in range(100)]
    assert statistics.mean(high_ability_scores) > statistics.mean(low_ability_scores)


def test_manifest_scores_within_question_bounds():
    from examgrade.generate_metadata import load_manifest
    from examgrade.questions import EXAM_BY_ID

    students = load_manifest()
    for s in students:
        for qid, score in s.scores.items():
            assert 0 <= score <= EXAM_BY_ID[qid].points


def test_manifest_total_true_score_matches_sum():
    from examgrade.generate_metadata import load_manifest

    students = load_manifest()
    for s in students:
        assert s.total_true_score == sum(s.scores.values())


def test_manifest_has_100_students():
    from examgrade.generate_metadata import load_manifest

    students = load_manifest()
    assert len(students) == 100
    assert len(set(s.student_id for s in students)) == 100
