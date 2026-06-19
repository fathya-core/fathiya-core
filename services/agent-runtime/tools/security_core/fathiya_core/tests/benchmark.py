"""
tests/benchmark.py — اختبار أداء الـ pipeline

يقيس:
- توقيتات كل مرحلة
- عدد retries
- latency لكل API call
- الوقت الإجمالي

يمكن تشغيله مستقلاً:
    python -m tests.benchmark
"""

import sys
import os
import time

# إضافة المسار الجذري للمشروع
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.benchmark import PipelineBenchmark, APICallRecord


def test_benchmark_basic() -> None:
    """اختبار أساسي لنظام القياس"""
    bench = PipelineBenchmark()

    # بدء الـ pipeline
    bench.start_pipeline()

    # محاكاة مرحلة framer
    bench.start_stage("framer")
    time.sleep(0.05)  # محاكاة عمل
    bench.record_api_call("framer", latency=0.05, success=True, attempt=1)
    framer_duration = bench.end_stage("framer")

    # محاكاة مرحلة solver
    bench.start_stage("solver")
    time.sleep(0.03)
    bench.record_api_call("solver", latency=0.03, success=False, attempt=1)
    bench.record_retry("solver")
    bench.record_api_call("solver", latency=0.04, success=True, attempt=2)
    solver_duration = bench.end_stage("solver")

    # محاكاة مرحلة evaluator
    bench.start_stage("evaluator")
    time.sleep(0.02)
    bench.record_api_call("evaluator", latency=0.02, success=True, attempt=1)
    eval_duration = bench.end_stage("evaluator")

    # إنهاء الـ pipeline
    bench.end_pipeline()

    # التحقق من النتائج
    assert framer_duration > 0, "مدة framer يجب أن تكون > 0"
    assert solver_duration > 0, "مدة solver يجب أن تكون > 0"
    assert eval_duration > 0, "مدة evaluator يجب أن تكون > 0"
    assert bench.total_time > 0, "الوقت الإجمالي يجب أن يكون > 0"
    assert bench.total_api_calls == 4, f"عدد استدعاءات API يجب أن يكون 4، حصلنا على {bench.total_api_calls}"
    assert bench.total_retries == 1, f"عدد الإعادات يجب أن يكون 1، حصلنا على {bench.total_retries}"
    assert bench.avg_api_latency > 0, "متوسط الاستجابة يجب أن يكون > 0"

    # التقرير
    report = bench.get_report()
    assert "total_time_seconds" in report
    assert "stages" in report
    assert "framer" in report["stages"]
    assert "solver" in report["stages"]
    assert "evaluator" in report["stages"]
    assert report["total_retries"] == 1
    assert report["api_calls_count"] == 4

    # الملخص النصي
    summary = bench.get_summary()
    assert "framer" in summary
    assert "solver" in summary

    print("[PASS] test_benchmark_basic")
    return report


def test_benchmark_reset() -> None:
    """اختبار إعادة التعيين"""
    bench = PipelineBenchmark()
    bench.start_pipeline()
    bench.start_stage("test")
    bench.record_api_call("test", latency=1.0, success=True)
    bench.record_retry("test")
    bench.end_stage("test")
    bench.end_pipeline()

    assert bench.total_api_calls == 1
    assert bench.total_retries == 1

    bench.reset()

    assert bench.total_api_calls == 0
    assert bench.total_retries == 0
    assert bench.total_time == 0.0
    assert len(bench.get_stage_durations()) == 0

    print("[PASS] test_benchmark_reset")


def test_benchmark_api_by_component() -> None:
    """اختبار فلترة استدعاءات API حسب المكوّن"""
    bench = PipelineBenchmark()
    bench.record_api_call("framer", latency=1.0, success=True)
    bench.record_api_call("solver", latency=2.0, success=True)
    bench.record_api_call("framer", latency=1.5, success=False)

    framer_calls = bench.get_api_calls_by_component("framer")
    assert len(framer_calls) == 2, f"يجب أن يكون 2 استدعاء لـ framer، حصلنا على {len(framer_calls)}"

    solver_calls = bench.get_api_calls_by_component("solver")
    assert len(solver_calls) == 1

    print("[PASS] test_benchmark_api_by_component")


def run_benchmarks() -> None:
    """تشغيل جميع اختبارات الأداء"""
    print("\n" + "=" * 50)
    print("  اختبارات الأداء — FATHIYA Benchmark")
    print("=" * 50 + "\n")

    passed = 0
    failed = 0

    tests = [
        test_benchmark_basic,
        test_benchmark_reset,
        test_benchmark_api_by_component,
    ]

    for test_fn in tests:
        try:
            result = test_fn()
            passed += 1
            if isinstance(result, dict):
                print(f"  -> التقرير: {result}\n")
        except Exception as e:
            failed += 1
            print(f"[FAIL] {test_fn.__name__}: {e}")

    print(f"\n{'=' * 50}")
    print(f"  النتيجة: {passed} نجح | {failed} فشل")
    print(f"{'=' * 50}\n")


if __name__ == "__main__":
    run_benchmarks()
