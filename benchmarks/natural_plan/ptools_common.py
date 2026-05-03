"""Shim: provides _REACT_STATE for benchmarks that don't have a native ptools_common.

Used by Class 3 induced ptool modules from learn/inducer_results/ that import
`from ptools_common import _REACT_STATE`. Workflow code is expected to write
context (narrative / prompt) into this dict at the start of its execution.
"""
_REACT_STATE: dict = {}
