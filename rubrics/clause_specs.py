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
# "Hard mode" clause types (added 2026-09-22, see methodology.md §12).
#
# CT1-4 turned out to be a ceiling task for Jev (100% accuracy across every
# condition, including the shuffle control) -- informative for "does it
# genuinely condition on the rubric" but not for "where does it break."
# Each of CT5-8 below isolates exactly one documented jev-1.13 weakness
# (docs.typesafe.ai/model-jaggedness/jev-1.13, reviewed 2026-09-17) so a
# drop in accuracy is attributable to a single cause, not a tangle of them.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Clause type 5: Computed threshold (targets: "bad at math/counting")
#
# Unlike CT2 (which states a single total explicitly and just compares it to
# a threshold -- a text-comparison task, not arithmetic), CT5 documents list
# several line items and state NO total. The model must sum them itself.
# ---------------------------------------------------------------------------
CT5_FOLDERS = ["over_budget", "under_budget"]
CT5_THRESHOLD_USD = 5_000
CT5_DESCRIPTIONS = {
    "over_budget": f"Line-item requests whose amounts sum to more than ${CT5_THRESHOLD_USD:,}.",
    "under_budget": f"Line-item requests whose amounts sum to ${CT5_THRESHOLD_USD:,} or less.",
}
CT5_RULE_TEXT = (
    "This is an itemized budget request form listing several line items with dollar "
    "amounts. The document does not state a total -- add up all the line item amounts "
    f"yourself. If the sum is more than ${CT5_THRESHOLD_USD:,}, file it under "
    f"`{{over_budget}}`. If the sum is ${CT5_THRESHOLD_USD:,} or less, file it under "
    "`{under_budget}`."
)

# ---------------------------------------------------------------------------
# Clause type 6: Temporal reasoning (targets: "bad at date/time ordering")
#
# Unlike CT4 (which uses an explicit narrative cue -- "superseded by the
# Agreement dated..."), CT6 states two dates with no narrative cue at all.
# The model must compare them itself to determine which version is current.
# ---------------------------------------------------------------------------
CT6_FOLDERS = ["current_version", "prior_version"]
CT6_DESCRIPTIONS = {
    "current_version": (
        "The newest version of a recurring document, determined by comparing its own "
        "effective date against the effective date of the version it references."
    ),
    "prior_version": (
        "An older version of a recurring document, determined by the same date "
        "comparison, where the referenced version is actually the newer one."
    ),
}
CT6_RULE_TEXT = (
    "Each document states two dates: its own effective date, and the effective date "
    "of a directly related version of the same document. Compare the two dates -- do "
    "not rely on any other wording. If this document's own effective date is LATER "
    "than the referenced version's date, it is the newest version -- file it under "
    "`{current_version}`. If this document's own effective date is EARLIER than the "
    "referenced version's date, a newer version exists elsewhere -- file it under "
    "`{prior_version}`."
)

# ---------------------------------------------------------------------------
# Clause type 7: Multi-hop relational (targets: "penalized by indirection/
# multi-hop reasoning")
#
# Unlike CT3 (a single direct lookup, project codename -> folder, plus one
# override condition), CT7 requires chaining TWO lookup tables: the document
# only ever names a team; the rubric provides team -> division and,
# separately, division -> program folder. Neither table alone resolves a
# document to a folder.
# ---------------------------------------------------------------------------
CT7_FOLDERS = ["program_atlas", "program_borealis", "program_cascade"]

_TEAM_BANK = [
    "Falcon", "Osprey", "Kestrel", "Heron", "Talon", "Condor", "Merlin", "Raven", "Harrier",
]
_DIVISION_CODES = ["DIV-A", "DIV-B", "DIV-C"]


@dataclass
class MultiHopFixtures:
    teams: list[str]
    divisions: list[str]
    team_to_division: dict[str, str]  # team name -> division code
    division_to_program: dict[str, str]  # division code -> canonical folder id


def build_multihop_fixtures() -> MultiHopFixtures:
    rng = sub_rng("ct7_fixtures")

    teams = list(_TEAM_BANK)
    rng.shuffle(teams)
    divisions = list(_DIVISION_CODES)

    groups: list[list[str]] = [[] for _ in divisions]
    for i, team in enumerate(teams):
        groups[i % len(divisions)].append(team)
    team_to_division = {team: div for div, group in zip(divisions, groups) for team in group}

    programs = list(CT7_FOLDERS)
    rng.shuffle(programs)
    division_to_program = dict(zip(divisions, programs))

    return MultiHopFixtures(teams, divisions, team_to_division, division_to_program)


CT7_FIXTURES = build_multihop_fixtures()

CT7_DESCRIPTIONS = {
    prog: f"Documents filed by a team in the division that routes to program {prog}."
    for prog in CT7_FOLDERS
}


def ct7_rule_text() -> str:
    fixtures = CT7_FIXTURES
    team_division_lines = "; ".join(
        f"{team} is on {div}" for team, div in sorted(fixtures.team_to_division.items())
    )
    division_program_lines = "; ".join(
        f"{div} routes to `{{{prog}}}`" for div, prog in fixtures.division_to_program.items()
    )
    return (
        "Each document is filed by an internal team, named in the document. First look "
        "up which division that team belongs to, then look up which program folder that "
        f"division routes to. Team-to-division assignments: {team_division_lines}. "
        f"Division-to-program routing: {division_program_lines}."
    )


# ---------------------------------------------------------------------------
# Clause type 8: Long-context distractor (targets: "degrades with large
# irrelevant state content")
#
# Same descriptive logic as CT1 (classify by document genre), but with 3-5
# paragraphs of plausible, irrelevant boilerplate surrounding the load-
# bearing sentences -- corpus/prose_prompts.py generates these ~4x longer
# than CT1-7 documents. Distinct folder names from CT1's (tax/invoices/
# contracts) purely so results tables never conflate the two at a glance.
# ---------------------------------------------------------------------------
CT8_FOLDERS = ["tax_form", "invoice_doc", "contract_doc"]
CT8_DESCRIPTIONS = {
    "tax_form": "Tax documents: filings, tax notices, withholding statements.",
    "invoice_doc": "Invoices: bills for goods or services rendered, requesting payment.",
    "contract_doc": "Contracts: signed agreements establishing obligations between parties.",
}
CT8_RULE_TEXT = (
    "Sort the document by its actual type, ignoring any unrelated boilerplate, "
    "disclaimers, or appendix material that may surround the relevant content. Tax "
    "documents go to `{tax_form}`. Invoices go to `{invoice_doc}`. Contracts go to "
    "`{contract_doc}`."
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


def _ct5_rule_text() -> str:
    return CT5_RULE_TEXT


def _ct6_rule_text() -> str:
    return CT6_RULE_TEXT


def _ct8_rule_text() -> str:
    return CT8_RULE_TEXT


CLAUSE_SPECS: dict[int, ClauseSpec] = {
    1: ClauseSpec(1, "descriptive", CT1_FOLDERS, CT1_DESCRIPTIONS, _ct1_rule_text),
    2: ClauseSpec(2, "conjunctive_threshold", CT2_FOLDERS, CT2_DESCRIPTIONS, _ct2_rule_text),
    3: ClauseSpec(3, "relational", CT3_FOLDERS, CT3_DESCRIPTIONS, ct3_rule_text),
    4: ClauseSpec(4, "negative_exclusionary", CT4_FOLDERS, CT4_DESCRIPTIONS, _ct4_rule_text),
    5: ClauseSpec(5, "computed_threshold", CT5_FOLDERS, CT5_DESCRIPTIONS, _ct5_rule_text),
    6: ClauseSpec(6, "temporal_reasoning", CT6_FOLDERS, CT6_DESCRIPTIONS, _ct6_rule_text),
    7: ClauseSpec(7, "multi_hop_relational", CT7_FOLDERS, CT7_DESCRIPTIONS, ct7_rule_text),
    8: ClauseSpec(8, "long_context_distractor", CT8_FOLDERS, CT8_DESCRIPTIONS, _ct8_rule_text),
}
