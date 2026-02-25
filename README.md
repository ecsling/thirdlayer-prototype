# ThirdLayer Prototype

**Agentic browser automation with workflow understanding, next-step prediction, and reliability constraints.**

## Thesis

LLMs are powerful but expensive, non-deterministic, and overkill for many repetitive browser workflows. This prototype demonstrates that a **simple Markov model** can learn workflow transitions from observation and predict next actions with measurable accuracy—providing a lightweight, inspectable, and cost-effective baseline for agentic browser automation.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      AGENT LOOP                          │
│                                                           │
│  ┌─────────┐   ┌───────────┐   ┌─────────┐   ┌────────┐│
│  │Observer │──▶│ Predictor │──▶│ Planner │──▶│Executor││
│  └─────────┘   └───────────┘   └─────────┘   └────────┘│
│                      │                │                  │
│                      ▼                ▼                  │
│                  ┌────────┐      ┌──────────┐           │
│                  │Validator│      │  Metrics │           │
│                  └────────┘      └──────────┘           │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
                  ┌────────────┐
                  │   Storage  │
                  │  (SQLite)  │
                  └────────────┘
```

### Module Responsibilities

- **Observer**: Captures current browser state (URL, title, timestamp)
- **Predictor**: Suggests candidate next actions using Markov transition probabilities
- **Planner**: Selects action to execute based on confidence threshold
- **Validator**: Filters unsafe/invalid actions (denylist + selector existence checks)
- **Executor**: Performs browser actions via Playwright
- **Metrics**: Tracks prediction accuracy, execution success, confidence, decision time
- **Storage**: Persists action history and transition counts in SQLite

## Why Markov > LLM for Baseline

1. **Determinism**: Same workflow → same predictions (no prompt drift)
2. **Inspectability**: Transition counts are queryable; confidence scores are explicit probabilities
3. **Cost**: Zero API calls; runs locally with ~0ms inference time
4. **Measurability**: Ground truth comparison is straightforward
5. **Reliability**: No hallucinations; predictions are grounded in observed data

Markov models establish a **performance floor** and cost ceiling. LLMs can augment later as a proposal engine for novel situations.

## Action Grammar

All browser actions are composable, JSON-serializable, and replayable:

- `navigate(url)` - Navigate to URL
- `click(selector)` - Click element
- `type(selector, text)` - Type text into input
- `press(key)` - Press keyboard key
- `wait_for(selector)` - Wait for element
- `extract(selector)` - Extract text content

Each action has a **stable signature** (sorted JSON) used as the Markov state key.

## Markov Models

### First-Order Markov
```
P(next_action | current_action)
```
Predicts next action based on the most recent action.

### Second-Order Markov
```
P(next_action | prev_action, current_action)
```
Predicts next action based on the last two actions. Falls back to first-order when insufficient data.

Transition counts are stored in SQLite and converted to probabilities on-the-fly. Top-K predictions are returned with confidence scores.

## Reliability Strategy

### 1. Safety Denylist
Rule-based filter for destructive patterns:
- logout, sign-out, delete, remove
- submit, purchase, payment, checkout
- account, settings, preferences

Actions matching these patterns are blocked before execution.

### 2. Confidence Threshold
Actions are only executed if prediction confidence exceeds threshold (default 0.5). Low-confidence predictions are logged but skipped.

### 3. Selector Validation
Before executing click/type/extract, validator checks if selector exists on page (2s timeout). Missing selectors fail validation.

### 4. Timeout Handling
All Playwright operations have explicit timeouts (default 10s). Failures are caught and logged with error type.

### 5. Structured Logging
All decisions, validations, and executions are logged as structured JSON for inspection and debugging.

### 6. Dry-Run Mode
Agent can run in dry-run mode: predictions and validations execute, but browser actions are only logged (not performed).

## Installation & Setup

```bash
# 1. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -e ".[dev]"

# 3. Install Playwright browsers
playwright install chromium
```

## Usage

### Recording Mode
Run a scripted workflow and record transitions:

```bash
python demo/run_demo.py record
```

This will:
1. Execute the Wikipedia search workflow step-by-step
2. Record each action to SQLite
3. Store first-order and second-order transition counts
4. Display execution results

### Prediction Mode
Run the agent loop using learned transitions:

```bash
python demo/run_demo.py predict
```

This will:
1. Load transitions from database
2. Execute first action manually
3. Let agent predict and execute remaining steps
4. Compare predictions to ground truth
5. Display metrics (accuracy, confidence, execution success)

### FastAPI Server
Start the metrics API:

```bash
uvicorn thirdlayer_prototype.main:app --reload
```

Endpoints:
- `GET /metrics` - System metrics snapshot
- `GET /transitions/top?k=10` - Top K most common transitions

## Demo Workflow: Wikipedia Search

```python
navigate("https://en.wikipedia.org")
type("#searchInput", "Artificial Intelligence")
press("Enter")
click("h1.firstHeading")
extract("p.mw-empty-elt + p")
```

This workflow:
1. Goes to Wikipedia
2. Types search query
3. Submits search
4. Clicks result heading
5. Extracts first paragraph

## Testing

```bash
pytest -q
```

Tests cover:
- Storage: action recording, transition counting, queries
- Predictor: first-order, second-order, fallback logic

## Metrics Tracked

- **Prediction accuracy**: % of predictions matching ground truth (when available)
- **Execution success rate**: % of actions that executed without errors
- **Average confidence**: Mean confidence across all predictions
- **Unsafe filtered count**: # of actions blocked by validator
- **Average decision time**: Mean time per agent loop iteration (ms)

Example metrics output:
```json
{
  "total_predictions": 4,
  "correct_predictions": 3,
  "prediction_accuracy": 0.75,
  "total_executions": 3,
  "successful_executions": 3,
  "execution_success_rate": 1.0,
  "average_confidence": 0.82,
  "unsafe_filtered": 0,
  "average_decision_time_ms": 342.5,
  "uptime_seconds": 12.4
}
```

## Known Failure Modes

1. **Selector brittleness**: CSS selectors break when page structure changes
   - Mitigation: Use stable selectors (IDs, data-testid, ARIA labels)

2. **Dynamic content**: Async-loaded elements may not exist when checked
   - Mitigation: Add wait_for actions explicitly; increase validation timeout

3. **Cold start**: No predictions available until workflow is recorded
   - Mitigation: Seed database with common patterns; provide fallback policy

4. **Context insensitivity**: Markov model ignores page content/state
   - Mitigation: Future work—condition transitions on URL patterns or page features

5. **Novel situations**: Zero-shot scenarios have no learned transitions
   - Mitigation: Fallback to scripted policy or LLM proposal for new workflows

## Future Extensions

### Short-term
- **Context-conditioned transitions**: `P(next | current, url_pattern)`
- **Hierarchical workflows**: Learn sub-workflow boundaries (e.g., "login", "search")
- **Execution replay**: Store full workflows for debugging and retraining

### Medium-term
- **LLM proposal engine**: Use LLM to suggest actions for novel situations; Markov for familiar patterns
- **Selector healing**: Auto-update broken selectors using page structure + LLM
- **Multi-modal state**: Include screenshots/DOM snapshots in state representation

### Long-term
- **Memory store integration**: RAG over past workflows for few-shot learning
- **Multi-agent orchestration**: Specialized agents for different workflow types
- **Self-improvement loop**: Agent evaluates its own accuracy and requests retraining

## Design Principles

1. **Determinism first**: Same inputs → same outputs (no randomness)
2. **Inspectability**: Every decision has an explicit reason in logs
3. **Minimal dependencies**: stdlib + Playwright + FastAPI (no ML frameworks)
4. **Composable actions**: Small primitives combine into complex workflows
5. **Measurable performance**: All claims backed by tracked metrics

## Project Structure

```
thirdlayer-prototype/
├── src/
│   └── thirdlayer_prototype/
│       ├── models/          # Action & State abstractions
│       │   ├── action.py
│       │   └── state.py
│       ├── db/              # SQLite storage
│       │   ├── schema.sql
│       │   └── storage.py
│       ├── agent/           # Core agent components
│       │   ├── loop.py      # Main decision loop
│       │   ├── observer.py
│       │   ├── predictor.py
│       │   ├── planner.py
│       │   ├── validator.py
│       │   ├── executor.py
│       │   └── metrics.py
│       └── main.py          # FastAPI server
├── demo/
│   ├── wikipedia_workflow.py
│   └── run_demo.py
├── tests/
│   ├── test_storage.py
│   └── test_predictor.py
└── README.md
```

## Contributing

This is a research prototype. Contributions welcome for:
- Additional demo workflows
- Improved validation rules
- Performance optimizations
- Extended Markov models (context-aware, hierarchical)

## License

MIT
