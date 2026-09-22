from rubrics.clause_specs import CLAUSE_SPECS
from rubrics.clauses import build_rubric


def test_build_rubric_all_clause_types_and_conditions():
    for ct in CLAUSE_SPECS:
        for condition in ("A", "B", "C", "SHUFFLE"):
            rubric = build_rubric(ct, condition)
            assert rubric.folders, f"ct{ct}/{condition} has no folders"
            assert set(rubric.criteria.keys()) == set(rubric.folders)
            # instructions must not contain unresolved {placeholders}
            assert "{" not in rubric.instructions and "}" not in rubric.instructions
            # every folder display name mentioned in criteria should also be
            # referenced somewhere in the instructions text (via backticks)
            for display in rubric.folders:
                assert display in rubric.instructions


def test_condition_a_rubric_is_human_readable():
    rubric = build_rubric(1, "A")
    assert "tax" in rubric.folders
    assert "invoices" in rubric.folders
    assert "contracts" in rubric.folders


def test_condition_b_rubric_is_opaque():
    rubric = build_rubric(1, "B")
    for display in rubric.folders:
        assert display not in ("tax", "invoices", "contracts")


def test_condition_c_rubric_relabels_without_matching_content():
    rubric = build_rubric(1, "C")
    canonical_folders = CLAUSE_SPECS[1].folders
    for canonical, display in rubric.mapping.items():
        assert display != canonical  # misleading: never labeled truthfully
