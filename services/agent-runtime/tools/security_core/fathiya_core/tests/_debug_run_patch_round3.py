import traceback

from core.orchestrator import FathiyaOrchestrator

cases = [
    "افحص example.com",
    "افحص 8.8.8.8 /login",
    "افحص 10.0.0.0/8 then /admin",
]

orch = FathiyaOrchestrator()
for text in cases:
    print("CASE:", text)
    try:
        route = orch.router.route(text)
        print("ROUTE:", route.flow, route.matched_keywords)
        result = orch.run(text)
        print("FINAL_FLOW:", result["route"].flow)
        print("OK")
    except Exception as exc:
        print(type(exc).__name__, exc)
        traceback.print_exc()
