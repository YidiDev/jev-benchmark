"""CT10: AP World History exam grading.

A third structurally distinct clause type, alongside CT1-8's single-shot
rubric classification (rubrics/, corpus/, arms/) and CT9's chunked
decision-tree execution (qtree/). CT10 tests a different capability
combination: applying a partial-credit rubric to open-ended paragraph
answers (a genuine scoring/generation task, not classification), with a
with/without-answer-key axis that separates "can the model apply a
rubric mechanically" from "does the model actually know world history."

See methodology.md §15 for the full design rationale.
"""
