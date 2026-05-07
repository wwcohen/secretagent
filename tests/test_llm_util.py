"""Tests for ``echo_boxed`` in ``secretagent.llm_util``.

The box renderer has three jobs:
  1. Put a tagged frame around arbitrary text.
  2. Wrap lines that are wider than ``echo.box_width`` (or, when that is
     unset/zero, the current terminal width).
  3. Preserve the input's existing newline structure — the old
     implementation called ``textwrap.fill`` on the whole string which
     collapsed embedded newlines into spaces.

The tests below exercise each job in isolation and check every edge case
we have reason to care about: empty input, all-blank input, boundary
widths, leading/trailing/consecutive blank lines, mixed short/long
lines, structured (JSON-like) content, unicode content, tag variants,
and the terminal-width auto-detection path.
"""

import json
import os

import pytest
from omegaconf import OmegaConf

from secretagent import config
from secretagent.llm_util import echo_boxed


# --- fixtures ---

@pytest.fixture(autouse=True)
def reset_global_config():
    config.GLOBAL_CONFIG = OmegaConf.create()
    yield
    config.GLOBAL_CONFIG = OmegaConf.create()


@pytest.fixture
def pin_terminal_width(monkeypatch):
    """Pin ``shutil.get_terminal_size`` so width-default tests are deterministic."""
    def _pin(columns=120, lines=24):
        monkeypatch.setattr(
            'secretagent.llm_util.shutil.get_terminal_size',
            lambda fallback=(120, 24): os.terminal_size((columns, lines)),
        )
    return _pin


# --- helpers ---

def _rows(captured: str) -> list[str]:
    return captured.splitlines()


def _content_lines(captured: str) -> list[str]:
    """Return the inner content rows with frame + right padding removed."""
    rows = _rows(captured)
    assert rows, 'expected at least top and bottom frame rows'
    assert rows[0].startswith('┌') and rows[0].endswith('┐'), rows[0]
    assert rows[-1].startswith('└') and rows[-1].endswith('┘'), rows[-1]
    out = []
    for row in rows[1:-1]:
        assert row.startswith('│ ') and row.endswith(' │'), row
        out.append(row[2:-2].rstrip())
    return out


def _padded_content_lines(captured: str) -> list[str]:
    """Content rows without rstrip — used to verify every row is padded to the same width."""
    rows = _rows(captured)
    out = []
    for row in rows[1:-1]:
        assert row.startswith('│ ') and row.endswith(' │'), row
        out.append(row[2:-2])
    return out


# --- geometry: frame integrity ---

def test_frame_characters_and_alignment(capsys, pin_terminal_width):
    pin_terminal_width()
    echo_boxed('alpha', 'tag')
    rows = _rows(capsys.readouterr().out)
    # three rows: top, one content, bottom
    assert len(rows) == 3
    top, body, bot = rows
    # frames have matching length
    assert len(top) == len(body) == len(bot)
    # frame chars at corners
    assert top[0] == '┌' and top[-1] == '┐'
    assert bot[0] == '└' and bot[-1] == '┘'
    assert body[0] == '│' and body[-1] == '│'
    # top/bottom interior is ─ except where the tag is centered in the top
    assert set(bot[1:-1]) == {'─'}
    assert 'tag' in top
    # top rule surrounds the tag with dashes
    interior = top[1:-1]
    assert interior.replace('tag', '', 1).count('─') == len(interior) - len('tag')


def test_every_row_padded_to_same_width(capsys):
    config.configure(echo={'box_width': 30})
    echo_boxed('short\n' + 'x' * 70 + '\nmedium line', 'z')
    rows = _rows(capsys.readouterr().out)
    widths = {len(r) for r in rows}
    assert len(widths) == 1, f'all rows must share the same column count, got {widths}'


def test_empty_tag_gives_plain_top_rule(capsys, pin_terminal_width):
    pin_terminal_width()
    echo_boxed('hi')
    top = _rows(capsys.readouterr().out)[0]
    assert top[0] == '┌' and top[-1] == '┐'
    assert set(top[1:-1]) == {'─'}


def test_long_tag_widens_top_rule(capsys):
    # tag longer than content forces the top rule to expand to fit.
    config.configure(echo={'box_width': 80})
    echo_boxed('x', 'a' * 20)
    top = _rows(capsys.readouterr().out)[0]
    assert 'a' * 20 in top
    # top still starts/ends with corners
    assert top[0] == '┌' and top[-1] == '┐'


# --- behavior: single-line, no wrap ---

def test_short_text_uses_auto_detected_width(capsys, pin_terminal_width):
    pin_terminal_width(columns=120)
    echo_boxed('hello world', 'tag')
    assert _content_lines(capsys.readouterr().out) == ['hello world']


def test_short_text_smaller_than_explicit_width(capsys):
    config.configure(echo={'box_width': 80})
    echo_boxed('short', 't')
    assert _content_lines(capsys.readouterr().out) == ['short']


def test_line_exactly_at_width_not_wrapped(capsys):
    config.configure(echo={'box_width': 10})
    echo_boxed('1234567890', 't')  # exactly 10 chars
    assert _content_lines(capsys.readouterr().out) == ['1234567890']


def test_line_one_over_width_wraps(capsys):
    config.configure(echo={'box_width': 10})
    echo_boxed('1234567890 abcdefghij', 't')
    lines = _content_lines(capsys.readouterr().out)
    assert len(lines) >= 2
    assert all(len(l) <= 10 for l in lines)


# --- behavior: wrapping correctness ---

def test_long_line_wraps_within_width(capsys):
    config.configure(echo={'box_width': 20})
    long = ('word ' * 30).strip()
    echo_boxed(long, 'x')
    lines = _content_lines(capsys.readouterr().out)
    assert len(lines) > 1
    assert all(len(l) <= 20 for l in lines)


def test_wrapping_preserves_all_words(capsys):
    config.configure(echo={'box_width': 25})
    original = 'the quick brown fox jumps over the lazy dog many times over'
    echo_boxed(original, 't')
    lines = _content_lines(capsys.readouterr().out)
    assert ' '.join(lines).split() == original.split()


def test_very_narrow_box_wraps_and_stays_in_bounds(capsys):
    # break_long_words=True (textwrap default) breaks any token longer than width,
    # so even width=5 must still produce lines <= 5.
    config.configure(echo={'box_width': 5})
    echo_boxed('supercalifragilistic', 't')
    lines = _content_lines(capsys.readouterr().out)
    assert len(lines) >= 2
    assert all(len(l) <= 5 for l in lines)


# --- behavior: preserving existing newline structure (the core fix) ---

def test_multiline_preserves_existing_newlines(capsys):
    config.configure(echo={'box_width': 80})
    echo_boxed('line one\nline two\nline three', 'm')
    assert _content_lines(capsys.readouterr().out) == [
        'line one', 'line two', 'line three',
    ]


def test_blank_paragraph_break_preserved(capsys):
    config.configure(echo={'box_width': 80})
    echo_boxed('header\n\nbody line', 'b')
    assert _content_lines(capsys.readouterr().out) == ['header', '', 'body line']


def test_consecutive_blank_lines_preserved(capsys):
    config.configure(echo={'box_width': 80})
    echo_boxed('a\n\n\n\nb', 't')
    assert _content_lines(capsys.readouterr().out) == ['a', '', '', '', 'b']


def test_leading_blank_line_preserved(capsys):
    config.configure(echo={'box_width': 80})
    echo_boxed('\nhello', 't')
    assert _content_lines(capsys.readouterr().out) == ['', 'hello']


def test_trailing_blank_line_preserved(capsys):
    config.configure(echo={'box_width': 80})
    echo_boxed('hello\n', 't')
    assert _content_lines(capsys.readouterr().out) == ['hello', '']


def test_only_newlines_input(capsys):
    config.configure(echo={'box_width': 80})
    echo_boxed('\n\n\n', 't')
    # '\n\n\n'.split('\n') == ['', '', '', ''] — four blank rows
    assert _content_lines(capsys.readouterr().out) == ['', '', '', '']


def test_regression_newlines_not_collapsed(capsys):
    """Guard against the old ``textwrap.fill`` bug.

    The previous implementation turned ``'a\nb'`` into ``'a b'`` once
    wrapping kicked in because ``textwrap.fill`` defaults to
    ``replace_whitespace=True``. Here both lines are short enough that
    the 'a b' form would fit on one row — if the bug came back, the test
    would see a single row instead of two.
    """
    config.configure(echo={'box_width': 10})
    echo_boxed('a\nb', 't')
    assert _content_lines(capsys.readouterr().out) == ['a', 'b']


# --- behavior: mixed and structured content ---

def test_mix_short_and_long_lines(capsys):
    config.configure(echo={'box_width': 20})
    text = 'short one\n' + 'x' * 80 + '\nshort two'
    echo_boxed(text, 'mix')
    lines = _content_lines(capsys.readouterr().out)
    assert lines[0] == 'short one'
    assert lines[-1] == 'short two'
    middle = lines[1:-1]
    # long line got wrapped into multiple chunks, all within width
    assert len(middle) > 1
    assert all(len(l) <= 20 for l in middle)


def test_json_like_structure_short_lines_untouched(capsys):
    config.configure(echo={'box_width': 80})
    payload = json.dumps({'a': 1, 'b': [2, 3], 'c': 'hello'}, indent=2)
    echo_boxed(payload, 'json')
    lines = _content_lines(capsys.readouterr().out)
    # each logical JSON line is short enough to remain intact
    assert lines == payload.split('\n')


def test_code_like_indentation_preserved_on_short_lines(capsys):
    config.configure(echo={'box_width': 80})
    code = 'def f():\n    x = 1\n    return x'
    echo_boxed(code, 'code')
    assert _content_lines(capsys.readouterr().out) == [
        'def f():', '    x = 1', '    return x',
    ]


def test_unicode_content_is_boxed(capsys):
    # emoji + CJK; textwrap measures by Python char count (len), which is
    # what echo_boxed uses internally. We only assert the content round-trips,
    # not terminal display width.
    config.configure(echo={'box_width': 80})
    echo_boxed('こんにちは 🌟 world', 't')
    assert _content_lines(capsys.readouterr().out) == ['こんにちは 🌟 world']


# --- behavior: width configuration ---

def test_explicit_zero_falls_back_to_terminal_width(capsys, pin_terminal_width):
    pin_terminal_width(columns=60)
    config.configure(echo={'box_width': 0})
    # 60 - 4 frame chars = 56 effective wrap width
    echo_boxed('x' * 100, 't')
    lines = _content_lines(capsys.readouterr().out)
    assert len(lines) >= 2
    assert all(len(l) <= 56 for l in lines)


def test_terminal_fallback_used_when_config_unset(capsys, pin_terminal_width):
    pin_terminal_width(columns=40)
    echo_boxed('x' * 200, 't')
    lines = _content_lines(capsys.readouterr().out)
    # 40 terminal columns minus 4 for the box frame
    assert all(len(l) <= 36 for l in lines)


def test_empty_string_input(capsys, pin_terminal_width):
    pin_terminal_width()
    echo_boxed('', 't')
    rows = _rows(capsys.readouterr().out)
    # one blank content row between the top and bottom frames
    assert len(rows) == 3
    assert rows[0].startswith('┌') and rows[0].endswith('┐')
    assert rows[1].startswith('│') and rows[1].endswith('│')
    assert rows[2].startswith('└') and rows[2].endswith('┘')


def test_explicit_width_overrides_terminal(capsys, pin_terminal_width):
    pin_terminal_width(columns=200)  # wide terminal
    config.configure(echo={'box_width': 15})
    echo_boxed('a ' * 100, 't')
    lines = _content_lines(capsys.readouterr().out)
    # must honor the explicit cap, not the wide terminal
    assert all(len(l) <= 15 for l in lines)


# --- behavior: real call-site shapes ---

def test_llm_output_shape_with_answer_tags(capsys):
    """A realistic LLM output containing <answer>...</answer> and prose."""
    config.configure(echo={'box_width': 40})
    text = (
        'Let me think step by step.\n'
        '\n'
        'The sport of basketball is clearly a team sport.\n'
        '<answer>yes</answer>'
    )
    echo_boxed(text, 'llm_output')
    lines = _content_lines(capsys.readouterr().out)
    # paragraph break survives
    assert '' in lines
    # the answer tag survives intact (not split by wrap since it's short enough)
    assert any('<answer>yes</answer>' in l for l in lines)


def test_code_eval_shape_with_traceback(capsys):
    """A traceback-like block: multiple lines, some long, with indentation."""
    config.configure(echo={'box_width': 80})
    text = (
        'Traceback (most recent call last):\n'
        '  File "x.py", line 1, in <module>\n'
        '    raise ValueError("something went terribly wrong and exceeded the width")\n'
        'ValueError: something went terribly wrong and exceeded the width'
    )
    echo_boxed(text, 'bad code_eval_output')
    lines = _content_lines(capsys.readouterr().out)
    # the short lines survive intact; in particular the indented `File ...` line
    # keeps its two-space leading indent (its length is <= 80 so it skips wrap).
    assert 'Traceback (most recent call last):' in lines
    assert '  File "x.py", line 1, in <module>' in lines
    # every line is within the configured cap
    assert all(len(l) <= 80 for l in lines)
