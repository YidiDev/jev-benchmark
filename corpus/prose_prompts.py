"""Per-document prose specs: the facts a document's text must contain (so an
arm reading only the document, never the metadata, has everything it needs
to determine the correct folder) plus a randomly assigned stylistic flavor
for realism/variety.
"""

from __future__ import annotations

from datetime import date

from harness.constants import sub_rng
from corpus.schema import DocumentMetadata

_DEFAULT_LENGTH_HINT = "roughly 120-220 words"
_DEFAULT_MAX_TOKENS_ESTIMATE = 400
# CT8 documents are deliberately padded with irrelevant boilerplate to test
# robustness to long, mostly-irrelevant context -- see rubrics/clause_specs.py.
_CT8_LENGTH_HINT = "roughly 500-700 words, including the irrelevant padding described below"
# Generous margin: a real batch-0 run averaged ~1237 tokens/doc against an
# earlier 1300 estimate and truncated mid-document in the next batch --
# bumped up with headroom rather than tuned to the exact observed average.
_CT8_MAX_TOKENS_ESTIMATE = 2000

STYLE_FLAVORS = ["formal_letter", "internal_memo", "plain_notice", "email_note"]

_STYLE_GUIDE = {
    "formal_letter": "a formal business letter on letterhead, with a salutation and sign-off",
    "internal_memo": "an internal company memo with a To/From/Date/Re header block",
    "plain_notice": "a plain administrative notice or filing, no letter formatting, just the substantive content",
    "email_note": "a short, slightly informal internal email with a subject line",
}


def assign_style(doc_id: str) -> str:
    rng = sub_rng(f"corpus_prose_style::{doc_id}")
    return rng.choice(STYLE_FLAVORS)


def build_doc_spec(metadata: DocumentMetadata) -> dict:
    """Returns {doc_id, style, facts} where `facts` is the plain-language
    brief Sonnet must faithfully render into prose -- these facts, not the
    rubric, are what the document must communicate."""
    style = assign_style(metadata.doc_id)
    ct = metadata.clause_type

    if ct == 1:
        genre = {
            "tax": "a tax filing notice, withholding statement, or tax assessment letter",
            "invoices": "an itemized invoice requesting payment for goods or services",
            "contracts": "a signed vendor or service agreement establishing obligations between two parties",
        }[metadata.doc_type]
        facts = f"This document should read unambiguously as {genre}. Invent plausible company names, dates, and amounts."

    elif ct == 2:
        facts = (
            f"This is an itemized invoice. It MUST state a clear total amount due of "
            f"exactly ${metadata.amount_usd:,.2f} (write this figure out plainly, e.g. "
            f"'Total Due: ${metadata.amount_usd:,.2f}'). Include 2-4 plausible line items "
            f"that could plausibly sum to that total (do not worry if they don't add up "
            f"precisely -- the total figure is what matters). Invent a plausible vendor "
            f"and client name."
        )

    elif ct == 3:
        client_clause = (
            f" The document should also naturally mention work performed for or with the "
            f"client '{metadata.mentioned_client}' (e.g. a deliverable for them, a meeting "
            f"with them, an invoice line referencing them)."
            if metadata.mentioned_client
            else ""
        )
        facts = (
            f"This is a project status update, deliverable notice, or internal report for "
            f"'Project {metadata.project_codename}'. The project name/codename MUST appear "
            f"explicitly and unambiguously in the text (e.g. 'Project {metadata.project_codename} "
            f"Q3 Status Update').{client_clause} Invent plausible team members, dates, and details."
        )

    elif ct == 4:
        if metadata.is_superseded:
            facts = (
                "This is a service or vendor agreement (contract). It MUST explicitly state "
                "that it has been superseded/replaced by a later, amended agreement -- for "
                "example a closing note like 'This Agreement was superseded by the Amended "
                "and Restated Agreement dated [a later date you invent].' Make this "
                "supersession statement clear and unambiguous."
            )
        else:
            facts = (
                "This is a current, active service or vendor agreement (contract) in full "
                "force. It must NOT mention being superseded, replaced, amended, or "
                "terminated -- it is simply the live agreement."
            )

    elif ct == 5:
        items_text = "; ".join(f"${amt:,.2f}" for amt in metadata.line_items)
        facts = (
            "This is an itemized budget or expense request form listing individual line "
            f"items. It must list exactly these line item amounts, each with a plausible "
            f"one-line description (e.g. 'Venue rental: $1,200.00'): {items_text}. Do NOT "
            "state, compute, or imply a total or sum anywhere in the document -- omit any "
            "'Total', 'Grand Total', or 'Amount Due' line entirely; the document must end "
            "after the last line item with no summary figure. Invent a plausible requester "
            "name and department."
        )

    elif ct == 6:
        effective_fmt = date.fromisoformat(metadata.effective_date).strftime("%B %-d, %Y")
        reference_fmt = date.fromisoformat(metadata.reference_date).strftime("%B %-d, %Y")
        facts = (
            "This is a recurring internal policy, procedure, or agreement document. It must "
            f"state its own effective date as {effective_fmt}, and separately mention that a "
            f"directly related version of the same document carries an effective date of "
            f"{reference_fmt} (phrase this neutrally, e.g. 'A related version of this document "
            f"has an effective date of {reference_fmt}.' or 'This document's counterpart version "
            f"is dated {reference_fmt}.'). State both dates as plain facts only -- do NOT use "
            "words like superseded, supersedes, replaces, replaced, terminated, amended, "
            "outdated, obsolete, current, latest, or any language suggesting which version is "
            "newer or controlling. A reader must be able to determine that only by comparing "
            "the two dates themselves."
        )

    elif ct == 7:
        facts = (
            f"This is an internal status report or update filed by the '{metadata.team}' "
            f"team. The team name '{metadata.team}' MUST appear explicitly and unambiguously "
            f"in the text (e.g. 'Filed by the {metadata.team} team' or 'Submitted on behalf of "
            f"Team {metadata.team}'). Do NOT mention any division code, department code, or "
            "program name anywhere in the document -- only the team name identifies who filed "
            "it. Invent plausible report content, dates, and details."
        )

    elif ct == 8:
        genre = {
            "tax_form": "a tax filing notice, withholding statement, or tax assessment letter",
            "invoice_doc": "an itemized invoice requesting payment for goods or services",
            "contract_doc": "a signed vendor or service agreement establishing obligations between two parties",
        }[metadata.doc_type]
        facts = (
            f"This document should read unambiguously as {genre}, but the load-bearing "
            "content that identifies it as such must be surrounded by several paragraphs of "
            "plausible, IRRELEVANT boilerplate that has no effect on its classification -- for "
            "example generic company background/history, a standard confidentiality or privacy "
            "notice, a lengthy 'about us' section, or an unrelated appendix. Do NOT place the "
            "genre-identifying content only at the very start or end -- bury at least some of "
            "it in the middle, interleaved with or surrounded by the irrelevant padding, so a "
            "reader cannot shortcut by only reading the first or last sentence. Invent plausible "
            "company names, dates, and amounts for the core content and for the padding alike."
        )

    else:
        raise ValueError(f"unknown clause_type {ct}")

    length_hint = _CT8_LENGTH_HINT if ct == 8 else _DEFAULT_LENGTH_HINT
    max_tokens_estimate = _CT8_MAX_TOKENS_ESTIMATE if ct == 8 else _DEFAULT_MAX_TOKENS_ESTIMATE

    return {
        "doc_id": metadata.doc_id,
        "style": style,
        "style_guide": _STYLE_GUIDE[style],
        "facts": facts,
        "length_hint": length_hint,
        "max_tokens_estimate": max_tokens_estimate,
    }
