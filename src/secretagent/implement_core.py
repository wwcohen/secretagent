"""Built-in Implementation.Factory classes for secretagent.

Provides DirectFactory, EchoFactory, SimulateFactory, and PromptLLMFactory.
"""

import ast
import pathlib
import re

from string import Template
from textwrap import dedent
from smolagents.local_python_executor import LocalPythonExecutor
from typing import Callable
import types

from secretagent import config, llm_util, record
from secretagent.core import Interface, Implementation, register_factory, all_interfaces

class DirectFactory(Implementation.Factory):
    """Use the function body as the implementation.
    """
    def build_fn(self, interface: Interface, **_kw) -> Callable:
        return interface.func


class EchoFactory(Implementation.Factory):
    """Just echos the arguments to a function.
    """
    def build_fn(self, interface: Interface, echo_doc=False, **_kw) -> Callable:
        def result_fn(*args, **kw):
            print(f'Called {interface.signature(*args, **kw)}')
            if echo_doc:
                print('doc'.center(40, '-'))
                print(interface.doc)
        return result_fn


class SimulateFactory(Implementation.Factory):
    """Simulate a function call with an LLM.
    """
    def build_fn(self, interface: Interface, **prompt_kw) -> Callable:
        def result_fn(*args, **kw):
            with config.configuration(**prompt_kw):
                prompt = self.create_prompt(interface, *args, **kw)
                llm_output, stats = llm_util.llm(
                    prompt, config.require('llm.model'))
                return_type = interface.annotations.get('return', str)
                answer = self.parse_output(return_type, llm_output)
                record.record(func=interface.name, args=args, kw=kw, output=answer, stats=stats)
                return answer
        return result_fn

    def create_prompt(self, interface, *args, **kw):
        """Construct a prompt that calls an LLM to predict the output of the function.
        """
        template_str = """
        Consider the following documentation stub for a Python function.  Note
        that this is documentation, not a full implementation.
        ```python
        $stub_src
        ```

        Imagine that this function was fully implemented as suggested by the
        documentation stub, and that function were called with these arguments:

        $args

        Propose a possible output of the function for these inputs that is
        consistent with the documentation. Use the following output format:

        $thoughts
        <answer>
        FINAL ANSWER
        </answer>

        If your answer is x, show it as it would printed by a Python
        interpreter called by print(x). Specifically if x is a string do NOT
        include quotes around it.  Also, do not include any text other than
        the final answer between the <answer> and </answer> tags.
        """
        template = Template(dedent(template_str))
        arg_names = list(interface.annotations.keys())[:-1]
        input_args = '; '.join(
            [
                f'{argname} = {repr(argval)}'
                for argval, argname in zip(args, arg_names)
            ] + [
                f'{argname} = {repr(argval)}'
                for argname, argval in kw.items()
            ])
        if config.get('llm.thinking'):
            thoughts = "<thought>\nANY THOUGHTS\n</thought>\n"
        else:
            thoughts = ""
        prompt = template.substitute(
            dict(stub_src=interface.src,
                 args=input_args,
                 thoughts=thoughts))
        return prompt

    def parse_output(self, return_type, text):
        """Take LLM output and return the final answer, in the correct type.
        """
        try:
            match_result = re.search(r'<answer>(.*)</answer>', text, re.DOTALL|re.MULTILINE)
            final_answer = match_result.group(1).strip()
        except AttributeError:
            raise AttributeError('cannot find final answer')
        if return_type in [int, str, float]:
            result = return_type(final_answer)
        else:
            # type is complex - for now don't both validating it
            # with typeguard.check_type(result, return_type)
            result = ast.literal_eval(final_answer)
        return result


class PromptLLMFactory(Implementation.Factory):
    """Prompt an LLM with a user-supplied template.

    Unlike SimulateFactory (which has a fixed prompt), this factory
    lets the caller supply their own prompt template and answer-extraction
    pattern.

    Builder kwargs (passed to implement_via):
        prompt_template_str: A string.Template with $args
            placeholders. Exactly one of prompt_template_str or
            prompt_template_file must be given.
        prompt_template_file: Path to a file containing the template.
        answer_pattern: Regex with one group to extract the answer.
            Defaults to r'<answer>(.*)</answer>'. If None and the
            return type is str, the full LLM output is returned.
    """
    def build_fn(self, interface: Interface,
                 prompt_template_str=None,
                 prompt_template_file=None,
                 answer_pattern=None,
                 **prompt_kw) -> Callable:
        if (prompt_template_str is None) == (prompt_template_file is None):
            raise ValueError(
                'Exactly one of prompt_template_str or prompt_template_file must be given')
        if prompt_template_file is not None:
            prompt_template_str = pathlib.Path(prompt_template_file).read_text()
        template = Template(dedent(prompt_template_str))

        def result_fn(*args, **kw):
            with config.configuration(**prompt_kw):
                arg_names = list(interface.annotations.keys())[:-1]
                arg_dict = dict(zip(arg_names, args))
                arg_dict.update(kw)
                prompt = template.substitute(arg_dict)
                llm_output, stats = llm_util.llm(
                    prompt, config.require('llm.model'))
                return_type = interface.annotations.get('return', str)
                answer = _extract_answer(return_type, llm_output, answer_pattern)
                record.record(func=interface.name, args=args, kw=kw,
                              output=answer, stats=stats)
                return answer
        return result_fn


def _extract_answer(return_type, text, answer_pattern):
    """Extract and type-cast the answer from LLM output."""
    if answer_pattern is None and return_type is str:
        return text.strip()
    if answer_pattern is None:
        raise ValueError(
            'answer_pattern is required when return type is not str')
    match_result = re.search(answer_pattern, text, re.DOTALL | re.MULTILINE)
    if match_result is None:
        raise ValueError(f'cannot find answer matching pattern {answer_pattern!r}')
    final_answer = match_result.group(1).strip()
    if return_type in [int, str, float]:
        return return_type(final_answer)
    return ast.literal_eval(final_answer)

class PoTFactory(Implementation.Factory):
    """Generate Python code and execute it.
    """
    def build_fn(
            self,
            interface: Interface,
            additional_imports: list[types.ModuleType] | None = None, 
            **prompt_kw
    ) -> Callable:
        tool_functions = {
            called_inf.name: called_inf.implementation.implementing_fn
            for called_inf in all_interfaces()
            if called_inf != interface}
        python_executor = LocalPythonExecutor(
            additional_authorized_imports=(additional_imports or []),
            )
        # Put tool functions in custom_tools directly, since
        # LocalPythonExecutor.__call__ passes custom_tools (not
        # additional_functions) to evaluate_python_code.
        python_executor.custom_tools = tool_functions
        # Provide final_answer in static_tools so the LLM can
        # return a value via final_answer(result).
        python_executor.static_tools = {
            "final_answer": lambda x: x,
        }
        def result_fn(*args, **kw):
            with config.configuration(**prompt_kw):
                prompt = self.create_prompt(interface, additional_imports, *args, **kw)
                llm_output, stats = llm_util.llm(
                    prompt, config.require('llm.model'))
                generated_code = _extract_answer(
                    str,
                    llm_output,
                    answer_pattern='```python\n(.*)\n```')
                code_output = python_executor(generated_code)
                answer = code_output.output
                if config.get('echo.code_eval_output'):
                    llm_util.echo_boxed(str(answer), 'code_eval_output')
                record.record(func=interface.name, args=args, kw=kw, output=answer, stats=stats, pot=generated_code)
                return answer
        return result_fn

    def create_prompt(self, interface, additional_authorized_imports, *args, **kw):
        """Construct a prompt that calls an LLM to predict the output of the function.
        """
        arg_names = list(interface.annotations.keys())[:-1]
        #TODO refactor
        input_args = '; '.join(
            [
                f'{argname} = {repr(argval)}'
                for argval, argname in zip(args, arg_names)
            ] + [
                f'{argname} = {repr(argval)}'
                for argname, argval in kw.items()
            ])
        tool_stub_src_listing = '\n\n'.join([
            tool_interface.src
            for tool_interface in all_interfaces()
            if tool_interface != interface
            ])
        if additional_authorized_imports:
            imports = '\n' + join(
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

        template_str = """
        Consider the following documentation stub for a Python function.  Note
        that this is documentation, not a full implementation.
        ```python
        $main_stub_src
        ```

        The unseen implementation might call any of the following
        'tool' methods.

        ```python
        $tool_stub_src_listing
        ```

        Imagine that all of these functions were implemented as
        suggested by the documentation stubs, and that function
        $func_name was called with these arguments:

        $input_args

        Output Python code that would compute the output of
        $func_name, by calling the tools, FOR THESE INPUTS.
        The code MUST call final_answer(result) as the last
        line to return the result.

        Note it is NOT necessary for the code to be a completely
        general inplementation, it only needs to work for these
        specific inputs.

        $imports
        Use the following output format:

        $thoughts
        <answer>
        ```python
        CODE TO COMPUTE OUTPUT FOR THESE INPUTS
        final_answer(result)
        ```
        </answer>
        """
        template = Template(dedent(template_str))
        prompt = template.substitute(**template_bindings)
        return prompt


register_factory('direct', DirectFactory())
register_factory('echo', EchoFactory())
register_factory('simulate', SimulateFactory())
register_factory('program_of_thought', PoTFactory())
register_factory('prompt_llm', PromptLLMFactory())
