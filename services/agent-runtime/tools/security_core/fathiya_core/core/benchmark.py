"""
core/benchmark.py — نظام قياس الأداء (Benchmark)

يقيس:
- الوقت المستغرق لكل مرحلة في الـ pipeline (framer, solver, evaluator)
- عدد محاولات إعادة المحاولة (retries)
- زمن الاستجابة (latency) لكل استدعاء API
- الوقت الإجمالي للتشغيل

الاستخدام:
    from core.benchmark import PipelineBenchmark

    bench = PipelineBenchmark()
    bench.start_stage("framer")
    # ... عمل الـ framer ...
    bench.end_stage("framer")

    bench.record_api_call("framer", latency=2.3, success=True)
    bench.record_retry("solver")

    report = bench.get_report()
    print(report)
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class APICallRecord:
    """سجل استدعاء API واحد"""
    component: str
    latency: float
    success: bool
    attempt: int = 1
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass
class StageTimings:
    """توقيتات مرحلة واحدة"""
    name: str
    start_time: float = 0.0
    end_time: float = 0.0
    duration: float = 0.0

    @property
    def is_complete(self) -> bool:
        return self.end_time > 0.0


class PipelineBenchmark:
    """
    نظام قياس أداء الـ pipeline.

    يتتبع:
    - توقيتات كل مرحلة
    - استدعاءات API
    - محاولات إعادة المحاولة
    - الوقت الإجمالي
    """

    def __init__(self) -> None:
        self._stages: Dict[str, StageTimings] = {}
        self._api_calls: List[APICallRecord] = []
        self._retries: Dict[str, int] = {}
        self._pipeline_start: float = 0.0
        self._pipeline_end: float = 0.0

    def start_pipeline(self) -> None:
        """بدء قياس الـ pipeline"""
        self._pipeline_start = time.time()

    def end_pipeline(self) -> None:
        """إنهاء قياس الـ pipeline"""
        self._pipeline_end = time.time()

    def start_stage(self, name: str) -> None:
        """بدء قياس مرحلة"""
        self._stages[name] = StageTimings(
            name=name,
            start_time=time.time()
        )

    def end_stage(self, name: str) -> float:
        """
        إنهاء قياس مرحلة.
        يرجع المدة بالثواني.
        """
        if name not in self._stages:
            return 0.0

        stage = self._stages[name]
        stage.end_time = time.time()
        stage.duration = round(stage.end_time - stage.start_time, 3)
        return stage.duration

    def record_api_call(
        self,
        component: str,
        latency: float,
        success: bool,
        attempt: int = 1
    ) -> None:
        """تسجيل استدعاء API"""
        self._api_calls.append(APICallRecord(
            component=component,
            latency=round(latency, 3),
            success=success,
            attempt=attempt,
        ))

    def record_retry(self, component: str) -> None:
        """تسجيل محاولة إعادة"""
        self._retries[component] = self._retries.get(component, 0) + 1

    @property
    def total_time(self) -> float:
        """الوقت الإجمالي للـ pipeline"""
        if self._pipeline_end > 0 and self._pipeline_start > 0:
            return round(self._pipeline_end - self._pipeline_start, 3)
        elif self._pipeline_start > 0:
            return round(time.time() - self._pipeline_start, 3)
        return 0.0

    @property
    def total_retries(self) -> int:
        """إجمالي محاولات إعادة المحاولة"""
        return sum(self._retries.values())

    @property
    def total_api_calls(self) -> int:
        """إجمالي استدعاءات API"""
        return len(self._api_calls)

    @property
    def avg_api_latency(self) -> float:
        """متوسط زمن استجابة API"""
        if not self._api_calls:
            return 0.0
        total = sum(c.latency for c in self._api_calls)
        return round(total / len(self._api_calls), 3)

    def get_stage_durations(self) -> Dict[str, float]:
        """استرجاع مدة كل مرحلة"""
        return {
            name: stage.duration
            for name, stage in self._stages.items()
            if stage.is_complete
        }

    def get_api_calls_by_component(self, component: str) -> List[APICallRecord]:
        """استرجاع استدعاءات API لمكوّن محدد"""
        return [c for c in self._api_calls if c.component == component]

    def get_report(self) -> Dict[str, Any]:
        """
        إنشاء تقرير أداء شامل.

        يرجع dict يحتوي:
        - total_time: الوقت الإجمالي
        - stages: توقيتات كل مرحلة
        - api_calls: عدد الاستدعاءات
        - avg_latency: متوسط زمن الاستجابة
        - retries: محاولات إعادة المحاولة
        - api_details: تفاصيل كل استدعاء
        """
        return {
            "total_time_seconds": self.total_time,
            "stages": self.get_stage_durations(),
            "api_calls_count": self.total_api_calls,
            "avg_api_latency_seconds": self.avg_api_latency,
            "total_retries": self.total_retries,
            "retries_by_component": dict(self._retries),
            "api_details": [
                {
                    "component": c.component,
                    "latency": c.latency,
                    "success": c.success,
                    "attempt": c.attempt,
                }
                for c in self._api_calls
            ],
        }

    def get_summary(self) -> str:
        """إنشاء ملخص نصي للأداء"""
        lines: List[str] = [
            "=== تقرير أداء FATHIYA Pipeline ===",
            f"الوقت الإجمالي: {self.total_time} ثانية",
            "",
            "--- توقيتات المراحل ---",
        ]

        for name, duration in self.get_stage_durations().items():
            lines.append(f"  {name}: {duration} ثانية")

        lines.extend([
            "",
            "--- استدعاءات API ---",
            f"  العدد: {self.total_api_calls}",
            f"  متوسط الاستجابة: {self.avg_api_latency} ثانية",
            f"  إعادة المحاولات: {self.total_retries}",
        ])

        if self._retries:
            for comp, count in self._retries.items():
                lines.append(f"    {comp}: {count}")

        lines.append("=" * 40)
        return "\n".join(lines)

    def reset(self) -> None:
        """إعادة تعيين جميع القياسات"""
        self._stages.clear()
        self._api_calls.clear()
        self._retries.clear()
        self._pipeline_start = 0.0
        self._pipeline_end = 0.0
