import copy
import json
import os
import pathlib
import re
import time

from typing import Any

from pydantic import Field
from together import Together

from secretagent import config, record
from secretagent.core import register_factory
from secretagent.implement.core import SimulateFactory
from secretagent.implement.util import load_template
from secretagent.llm_util import _default_max_tokens, echo_boxed

# Together pricing in USD per 1M tokens: (input, output)
# Keep this intentionally small and explicit for current benchmark usage.
_TOGETHER_PRICE_PER_MTOKENS: dict[str, tuple[float, float]] = {
    'Qwen/Qwen3.5-9B': (0.10, 0.15),
}
_DEFAULT_VLM_SYSTEM_PROMPT = 'You are an expert frontend developer.'


def _strip_answer_tags_vlm(text: str) -> str:
    """Remove ``<answer>`` / ``</answer>`` wrapper when the model omits the closing tag."""
    t = text.strip()
    if re.match(r'(?is)^<answer>', t):
        t = re.sub(r'(?is)^<answer>\s*', '', t, count=1)
        t = re.sub(r'(?is)\s*</answer>\s*$', '', t).strip()
    return t


def _scrub_vlm_messages_for_echo(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deep-copy messages for logging: keep all text; redact base64 in image URLs only."""
    scrubbed: list[dict[str, Any]] = copy.deepcopy(messages)
    for msg in scrubbed:
        content = msg.get('content')
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict) or part.get('type') != 'image_url':
                continue
            iu = part.get('image_url')
            if not isinstance(iu, dict):
                continue
            url = iu.get('url') or ''
            if 'base64,' in url:
                pre, _, b64 = url.partition('base64,')
                iu['url'] = f'{pre}base64,<{len(b64)} base64 chars elided>'
            elif len(url) > 400:
                iu['url'] = f'<image url, {len(url)} chars elided>'
    return scrubbed


def _format_vlm_messages_for_echo(messages: list[dict[str, Any]]) -> str:
    """Full model input as JSON (images redacted)."""
    try:
        return json.dumps(
            _scrub_vlm_messages_for_echo(messages),
            indent=2,
            ensure_ascii=False,
        )
    except (TypeError, ValueError):
        return repr(messages)


def _normalize_together_model_name(model_name: str) -> str:
    return model_name.removeprefix('together_ai/')


def _estimate_together_cost_usd(
    model_name: str,
    input_tokens: float,
    output_tokens: float,
) -> float:
    model_id = _normalize_together_model_name(model_name)
    rates = _TOGETHER_PRICE_PER_MTOKENS.get(model_id)
    if rates is None:
        return 0.0
    input_rate, output_rate = rates
    # Together pricing metadata is expressed in USD per 1M tokens.
    return (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000.0


def _vlm_resolved_model() -> str:
    return str(config.get('vlm.model') or config.require('llm.model'))


def _vlm_use_gemini(model_name: str) -> bool:
    """Gemini path when ``vlm.provider: gemini`` or model id is litellm-style ``gemini/...``."""
    prov = (config.get('vlm.provider') or '').strip().lower()
    if prov == 'gemini':
        return True
    return model_name.strip().lower().startswith('gemini/')


def _ordered_vlm_image_slots(images: dict[str, Any]) -> list[tuple[str, str]]:
    """Stable VLM labels and order: reference first, rendered second; no base64 merging.

    Accepts benchmark keys ``reference_screenshot`` / ``generated_screenshot`` (or
    ``rendered_screenshot``) or the canonical names ``reference_image`` /
    ``rendered_image``. Any other keys are
    appended after, sorted, each as its own separate ``image_url`` part.
    """
    out: list[tuple[str, str]] = []
    used: set[str] = set()

    def take(label: str, *source_keys: str) -> None:
        for k in source_keys:
            if k not in images:
                continue
            val = images[k]
            if val is None or val == '':
                continue
            out.append((label, str(val)))
            used.add(k)
            return

    take('reference_image', 'reference_screenshot', 'reference_image')
    take(
        'rendered_image',
        'generated_screenshot',
        'rendered_screenshot',
        'rendered_image',
    )

    for k in sorted(images.keys()):
        if k in used:
            continue
        val = images[k]
        if val is None or val == '':
            continue
        out.append((k, str(val)))

    return out


def create_vlm_messages(
    prompt: str,
    images: dict[str, Any] | None = None,
    system_prompt: str = '',
) -> list[dict[str, Any]]:
    if images:
        content_parts = []
        slots = _ordered_vlm_image_slots(images)
        key_order = ', '.join(label for label, _ in slots)
        content_parts.append({
            'type': 'text',
            'text': f'[Multimodal images attached in order: {key_order}]\n',
        })
        for slot_label, b64_payload in slots:
            content_parts.append({
                'type': 'text',
                'text': f'[Image: {slot_label}]\n',
            })
            content_parts.append({
                'type': 'image_url',
                'image_url': {'url': f'data:image/png;base64,{b64_payload}'},
            })
        content_parts.append({
            "type": "text",
            "text": prompt,
        })
        if system_prompt:
            return [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content_parts},
            ]
        return [{"role": "user", "content": content_parts}]

    if system_prompt:
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
    return [{"role": "user", "content": prompt}]


def _call_vlm_gemini(
    messages: list[dict[str, Any]],
    model_name: str,
    start_time: float,
    timeout_seconds: float | None,
    max_retries: int,
    retry_sleep_seconds: float,
) -> tuple[str, dict[str, float]]:
    """Vision-capable Gemini via litellm (uses ``GEMINI_API_KEY``)."""
    from litellm import completion, completion_cost

    if not os.environ.get('GEMINI_API_KEY'):
        raise RuntimeError(
            'GEMINI_API_KEY is not set. Required for Gemini VLM '
            '(vlm.provider=gemini or llm.model like gemini/gemini-2.0-flash).'
        )

    extra_kw: dict[str, Any] = {}
    if timeout_seconds:
        extra_kw['timeout'] = float(timeout_seconds)
    mt = config.get('vlm.max_tokens')
    if mt is not None:
        extra_kw['max_tokens'] = int(mt)
    else:
        default_mt = _default_max_tokens(model_name)
        if default_mt is not None:
            extra_kw['max_tokens'] = int(default_mt)
    if config.get('vlm.temperature') is not None:
        extra_kw['temperature'] = float(config.get('vlm.temperature'))

    response = None
    last_error: BaseException | None = None
    attempts_used = 0
    for attempt in range(1, max_retries + 1):
        attempts_used = attempt
        try:
            response = completion(model=model_name, messages=messages, **extra_kw)
            break
        except Exception as ex:
            last_error = ex
            if attempt < max_retries:
                print(
                    f'[vlm/gemini] request failed attempt {attempt}/{max_retries}: '
                    f'{type(ex).__name__}: {ex}',
                    flush=True,
                )
                time.sleep(retry_sleep_seconds)
    if response is None:
        raise RuntimeError(
            f'Gemini VLM request failed after {max_retries} attempts: '
            f'{type(last_error).__name__}: {last_error}'
        ) from last_error

    usage = getattr(response, 'usage', None)
    input_tokens = float(getattr(usage, 'prompt_tokens', 0) or 0)
    output_tokens = float(getattr(usage, 'completion_tokens', 0) or 0)
    try:
        cost = float(completion_cost(completion_response=response))
    except Exception:
        cost = 0.0
    stats = {
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'latency': time.time() - start_time,
        'cost': cost,
        'retries': float(max(0, attempts_used - 1)),
    }
    msg = response.choices[0].message
    content = getattr(msg, 'content', None)
    reasoning = getattr(msg, 'reasoning_content', None)
    raw_content = str(content if content else (reasoning or ''))
    if config.get('echo.llm_output'):
        echo_boxed(raw_content, 'vlm_output')
    return raw_content, stats


def _call_vlm_impl(
    messages: list[dict[str, Any]],
    output_mode: str = 'answer_tag',
) -> tuple[str, dict[str, float]]:
    start_time = time.time()
    model_name = _vlm_resolved_model()
    if config.get('echo.model'):
        print(f'calling VLM model {model_name}', flush=True)
    if config.get('echo.llm_input'):
        echo_boxed(_format_vlm_messages_for_echo(messages), 'vlm_input')
    timeout_seconds = config.get('vlm.timeout_seconds', 120)
    max_retries = int(config.get('vlm.retries', 5) or 5)
    retry_sleep_seconds = float(config.get('vlm.retry_sleep_seconds', 1.0) or 1.0)

    if _vlm_use_gemini(model_name):
        return _call_vlm_gemini(
            messages,
            model_name,
            start_time,
            float(timeout_seconds) if timeout_seconds else 0.0,
            max_retries,
            retry_sleep_seconds,
        )

    together_key = os.environ.get('TOGETHER_API_KEY')
    if not together_key:
        raise RuntimeError(
            'TOGETHER_API_KEY is not set. For Gemini Flash, set GEMINI_API_KEY and use '
            "llm.model: gemini/gemini-2.0-flash (or vlm.provider: gemini)."
        )
    together_client = Together(api_key=together_key)
    response = None
    last_error = None
    attempts_used = 0
    for attempt in range(1, max_retries + 1):
        attempts_used = attempt
        request_kw = {
            'model': model_name,
            'max_tokens': int(config.get('vlm.max_tokens') or 2048),
            'messages': messages,
        }
        temperature = config.get('vlm.temperature')
        if temperature is not None:
            request_kw['temperature'] = float(temperature)
        # Keep model output in `content` unless explicitly enabled.
        request_kw['chat_template_kwargs'] = {
            'enable_thinking': bool(config.get('vlm.enable_thinking', False))
        }
        if timeout_seconds:
            request_kw['timeout'] = float(timeout_seconds)
        try:
            response = together_client.chat.completions.create(**request_kw)
            break
        except TypeError as ex:
            # Backward compatibility for SDK versions that do not accept some kwargs.
            ex_text = str(ex)
            if 'chat_template_kwargs' in request_kw and 'chat_template_kwargs' in ex_text:
                request_kw.pop('chat_template_kwargs', None)
                response = together_client.chat.completions.create(**request_kw)
                break
            if 'timeout' in request_kw and 'timeout' in ex_text:
                request_kw.pop('timeout', None)
                response = together_client.chat.completions.create(**request_kw)
                break
            last_error = ex
        except Exception as ex:
            last_error = ex
            if attempt < max_retries:
                print(
                    f'[vlm] request failed attempt {attempt}/{max_retries}: {type(ex).__name__}: {ex}',
                    flush=True,
                )
                time.sleep(retry_sleep_seconds)
    if response is None:
        raise RuntimeError(
            f'VLM request failed after {max_retries} attempts: {type(last_error).__name__}: {last_error}'
        ) from last_error
    usage = getattr(response, 'usage', None)
    input_tokens = float(getattr(usage, 'prompt_tokens', 0) or 0)
    output_tokens = float(getattr(usage, 'completion_tokens', 0) or 0)
    cost = _estimate_together_cost_usd(
        model_name=model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    stats = {
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'latency': time.time() - start_time,
        'cost': cost,
        'retries': float(max(0, attempts_used - 1)),
    }
    msg = response.choices[0].message
    content = getattr(msg, 'content', None)
    reasoning = getattr(msg, 'reasoning_content', None)
    raw_content = str(content if content else (reasoning or ''))
    if config.get('echo.llm_output'):
        echo_boxed(raw_content, 'vlm_output')
    return raw_content, stats


def call_vlm(
    messages: list[dict[str, Any]],
    output_mode: str = 'answer_tag',
) -> tuple[str, dict[str, float]]:
    """Use a VLM model."""
    # return cached(_call_vlm_impl)(messages, output_mode)
    return _call_vlm_impl(messages, output_mode)


class ImplementVLMFactory(SimulateFactory):
    """Implement an Interface using a VLM.

    Two prompt shapes (``prompt_mode`` in config):

    1. **Unstructured baseline** — ``prompt_mode`` ``docstring`` or ``unstructured``.
       User message is built from ``interface.doc`` (set your stub docstring in YAML or
       code), optional ``Target framework:``, and optional ``user_text``. No
       ``simulate_pydantic.txt`` template.

    2. **Structured (SimulateFactory-style)** — ``prompt_mode`` ``simulate`` or
       ``structured``. User message uses ``simulate_pydantic.txt`` via
       :meth:`create_prompt` (maps ``$args`` to ``interface.format_args`` output).
       ``system_prompt`` is empty for that message.
    """
    examples_cases: list | None = None
    default_images: dict[str, Any] | None = None
    output_mode: str = 'answer_tag'
    prompt_mode: str = 'simulate'
    user_text: str | None = None
    prompt_kw: dict = Field(default_factory=dict)

    def setup(
        self,
        example_file=None,
        images=None,
        output_mode: str = 'answer_tag',
        prompt_mode: str = 'simulate',
        user_text: str | None = None,
        **prompt_kw,
    ):
        self.prompt_kw = prompt_kw
        self.default_images = images
        self.output_mode = output_mode
        self.prompt_mode = prompt_mode
        self.user_text = user_text
        self.examples_cases = None
        if example_file:
            import json
            data = json.loads(pathlib.Path(example_file).read_text())
            self.examples_cases = data.get(self.bound_interface.name, [])

    def create_prompt(self, interface, *args, examples=None, **kw):
        """``simulate_pydantic.txt`` uses ``$args``; :class:`SimulateFactory` passes ``input_args``."""
        template = load_template('simulate_pydantic.txt')
        input_args = interface.format_args(*args, **kw)
        if not input_args.strip():
            raise ValueError(f'input_args null for {args=} {kw=}')
        return template.substitute(
            dict(stub_src=interface.src, args=input_args),
        )

    def __call__(self, *args, **call_kw):
        interface = self.bound_interface
        run_kw = dict(call_kw)
        call_images = run_kw.pop('images', None)
        react_only = run_kw.pop('react_images', None)
        if call_images is None:
            call_images = react_only
        merged_images = call_images if call_images is not None else self.default_images
        with config.configuration(**self.prompt_kw):
            messages = self.create_vlm_prompt(
                interface,
                *args,
                images=merged_images,
                examples=self.examples_cases,
                prompt_mode=self.prompt_mode,
                user_text=self.user_text,
                **run_kw,
            )
            raw_output, stats = call_vlm(messages=messages, output_mode=self.output_mode)
            if self.output_mode == 'freeform':
                output = raw_output
            else:
                output = self.parse_output(str, raw_output)
                output = _strip_answer_tags_vlm(str(output))
            record.record(
                func=interface.name,
                args=args,
                kw=run_kw,
                output=output,
                stats=stats,
            )
            return output

    def create_vlm_prompt(
        self,
        interface,
        *args,
        images: dict[str, Any] | None = None,
        examples=None,
        prompt_mode: str = 'simulate',
        user_text: str | None = None,
        **kw,
    ) -> list[dict[str, Any]]:
        # --- Type 1: unstructured baseline (no simulate_pydantic.txt) ---
        if prompt_mode in ('docstring', 'unstructured'):
            arg_names = list(interface.annotations.keys())[:-1]
            arg_dict = dict(zip(arg_names, args))
            arg_dict.update(kw)
            framework = arg_dict.get('framework')
            prompt = (interface.doc or '').strip()
            if framework:
                prompt = f'{prompt}\n\nTarget framework: {framework}'
            if user_text:
                prompt = f'{prompt}\n\n{user_text}'
            system_prompt = config.get('vlm.system_prompt') or _DEFAULT_VLM_SYSTEM_PROMPT
            return create_vlm_messages(
                prompt=prompt, images=images, system_prompt=system_prompt)

        # --- Type 2: structured — SimulateFactory.create_prompt → simulate_pydantic.txt ---
        # ``simulate``, ``structured``, or any other value (historical default).
        prompt = self.create_prompt(interface, *args, examples=examples, **kw)
        system_prompt = ''
        return create_vlm_messages(prompt=prompt, images=images, system_prompt=system_prompt)


register_factory('vlm', ImplementVLMFactory())
