# ThirdLayer Prototype - Visual System Overview

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                    THIRDLAYER AGENTIC BROWSER SYSTEM                       ║
║                                                                            ║
║  "Learn workflows from observation, predict next steps, act reliably"     ║
╚═══════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────┐
│                              USER MODES                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─────────────────────┐              ┌──────────────────────┐          │
│  │  RECORDING MODE     │              │  PREDICTION MODE     │          │
│  │                     │              │                      │          │
│  │  • Execute workflow │              │  • Load transitions  │          │
│  │  • Store transitions│              │  • Run agent loop    │          │
│  │  • Build model      │              │  • Predict & execute │          │
│  └─────────────────────┘              └──────────────────────┘          │
│           │                                      │                       │
└───────────┼──────────────────────────────────────┼────────────────────────┘
            │                                      │
            └──────────────────┬───────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         AGENT DECISION LOOP                              │
│                         (250-400ms per iteration)                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────┐│
│   │          │   │          │   │          │   │          │   │      ││
│   │ OBSERVE  │──▶│ PREDICT  │──▶│   PLAN   │──▶│ VALIDATE │──▶│EXEC  ││
│   │          │   │          │   │          │   │          │   │      ││
│   └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────┘│
│   page.url       top-K          threshold       denylist       actions  │
│   page.title     confidence     decision        selectors               │
│   ~10ms          ~5ms            <1ms            ~50ms         100-300ms│
│                                                                           │
└───────────────────────────────────┬───────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         MARKOV PREDICTOR                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  FIRST-ORDER:  P(next | current)                                         │
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │  navigate → type     (10 occurrences)  → 50% confidence     │        │
│  │  navigate → click    (5 occurrences)   → 25% confidence     │        │
│  │  navigate → press    (5 occurrences)   → 25% confidence     │        │
│  └─────────────────────────────────────────────────────────────┘        │
│                                                                           │
│  SECOND-ORDER:  P(next | prev, current)                                  │
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │  (navigate, type) → press   (8 occurrences) → 80% confidence│        │
│  │  (navigate, type) → click   (2 occurrences) → 20% confidence│        │
│  └─────────────────────────────────────────────────────────────┘        │
│                                                                           │
│  Automatic fallback: 2nd-order → 1st-order → empty                      │
│                                                                           │
└───────────────────────────────────┬───────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         SQLITE STORAGE                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌────────────────────┐  ┌──────────────────────┐  ┌─────────────────┐ │
│  │ actions            │  │ transitions_1st      │  │ transitions_2nd │ │
│  ├────────────────────┤  ├──────────────────────┤  ├─────────────────┤ │
│  │ id: 1              │  │ from: navigate       │  │ from1: navigate │ │
│  │ sig: {type:nav..}  │  │ to: type             │  │ from2: type     │ │
│  │ json: {...}        │  │ count: 10            │  │ to: press       │ │
│  │ timestamp: 1234.5  │  │                      │  │ count: 8        │ │
│  │ url: https://...   │  │ UNIQUE(from, to)     │  │ UNIQUE(...)     │ │
│  │ success: 1         │  │                      │  │                 │ │
│  └────────────────────┘  └──────────────────────┘  └─────────────────┘ │
│                                                                           │
│  Storage Operations:                                                     │
│  • record_action()          ~1ms                                         │
│  • record_transition()      ~1ms (UPSERT)                                │
│  • get_transitions()        ~5ms (SELECT + ORDER BY count DESC)          │
│                                                                           │
└───────────────────────────────────┬───────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         ACTION GRAMMAR                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  navigate(url)           →  {"type":"navigate","url":"https://..."}     │
│  click(selector)         →  {"selector":"#btn","type":"click"}          │
│  type(selector, text)    →  {"selector":"#input","text":"hi","type":..} │
│  press(key)              →  {"key":"Enter","type":"press"}              │
│  wait_for(selector)      →  {"selector":"#el","type":"wait_for"}        │
│  extract(selector)       →  {"selector":"p","type":"extract"}           │
│                                                                           │
│  Signature = JSON.dumps(action, sort_keys=True)  ← STABLE KEY           │
│                                                                           │
└───────────────────────────────────┬───────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         RELIABILITY LAYER                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │ VALIDATOR                                                     │       │
│  │                                                               │       │
│  │  1. Denylist Check                                            │       │
│  │     ✗ logout, delete, submit, purchase, payment, account     │       │
│  │                                                               │       │
│  │  2. Selector Existence Check                                  │       │
│  │     ✓ page.locator(selector).count() > 0                     │       │
│  │                                                               │       │
│  │  3. Field Validation                                          │       │
│  │     ✓ All required fields present                            │       │
│  └──────────────────────────────────────────────────────────────┘       │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │ PLANNER                                                       │       │
│  │                                                               │       │
│  │  Confidence Threshold: 0.5 (default)                          │       │
│  │                                                               │       │
│  │  IF confidence >= 0.5:  EXECUTE                               │       │
│  │  IF confidence <  0.5:  SKIP                                  │       │
│  └──────────────────────────────────────────────────────────────┘       │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │ EXECUTOR                                                      │       │
│  │                                                               │       │
│  │  • All operations wrapped in try/except                       │       │
│  │  • Timeout: 10s (configurable)                                │       │
│  │  • Return ExecutionResult(success, error, extracted_text)     │       │
│  └──────────────────────────────────────────────────────────────┘       │
│                                                                           │
└───────────────────────────────────┬───────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         METRICS TRACKER                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  Tracked Metrics:                                                        │
│  • prediction_accuracy        = correct / total_predictions              │
│  • execution_success_rate     = successful / total_executions            │
│  • average_confidence         = sum(confidence) / total_predictions      │
│  • unsafe_filtered            = count of blocked actions                 │
│  • average_decision_time_ms   = avg loop iteration time                  │
│  • uptime_seconds             = time since startup                       │
│                                                                           │
│  Example Output:                                                         │
│  {                                                                        │
│    "total_predictions": 4,                                               │
│    "correct_predictions": 4,                                             │
│    "prediction_accuracy": 1.0,                                           │
│    "execution_success_rate": 1.0,                                        │
│    "average_confidence": 0.85,                                           │
│    "unsafe_filtered": 0,                                                 │
│    "average_decision_time_ms": 310.9                                     │
│  }                                                                        │
│                                                                           │
└───────────────────────────────────┬───────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         FASTAPI SERVER                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  GET /                                                                    │
│  └─▶ Service info, available endpoints                                   │
│                                                                           │
│  GET /metrics                                                             │
│  └─▶ {total_transitions, recent_actions_count, database_path}            │
│                                                                           │
│  GET /transitions/top?k=10                                                │
│  └─▶ [{from_action, to_action, count}, ...]                              │
│                                                                           │
│  Runs on: http://localhost:8000                                          │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘


╔═══════════════════════════════════════════════════════════════════════════╗
║                         KEY DESIGN PRINCIPLES                              ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  1. DETERMINISM FIRST                                                      ║
║     Same inputs always produce same outputs. No randomness.                ║
║                                                                            ║
║  2. INSPECTABILITY                                                         ║
║     Every decision has explicit reason. All data queryable.                ║
║                                                                            ║
║  3. RELIABILITY CONSTRAINTS                                                ║
║     Multiple safety layers before execution.                               ║
║                                                                            ║
║  4. MINIMAL DEPENDENCIES                                                   ║
║     Stdlib + Playwright + FastAPI. No ML frameworks.                       ║
║                                                                            ║
║  5. COMPOSABLE ACTIONS                                                     ║
║     Small primitives combine into complex workflows.                       ║
║                                                                            ║
║  6. MEASURABLE PERFORMANCE                                                 ║
║     All claims backed by tracked metrics.                                  ║
║                                                                            ║
╚═══════════════════════════════════════════════════════════════════════════╝


╔═══════════════════════════════════════════════════════════════════════════╗
║                         EXAMPLE WORKFLOW                                   ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  Wikipedia Search Workflow:                                                ║
║                                                                            ║
║  1. navigate("https://en.wikipedia.org")                                   ║
║     └─▶ Load homepage                                                      ║
║                                                                            ║
║  2. type("#searchInput", "Artificial Intelligence")                        ║
║     └─▶ Fill search box                                                    ║
║                                                                            ║
║  3. press("Enter")                                                         ║
║     └─▶ Submit search                                                      ║
║                                                                            ║
║  4. click("h1.firstHeading")                                               ║
║     └─▶ Click article title                                                ║
║                                                                            ║
║  5. extract("p.mw-empty-elt + p")                                          ║
║     └─▶ Extract first paragraph                                            ║
║                                                                            ║
║  After recording, the agent can:                                           ║
║  • Predict step 2 after step 1 (100% confidence)                           ║
║  • Predict step 3 after step 2 (100% confidence)                           ║
║  • Execute autonomously with validation                                    ║
║                                                                            ║
╚═══════════════════════════════════════════════════════════════════════════╝


╔═══════════════════════════════════════════════════════════════════════════╗
║                         MARKOV vs LLM                                      ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  Metric            │  Markov Baseline  │  LLM (GPT-4)                     ║
║  ─────────────────────────────────────────────────────────────────────    ║
║  Inference time    │  5ms              │  500-2000ms                      ║
║  Cost per predict  │  $0               │  $0.01-0.03                      ║
║  Determinism       │  100%             │  ~70%                            ║
║  Cold start        │  Needs training   │  Zero-shot capable               ║
║  Context aware     │  No               │  Yes                             ║
║  Explainability    │  Full (counts)    │  Limited                         ║
║  Best for          │  Repetitive flows │  Novel situations                ║
║                                                                            ║
║  Conclusion: Markov for familiar patterns, LLM for novel situations        ║
║                                                                            ║
╚═══════════════════════════════════════════════════════════════════════════╝
```
