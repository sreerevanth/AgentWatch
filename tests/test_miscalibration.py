from __future__ import annotations

import pytest

from agentwatch.lattice.miscalibration import (
    MiscalibrationDetector,
)


def test_empty_history_has_zero_brier_score():
    detector = MiscalibrationDetector()

    assert detector.brier_score() == 0.0

    result = detector.evaluate()

    assert result.brier_score == 0.0
    assert result.warning is False
    assert result.blocked is False
    assert result.sample_size == 0


def test_record_adds_history_entry():
    detector = MiscalibrationDetector()

    detector.record(0.8, True)

    assert len(detector.history) == 1
    assert detector.history[0].confidence == 0.8
    assert detector.history[0].success is True


def test_invalid_confidence_raises_value_error():
    detector = MiscalibrationDetector()

    with pytest.raises(ValueError):
        detector.record(1.2, True)

    with pytest.raises(ValueError):
        detector.record(-0.1, False)


def test_invalid_thresholds_raise_value_error():
    with pytest.raises(ValueError):
        MiscalibrationDetector(warning_threshold=-0.1)

    with pytest.raises(ValueError):
        MiscalibrationDetector(blocking_threshold=1.1)

    with pytest.raises(ValueError):
        MiscalibrationDetector(
            warning_threshold=0.3,
            blocking_threshold=0.2,
        )


def test_good_calibration_does_not_trigger_warning():
    detector = MiscalibrationDetector()

    detector.record(1.0, True)
    detector.record(0.0, False)
    detector.record(0.9, True)

    result = detector.evaluate()

    assert result.warning is False
    assert result.blocked is False


def test_warning_threshold_is_triggered():
    detector = MiscalibrationDetector()

    detector.record(0.5, True)
    detector.record(0.5, False)

    result = detector.evaluate()

    assert result.warning is True


def test_blocking_threshold_is_triggered():
    detector = MiscalibrationDetector()

    detector.record(1.0, False)
    detector.record(1.0, False)

    result = detector.evaluate()

    assert result.blocked is True


def test_sample_size_matches_history():
    detector = MiscalibrationDetector()

    detector.record(0.7, True)
    detector.record(0.2, False)
    detector.record(0.9, True)

    assert detector.evaluate().sample_size == 3


