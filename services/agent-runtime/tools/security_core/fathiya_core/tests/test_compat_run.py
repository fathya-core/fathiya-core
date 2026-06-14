"""
test_compat_run.py — اختبار التشغيل الكامل مع التحقق من التوافق
يحاكي ما يفعله main.py بالضبط (الوصول إلى .verdict / .reason / .revision_note)
لجميع الحالات: domain, ip, cidr, negative control
"""
import os
import sys
import traceback

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _simulate_main_output(result: dict) -> dict:
    """
    يحاكي بالضبط ما يفعله main.py في السطور 22-24:
        result["evaluation"].verdict
        result["evaluation"].reason
        result["evaluation"].revision_note
    إذا انهار هنا، فهذا هو الـ bug الأصلي.
    """
    evaluation = result["evaluation"]
    return {
        "verdict": evaluation.verdict,
        "reason": evaluation.reason,
        "revision_note": evaluation.revision_note,
        "final_answer": result["final_answer"],
        "revised_by_loop": result["revised_by_loop"],
        "session_id": result["session_id"],
    }


TEST_CASES = [
    {
        "name": "domain_case",
        "input": "أريد فحص أمني لموقع example.com",
        "expected_flow": "security",
        "expect_valid_target": True,
    },
    {
        "name": "ip_case",
        "input": "أريد فحص أمني للهدف 8.8.8.8 /login",
        "expected_flow": "security",
        "expect_valid_target": True,
    },
    {
        "name": "cidr_case",
        "input": "scan 10.0.0.0/8 for vulnerabilities",
        "expected_flow": "security",
        "expect_valid_target": True,
    },
    {
        "name": "negative_control",
        "input": "ما هو الطقس اليوم في الرياض؟",
        "expected_flow": "general",
        "expect_valid_target": False,
    },
]


def run_all_cases():
    from core.orchestrator import FathiyaOrchestrator

    results = []
    for case in TEST_CASES:
        entry = {"name": case["name"], "status": "PASS", "error": "", "details": {}}
        try:
            orchestrator = FathiyaOrchestrator()
            route = orchestrator.router.route(case["input"])
            entry["details"]["routed_flow"] = route.flow

            if case["expected_flow"] == "security" and route.flow != "security":
                entry["status"] = "FAIL"
                entry["error"] = f"Expected security flow, got {route.flow}"
                results.append(entry)
                continue

            if case["expected_flow"] == "general":
                # الحالة السلبية: نتحقق فقط أن الراوتر لا يوجه للأمني
                # أو إذا وجّه للأمني، نتحقق أن الإخراج لا ينهار
                if route.flow == "security":
                    # حتى لو وُجّه للأمني خطأً، يجب ألا ينهار
                    result = orchestrator.run(case["input"])
                    output = _simulate_main_output(result)
                    entry["details"]["output"] = output
                    entry["details"]["note"] = "routed to security unexpectedly but did not crash"
                else:
                    # المسار العام يحتاج OPENROUTER_API_KEY — نتخطاه
                    entry["status"] = "SKIP"
                    entry["error"] = "general flow requires OPENROUTER_API_KEY (expected)"
                results.append(entry)
                continue

            result = orchestrator.run(case["input"])

            # هذا هو الاختبار الحرج: محاكاة main.py
            output = _simulate_main_output(result)
            entry["details"]["output"] = output

            # تحقق إضافي
            assert result["route"].flow == "security"
            assert "analysis" in result
            assert result["session_id"] is not None
            assert output["verdict"] in ("approve", "revise")
            assert isinstance(output["reason"], str) and len(output["reason"]) > 0
            assert isinstance(output["revision_note"], str)

        except Exception as exc:
            entry["status"] = "FAIL"
            entry["error"] = f"{type(exc).__name__}: {exc}"
            entry["details"]["traceback"] = traceback.format_exc()

        results.append(entry)

    return results


if __name__ == "__main__":
    test_results = run_all_cases()

    print("=" * 60)
    print("COMPATIBILITY TEST RESULTS")
    print("=" * 60)

    for item in test_results:
        status = item["status"]
        name = item["name"]
        if status == "PASS":
            print(f"  [PASS] {name}")
            if "output" in item["details"]:
                o = item["details"]["output"]
                print(f"         verdict={o['verdict']}, reason={o['reason'][:60]}...")
        elif status == "SKIP":
            print(f"  [SKIP] {name} :: {item['error']}")
        else:
            print(f"  [FAIL] {name} :: {item['error']}")
            if "traceback" in item["details"]:
                print(item["details"]["traceback"])

    passed = sum(1 for r in test_results if r["status"] == "PASS")
    skipped = sum(1 for r in test_results if r["status"] == "SKIP")
    failed = sum(1 for r in test_results if r["status"] == "FAIL")

    print(f"\nTOTAL={len(test_results)} PASSED={passed} SKIPPED={skipped} FAILED={failed}")
    sys.exit(1 if failed else 0)
