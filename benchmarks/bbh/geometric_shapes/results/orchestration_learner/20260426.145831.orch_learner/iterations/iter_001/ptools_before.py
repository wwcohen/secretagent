"""Tools for the geometric_shapes benchmark.

The task: given an SVG path element, identify which geometric shape it draws,
returning the correct multiple-choice letter (e.g. "(J)").
"""

from collections import defaultdict
from typing import List, Optional, Tuple

from secretagent.core import interface, implement_via

# ── path normalization ──────────────────────────────────────────────────────

def _round_pt(x: float, y: float, decimals: int = 2) -> Tuple[float, float]:
    return (round(x, decimals), round(y, decimals))

def _parse_coord(s: str) -> Tuple[float, float]:
    """Parse 'x,y' or 'x y' into a float tuple."""
    parts = s.replace(',', ' ').split()
    return (float(parts[0]), float(parts[1]))

def _segments_from_commands(commands: List[str]) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
    """Extract line segments from a list of SVG commands.

    Returns a list of (start, end) point pairs, one per L command.
    """
    segments = []
    current = None
    for cmd in commands:
        cmd = cmd.strip()
        if cmd.upper().startswith('M'):
            current = _round_pt(*_parse_coord(cmd[1:].strip()))
        elif cmd.upper().startswith('L'):
            end = _round_pt(*_parse_coord(cmd[1:].strip()))
            if current is not None:
                segments.append((current, end))
            current = end
    return segments

def _find_eulerian_path(adj, degree):
    """Find an Eulerian path using Hierholzer's algorithm on a multigraph.

    adj: dict mapping node -> list of (neighbor, edge_index)
    degree: dict mapping node -> degree (number of edges)

    Returns a list of nodes forming the path, or None if no Eulerian path exists.
    """
    # find start node: prefer an odd-degree node, else any node with edges
    odd_nodes = [n for n, d in degree.items() if d % 2 == 1]
    if len(odd_nodes) > 2:
        return None  # no Eulerian path possible
    start = odd_nodes[0] if odd_nodes else next((n for n, d in degree.items() if d > 0), None)
    if start is None:
        return None

    stack = [start]
    path = []
    used = set()
    while stack:
        v = stack[-1]
        found = False
        while adj[v]:
            u, idx = adj[v].pop()
            if idx not in used:
                used.add(idx)
                # also remove from the other side's list lazily (handled by used set)
                stack.append(u)
                found = True
                break
        if not found:
            path.append(stack.pop())
    path.reverse()
    return path

def normalize_path(commands: List[str]) -> List[str]:
    """Rearrange SVG commands into continuous chains where possible.

    Treats each L command as an undirected edge between two points, then
    finds a continuous traversal (Eulerian path) of those edges. Falls back
    to separate M-started chains for disconnected components.
    """
    segments = _segments_from_commands(commands)
    if not segments:
        return commands

    # build adjacency for Eulerian path
    adj = defaultdict(list)
    degree = defaultdict(int)
    for idx, (a, b) in enumerate(segments):
        adj[a].append((b, idx))
        adj[b].append((a, idx))
        degree[a] += 1
        degree[b] += 1

    # try to find an Eulerian path over the whole graph
    path = _find_eulerian_path(adj, degree)
    if path is not None and len(path) == len(segments) + 1:
        result = [f'M {path[0][0]},{path[0][1]}']
        for pt in path[1:]:
            result.append(f'L {pt[0]},{pt[1]}')
        return result

    # fallback: chain segments greedily per connected component
    point_to_segs = defaultdict(list)
    for idx, (a, b) in enumerate(segments):
        point_to_segs[a].append(idx)
        point_to_segs[b].append(idx)

    used = [False] * len(segments)
    result = []

    for start_idx in range(len(segments)):
        if used[start_idx]:
            continue
        # start a new chain from this segment
        a, b = segments[start_idx]
        used[start_idx] = True
        chain = [a, b]
        # extend forward
        while True:
            tip = chain[-1]
            found = False
            for idx in point_to_segs[tip]:
                if not used[idx]:
                    used[idx] = True
                    sa, sb = segments[idx]
                    chain.append(sb if sa == tip else sa)
                    found = True
                    break
            if not found:
                break
        result.append(f'M {chain[0][0]},{chain[0][1]}')
        for pt in chain[1:]:
            result.append(f'L {pt[0]},{pt[1]}')

    return result

# ── sub-tools ────────────────────────────────────────────────────────────────

@interface
def extract_path_and_options(input: str) -> Tuple[str, List[Tuple[str, str]]]:
    """Extract the SVG path string and answer options from the prompt.

    Returns (path, options) where path is the raw SVG path d="..." string
    and options is a list of (letter, shape_name) pairs, e.g. [('A', 'circle'), ('B', 'heptagon')].
    """
    ...

@interface
def decompose_path(path: str) -> List[str]:
    """Break an SVG path string into a list of individual command strings.

    Each entry is one command with its arguments, e.g. 'M 37.73,31.58' or 'L 41.81,33.73'.
    """
    ...

@interface
def describe_command(command: str, previous_command: Optional[str] = None) -> str:
    """Describe what a single SVG path command does in plain English,
    including where it starts from.

    For an M command, describe the move to the given point.
    For an L command, previous_command provides the starting point;
    describe the line drawn from that starting point to the new point.

    E.g. describe_command('L 41.81,33.73', 'M 37.73,31.58')
      -> 'Draw a line from (37.73, 31.58) to (41.81, 33.73)'.
    """
    ...

@interface
def compute_angle(prev_command: str, current_command: str, next_command: str) -> str:
    """Compute the angle formed at the point where two line segments meet.

    prev_command and current_command define the incoming segment;
    current_command and next_command define the outgoing segment.
    The angle is measured at the endpoint of current_command.

    Returns a plain-English description of the angle, or indicates
    that no angle applies (e.g. for a move command).
    """
    ...

@interface
def describe_shape(annotated_commands: List[str]) -> str:
    """Given the full list of commands with angle descriptions interspersed,
    describe what geometric shape the path forms.
    """
    ...

@interface
def select_option(description: str, options: List[Tuple[str, str]]) -> str:
    """Given a shape description and the list of answer options, return the
    option letter that best matches, e.g. '(F)'.
    """
    ...

# ── top-level interface ───────────────────────────────────────────────────────

@interface
def identify_shape(input: str) -> str:
    """Given an SVG path multiple-choice question, return the correct option letter.

    The input is the full question text including the <path d="..."/> element
    and labeled options. Returns a string like "(J)".
    """
    ...

@interface
def react_identify_shape(input: str) -> str:
    """Given an SVG path multiple-choice question, return a freeform answer
    string. Intended to be bound via simulate_pydantic with the sub-tools as
    the tool list (ReAct); its output is post-processed by
    extract_option_letter in geometric_shapes_react_workflow.
    """
    ...

# ── hand-coded workflow ───────────────────────────────────────────────────────

def geometric_shapes_workflow(input: str) -> str:
    """Hand-coded workflow implementing identify_shape.

    To use:
        ptools.identify_shape.method=direct
        ptools.identify_shape.fn=ptools.geometric_shapes_workflow
    """
    path, options = extract_path_and_options(input)
    commands = normalize_path(decompose_path(path))

    # describe each command, passing the previous command for L commands
    descriptions = [describe_command(commands[0])]
    for i in range(1, len(commands)):
        descriptions.append(describe_command(commands[i], previous_command=commands[i - 1]))

    # build annotated list with angles interspersed
    annotated = [descriptions[0]]
    for i in range(1, len(descriptions)):
        if i + 1 < len(commands):
            angle = compute_angle(commands[i - 1], commands[i], commands[i + 1])
            annotated.append(angle)
        annotated.append(descriptions[i])

    description = describe_shape(annotated)
    return select_option(description, options)

# ── zero-shot unstructured workflow ──────────────────────────────────────────

@implement_via('prompt_llm', prompt_template_file='prompt_templates/zeroshot.txt')
def zeroshot_identify_shape(input: str) -> str:
    ...

@implement_via('simulate')
def extract_option_letter(llm_output: str) -> str:
    """Given raw LLM output, extract and return the multiple-choice letter (e.g. "(J)").
    """
    ...

@interface
def identify_shape_orchestrated(input: str) -> str:
    """Given an SVG path multiple-choice question, return the correct option letter (e.g. "(J)")."""
    ...


def zeroshot_unstructured_workflow(input: str) -> str:
    """Workflow for zero-shot prompt with letter extraction.

    To use:
        ptools.identify_shape.method=direct
        ptools.identify_shape.fn=ptools.zeroshot_unstructured_workflow
    """
    llm_output = zeroshot_identify_shape(input)
    return extract_option_letter(llm_output)


def geometric_shapes_react_workflow(input: str) -> str:
    """Workflow that runs ReAct over the sub-tools and extracts the option
    letter from its freeform final answer.

    To use:
        ptools.identify_shape.method=direct
        ptools.identify_shape.fn=ptools.geometric_shapes_react_workflow
        ptools.react_identify_shape.method=simulate_pydantic
        ptools.react_identify_shape.tools=[...]
    """
    react_answer = react_identify_shape(input)
    return extract_option_letter(react_answer)
