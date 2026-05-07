"""Shared interfaces for answer extraction across all MUSR splits."""

import collections
import json
import pathlib
import re
from string import Template

from pydantic import Field

from secretagent import config
from secretagent.core import interface, register_factory
from secretagent.implement.pydantic import SimulatePydanticFactory
from secretagent.llm_util import llm


@interface
def raw_answer(narrative: str, question: str, choices: list) -> str:
    """Read the narrative and answer the multiple-choice question."""


@interface
def extract_index(answer_text: str, choices: list) -> int:
    """Given an answer and choices, return the 0-based index of the matching choice."""


# ============================================================
# ReAct support: search / lookup / finish tools + entry point
# ============================================================
#
# Design notes
# ------------
# These three tools implement the canonical Yao+ ReAct action set
# (Wikipedia search, in-article lookup, terminal finish), adapted for
# MUSR where the "environment" is the narrative passage rather than
# Wikipedia.
#
# The tools need read-access to the current narrative, but the
# secretagent @interface decorator registers tools as global singletons.
# We use module-level state (`_REACT_STATE`) instead of closures —
# benchmark evaluation is sequential (one example at a time per
# process), so a single mutable dict is safe. The entry point
# `react_answer_impl` resets the state at the start of each example.
#
# Wiring (config snippet):
#   ptools:
#     search:        {method: direct}
#     lookup:        {method: direct}
#     finish:        {method: direct}
#     react_solve:
#       method: simulate_pydantic
#       tools:
#         - ptools_common.search
#         - ptools_common.lookup
#         - ptools_common.finish
#     answer_question:
#       method: direct
#       fn: ptools_common.react_answer_impl

_REACT_STATE: dict = {
    'narrative': '',
    'finish_answer': None,
    'lookup_last': None,
    'lookup_matches': [],
    'lookup_idx': 0,
}


def _reset_react_state(narrative: str) -> None:
    _REACT_STATE['narrative'] = narrative
    _REACT_STATE['finish_answer'] = None
    _REACT_STATE['lookup_last'] = None
    _REACT_STATE['lookup_matches'] = []
    _REACT_STATE['lookup_idx'] = 0


def _split_into_sentences(text: str) -> list[str]:
    """Naive sentence splitter — adequate for MUSR narratives."""
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [p.strip() for p in parts if p.strip()]


#
# search / lookup / finish: plain Python functions, NOT @interface.
# pydantic-ai's Agent introspects tools via inspect.signature and
# attributes like __qualname__ — wrapping them in `@interface` (which
# turns them into BaseModel-backed Factory instances at bind time)
# breaks that introspection. Plain functions work directly.
#

def search(query: str) -> str:
    """Search the narrative for sentences containing the query (case-insensitive substring match).

    Returns up to 5 matching sentences, each prefixed with '- '. If more
    than 5 sentences match, indicates how many additional matches were
    truncated. Use this for broad keyword exploration over the narrative
    (e.g. search('alibi'), search('Alice'), search('9pm')).
    """
    narrative = _REACT_STATE.get('narrative') or ''
    if not narrative:
        return "Error: no narrative loaded for this call."
    sentences = _split_into_sentences(narrative)
    q = query.lower()
    matches = [s for s in sentences if q in s.lower()]
    if not matches:
        return f"No sentences contain {query!r}."
    head = matches[:5]
    body = '\n'.join(f"- {s}" for s in head)
    if len(matches) > 5:
        body += f"\n(... {len(matches) - 5} more matches; refine the query or use lookup to paginate)"
    return body


def lookup(string: str) -> str:
    """Paginate through sentences in the narrative containing the string.

    First call with a new string returns the first match; subsequent
    calls with the SAME string return the next match. Calling with a
    different string resets pagination. Returns 'No more matches.' when
    exhausted. Use this when search returned too many matches and you
    want to walk through them one at a time.
    """
    narrative = _REACT_STATE.get('narrative') or ''
    if not narrative:
        return "Error: no narrative loaded for this call."
    if _REACT_STATE['lookup_last'] != string:
        sentences = _split_into_sentences(narrative)
        s_lower = string.lower()
        _REACT_STATE['lookup_last'] = string
        _REACT_STATE['lookup_matches'] = [s for s in sentences if s_lower in s.lower()]
        _REACT_STATE['lookup_idx'] = 0
    matches = _REACT_STATE['lookup_matches']
    if not matches:
        return f"No sentences contain {string!r}."
    idx = _REACT_STATE['lookup_idx']
    if idx >= len(matches):
        return f"No more matches for {string!r} ({len(matches)} total)."
    result = matches[idx]
    _REACT_STATE['lookup_idx'] = idx + 1
    return f"({idx + 1}/{len(matches)}) {result}"


def finish(answer_index: int) -> str:
    """Submit the final 0-based answer index.

    Call this exactly once when you have determined the correct answer.
    The answer_index must be the 0-based index into the choices list
    (0 for the first choice, 1 for the second, etc.). After calling
    finish, stop calling other tools and respond with the same index.
    """
    _REACT_STATE['finish_answer'] = int(answer_index)
    return (
        f"Recorded answer index {answer_index}. "
        "Stop calling tools and respond with the same index."
    )


@interface
def react_solve(narrative: str, question: str, choices: list) -> str:
    """Solve a multiple-choice MUSR question by ReAct over the narrative.

    You have THREE tools:
      - search(query): find sentences in the narrative containing the query
      - lookup(string): paginate sentences containing the string
      - finish(answer_index): submit the 0-based answer index when ready

    BUDGET: aim for at most 6–8 tool calls total. Do NOT dump the whole
    narrative. Do NOT search for the same query twice. Do NOT keep
    paginating once you have enough evidence.

    Process:
      1. Read the question and the choices.
      2. Use a few targeted search/lookup calls to gather evidence.
      3. Reason briefly about which choice is best supported.
      4. Call finish(answer_index) with your final answer (0-based).
      5. After finish, return the SAME index as your final response,
         e.g. respond with just "1" if you called finish(1).

    Return: just the 0-based answer index as a short string (e.g. "0",
    "1", or "2"). The index must match what you passed to finish.
    """


def react_answer_impl(narrative: str, question: str, choices: list) -> int:
    """Direct-method entry point for ReAct configs.

    Sets up per-call state, runs `react_solve` (which is bound to a
    pydantic-ai Agent with the search/lookup/finish tools), and returns
    the 0-based answer index.

    Recovery order:
      1. If the agent called finish(), use the recorded index.
      2. Else, parse the first integer found in the agent's string output.
      3. Else, return -1 (recorded as wrong by the evaluator).

    Bind via:
        ptools:
          answer_question:
            method: direct
            fn: ptools_common.react_answer_impl
    """
    _reset_react_state(narrative)
    raw: str | None = None
    try:
        raw = react_solve(narrative, question, choices)
    except Exception:
        # Agent loop blew up (e.g. request limit, output validation).
        # finish() may still have been called before the failure — fall
        # through and check state.
        pass
    final = _REACT_STATE['finish_answer']
    if final is not None:
        return int(final)
    if isinstance(raw, str):
        m = re.search(r'-?\d+', raw)
        if m:
            return int(m.group(0))
    return -1


# ============================================================
# ReAct + engineered (hand-designed) ptools support
# ============================================================
#
# Generic ReAct entry point bound via simulate_pydantic with task-
# specific engineered ptools as the agent's tool set. Each task module
# (ptools_murder, ptools_object, ptools_team) defines plain-function
# wrappers over its engineered ptools that read the narrative from
# `_REACT_STATE` so the agent does not have to pass the long narrative
# as an argument on every call.
#
# Wiring (config snippet, murder example):
#   ptools:
#     react_solve_engineered:
#       method: simulate_pydantic
#       tools:
#         - ptools_murder.solve_extract_suspects
#         - ptools_murder.solve_verify_alibis
#         - ptools_murder.solve_deduce_murderer
#     extract_suspects_and_evidence: {method: simulate}
#     verify_alibis: {method: simulate}
#     deduce_murderer: {method: simulate}
#     answer_question:
#       method: direct
#       fn: ptools_common.react_engineered_answer_impl


@interface
def react_solve_engineered(narrative: str, question: str, choices: list) -> str:
    """Solve a multiple-choice MUSR question using the available domain tools.

    The runtime registers a small set of analysis tools tailored to this
    task family. Read each tool's docstring (which explains its purpose
    and required arguments) before deciding which to call. The current
    narrative has already been loaded into the runtime, so tools that
    need it will receive it automatically — you do NOT need to pass the
    narrative as an argument.

    Process:
      1. Read the question and the answer choices.
      2. Call the available tools (in a sensible order) to extract
         evidence, verify constraints, or score candidates. You can pass
         the output of one tool as input to another when its docstring
         asks for it.
      3. Reason briefly about which choice is best supported.
      4. Return the 0-based answer index as a short string (e.g. "0",
         "1", or "2"). Stop calling tools after deciding.

    BUDGET: aim for at most 5–8 tool calls total. Prefer focused calls
    over re-running the same tool.
    """


def react_engineered_answer_impl(narrative: str, question: str, choices: list) -> int:
    """Direct-method entry point for ReAct + engineered-ptool configs.

    Loads the narrative into _REACT_STATE so the (stateful) tool wrappers
    can access it without the agent passing it as an arg, then runs
    `react_solve_engineered` (bound to a pydantic-ai Agent with the
    task's engineered ptools as tools), and returns the 0-based answer
    index parsed from the agent's final string output.

    Recovery order:
      1. If the agent's final string output contains an integer, return it.
      2. Else, return -1 (recorded as wrong by the evaluator).
    """
    _reset_react_state(narrative)
    raw: str | None = None
    try:
        raw = react_solve_engineered(narrative, question, choices)
    except Exception:
        # Agent loop blew up (e.g. request limit, output validation).
        pass
    if isinstance(raw, str):
        m = re.search(r'-?\d+', raw)
        if m:
            return int(m.group(0))
    return -1


# ============================================================
# AWM (Agent Workflow Memory) support: workflow-augmented agent
# ============================================================
#
# A custom factory that subclasses SimulatePydanticFactory and prepends
# a learned natural-language workflow string to every prompt. The
# workflow is loaded once at config bind time from a JSON or text file.
#
# Wiring (config snippet):
#   ptools:
#     react_solve:
#       method: simulate_pydantic_with_workflow
#       workflow_file: awm_workflows.json
#       workflow_key: murder           # one of: murder, object, team
#       tools:
#         - ptools_common.search
#         - ptools_common.lookup
#         - ptools_common.finish
#     answer_question:
#       method: direct
#       fn: ptools_common.react_answer_impl

class SimulatePydanticWithWorkflowFactory(SimulatePydanticFactory):
    """Simulate-pydantic factory that prepends a learned workflow guide.

    The workflow is loaded from a file at bind time and prepended to the
    prompt produced by the parent factory. The agent (and its tools)
    are otherwise unchanged — only the prompt is augmented.

    Builder kwargs:
        workflow_file: path to a .json (then keyed by workflow_key) or
            .txt file containing the workflow guide.
        workflow_key: if workflow_file is JSON, the key to look up.
            If omitted, all workflows in the JSON are concatenated.
        tools: same as SimulatePydanticFactory.
    """

    workflow_text: str = Field(default='')

    def setup(self, workflow_file=None, workflow_key=None, tools=None, **prompt_kw):
        super().setup(tools=tools, **prompt_kw)
        if workflow_file:
            content = pathlib.Path(workflow_file).read_text()
            if str(workflow_file).endswith('.json'):
                workflows_dict = json.loads(content)
                if workflow_key is not None:
                    self.workflow_text = workflows_dict.get(workflow_key, '')
                else:
                    # Concatenate all entries
                    self.workflow_text = '\n\n'.join(
                        f"### {k}\n{v}" for k, v in workflows_dict.items()
                    )
            else:
                self.workflow_text = content

    def create_prompt(self, interface, *args, **kw):
        prompt = super().create_prompt(interface, *args, **kw)
        if self.workflow_text:
            prompt = (
                "## Learned workflow guide\n"
                "The following workflow was induced from successful past "
                "trajectories on similar problems. Use it as guidance for the "
                "task below.\n\n"
                f"{self.workflow_text}\n\n"
                "---\n\n"
                f"{prompt}"
            )
        return prompt


register_factory('simulate_pydantic_with_workflow', SimulatePydanticWithWorkflowFactory())


# ============================================================
# Self-Consistency (Wang+ ICLR 2023): sample CoT N times, majority vote
# ============================================================
#
# Wiring (config snippet):
#   self_consistency:
#     n_samples: 5
#     temperature: 0.7
#     prompt_template_file: prompt_templates/zero_shot_cot.txt
#   ptools:
#     answer_question:
#       method: direct
#       fn: ptools_common.self_consistency_impl

_ANSWER_RE = re.compile(r'<answer>\s*(-?\d+)\s*</answer>', re.DOTALL)


def _parse_answer_index(text: str) -> int | None:
    """Extract a 0-based answer index from LLM output.

    Preference order:
      1. Integer inside <answer>...</answer> tags.
      2. First integer appearing anywhere in the string.
    Returns None if nothing parseable is found.
    """
    if not isinstance(text, str):
        return None
    m = _ANSWER_RE.search(text)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            pass
    m = re.search(r'-?\d+', text)
    if m:
        try:
            return int(m.group(0))
        except ValueError:
            pass
    return None


def _format_choices(choices: list) -> str:
    return '\n'.join(f'{i}. {c}' for i, c in enumerate(choices))


def self_consistency_impl(narrative: str, question: str, choices: list) -> int:
    """Direct-method entry point for self-consistency baseline.

    Samples N chain-of-thought rollouts at temperature > 0 and returns the
    majority-vote answer index. Ties are broken by earliest vote.

    Config keys:
      self_consistency.n_samples: number of samples (default 5)
      self_consistency.temperature: sampling temperature (default 0.7)
      self_consistency.prompt_template_file: CoT prompt template
        (must expose $narrative, $question, $choices placeholders)

    Caching MUST be disabled (cachier.enable_caching: false) — with caching
    on, identical prompts produce identical samples and the vote degenerates.
    """
    n_samples = int(config.get('self_consistency.n_samples', 5))
    temperature = float(config.get('self_consistency.temperature', 0.7))
    template_file = config.require('self_consistency.prompt_template_file')
    model = config.require('llm.model')

    template = Template(pathlib.Path(template_file).read_text())
    prompt = template.substitute(
        narrative=narrative,
        question=question,
        choices=_format_choices(choices),
    )

    votes: list[int] = []
    with config.configuration(llm=dict(temperature=temperature)):
        for _ in range(n_samples):
            try:
                text, _stats = llm(prompt, model)
            except Exception:
                continue
            idx = _parse_answer_index(text)
            if idx is not None:
                votes.append(idx)

    if not votes:
        return -1
    counts = collections.Counter(votes)
    # Counter.most_common preserves insertion order for ties, so the
    # earliest-seen winning index wins.
    return counts.most_common(1)[0][0]


# ============================================================
# Self-Discover (Zhou+ NeurIPS 2024): discovered reasoning structure
# ============================================================
#
# A reasoning structure is induced once per task (SELECT → ADAPT →
# IMPLEMENT; see induce_self_discover.py) and stored in a JSON file
# keyed by task name. At inference time the structure is prepended to
# the CoT-style prompt; the LLM fills in the structure and returns the
# final answer index.
#
# Wiring (config snippet):
#   self_discover:
#     structure_file: self_discover_structures.json
#     structure_key: murder          # one of: murder, object, team
#     prompt_template_file: prompt_templates/self_discover.txt
#   ptools:
#     answer_question:
#       method: direct
#       fn: ptools_common.self_discover_answer_impl


def self_discover_answer_impl(narrative: str, question: str, choices: list) -> int:
    """Direct-method entry point for self-discover baseline.

    Loads a pre-induced reasoning structure (from JSON keyed by task),
    splices it into the prompt template, then calls the LLM once per
    instance and parses the answer index.

    Config keys:
      self_discover.structure_file: JSON file of induced structures
      self_discover.structure_key: which task's structure to load
      self_discover.prompt_template_file: template with
        $narrative $question $choices $structure placeholders
    """
    structure_file = config.require('self_discover.structure_file')
    structure_key = config.require('self_discover.structure_key')
    template_file = config.require('self_discover.prompt_template_file')
    model = config.require('llm.model')

    structures = json.loads(pathlib.Path(structure_file).read_text())
    structure = structures.get(structure_key, '')
    if not structure:
        # Treat missing structure as a non-fatal warning — the prompt
        # will still run but without the self-discover scaffold.
        print(f'WARNING: no structure for key {structure_key!r}')

    template = Template(pathlib.Path(template_file).read_text())
    prompt = template.substitute(
        narrative=narrative,
        question=question,
        choices=_format_choices(choices),
        structure=structure,
    )

    try:
        text, _stats = llm(prompt, model)
    except Exception:
        return -1
    idx = _parse_answer_index(text)
    return idx if idx is not None else -1
