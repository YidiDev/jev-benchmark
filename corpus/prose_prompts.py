"""Per-document prose specs: the facts a document's text must contain (so an
arm reading only the document, never the metadata, has everything it needs
to determine the correct folder) plus a randomly assigned stylistic flavor
for realism/variety.
"""

from __future__ import annotations

from harness.constants import sub_rng
from corpus.schema import DocumentMetadata

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
    else:
        raise ValueError(f"unknown clause_type {ct}")

    return {
        "doc_id": metadata.doc_id,
        "style": style,
        "style_guide": _STYLE_GUIDE[style],
        "facts": facts,
    }
