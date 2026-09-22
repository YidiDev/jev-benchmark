"""Clause type 9: chained decision-tree execution.

A separate, parallel subsystem from corpus/rubrics/arms (which are built
around "one document, one Choice call, one folder"). CT9 tests something
structurally different -- multi-call chunked traversal of a 10-level
decision DAG, with real compounding between calls -- so it gets its own
package rather than being shoehorned into the CLAUSE_TYPES=1..8 registry.
See methodology.md §13 for the full design rationale.
"""
