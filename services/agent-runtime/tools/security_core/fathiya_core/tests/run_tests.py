import os
import sys
from typing import Dict, List, Optional, Tuple

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


TEST_CASES = [
    {
        "name": "security_smoke_domain",
        "input": "أريد فحص أمني لموقع example.com",
        "expected_flow": "security",
    },
    {
        "name": "security_smoke_ip",
        "input": "أريد فحص أمني للهدف 8.8.8.8 /login",
        "expected_flow": "security",
    },
    {
        "name": "security_smoke_cidr",
        "input": "scan 10.0.0.0/8 for vulnerabilities",
        "expected_flow": "security",
    },
]


def _load_orchestrator() -> Tuple[Optional[object], Optional[str]]:
    try:
        from core.orchestrator import FathiyaOrchestrator
        return FathiyaOrchestrator, None
    except ModuleNotFoundError as exc:
        missing = getattr(exc, "name", None) or str(exc)
        return None, f"missing optional dependency: {missing}"
    except Exception as exc:
        return None, f"unexpected import error: {exc}"


def _assert_result_shape(result: Dict, expected_flow: str) -> None:
    assert isinstance(result, dict), "result must be a dict"
    assert "route" in result, "result must contain route"
    assert "final_answer" in result, "result must contain final_answer"
    assert "session_id" in result, "result must contain session_id"
    assert result["route"].flow == expected_flow, (
        f"expected flow={expected_flow} but got {result['route'].flow}"
    )

    assert "analysis" in result, "result must contain analysis"
    analysis = result["analysis"]
    if expected_flow == "security":
        assert "target_profile" in analysis, "security analysis must contain target_profile"
        assert "surface_summary" in analysis, "security analysis must contain surface_summary"
        assert "security_report" in analysis, "security analysis must contain security_report"


def run_tests() -> List[Dict[str, str]]:
    orchestrator_cls, import_error = _load_orchestrator()
    if orchestrator_cls is None:
        return [
            {
                "name": "phase3_runner_bootstrap",
                "status": "ERROR",
                "error": import_error or "unable to import orchestrator",
            }
        ]

    orchestrator = orchestrator_cls()
    results: List[Dict[str, str]] = []

    for case in TEST_CASES:
        entry = {"name": case["name"], "status": "PASS", "error": ""}
        try:
            route = orchestrator.router.route(case["input"])
            assert route.flow == case["expected_flow"], (
                f"runner input must route to {case['expected_flow']} explicitly, got {route.flow}"
            )
            result = orchestrator.run(case["input"])
            _assert_result_shape(result, case["expected_flow"])
        except AssertionError as exc:
            entry["status"] = "FAIL"
            entry["error"] = f"AssertionError: {exc}"
        except ModuleNotFoundError as exc:
            entry["status"] = "ERROR"
            entry["error"] = f"missing optional dependency: {getattr(exc, 'name', str(exc))}"
        except Exception as exc:
            entry["status"] = "FAIL"
            entry["error"] = f"Exception: {exc}"
        results.append(entry)

    return results


if __name__ == "__main__":
    test_results = run_tests()
    failed = [item for item in test_results if item["status"] == "FAIL"]
    errors = [item for item in test_results if item["status"] == "ERROR"]
    skipped = [item for item in test_results if item["status"] == "SKIP"]
    passed = [item for item in test_results if item["status"] == "PASS"]

    for item in test_results:
        if item["status"] == "PASS":
            print(f"[PASS] {item['name']}")
        elif item["status"] == "ERROR":
            print(f"[ERROR] {item['name']} :: {item['error']}")
        elif item["status"] == "SKIP":
            print(f"[SKIP] {item['name']} :: {item['error']}")
        else:
            print(f"[FAIL] {item['name']} :: {item['error']}")

    print(
        "TOTAL={total} PASSED={passed} SKIPPED={skipped} ERRORS={errors} FAILED={failed}".format(
            total=len(test_results),
            passed=len(passed),
            skipped=len(skipped),
            errors=len(errors),
            failed=len(failed),
        )
    )
    sys.exit(1 if failed or errors else 0)
