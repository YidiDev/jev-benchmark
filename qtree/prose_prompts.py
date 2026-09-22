"""Per-form prose specs for CT9: the natural-language paraphrase brief
Sonnet must faithfully render for each of a form's 30 structured answers.
Colloquial phrasing is *encouraged* (varied register, hedging, filler --
"um I guess I would, yeah") but the underlying answer must never become
genuinely ambiguous -- a reader (human or model) must always be able to
recover the true structured value, same discipline used for CT6's dates.
"""

from __future__ import annotations

from harness.constants import sub_rng
from qtree.questions import SPECIAL_BY_ID, STANDARD_BY_ID, SPECIAL_OUTCOMES
from qtree.schema import FormMetadata

STYLE_FLAVORS = ["casual_chat", "formal_written", "brief_direct", "rambling_hedge"]
_STYLE_GUIDE = {
    "casual_chat": "very casual, spoken-register phrasing with filler words (um, yeah, I guess, like)",
    "formal_written": "formal, complete-sentence written register, as if typed carefully",
    "brief_direct": "terse and direct, minimal extra words, but still a full natural sentence or two",
    "rambling_hedge": "a bit rambling or hedging, with asides, but the core answer is still clearly recoverable",
}


def assign_style(form_id: str) -> str:
    rng = sub_rng(f"qtree_prose_style::{form_id}")
    return rng.choice(STYLE_FLAVORS)


def _standard_answer_brief(question_id: str, value: str) -> str:
    q = STANDARD_BY_ID[question_id]
    return (
        f"Q: \"{q.text}\"\n"
        f"   True answer value: {value!r} (one of {q.options}). Write a natural, "
        f"colloquial free-text response that clearly communicates this specific "
        f"value -- not necessarily the literal word, paraphrase naturally, but the "
        f"true value must be unambiguously recoverable from the phrasing. 1-2 "
        f"sentences."
    )


def _special_answer_brief(question_id: str, content_correct: bool, length_compliant: bool) -> str:
    q = SPECIAL_BY_ID[question_id]
    correctness_instr = (
        f"The answer MUST accurately and correctly state this true fact: {q.true_fact!r} "
        "(paraphrase naturally, doesn't need to be word-for-word, but the substance must be correct)."
        if content_correct
        else (
            f"The answer MUST state something FACTUALLY WRONG about this topic -- contradict or "
            f"misstate the true fact (which is actually: {q.true_fact!r}, for your reference only, "
            f"do NOT let the correct fact appear in the answer). Make the wrong claim sound plausible "
            "and confident, not obviously wrong or hedged."
        )
    )
    length_instr = (
        "The answer MUST be 3 sentences or less, per the question's instruction."
        if length_compliant
        else (
            "The answer MUST be 4 or more sentences -- deliberately exceeding the question's "
            "'3 sentences or less' instruction, e.g. by rambling or adding unnecessary detail."
        )
    )
    return f"Q: \"{q.text}\"\n   {correctness_instr} {length_instr}"


def build_form_spec(metadata: FormMetadata) -> dict:
    style = assign_style(metadata.form_id)
    standard = metadata.answers["standard"]
    special = metadata.answers["special"]

    briefs = [_standard_answer_brief(qid, val) for qid, val in standard.items()]
    briefs += [
        _special_answer_brief(qid, bits["content_correct"], bits["length_compliant"])
        for qid, bits in special.items()
    ]

    return {
        "form_id": metadata.form_id,
        "style": style,
        "style_guide": _STYLE_GUIDE[style],
        "briefs": briefs,
    }
