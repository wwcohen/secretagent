import os
import pathlib
import time

from typing import Any

from pydantic import Field
from together import Together

from secretagent import config, record
from secretagent.core import register_factory
from secretagent.implement.core import SimulateFactory

# Together pricing in USD per 1M tokens: (input, output)
# Keep this intentionally small and explicit for current benchmark usage.
_TOGETHER_PRICE_PER_MTOKENS: dict[str, tuple[float, float]] = {
    'Qwen/Qwen3.5-9B': (0.10, 0.15),
}
_DEFAULT_VLM_SYSTEM_PROMPT = 'You are an expert frontend developer.'


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


def create_vlm_messages(
    prompt: str,
    images: dict[str, Any] | None = None,
    system_prompt: str = '',
) -> list[dict[str, Any]]:
    if images:
        content_parts = []
        for _, image_url in images.items():
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{image_url}"},
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


def _call_vlm_impl(
    messages: list[dict[str, Any]],
    output_mode: str = 'answer_tag',
) -> tuple[str, dict[str, float]]:
    start_time = time.time()
    model_name = config.get('vlm.model') or config.require('llm.model')
    together_client = Together(api_key=os.environ['TOGETHER_API_KEY'])
    timeout_seconds = config.get('vlm.timeout_seconds', 120)
    max_retries = int(config.get('vlm.retries', 5) or 5)
    retry_sleep_seconds = float(config.get('vlm.retry_sleep_seconds', 1.0) or 1.0)
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
    return raw_content, stats


def call_vlm(
    messages: list[dict[str, Any]],
    output_mode: str = 'answer_tag',
) -> tuple[str, dict[str, float]]:
    """Use a VLM model."""
    # return cached(_call_vlm_impl)(messages, output_mode)
    return _call_vlm_impl(messages, output_mode)


class ImplementVLMFactory(SimulateFactory):
    """Implement an Interface using a VLM."""
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

    def __call__(self, *args, **call_kw):
        interface = self.bound_interface
        run_kw = dict(call_kw)
        call_images = run_kw.pop('images', None)
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
        if prompt_mode == 'docstring':
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
        else:
            prompt = self.create_prompt(interface, *args, examples=examples, **kw)
            system_prompt = ''

        return create_vlm_messages(prompt=prompt, images=images, system_prompt=system_prompt)


register_factory('vlm', ImplementVLMFactory())
