from core.orchestrator import FathiyaOrchestrator


def start_fathiya():
    print("--- [FATHIYA CORE: Discovery Mode] ---")
    query = input("أدخل تساؤلك هنا: ")

    orchestrator = FathiyaOrchestrator()

    print("\n[جاري تشغيل FATHIYA CORE...]")

    try:
        result = orchestrator.run(query)

        print("\n--- تقرير التشخيص النهائي ---")
        print(result["analysis_json"])

        print("\n--- الرد الأولي من Solver ---")
        print(result["solver_answer"])

        print("\n--- نتيجة التقييم ---")
        print(f'verdict: {result["evaluation"].verdict}')
        print(f'reason: {result["evaluation"].reason}')
        print(f'revision_note: {result["evaluation"].revision_note}')

        print("\n--- الرد النهائي ---")
        print(result["final_answer"])
        print(f'\nrevised_by_loop: {result["revised_by_loop"]}')

        print(f'\n[تم حفظ الجلسة في الذاكرة | session_id={result["session_id"]}]')

        print("\n--- آخر الجلسات المحفوظة ---")
        for row in result["recent_sessions"]:
            session_id, created_at, user_input, evaluator_verdict = row
            print(
                f"[{session_id}] {created_at} | "
                f"verdict={evaluator_verdict} | "
                f"user_input={user_input}"
            )

    except Exception as e:
        print(f"\n[فشل التشغيل] {e}")


if __name__ == "__main__":
    start_fathiya()