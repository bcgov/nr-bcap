from __future__ import annotations

import pytest

from runner import (
    CrossModelSearchTestRunner,
    SnapshotCase,
    TranslateMode,
    load_test_cases,
)


TEST_CASES = load_test_cases()


def _build_params() -> list[pytest.param]:
    if not TEST_CASES:
        return [pytest.param(
            None,
            None,
            marks=pytest.mark.skip(reason="No test_cases.json found"),
        )]

    params = []

    for tc in TEST_CASES:
        targets = tc.intersection_targets or (TranslateMode.NONE,)

        for target in targets:
            test_id = f"{tc.name}__{target}".replace(" ", "_")
            params.append(pytest.param(tc, target, id=test_id))

    return params


class TestCrossModelSearchSnapshot:
    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.runner = CrossModelSearchTestRunner()

    @pytest.mark.parametrize(("test_case", "target"), _build_params())
    def test_baseline_match(self, test_case: SnapshotCase, target: str) -> None:
        result = self.runner._run_single_test(test_case, target, update_baselines=False)

        if result.baseline_count is None:
            pytest.skip(f"No baseline for {test_case.name} -> {target}")

        assert result.passed, (
            f"{result.test_name} -> {result.intersection_target}: "
            f"expected {result.baseline_count}, got {result.current_count}"
        )


class TestUpdateBaselines:
    def test_update(self) -> None:
        if not TEST_CASES:
            pytest.skip("No test_cases.json found")

        runner = CrossModelSearchTestRunner()
        results = runner.run_tests(TEST_CASES, update_baselines=True)
        failed = [r for r in results if not r.passed]

        assert not failed, (
            "Failures during baseline update:\n"
            + "\n".join(
                f"  - {r.test_name} -> {r.intersection_target}: "
                f"expected {r.baseline_count}, got {r.current_count}"
                for r in failed
            )
        )
