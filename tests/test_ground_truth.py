from corpus.schema import DocumentMetadata
from rubrics.clause_specs import CT2_THRESHOLD_USD, CT3_FIXTURES
from rubrics.conditions import folder_mapping
from rubrics.ground_truth import canonical_folder, correct_folder
from rubrics.shuffle_control import shuffle_mapping


def _meta(**kw) -> DocumentMetadata:
    base = dict(doc_id="t0", split="test")
    base.update(kw)
    return DocumentMetadata(**base)


def test_ct1_descriptive():
    for doc_type in ("tax", "invoices", "contracts"):
        m = _meta(clause_type=1, doc_type=doc_type)
        assert canonical_folder(m) == doc_type


def test_ct2_threshold_boundaries():
    above = _meta(clause_type=2, amount_usd=CT2_THRESHOLD_USD + 0.01)
    exactly_at = _meta(clause_type=2, amount_usd=CT2_THRESHOLD_USD)
    below = _meta(clause_type=2, amount_usd=CT2_THRESHOLD_USD - 1)
    assert canonical_folder(above) == "large_invoices"
    assert canonical_folder(exactly_at) == "small_invoices"  # "over" is strict per rule text
    assert canonical_folder(below) == "small_invoices"


def test_ct3_relational_project_routing():
    codename_a, codename_b = CT3_FIXTURES.project_codenames
    m_a = _meta(clause_type=3, project_codename=codename_a, mentioned_client=None)
    m_b = _meta(clause_type=3, project_codename=codename_b, mentioned_client=None)
    assert canonical_folder(m_a) == CT3_FIXTURES.project_folder_map[codename_a]
    assert canonical_folder(m_b) == CT3_FIXTURES.project_folder_map[codename_b]


def test_ct3_retainer_exception_overrides_project():
    codename_a, _ = CT3_FIXTURES.project_codenames
    retainer_client = sorted(CT3_FIXTURES.retainer_clients)[0]
    m = _meta(clause_type=3, project_codename=codename_a, mentioned_client=retainer_client)
    assert canonical_folder(m) == "retainer_clients"


def test_ct3_non_retainer_client_does_not_override():
    codename_a, _ = CT3_FIXTURES.project_codenames
    non_retainer = next(
        c for c in CT3_FIXTURES.all_client_candidates if c not in CT3_FIXTURES.retainer_clients
    )
    m = _meta(clause_type=3, project_codename=codename_a, mentioned_client=non_retainer)
    assert canonical_folder(m) == CT3_FIXTURES.project_folder_map[codename_a]


def test_ct4_negative_exclusionary():
    active = _meta(clause_type=4, is_superseded=False)
    superseded = _meta(clause_type=4, is_superseded=True)
    assert canonical_folder(active) == "contracts"
    assert canonical_folder(superseded) == "archive"


def test_correct_folder_translates_through_every_condition():
    m = _meta(clause_type=1, doc_type="tax")
    canonical = canonical_folder(m)
    for condition in ("A", "B", "C"):
        expected = folder_mapping(1, condition)[canonical]
        assert correct_folder(m, condition=condition) == expected


def test_correct_folder_under_shuffle_control_differs_from_plain_opaque():
    # For at least one clause type, the shuffled answer must differ from the
    # plain Condition B answer for some document -- otherwise the control
    # isn't actually permuting anything and the test corpus would silently
    # pass under both.
    any_difference = False
    for ct in (1, 2, 3, 4):
        if ct == 1:
            docs = [_meta(clause_type=1, doc_type=dt) for dt in ("tax", "invoices", "contracts")]
        elif ct == 2:
            docs = [
                _meta(clause_type=2, amount_usd=1),
                _meta(clause_type=2, amount_usd=999_999),
            ]
        elif ct == 3:
            a, b = CT3_FIXTURES.project_codenames
            docs = [
                _meta(clause_type=3, project_codename=a, mentioned_client=None),
                _meta(clause_type=3, project_codename=b, mentioned_client=None),
            ]
        else:
            docs = [
                _meta(clause_type=4, is_superseded=False),
                _meta(clause_type=4, is_superseded=True),
            ]
        for m in docs:
            plain_b = correct_folder(m, condition="B")
            shuffled = correct_folder(m, shuffle=True)
            if plain_b != shuffled:
                any_difference = True
    assert any_difference
