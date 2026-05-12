"""Utility helpers for DesignBench rendering and visual metrics."""

from pathlib import Path
from typing import Dict


def render_to_screenshot(code_path: str, save_path: str, framework: str) -> bool:
    """Render source code into a screenshot with DesignBench evaluator tools."""
    try:
        from metric_utils import render_ui  # type: ignore
    except ImportError as ex:
        raise ImportError(
            'Cannot import DesignBench metric_utils.render_ui. '
            'Set DESIGNBENCH_ROOT to the local DesignBench repository.'
        ) from ex

    result = render_ui(code_path=code_path, save_path=save_path, frame_work=framework)
    return result is True or Path(save_path).exists()


def evaluate_visual(reference_img: str, generated_img: str) -> Dict[str, float]:
    """Compute MAE/CLIP/SSIM between reference and generated screenshots."""
    try:
        from metric import mae_score, clip_similarity, ssim_similarity  # type: ignore
        from PIL import Image
    except ImportError as ex:
        raise ImportError(
            'Cannot import DesignBench metric functions or PIL. '
            'Install evaluator dependencies first.'
        ) from ex

    ref = Image.open(reference_img)
    gen = Image.open(generated_img)
    return {
        'mae': float(mae_score(ref, gen)),
        'clip_similarity': float(clip_similarity(reference_img, generated_img)),
        'ssim': float(ssim_similarity(reference_img, generated_img)),
    }
