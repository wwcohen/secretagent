"""Built-in Implementation.Factory classes for secretagent.

Provides DirectFactory, SimulateFactory, PromptLLMFactory, and PoTFactory.
"""

import ast
import json
import pathlib
import re

from string import Template
from textwrap import dedent
from smolagents.local_python_executor import LocalPythonExecutor, BASE_PYTHON_TOOLS
from typing import Any, Callable

from pydantic import Field

from secretagent import config, llm_util, record
from secretagent.core import Interface, Implementation, register_factory, all_interfaces
from secretagent.implement.util import (
    resolve_dotted, resolve_tools, load_tool_module,
    load_template, format_examples_as_doctests,
    _find_learned_module_path, _load_module_from_file,
)


class DirectFactory(Implementation.Factory):
    """Use a Python function as the implementation.

    Defaults to the body of the interface functions.

    Example: foo.implement_via('direct', pyfn_implementing_foo)
    """
    direct_fn: Any = None

    def setup(self, fn: Callable | str | None = None, **_kw):
        if isinstance(fn, str) and fn.startswith('__learned__.'):
            attr = fn[len('__learned__.'):]
            learner = _kw.get('learner')
            if learner is None:
                raise ValueError(
                    "fn='__learned__.<attr>' requires a 'learner' argument")
            path = _find_learned_module_path(learner, 'ptools_evolved.py')
            mod = _load_module_from_file(path, module_name=f'learned_{learner}')
            if not hasattr(mod, attr):
                raise AttributeError(
                    f'{path} does not define an attribute named {attr!r}')
            # Bind implementations on the learned module's own Interface objects
            # so that the learned function can call its co-module tools. Without
            # this, workflow() would fail with NotImplementedError because the
            # evolved module's Interface objects are distinct from the base
            # ptools module's and have no implementations bound to them.
            # Skip the entry point itself — re-binding it would recurse here.
            from secretagent.core import implement_via_config
            ptools_cfg = config.get('ptools') or {}
            entry_name = self.bound_interface.name if self.bound_interface else None
            sub_cfg = {
                name: cfg for name, cfg in ptools_cfg.items()
                if name != entry_name and hasattr(mod, name)
            }
            if sub_cfg:
                implement_via_config(mod, sub_cfg)
            self.direct_fn = getattr(mod, attr)
        elif isinstance(fn, str):
            self.direct_fn = resolve_dotted(fn)
        elif fn is not None:
            self.direct_fn = fn
        else:
            self.direct_fn = self.bound_interface.func

    def __call__(self, *args, **kw):
        return self.direct_fn(*args, **kw)

class SimulateFactory(Implementation.Factory):
    """Simulate a function call with an LLM.

    Examples: 
      foo.implement_via('simulate')
      foo.implement_via('simulate', llm.model=..., example_file='foo_demonstrations.json')

    The example_files are in json and look like this:
    {
      "sport_for": [
        {"input_args": ["Bam Adebayo"], "expected_output": "basketball"},
        {"input_args": ["scored a reverse layup"], "expected_output": "basketball"}
      ],
      "analyze_sentence": [
        {"input_args": ["Bam Adebayo scored a reverse layup."], "expected_output": ["Bam Adebayo", "scored a reverse layup", ""]}
      ]
    }

    If you were to configuring with a yaml file you would use:

    ptools:
      sport_for:
        method: simulate
        example_file: examples/examples.json
      analyze_sentence:
        method: simulate
        example_file: examples/examples.json
    """
    examples_cases: list | None = None
    prompt_kw: dict = Field(default_factory=dict)

    def setup(self, example_file=None, **prompt_kw):
        self.prompt_kw = prompt_kw
        if example_file:
            data = json.loads(pathlib.Path(example_file).read_text())
            self.examples_cases = data.get(self.bound_interface.name, [])

    def __call__(self, *args, **kw):
        interface = self.bound_interface
        with config.configuration(**self.prompt_kw):
            prompt = self.create_prompt(interface, *args, examples=self.examples_cases, **kw)
            llm_output, stats = llm_util.llm(prompt, self.llm_model)
            try:
                return_type = interface.annotations.get('return', str)
                answer = self.parse_output(return_type, llm_output)
            except Exception as ex:
                record.record(func=interface.name, args=args, kw=kw,
                              output=f'**exception**: {ex}', stats=stats)
                raise
            record.record(func=interface.name, args=args, kw=kw, output=answer, stats=stats)
            return answer

    def create_prompt(self, interface, *args, examples=None, **kw):
        """Construct a prompt that calls an LLM to predict the output of the function.
        """
        template = load_template('simulate.txt')
        input_args = interface.format_args(*args, **kw)
        if (not input_args.strip()):
            raise ValueError(f'input_args null for {args=} {kw=}')
        if config.get('llm.thinking'):
            thoughts = "<thought>\nANY THOUGHTS\n</thought>\n"
        else:
            thoughts = ""
        examples_text = ""
        if examples:
            examples_text = format_examples_as_doctests(interface.name, examples)
        return_type = interface.annotations.get('return', str)
        schema_block = _format_pydantic_schema(return_type)
        prompt = template.substitute(
            dict(stub_src=interface.src,
                 input_args=input_args,
                 thoughts=thoughts,
                 examples=examples_text,
                 schema_block=schema_block))
        return prompt

    def parse_output(self, return_type, text):
        """Take LLM output and return the final answer, in the correct type.

        Tries <answer>...</answer> tags first.  For dict/list return types,
        falls back to extracting JSON from a markdown code block or the first
        bare {...} / [...] object in the output — handles models that don't
        follow the tag format for complex types.
        """
        import json
        match_result = re.search(r'<answer>(.*)</answer>', text, re.DOTALL|re.MULTILINE)
        if match_result:
            final_answer = match_result.group(1).strip()
            if return_type in [int, str, float]:
                return _coerce_numeric(final_answer, return_type)
            final_answer = _strip_code_fences(final_answer)
            pydantic_result = _parse_pydantic_constructor(final_answer, return_type)
            if pydantic_result is not None:
                return pydantic_result
            try:
                parsed = json.loads(final_answer)
            except json.JSONDecodeError:
                parsed = ast.literal_eval(final_answer)
            return _maybe_model_validate(parsed, return_type)

        # Fallback for dict/list: extract JSON from the raw output
        if return_type in [dict, list] or (hasattr(return_type, '__origin__')
                                           and return_type.__origin__ in [dict, list]):
            open_ch, close_ch = ('{', '}') if return_type is dict else ('[', ']')
            # prefer a fenced code block
            code_match = re.search(
                r'```(?:json|python)?\s*(' + re.escape(open_ch) + r'.*?' + re.escape(close_ch) + r')\s*```',
                text, re.DOTALL)
            if code_match:
                candidate = code_match.group(1).strip()
            else:
                # find the outermost balanced bracket span
                start = text.find(open_ch)
                end = text.rfind(close_ch)
                candidate = text[start:end + 1].strip() if start != -1 and end != -1 else ''
            if candidate:
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    return ast.literal_eval(candidate)

        # For str return type without <answer> tags, return the raw text
        if return_type is str:
            return text.strip()

        # Fence-fallback: model emitted ```python\nClassName(...)\n``` without
        # <answer> tags. Recoverable when return_type is a pydantic BaseModel.
        fence_match = re.search(r'```(?:python|json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if fence_match:
            candidate = fence_match.group(1).strip()
            pydantic_result = _parse_pydantic_constructor(candidate, return_type)
            if pydantic_result is not None:
                return pydantic_result
        raise ValueError('cannot find final answer')


class PromptLLMFactory(Implementation.Factory):
    """Prompt an LLM with a user-supplied template.

    Unlike SimulateFactory (which has a fixed prompt), this factory
    lets the caller supply their own prompt template and answer-extraction
    pattern.

    Examples:
      foo.implement_via('prompt_llm', prompt_template_str='Is $sentence true?')
      foo.implement_via('prompt_llm', prompt_template_file='prompts/foo.txt',
                        answer_pattern=r'<answer>(.*)</answer>')

    Builder kwargs (passed to implement_via):
        prompt_template_str: A string.Template with $args
            placeholders. Exactly one of prompt_template_str or
            prompt_template_file must be given.
        prompt_template_file: Path to a file containing the template.
        answer_pattern: Regex with one group to extract the answer.
            Defaults to r'<answer>(.*)</answer>'. If None and the
            return type is str, the full LLM output is returned.
    """
    template: Any = None
    answer_pattern: str | None = None
    prompt_kw: dict = Field(default_factory=dict)

    def setup(self, prompt_template_str=None, prompt_template_file=None,
              answer_pattern=r'<answer>(.*)</answer>', **prompt_kw):
        if (prompt_template_str is None) == (prompt_template_file is None):
            raise ValueError(
                'Exactly one of prompt_template_str or prompt_template_file must be given')
        if prompt_template_file is not None:
            # Relative paths resolve against config.get('root') when set,
            # falling back to the current working directory. This lets a
            # caller that has already called config.set_root() load
            # templates without relying on cwd — the historical behavior.
            path = pathlib.Path(prompt_template_file)
            if not path.is_absolute() and not path.exists():
                root = config.get('root')
                if root is not None:
                    root_path = pathlib.Path(root) / prompt_template_file
                    if root_path.exists():
                        path = root_path
            prompt_template_str = path.read_text()
        self.template = Template(dedent(prompt_template_str))
        self.answer_pattern = answer_pattern
        self.prompt_kw = prompt_kw

    def __call__(self, *args, **kw):
        interface = self.bound_interface
        with config.configuration(**self.prompt_kw):
            arg_names = list(interface.annotations.keys())[:-1]
            arg_dict = dict(zip(arg_names, args))
            arg_dict.update(kw)
            prompt = self.template.substitute(arg_dict)
            llm_output, stats = llm_util.llm(
                prompt, self.llm_model)
            try:
                return_type = interface.annotations.get('return', str)
                answer = _extract_answer(return_type, llm_output, self.answer_pattern)
            except Exception as ex:
                record.record(func=interface.name, args=args, kw=kw,
                              output=f'**exception**: {ex}', stats=stats)
                raise
            record.record(func=interface.name, args=args, kw=kw,
                          output=answer, stats=stats)
            return answer


def _coerce_numeric(s: str, t: type):
    """Cast s to t, stripping commas and $ for numeric types.

    LLMs naturally emit dollar amounts as `$25,502.0` or `-25,502.0`;
    bare float()/int() rejects those. Strip the formatting before
    coercing for int/float; pass through unchanged for str.
    """
    if t in (int, float):
        s = s.strip().replace(',', '').replace('$', '')
    return t(s)


def _strip_code_fences(text: str) -> str:
    """Strip enclosing ```python|json ... ``` fences if present.

    Returns the inner content, or the original text if no fence is found.
    """
    m = re.match(r'^```(?:python|json)?\s*\n?(.*?)\n?```\s*$',
                 text.strip(), re.DOTALL)
    return m.group(1).strip() if m else text


def _eval_ast_node(node):
    """Evaluate an AST node, treating nested Calls as dicts of kwargs.

    Used by _parse_pydantic_constructor to handle expressions like
    `[BagItem(id=1, name='bag')]` — converts BagItem(...) into a dict
    that pydantic's model_validate can recursively validate.
    """
    if isinstance(node, ast.Call):
        return {kw.arg: _eval_ast_node(kw.value) for kw in node.keywords}
    if isinstance(node, ast.List):
        return [_eval_ast_node(e) for e in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(_eval_ast_node(e) for e in node.elts)
    if isinstance(node, ast.Dict):
        return {_eval_ast_node(k): _eval_ast_node(v)
                for k, v in zip(node.keys, node.values)}
    if isinstance(node, ast.Set):
        return {_eval_ast_node(e) for e in node.elts}
    return ast.literal_eval(node)


def _parse_pydantic_constructor(text: str, return_type):
    """If text is `ClassName(...)` and return_type is a pydantic BaseModel,
    parse the constructor call and call return_type.model_validate.

    Returns None if not applicable so the caller can fall through to
    json.loads / ast.literal_eval.
    """
    try:
        from pydantic import BaseModel
    except ImportError:
        return None
    if not (isinstance(return_type, type) and issubclass(return_type, BaseModel)):
        return None
    try:
        tree = ast.parse(text.strip(), mode='eval')
    except SyntaxError:
        return None
    if not isinstance(tree.body, ast.Call) or not isinstance(tree.body.func, ast.Name):
        return None
    kwargs = {kw.arg: _eval_ast_node(kw.value) for kw in tree.body.keywords}
    return return_type.model_validate(kwargs)


def _format_pydantic_schema(model_cls) -> str:
    """Build a schema block to embed in simulate prompts.

    Returns an empty string for non-pydantic return types so the prompt
    template substitution stays a no-op.  When the return type is a
    pydantic BaseModel, embeds the JSON Schema so the LLM sees the
    actual field names and types instead of inferring them from the
    function signature alone.
    """
    try:
        from pydantic import BaseModel
    except ImportError:
        return ""
    if not (isinstance(model_cls, type) and issubclass(model_cls, BaseModel)):
        return ""
    schema = model_cls.model_json_schema()
    return (
        f"\nThe return value must be a `{model_cls.__name__}` matching this JSON Schema:\n\n"
        f"```json\n{json.dumps(schema, indent=2)}\n```\n\n"
        f"Use EXACTLY the field names and types shown above. Return a single JSON object\n"
        f"matching this schema (no extra fields, no renamed fields).\n"
    )


def _maybe_model_validate(parsed, return_type):
    """If return_type is a pydantic BaseModel and parsed is a dict-like,
    coerce via model_validate so missing/renamed fields surface as
    ValidationError instead of being returned as a raw dict.
    """
    try:
        from pydantic import BaseModel
    except ImportError:
        return parsed
    if isinstance(return_type, type) and issubclass(return_type, BaseModel):
        return return_type.model_validate(parsed)
    return parsed


def _extract_answer(return_type, text, answer_pattern):
    """Extract and type-cast the answer from LLM output."""
    if answer_pattern is None and return_type is str:
        return text.strip()
    if answer_pattern is None:
        raise ValueError(
            'answer_pattern is required when return type is not str')
    match_result = re.search(answer_pattern, text, re.DOTALL | re.MULTILINE)
    if match_result is None:
        llm_util.echo_boxed(text, 'bad code_eval_output')
        raise ValueError(f'cannot find answer matching pattern {answer_pattern!r}')
    final_answer = match_result.group(1).strip()
    if return_type in [int, str, float]:
        return _coerce_numeric(final_answer, return_type)
    final_answer = _strip_code_fences(final_answer)
    pydantic_result = _parse_pydantic_constructor(final_answer, return_type)
    if pydantic_result is not None:
        return pydantic_result
    parsed = ast.literal_eval(final_answer)
    return _maybe_model_validate(parsed, return_type)

class ToolUsingFactory(Implementation.Factory):
    """Abstract base for factories that use resolved tool lists.

    Subclasses call setup_tools() in their setup() method to get a
    resolved list of tool callables, with support for tool_module
    scoping and learned tool loading.
    """
    tools: list = Field(default_factory=list)

    def setup_tools(self, tools=None, tool_module=None, learner=None):
        """Resolve tools and return the list of callables.

        Args:
            tools: tool specification (None, '__all__', or a list)
            tool_module: None, a module name string, or '__learned__'
            learner: learner tag, required when tool_module='__learned__'

        Returns:
            list of resolved tool callables
        """
        mod = load_tool_module(
            tool_module,
            interface_name=self.bound_interface.name,
            learner=learner)
        resolved = resolve_tools(self.bound_interface, tools, tool_module=mod)
        return resolved


class PoTFactory(ToolUsingFactory):
    """Generate Python code with an LLM and execute it in a sandbox.

    Examples:
      foo.implement_via('program_of_thought')
      foo.implement_via('program_of_thought', tools='__all__')
      foo.implement_via('program_of_thought',
                        tools=[bar, baz],
                        additional_imports=['numpy'])
    """
    python_executor: Any = None
    tool_interfaces: list = Field(default_factory=list)
    additional_imports: Any = None
    inject_args: bool = False
    prompt_kw: dict = Field(default_factory=dict)

    def setup(self, tools='__all__', additional_imports=None, inject_args=False,
              tool_module=None, learner=None, **prompt_kw):
        interface = self.bound_interface
        self.prompt_kw = prompt_kw
        self.additional_imports = additional_imports
        self.inject_args = inject_args
        resolved_tools = self.setup_tools(tools, tool_module=tool_module, learner=learner)
        tool_functions = {fn.__name__: fn for fn in resolved_tools}
        self.python_executor = LocalPythonExecutor(
            additional_authorized_imports=(additional_imports or []),
            )
        # Put tool functions in custom_tools directly, since
        # LocalPythonExecutor.__call__ passes custom_tools (not
        # additional_functions) to evaluate_python_code.
        self.python_executor.custom_tools = tool_functions
        # Merge smolagents' BASE_PYTHON_TOOLS (len, list, dict, sorted,
        # etc.) into static_tools so generated code can use standard
        # builtins. Previously these were blocked because static_tools
        # was overwritten with only final_answer (issue #7).
        self.python_executor.static_tools = {
            **BASE_PYTHON_TOOLS,
            "final_answer": lambda x: x,
        }
        # collect interfaces for tool stubs in the prompt
        self.tool_interfaces = [
            iface for iface in all_interfaces()
            if iface is not interface
            and iface.implementation is not None
            and iface.name in tool_functions]

    def __call__(self, *args, **kw):
        interface = self.bound_interface
        with config.configuration(**self.prompt_kw):
            # Inject input arg values into sandbox so LLM can reference
            # them as variables without copying large strings into code.
            if self.inject_args:
                arg_names = list(interface.annotations.keys())[:-1]
                for name, val in zip(arg_names, args):
                    self.python_executor.custom_tools[name] = val
            prompt = self.create_prompt(
                interface, self.tool_interfaces, self.additional_imports,
                *args, inject_args=self.inject_args, **kw)
            llm_output, stats = llm_util.llm(
                prompt, self.llm_model)
            try:
                generated_code = _extract_answer(
                    str,
                    llm_output,
                    answer_pattern='```python\n(.*?)\n```')
                if config.get('echo.code_eval_input'):
                    llm_util.echo_boxed(generated_code, 'code_eval_input')
                code_output = self.python_executor(generated_code)
                answer = code_output.output
            except Exception as ex:
                record.record(
                    func=interface.name, args=args, kw=kw,
                    output=f'**exception**: {ex}', stats=stats,
                    step_info=dict(generated_code=llm_output))
                raise
            if config.get('echo.code_eval_output'):
                llm_util.echo_boxed(str(answer), 'code_eval_output')
            record.record(
                func=interface.name, args=args, kw=kw, output=answer, stats=stats,
                step_info=dict(generated_code=generated_code))
            return answer

    def create_prompt(self, interface, tool_interfaces, additional_authorized_imports,
                      *args, inject_args=False, **kw):
        """Construct a prompt that calls an LLM to predict the output of the function.
        """
        if inject_args:
            arg_names = list(interface.annotations.keys())[:-1]
            var_list = ', '.join(f'`{n}`' for n in arg_names)
            input_args = interface.format_args(*args, **kw)
            input_args += f'\n\nThe input args are available in these variables: {var_list}'
        else:
            input_args = interface.format_args(*args, **kw)
        if (not input_args.strip()):
            raise ValueError(f'input_args null for {interface.name} on {args=} {kw=}')
        tool_stub_src_listing = '\n\n'.join([
            tool_interface.src
            for tool_interface in tool_interfaces
            ])
        if additional_authorized_imports:
            imports = '\n' + '\n'.join(
                ['You may use these packages:\n'] + 
                [f'import {package}'
                 for package in additional_authorized_imports]
            ) + '\n\n'
        else:
            imports = ''

        if config.get('llm.thinking'):
            thoughts = '<thought>\nANY THOUGHTS\n</thought>\n\n'
        else:
            thoughts = ''

        template_bindings=dict(
            main_stub_src=interface.src,
            func_name=interface.name,
            tool_stub_src_listing=tool_stub_src_listing,
            input_args=input_args,
            imports=imports,
            thoughts=thoughts
        )

        template = load_template('program_of_thought.txt')
        prompt = template.substitute(**template_bindings)
        if inject_args:
            prompt = prompt.replace(
                'Start the\ncode block by initializing a variable for each input.  It is ESSENTIAL\n'
                'that the code is able to be run independently.',
                'The input variables are already loaded in the execution environment — '
                'do not write them out in the code. Use them in your code if needed.')
        return prompt






register_factory('direct', DirectFactory())
register_factory('simulate', SimulateFactory())
register_factory('program_of_thought', PoTFactory())
register_factory('prompt_llm', PromptLLMFactory())
