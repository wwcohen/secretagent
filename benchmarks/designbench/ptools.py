"""Interfaces for DesignBench code generation.

Screen-to-code: VLMs get PNG/JPEG bytes in ``input_kw['images']`` under keys that
match the screenshot parameters on each interface (e.g. ``reference_screenshot``).
Those string parameters are always ``""`` here so prompts never embed base64;
golden HTML is never passed to the model.
"""

import base64
import re
import tempfile
from pathlib import Path

from secretagent.core import interface
from secretagent import config
from secretagent.implement.code_transport import decode_transport_layers, encode_transport
from secretagent.llm_util import echo_boxed

from eval_util import render_to_screenshot


@interface
def generate_code(framework: str, reference_screenshot: str) -> str:
    """Screen-to-code for ``framework``; reference pixels in ``images['reference_screenshot']`` only.

    At run time, ``benchmarks/designbench/expt.py`` replaces this docstring with
    ``get_design_generation_prompt`` from the DesignBench repo (vanilla / react / vue / …).
    """
    ...


@interface
def propose_code(framework: str, reference_screenshot: str) -> str:
    """Same contract as ``generate_code`` (initial proposal in refine and ReAct flows).

    At run time, ``expt._set_designbench_generate_code_doc`` injects the DesignBench
    ``get_design_generation_prompt`` text for the active stack.
    """
    ...


def _extract_code_block(text: str, framework: str) -> str:
    fence_map = {
        'vanilla': 'html',
        'react': 'jsx',
        'vue': 'vue',
        'angular': 'angular',
    }
    lang = fence_map.get(framework, 'html')

    match = re.search(rf"```{lang}\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    match = re.search(r"```\w*\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Token/truncation limits often drop the closing ```; strip an opening fence only.
    stripped = text.strip()
    open_lang = re.match(rf"(?i)^```{re.escape(lang)}\s*\n", stripped)
    if open_lang:
        return stripped[open_lang.end() :].strip()
    open_any = re.match(r"^```\w*\s*\n", stripped)
    if open_any:
        return stripped[open_any.end() :].strip()

    return stripped


def extract_code(response: str, framework: str) -> str:
    """Extract code block from model output."""
    return _extract_code_block(response, framework)


# Angular 17+ treats ``@name`` in templates as control-flow / block syntax. Literal
# npm scopes like ``@angular/cli`` must use ``&#64;`` or the compiler raises NG5002.
_NPM_SCOPE_IN_TEXT = re.compile(r'@([\w.-]+)/([\w.-]+)')
# Model HTML often uses *ngFor over ad hoc fields; the shell NewComponent has no
# typings. ``$any(this).name`` opts those expressions out of strict template checks.
_NGFOR_OF_SIMPLE = re.compile(
    r'(\*ngFor="let \w+ of\s+)(?!\$any\()(\w+)((?:;[^"]*)?")',
)

# VLM may emit this alone on line 1 to exit ``propose_then_refine_loop`` before ``refine_rounds``.
_REFINE_DONE_PREFIX = re.compile(r'(?is)^\s*REFINE_DONE\s*(?:\n\s*|\Z)')


def _strip_refine_done_signal(text: str) -> tuple[str, bool]:
    m = _REFINE_DONE_PREFIX.match(text)
    if not m:
        return text, False
    return text[m.end() :], True


def _echo_refine_io_summary(
    phase: str,
    raw_llm_text: str,
    extracted: str,
    framework: str,
) -> None:
    """When ``echo.llm_input`` / ``echo.llm_output`` are on, print fence + length stats (VLM echoes full I/O separately)."""
    if not (config.get('echo.llm_input') or config.get('echo.llm_output')):
        return
    rs = raw_llm_text.rstrip()
    fence_at_eof = rs.endswith('```')
    tail = raw_llm_text[-400:] if len(raw_llm_text) > 400 else raw_llm_text
    echo_boxed(
        f'{phase}  framework={framework!r}\n'
        f'raw_llm_chars={len(raw_llm_text)}  extracted_code_chars={len(extracted)}\n'
        f'raw_rstrip_ends_with_closing_fence={fence_at_eof}\n'
        f'If False, the model often hit max_tokens and HTML in artifacts will look cut off.\n'
        f'raw_tail_repr (last 400 chars):\n{tail!r}\n',
        'designbench_refine_io',
    )


def prepare_code_for_render(code: str, framework: str) -> str:
    """Normalize generated source before DesignBench render (framework-specific)."""
    if framework != 'angular':
        return code
    code = _NPM_SCOPE_IN_TEXT.sub(r'&#64;\1/\2', code)
    return _NGFOR_OF_SIMPLE.sub(r'\1$any(this).\2\3', code)


def _render_generated_image_code(
    code: str,
    framework: str,
    react_images: dict | None = None,
) -> dict:
    """Render ``code`` for ``framework``; JSON includes ``react_images['generated_screenshot']`` (base64) merged with any prior ``react_images`` (e.g. ``reference_screenshot``)."""
    code = decode_transport_layers(code)
    print(
        '\n'
        '+==============================================================================+\n'
        '|  DESIGNBENCH  render_generated_image  >>>  LOCAL SCREENSHOT (not LLM)      |\n'
        '+------------------------------------------------------------------------------+\n'
        f'|  framework={framework!r}  code_chars={len(code)}  '
        f'prior_image_keys={sorted((react_images or {}).keys())!r}\n'
        '+==============================================================================+\n',
        flush=True,
    )
    ext = {
        'vanilla': 'html',
        'react': 'jsx',
        'vue': 'vue',
        'angular': 'html',
    }.get(framework, 'html')
    with tempfile.TemporaryDirectory(prefix='designbench_react_') as tmp_dir:
        code_path = Path(tmp_dir) / f'candidate.{ext}'
        screenshot_path = Path(tmp_dir) / 'candidate.png'
        code_path.write_text(prepare_code_for_render(code, framework), encoding='utf-8')
        rendered = render_to_screenshot(
            code_path=str(code_path),
            save_path=str(screenshot_path),
            framework=framework,
        )
        if not rendered or not screenshot_path.exists():
            print(
                '|  DESIGNBENCH  render_generated_image  <<<  FAILED (no PNG written)         |\n'
                '+==============================================================================+\n',
                flush=True,
            )
            return {
                'status': 'render_failed',
                'react_images': dict(react_images or {}),
            }
        encoded = base64.b64encode(screenshot_path.read_bytes()).decode('ascii')
        result_images = dict(react_images or {})
        result_images['generated_screenshot'] = encoded
        nbytes = screenshot_path.stat().st_size
        print(
            f'|  DESIGNBENCH  render_generated_image  <<<  OK  PNG_bytes={nbytes}  '
            f'keys_out={sorted(result_images.keys())!r}\n'
            '+==============================================================================+\n',
            flush=True,
        )
        # Return the full merged map so ReAct / logs show both reference and generated.
        return {
            'status': 'ok',
            'generated_image_bytes': nbytes,
            'react_images': dict(result_images),
            'available_images': sorted(result_images.keys()),
        }


@interface
def render_generated_image(
    code: str,
    framework: str,
    react_images: dict | None = None,
) -> dict:
    """ReAct JSON: ``code`` is standard base64 of UTF-8 source (not raw HTML in JSON); ``framework`` is plain (e.g. vanilla); returns ``status`` and ``react_images`` with ``generated_screenshot`` merged."""
    return _render_generated_image_code(code, framework, react_images)


@interface
def fix_code_from_rendered_and_reference(
    current_code: str,
    framework: str,
    reference_screenshot: str,
    generated_screenshot: str,
    react_images: dict | None = None,
) -> str:
    """ReAct JSON: ``current_code`` is standard base64 of UTF-8 source; screenshot string args ``""``; ``react_images`` mirrors ``images``; returns full fenced ``framework`` source vs reference vs generated screenshots.

    Expert frontend developer: compare generated render to the golden reference.

    - Compare the generated render against the golden reference screenshot.
    - Match the reference exactly: layout, spacing, sizing, text, colors, typography, borders, and alignment.
    - Fix only the parts that mismatch; keep already-correct parts unchanged.
    - Always return the full corrected code, not a diff or partial snippet.
    - Return only updated code for `framework` inside a markdown code block.
    - If the render already matches the reference and no edits are needed, put the line ``REFINE_DONE`` at the very start of your message, then the full code in a markdown fence (may be unchanged).
    """
    ...


# ── fixed refine workflow (``generate_code`` via ``method: direct``, ``fn: ptools....``) ──


def propose_then_refine_loop(
    framework: str,
    reference_screenshot: str,
    *,
    images: dict | None = None,
    **kwargs: object,
) -> str:
    """Propose once, then up to ``benchmark.refine_rounds`` × (render → VLM fix).

    Same pattern as other benchmarks: orchestration lives in ``ptools`` and is
    bound with ``ptools.generate_code.method=direct`` / ``fn: ptools.propose_then_refine_loop``.

    Steps:

    1. ``propose_code``
    2. Loop (default 20, stops early): ``render_generated_image`` (local PNG) then
       ``fix_code_from_rendered_and_reference`` (VLM) with
       ``react_images`` containing ``reference_screenshot`` and
       ``generated_screenshot`` (the render just produced). The loop ends when the
       fixer starts with ``REFINE_DONE``, when extracted code is unchanged from the
       prior iteration, on render failure, or when ``refine_rounds`` is reached.
    """
    del kwargs
    images = dict(images or {})
    rounds = int(config.get('benchmark.refine_rounds', 20))

    draft = propose_code(framework, reference_screenshot, images=images)
    code = extract_code(draft, framework)
    last_text = draft
    _echo_refine_io_summary('propose_code (after VLM)', draft, code, framework)
    if not code.strip():
        return last_text

    react_images = dict(images)
    for round_i in range(rounds):
        enc = encode_transport(code)
        render_out = render_generated_image(
            enc, framework, react_images=react_images
        )
        if not isinstance(render_out, dict) or render_out.get('status') != 'ok':
            break
        merged = render_out.get('react_images')
        if isinstance(merged, dict):
            react_images = dict(merged)

        ref_b64 = react_images.get('reference_screenshot')
        rendered_b64 = react_images.get('generated_screenshot')
        if not (
            isinstance(ref_b64, str)
            and ref_b64.strip()
            and isinstance(rendered_b64, str)
            and rendered_b64.strip()
        ):
            break
        fix_images = {
            'reference_screenshot': ref_b64,
            'generated_screenshot': rendered_b64,
        }

        fixed = fix_code_from_rendered_and_reference(
            enc,
            framework,
            '',
            '',
            react_images=fix_images,
        )
        fixed_body, done = _strip_refine_done_signal(fixed)
        last_text = fixed_body
        new_code = extract_code(fixed_body, framework)
        _echo_refine_io_summary(
            f'fix_code_from_rendered_and_reference (after VLM, round {round_i + 1}/{rounds})',
            fixed_body,
            new_code,
            framework,
        )
        if done:
            code = new_code
            break
        if new_code.strip() == code.strip():
            code = new_code
            break
        code = new_code
        if not code.strip():
            break

    return last_text
