"""TabMWPEvaluator: numeric-tolerant or case-insensitive text match."""

from typing import Any

from secretagent.evaluate import Evaluator


class TabMWPEvaluator(Evaluator):
    """Compare predicted and expected answers for TabMWP.

    Handles numeric answers (integer and decimal) and text answers.
    """

    @staticmethod
    def _normalize(s) -> str:
        """Strip whitespace, currency symbols, percent signs."""
        s = str(s).strip()
        s = s.lstrip('$€£¥')
        s = s.rstrip('%')
        return s.strip()

    def compare_predictions(self, predicted_output, expected_output) -> dict[str, Any]:
        predicted = self._normalize(predicted_output)
        expected = self._normalize(expected_output)

        try:
            pred_num = float(predicted.replace(',', ''))
            exp_num = float(expected.replace(',', ''))
            if exp_num == int(exp_num):
                correct = abs(pred_num - exp_num) < 0.5
            else:
                correct = abs(pred_num - exp_num) < 0.01
            return dict(correct=correct)
        except (ValueError, OverflowError):
            pass

        return dict(correct=predicted.lower() == expected.lower())
