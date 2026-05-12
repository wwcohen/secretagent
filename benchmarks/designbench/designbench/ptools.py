"""Interfaces for DesignBench code generation."""

import base64
import re
import tempfile
from pathlib import Path

from secretagent.core import interface

from eval_util import render_to_screenshot


@interface
def generate_code(reference_html: str, framework: str, metadata: dict) -> str:
    """You are an expert HTML/CSS developer.
    You take screenshots of a reference web page from the user, and then build single page apps.

    - Make sure the app looks exactly like the screenshot.
    - Pay close attention to background color, text color, font size, font family, padding, margin, border, etc. Match the colors and sizes exactly.
    - Use the exact text from the screenshot.
    - Do not add placeholder comments in place of real code. Write the full code.
    - Repeat elements as needed to match the screenshot.
    - For images, use placeholder images from https://placehold.co and include detailed alt text.

    Please return code inside a markdown code block appropriate for `framework`.
    Do not output any extra information or comments.
    """


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

    return text.strip()


def extract_code(response: str, framework: str) -> str:
    """Extract code block from model output."""
    return _extract_code_block(response, framework)


def render_generated_image(
    code: str,
    framework: str,
    react_images: dict | None = None,
) -> dict:
    """Render code and return a base64 screenshot for ReAct VLM steps."""
    ext = {
        'vanilla': 'html',
        'react': 'jsx',
        'vue': 'vue',
        'angular': 'html',
    }.get(framework, 'html')
    with tempfile.TemporaryDirectory(prefix='designbench_react_') as tmp_dir:
        code_path = Path(tmp_dir) / f'candidate.{ext}'
        screenshot_path = Path(tmp_dir) / 'candidate.png'
        code_path.write_text(code, encoding='utf-8')
        rendered = render_to_screenshot(
            code_path=str(code_path),
            save_path=str(screenshot_path),
            framework=framework,
        )
        if not rendered or not screenshot_path.exists():
            return {'status': 'render_failed', 'react_images': {}}
        encoded = base64.b64encode(screenshot_path.read_bytes()).decode('ascii')
        result_images = dict(react_images or {})
        result_images['generated'] = encoded
        return {
            'status': 'ok',
            'generated_image_bytes': screenshot_path.stat().st_size,
            'react_images': {'generated': encoded},
            'available_images': sorted(result_images.keys()),
        }


def fix_code_from_rendered_and_reference(
    current_code: str,
    framework: str,
    metadata: dict,
) -> str:
    """You are an expert frontend developer.
    You are given the current code, metadata, and screenshots from tools.

    - Compare the generated render against the golden reference screenshot.
    - Match the reference exactly: layout, spacing, sizing, text, colors, typography, borders, and alignment.
    - Fix only the parts that mismatch; keep already-correct parts unchanged.
    - Always return the full corrected code, not a diff or partial snippet.
    - Return only updated code for `framework` inside a markdown code block.
    """
