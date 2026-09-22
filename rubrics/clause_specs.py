"""Static specification of the four clause types from test-plan.md §3.

Each clause type owns its own small set of *canonical* folder ids (never
shown to an arm directly -- see conditions.py for the semantic/opaque/
misleading display-name layer on top) and, where the clause is relational,
the lookup tables a correct answer depends on.

Company names, project codenames, and which entities are "on retainer" are
all chosen by a seeded RNG from generic word banks rather than hand-picked,
per the instruction to stay uninfluenced by semantics wherever a choice is
otherwise arbitrary. The word banks themselves are just vocabulary; the
*selection and combination* is what must be arbitrary, and is.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from harness.constants import sub_rng
from rubrics.rng_util import derangement  # noqa: F401  (re-exported for callers)

# ---------------------------------------------------------------------------
# Clause type 1: Descriptive
# ---------------------------------------------------------------------------
CT1_FOLDERS = ["tax", "invoices", "contracts"]
CT1_DESCRIPTIONS = {
    "tax": "Tax documents: filings, tax notices, withholding statements.",
    "invoices": "Invoices: bills for goods or services rendered, requesting payment.",
    "contracts": "Contracts: signed agreements establishing obligations between parties.",
}
CT1_RULE_TEXT = (
    "Sort the document by its type. Tax documents go to `{tax}`. "
    "Invoices go to `{invoices}`. Contracts go to `{contracts}`."
)

# ---------------------------------------------------------------------------
# Clause type 2: Conjunctive + threshold
# ---------------------------------------------------------------------------
CT2_FOLDERS = ["large_invoices", "small_invoices"]
CT2_THRESHOLD_USD = 10_000
CT2_DESCRIPTIONS = {
    "large_invoices": f"Invoices billing more than ${CT2_THRESHOLD_USD:,}.",
    "small_invoices": f"Invoices billing ${CT2_THRESHOLD_USD:,} or less.",
}
CT2_RULE_TEXT = (
    "All of these documents are invoices. Invoices billing more than "
    f"${CT2_THRESHOLD_USD:,} go to `{{large_invoices}}`. Invoices billing "
    f"${CT2_THRESHOLD_USD:,} or less go to `{{small_invoices}}`."
)

# ---------------------------------------------------------------------------
# Clause type 3: Relational (parent-project lookup + retainer-list lookup)
# ---------------------------------------------------------------------------
CT3_FOLDERS = ["project_one", "project_two", "retainer_clients"]

_PROJECT_CODENAME_BANK = [
    "Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Theta", "Sigma",
]
_COMPANY_PREFIX_BANK = [
    "Meridian", "Cobalt", "Harbor", "Lattice", "Summit", "Granite", "Cascade",
    "Beacon", "Fulcrum", "Verdant", "Anchor", "Torrent", "Solace", "Ember",
    "Vantage", "Cinder", "Marrow", "Quill", "Ridgeline", "Tidewater",
]
_COMPANY_SUFFIX_BANK = [
    "Textiles", "Dynamics", "Logistics", "Robotics", "Capital", "Foundry",
    "Analytics", "Systems", "Ventures", "Holdings", "Partners", "Works",
    "Materials", "Labs", "Freight", "Group",
]


@dataclass
class RelationalFixtures:
    project_codenames: list[str]  # exactly 2, mapped to project_one/project_two
    project_folder_map: dict[str, str]  # codename -> "project_one" | "project_two"
    all_client_candidates: list[str]  # company names that can appear in CT3 docs
    retainer_clients: set[str]  # subset of the above, "on retainer"


def build_relational_fixtures() -> RelationalFixtures:
    rng = sub_rng("ct3_fixtures")

    codenames = rng.sample(_PROJECT_CODENAME_BANK, 2)
    project_folder_map = {codenames[0]: "project_one", codenames[1]: "project_two"}

    n_candidates = 20
    candidates: list[str] = []
    seen = set()
    while len(candidates) < n_candidates:
        name = f"{rng.choice(_COMPANY_PREFIX_BANK)} {rng.choice(_COMPANY_SUFFIX_BANK)}"
        if name not in seen:
            seen.add(name)
            candidates.append(name)

    retainer = set(rng.sample(candidates, 6))

    return RelationalFixtures(
        project_codenames=codenames,
        project_folder_map=project_folder_map,
        all_client_candidates=candidates,
        retainer_clients=retainer,
    )


CT3_FIXTURES = build_relational_fixtures()

CT3_DESCRIPTIONS = {
    "project_one": f"Documents belonging to project {CT3_FIXTURES.project_codenames[0]}.",
    "project_two": f"Documents belonging to project {CT3_FIXTURES.project_codenames[1]}.",
    "retainer_clients": "Documents naming a client on the retainer list (below), regardless of project.",
}


def ct3_rule_text() -> str:
    codenames = CT3_FIXTURES.project_codenames
    retainer_list = ", ".join(sorted(CT3_FIXTURES.retainer_clients))
    return (
        f"Each document belongs to one project: {codenames[0]} or {codenames[1]}. "
        f"A document belonging to project {codenames[0]} goes to `{{project_one}}`. "
        f"A document belonging to project {codenames[1]} goes to `{{project_two}}`. "
        "Exception: if the document names a client on the retainer list, it goes "
        f"to `{{retainer_clients}}` regardless of which project it belongs to. "
        f"Retainer list: {retainer_list}."
    )


# ---------------------------------------------------------------------------
# Clause type 4: Negative / exclusionary
# ---------------------------------------------------------------------------
CT4_FOLDERS = ["contracts", "archive"]
CT4_DESCRIPTIONS = {
    "contracts": "Active, current contracts.",
    "archive": "Contracts that have been superseded by a newer version.",
}
CT4_RULE_TEXT = (
    "All of these documents are contracts. Contracts go to `{contracts}`, "
    "unless the contract has been superseded by a newer version -- then it "
    "goes to `{archive}`."
)

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


@dataclass
class ClauseSpec:
    clause_type: int
    name: str
    folders: list[str]
    descriptions: dict[str, str]
    rule_text_fn: callable = field(repr=False)  # () -> str with {folder} placeholders


def _ct1_rule_text() -> str:
    return CT1_RULE_TEXT


def _ct2_rule_text() -> str:
    return CT2_RULE_TEXT


def _ct4_rule_text() -> str:
    return CT4_RULE_TEXT


CLAUSE_SPECS: dict[int, ClauseSpec] = {
    1: ClauseSpec(1, "descriptive", CT1_FOLDERS, CT1_DESCRIPTIONS, _ct1_rule_text),
    2: ClauseSpec(2, "conjunctive_threshold", CT2_FOLDERS, CT2_DESCRIPTIONS, _ct2_rule_text),
    3: ClauseSpec(3, "relational", CT3_FOLDERS, CT3_DESCRIPTIONS, ct3_rule_text),
    4: ClauseSpec(4, "negative_exclusionary", CT4_FOLDERS, CT4_DESCRIPTIONS, _ct4_rule_text),
}
