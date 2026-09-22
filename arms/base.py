"""Common interface every arm implements (nli-bart, emb-bge, jev, haiku,
openjev), so harness/scoring.py and harness/cost.py can work uniformly
across all five without special-casing.

Decomposition is fixed in rubrics/clauses.py: every arm receives the same
`Rubric` (instructions + criteria + folders, already resolved for a given
clause_type/condition) and the same raw document text, and must return
exactly one folder choice. This mirrors test-plan.md's "one Choice question
per document" decomposition applied identically everywhere.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from rubrics.clauses import Rubric


@dataclass
class Prediction:
    folder: str
    probabilities: dict[str, float] = field(default_factory=dict)
    confidence: Optional[float] = None
    latency_ms: float = 0.0
    # Only populated by token-metered API arms (jev, haiku, openjev); local
    # baseline arms (nli-bart, emb-bge) leave these at 0 since they run on
    # local hardware with no per-token billing.
    input_tokens: int = 0
    output_tokens: int = 0
    # Only populated by arms using Anthropic prompt caching (see
    # arms/haiku.py); input_tokens above is the *uncached* portion in that
    # case. See harness/spend_ledger.py's cost_for for how these are priced.
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0


class Arm:
    name: str  # short id: used as PRICING key (where applicable) and as the
    # results/predictions/{name}.jsonl filename.

    def predict(self, doc_text: str, rubric: Rubric) -> Prediction:
        raise NotImplementedError
