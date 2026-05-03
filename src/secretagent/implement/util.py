"""Utility helpers shared across implementation factories."""

import functools
import importlib
import importlib.util
import pathlib
from glob import glob
from pathlib import Path
from string import Template
from typing import Any, Callable

from secretagent import config
from secretagent.core import Interface, all_interfaces


def resolve_dotted(name: str) -> Any:
    """Resolve a dotted name like 'module.func' to the actual object.
    """
    parts = name.split('.')
    obj = importlib.import_module(parts[0])
    for part in parts[1:]:
        obj = getattr(obj, part)
    return obj


def resolve_tools(interface: Interface, tools, tool_module=None) -> list[Callable]:
    """Resolve a tools specification into a list of callables.

    The tools parameter can be:
      - None or [] → no tools (returns [])
      - '__all__' → all implemented interfaces except the given one;
        if tool_module is given, scoped to interfaces in that module
      - a list where each element is:
          - a callable (used as-is)
          - an Interface (resolved to its implementing function)
          - a string (resolved via resolve_dotted; if tool_module is given,
            bare names are prefixed with the module path)

    The tool_module parameter can be:
      - None → no scoping (original behaviour)
      - a Python module object → scope '__all__' to interfaces whose func
        lives in that module; bare string names are prefixed with the
        module's package path
    """
    if tools == '__all__':
        if tool_module is not None:
            mod_name = tool_module.__name__
            tools = [iface for iface in all_interfaces()
                     if iface is not interface
                     and iface.implementation is not None
                     and iface.func.__module__ == mod_name]
        else:
            tools = [iface for iface in all_interfaces()
                     if iface is not interface and iface.implementation is not None]
    tools = tools or []
    resolved = []
    for tool in tools:
        if isinstance(tool, str):
            # If tool_module is given and the name has no dots, prefer direct
            # attribute access — this works even when the module was loaded
            # from a file path (e.g. `__learned__`) and isn't importable via
            # dotted name on sys.path. Falls back to resolve_dotted.
            if tool_module is not None and '.' not in tool:
                attr = getattr(tool_module, tool, None)
                if attr is not None:
                    tool = attr
                else:
                    tool = resolve_dotted(f'{tool_module.__name__}.{tool}')
            else:
                tool = resolve_dotted(tool)
        if isinstance(tool, Interface):
            if tool.implementation is None:
                raise ValueError(f'Interface {tool.name!r} has no implementation')
            # Wrap in a plain function so that downstream consumers
            # (e.g. pydantic-ai Agent) get a proper function with the
            # right signature and no circular Pydantic references.
            @functools.wraps(tool.func)
            def wrapper(*args, _iface=tool, **kw):
                return _iface(*args, **kw)
            resolved.append(wrapper)
        else:
            if not callable(tool):
                raise ValueError(
                    f'Tool {tool!r} is not callable')
            resolved.append(tool)
    return resolved


def _load_module_from_file(filepath, module_name='learned_ptools'):
    """Import a Python file and return the module."""
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _find_learned_module_path(learner, filename, interface_name=None):
    """Find the most recent learned module file matching the learner tag.

    When interface_name is provided, matches directories named like
    {TS}.{interface_name}__{learner} (e.g. rote/ptool_inducer outputs).
    When interface_name is None, matches directories named like
    {TS}.{learner} (e.g. orch_learner outputs, where no per-interface
    prefix is used).
    """
    train_dir = config.require('learn.train_dir')
    if interface_name is not None:
        tag = f'{interface_name}__{learner}'
    else:
        tag = learner
    pattern = str(Path(train_dir) / f'*{tag}' / filename)
    matches = sorted(glob(pattern))
    if not matches:
        raise FileNotFoundError(
            f'no learned file found matching {pattern}')
    return Path(matches[-1])


def _find_learned_ptools_path(interface_name, learner):
    """Find the most recent learned_ptools.py matching the interface and learner."""
    return _find_learned_module_path(
        learner, 'learned_ptools.py', interface_name=interface_name,
    )


def load_tool_module(tool_module_spec, interface_name=None, learner=None):
    """Resolve a tool_module specification into a Python module.

    The tool_module_spec can be:
      - None → returns None (no tool module)
      - a string → imported via importlib.import_module
      - '__learned__' → loads learned_ptools.py from the learner's
        directory under config 'learn.train_dir', requires interface_name
        and learner to locate the file
    """
    if tool_module_spec is None:
        return None
    if tool_module_spec == '__learned__':
        if learner is None:
            raise ValueError(
                "tool_module='__learned__' requires a 'learner' argument")
        if interface_name is None:
            raise ValueError(
                "tool_module='__learned__' requires an interface_name")
        path = _find_learned_ptools_path(interface_name, learner)
        return _load_module_from_file(path)
    if isinstance(tool_module_spec, str):
        return importlib.import_module(tool_module_spec)
    return tool_module_spec


PROMPT_TEMPLATE_DIR = pathlib.Path(__file__).parent / 'prompt_templates'


def load_template(name: str) -> Template:
    """Load a prompt template from the prompt_templates directory."""
    return Template((PROMPT_TEMPLATE_DIR / name).read_text())


def format_examples_as_doctests(interface_name: str, cases: list) -> str:
    """Format example cases as doctest-style examples for the prompt."""
    lines = ["Here are some examples:", ""]
    for case in cases:
        args = case.get('input_args', []) if isinstance(case, dict) else (case.input_args or [])
        out = case.get('expected_output') if isinstance(case, dict) else case.expected_output
        args_str = ', '.join(repr(a) for a in args)
        lines.append(f">>> {interface_name}({args_str})")
        lines.append(repr(out))
    return '\n'.join(lines) + '\n'


