import pytest
from conftest import needs_api_key, CI_TEST_MODEL
from secretagent.core import interface, implement_via, all_interfaces, _INTERFACES


@interface
def sport_for(player_or_event: str) -> str:
    """Return the sport associated with a famous player."""
    ...


@pytest.fixture(autouse=True)
def reset_interfaces():
    """Reset sport_for's implementation before each test."""
    sport_for.implementation = None
    yield
    sport_for.implementation = None


def test_unbound_interface_raises():
    with pytest.raises(NotImplementedError, match='no implementation registered'):
        sport_for('Kobe Bryant')


def test_all_interfaces():
    names = [i.name for i in all_interfaces()]
    assert 'sport_for' in names


def test_rebind():
    sport_for.implement_via('direct')
    sport_for.implement_via('direct')
    assert sport_for.implementation is not None


def test_implement_via_decorator():
    @implement_via('direct')
    def too_long(x: str, n: int = 3) -> bool:
        """x is longer than n characters."""
        return len(x) > n

    assert too_long("hello world") is True
    _INTERFACES.remove(too_long)


def test_direct():
    @interface
    def sport_for_direct(player_or_event: str) -> str:
        """Return the sport associated with a famous player."""
        return {'Kobe Bryant': 'basketball', 'Babe Ruth': 'baseball'}[player_or_event]

    sport_for_direct.implement_via('direct')
    assert sport_for_direct('Kobe Bryant') == 'basketball'
    assert sport_for_direct('Babe Ruth') == 'baseball'
    # clean up
    _INTERFACES.remove(sport_for_direct)


def test_prompt_llm_requires_exactly_one_template():
    """Must give exactly one of prompt_template_str or prompt_template_file."""
    with pytest.raises(ValueError, match='Exactly one'):
        sport_for.implement_via('prompt_llm')
    with pytest.raises(ValueError, match='Exactly one'):
        sport_for.implement_via('prompt_llm',
                                prompt_template_str='hi',
                                prompt_template_file='foo.txt')


def test_format_args_validates_arg_count():
    """format_args should raise when args don't match signature (e.g. missing param type hints)."""
    @interface
    def missing_param_hint(x) -> str:
        """Missing type hint on x."""

    # x has no type annotation, so format_args can't map the positional arg
    with pytest.raises(ValueError, match='cannot format'):
        missing_param_hint.format_args('hello')
    _INTERFACES.remove(missing_param_hint)


def test_direct_with_custom_fn():
    """DirectFactory should accept a custom fn parameter."""
    @interface
    def my_func(x: int) -> int:
        """Double x."""

    def custom_impl(x):
        return x * 3

    my_func.implement_via('direct', fn=custom_impl)
    assert my_func(5) == 15
    _INTERFACES.remove(my_func)


def test_direct_with_dotted_string_fn():
    """DirectFactory should resolve a dotted string like 'os.path.exists'."""
    @interface
    def check_path(path: str) -> bool:
        """Check if path exists."""

    check_path.implement_via('direct', fn='os.path.exists')
    assert check_path('/') is True
    _INTERFACES.remove(check_path)


def _stub_for_src_test(x: int) -> int:
    """Double x."""
    return x * 2


def _stub_with_ellipsis(x: int) -> int:
    """Double x."""
    ...


def test_interface_strips_body_by_default():
    """When simulate.full_src is not set, @interface should strip the function body after the docstring."""
    from secretagent import config

    with config.configuration(simulate=dict(full_src=False)):
        iface = interface(_stub_for_src_test)

    assert 'return x * 2' not in iface.src
    assert 'Double x.' in iface.src
    assert 'def _stub_for_src_test' in iface.src
    _INTERFACES.remove(iface)


def test_interface_retains_ellipsis_after_docstring():
    """When stripping, an Ellipsis immediately after the docstring should be kept."""
    from secretagent import config

    with config.configuration(simulate=dict(full_src=False)):
        iface = interface(_stub_with_ellipsis)

    assert '...' in iface.src
    assert 'Double x.' in iface.src
    assert 'def _stub_with_ellipsis' in iface.src
    _INTERFACES.remove(iface)


def test_interface_keeps_full_src_when_configured():
    """When simulate.full_src is truthy, @interface should keep the full function body."""
    from secretagent import config

    with config.configuration(simulate=dict(full_src=True)):
        iface = interface(_stub_for_src_test)

    assert 'return x * 2' in iface.src
    assert 'Double x.' in iface.src
    assert 'def _stub_for_src_test' in iface.src
    _INTERFACES.remove(iface)


# --- parse_output numeric fallback ---

class TestParseOutputNumericFallback:
    """SimulateFactory.parse_output should handle bare numeric responses."""

    def setup_method(self):
        from secretagent.implement.core import SimulateFactory
        self.factory = SimulateFactory()

    def test_bare_float(self):
        assert self.factory.parse_output(float, "1.0") == 1.0

    def test_bare_int(self):
        assert self.factory.parse_output(int, "42") == 42

    def test_bare_negative_float(self):
        assert self.factory.parse_output(float, "-3.14") == -3.14

    def test_bare_float_with_whitespace(self):
        assert self.factory.parse_output(float, "  1.0\n") == 1.0

    def test_bare_float_with_dollar_and_commas(self):
        assert self.factory.parse_output(float, "$25,502.0") == 25502.0

    def test_answer_tags_still_preferred(self):
        result = self.factory.parse_output(float, "reasoning here\n<answer>7.0</answer>")
        assert result == 7.0

    def test_prose_with_number_raises(self):
        with pytest.raises(ValueError, match="cannot find final answer"):
            self.factory.parse_output(float, "The answer is 7.0")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="cannot find final answer"):
            self.factory.parse_output(float, "")

    def test_trailing_period_raises(self):
        with pytest.raises(ValueError, match="cannot find final answer"):
            self.factory.parse_output(float, "1.0.")


@needs_api_key
def test_simulate():
    sport_for.implement_via('simulate', llm = dict(model=CI_TEST_MODEL))
    result = sport_for('Kobe Bryant')
    assert isinstance(result, str)
    assert len(result) > 0
