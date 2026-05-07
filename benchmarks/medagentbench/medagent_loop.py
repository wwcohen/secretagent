"""Multi-turn interaction loops for MedAgentBench.

Provides two protocol implementations:
  - medagent_loop: raw text loop (GET/POST/FINISH) matching the paper
  - codeact_loop: iterative code generation with error feedback

Prompts are loaded from prompt_templates/ (not hardcoded).
"""

import json
import time
from pathlib import Path

from litellm import completion, completion_cost
from secretagent import config, record
from secretagent.llm_util import echo_boxed

import fhir_tools

_TEMPLATE_DIR = Path(__file__).parent / 'prompt_templates'


def _load_template(name):
    return (_TEMPLATE_DIR / name).read_text()


def _completion_with_backoff(**kw):
    """Retry completion with exponential backoff for rate limits."""
    for attempt in range(5):
        try:
            return completion(**kw)
        except Exception:
            if attempt == 4:
                raise
            time.sleep(2 ** attempt)


def _llm_call(model, messages, max_tokens, tag=''):
    """Single LLM call with stats tracking and echo support."""
    start = time.time()
    response = _completion_with_backoff(model=model, messages=messages, max_tokens=max_tokens)
    latency = time.time() - start

    raw = response.choices[0].message.content or ''
    stats = dict(
        input_tokens=response.usage.prompt_tokens,
        output_tokens=response.usage.completion_tokens,
        latency=latency, cost=0.0)
    try:
        stats['cost'] = completion_cost(completion_response=response)
    except Exception:
        pass

    if config.get('echo.llm_output') and tag:
        echo_boxed(raw, tag)
    return raw, stats


def _extract_task_context(context):
    """Extract raw task context from the enriched context string."""
    marker = 'Task context: '
    if marker in context:
        return context[context.index(marker) + len(marker):]
    return ''


def _accumulate_stats(total, new):
    for k in total:
        total[k] += new.get(k, 0)


# ──────────────────────────────────────────────────────────────────────
# L0: Paper baseline — multi-turn text loop (GET/POST/FINISH)
# ──────────────────────────────────────────────────────────────────────

def medagent_loop(instruction: str, context: str) -> list:
    """Multi-turn text loop matching the MedAgentBench paper protocol."""
    model = config.require('llm.model')
    max_round = int(config.get('fhir.max_round', 8))
    max_tokens = int(config.get('llm.max_tokens', 2048))
    fhir_base = config.get('fhir.api_base', 'http://localhost:8080/fhir/')

    funcs = json.loads((_TEMPLATE_DIR.parent / 'data' / 'funcs_v1.json').read_text())
    system_prompt = _load_template('unstructured_baseline.txt').format(
        api_base=fhir_base, functions=json.dumps(funcs),
        context=_extract_task_context(context), question=instruction)

    messages = [{"role": "user", "content": system_prompt}]
    total_stats = dict(input_tokens=0, output_tokens=0, latency=0.0, cost=0.0)

    for round_idx in range(max_round):
        raw, stats = _llm_call(model, messages, max_tokens, f'llm_output (round {round_idx})')
        _accumulate_stats(total_stats, stats)

        r = raw.strip().replace('```tool_code', '').replace('```', '').strip()

        if r.startswith('GET'):
            raw_res = fhir_tools._send_get_request_raw(r[3:].strip() + '&_format=json')
            if 'data' in raw_res:
                feedback = (f"Here is the response from the GET request:\n{raw_res['data']}. "
                            "Please call FINISH if you have got answers for all the questions "
                            "and finished all the requested tasks")
            else:
                feedback = f"Error in sending the GET request: {raw_res['error']}"
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": feedback})

        elif r.startswith('POST'):
            lines = r.split('\n')
            post_url = lines[0][4:].strip()
            try:
                payload = json.loads('\n'.join(lines[1:]))
                fhir_tools.log_post(post_url, payload)
                feedback = ("POST request accepted and executed successfully. "
                            "Please call FINISH if you have got answers for all the questions "
                            "and finished all the requested tasks")
            except Exception:
                feedback = "Invalid POST request"
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": feedback})

        elif r.startswith('FINISH('):
            try:
                answers = json.loads(r[len('FINISH('):-1])
                if not isinstance(answers, list):
                    answers = [answers]
            except (json.JSONDecodeError, TypeError):
                answers = [r[len('FINISH('):-1]]
            record.record(func='solve_medical_task', args=(instruction, context),
                          kw={}, output=answers, stats=total_stats,
                          step_info={'rounds': round_idx + 1})
            return answers
        else:
            break

    record.record(func='solve_medical_task', args=(instruction, context),
                  kw={}, output='**max rounds reached**', stats=total_stats,
                  step_info={'rounds': max_round, 'status': 'TASK_LIMIT_REACHED'})
    return []


# ──────────────────────────────────────────────────────────────────────
# L3: CodeAct — iterative code generation with error feedback
# ──────────────────────────────────────────────────────────────────────

def codeact_loop(instruction: str, context: str) -> list:
    """CodeAct: generate code, execute, re-prompt with errors, up to 8 passes."""
    import re as re_mod
    from smolagents.local_python_executor import LocalPythonExecutor, BASE_PYTHON_TOOLS

    model = config.require('llm.model')
    max_passes = int(config.get('fhir.max_round', 8))
    max_tokens = int(config.get('llm.max_tokens', 4096))
    fhir_base = config.get('fhir.api_base', 'http://localhost:8080/fhir/')

    executor = LocalPythonExecutor(additional_authorized_imports=['json', 're'])
    executor.custom_tools = {
        'fhir_get': fhir_tools.fhir_get,
        'fhir_post': fhir_tools.fhir_post,
        'instruction': instruction, 'context': context,
    }
    executor.static_tools = {**BASE_PYTHON_TOOLS, 'final_answer': lambda x: x}

    funcs = json.loads((_TEMPLATE_DIR.parent / 'data' / 'funcs_v1.json').read_text())
    prompt = _load_template('codeact.txt').format(
        api_base=fhir_base, functions=json.dumps(funcs),
        context=_extract_task_context(context), question=instruction)
    messages = [{"role": "user", "content": prompt}]
    total_stats = dict(input_tokens=0, output_tokens=0, latency=0.0, cost=0.0)

    for attempt in range(max_passes):
        raw, stats = _llm_call(model, messages, max_tokens, f'codeact (pass {attempt})')
        _accumulate_stats(total_stats, stats)

        match = re_mod.search(r'```python\n(.*?)\n```', raw, re_mod.DOTALL)
        if not match:
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content":
                "No ```python``` code block found. Please output ONLY a ```python``` code block."})
            continue

        code = match.group(1)
        try:
            result = executor(code)
            answer = result.output
            if not isinstance(answer, list):
                answer = [answer]
            record.record(func='solve_medical_task', args=(instruction, context),
                          kw={}, output=answer, stats=total_stats,
                          step_info={'passes': attempt + 1, 'code': code})
            return answer
        except Exception as ex:
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content":
                f"Code execution error:\n{ex}\n\nFix the code and try again."})

    record.record(func='solve_medical_task', args=(instruction, context),
                  kw={}, output='**max passes reached**', stats=total_stats,
                  step_info={'passes': max_passes, 'status': 'EXHAUSTED'})
    return []
