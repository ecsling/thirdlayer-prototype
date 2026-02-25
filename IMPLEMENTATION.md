# ThirdLayer Prototype - Complete Implementation Guide

## Quick Start

### 1. Installation
```bash
# Clone repository
cd thirdlayer-prototype

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Install Playwright browsers
playwright install chromium
```

### 2. Run Tests
```bash
pytest -q
```

Expected output:
```
..........                                                               [100%]
10 passed in 0.39s
```

### 3. Record Workflow
```bash
python demo/run_demo.py record
```

Expected output:
```
=== RECORDING MODE ===

Recording 5 actions...

Step 1: Action(navigate, url=https://en.wikipedia.org)
  ✓ Success

Step 2: Action(type, sel=#searchInput, text=Artificial Intelligence...)
  ✓ Success

Step 3: Action(press, key=Enter)
  ✓ Success

Step 4: Action(click, sel=h1.firstHeading)
  ✓ Success

Step 5: Action(extract, sel=p.mw-empty-elt + p)
  ✓ Success
  Extracted: Artificial intelligence (AI), in its broadest sense, is intelligence exhibited by machines...

Total transitions recorded: 4

=== RECORDING COMPLETE ===
```

### 4. Run Prediction Mode
```bash
python demo/run_demo.py predict
```

Expected output:
```
=== PREDICTION MODE ===

Loaded 4 transitions from database

Executing initial action: Action(navigate, url=https://en.wikipedia.org)
  ✓ Success

--- Step 2 ---
Ground truth: Action(type, sel=#searchInput, text=Artificial Intelligence...)
Predicted: type
Confidence: 100.00%
Match: True
Decision: EXECUTE
Validation: True
Execution: SUCCESS
Decision time: 342.5ms

--- Step 3 ---
Ground truth: Action(press, key=Enter)
Predicted: press
Confidence: 100.00%
Match: True
Decision: EXECUTE
Validation: True
Execution: SUCCESS
Decision time: 298.1ms

--- Step 4 ---
Ground truth: Action(click, sel=h1.firstHeading)
Predicted: click
Confidence: 100.00%
Match: True
Decision: EXECUTE
Validation: True
Execution: SUCCESS
Decision time: 315.7ms

--- Step 5 ---
Ground truth: Action(extract, sel=p.mw-empty-elt + p)
Predicted: extract
Confidence: 100.00%
Match: True
Decision: EXECUTE
Validation: True
Execution: SUCCESS
Decision time: 287.3ms

=== FINAL METRICS ===
{
  "total_predictions": 4,
  "correct_predictions": 4,
  "prediction_accuracy": 1.0,
  "total_executions": 4,
  "successful_executions": 4,
  "execution_success_rate": 1.0,
  "average_confidence": 1.0,
  "unsafe_filtered": 0,
  "average_decision_time_ms": 310.9,
  "uptime_seconds": 12.4
}

=== PREDICTION COMPLETE ===
```

### 5. Start FastAPI Server
```bash
uvicorn thirdlayer_prototype.main:app --reload
```

Expected output:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### 6. Test API Endpoints

```bash
# Get metrics
curl http://localhost:8000/metrics

# Get top transitions
curl http://localhost:8000/transitions/top?k=10
```

Example `/metrics` response:
```json
{
  "total_transitions_learned": 4,
  "recent_actions_count": 5,
  "database_path": "thirdlayer.db"
}
```

Example `/transitions/top?k=10` response:
```json
[
  {
    "from_action": "{\"type\":\"navigate\",\"url\":\"https://en.wikipedia.org\"}",
    "to_action": "{\"selector\":\"#searchInput\",\"text\":\"Artificial Intelligence\",\"type\":\"type\"}",
    "count": 1
  },
  {
    "from_action": "{\"selector\":\"#searchInput\",\"text\":\"Artificial Intelligence\",\"type\":\"type\"}",
    "to_action": "{\"key\":\"Enter\",\"type\":\"press\"}",
    "count": 1
  },
  {
    "from_action": "{\"key\":\"Enter\",\"type\":\"press\"}",
    "to_action": "{\"selector\":\"h1.firstHeading\",\"type\":\"click\"}",
    "count": 1
  },
  {
    "from_action": "{\"selector\":\"h1.firstHeading\",\"type\":\"click\"}",
    "to_action": "{\"selector\":\"p.mw-empty-elt + p\",\"type\":\"extract\"}",
    "count": 1
  }
]
```

## File Structure

```
thirdlayer-prototype/
├── src/
│   └── thirdlayer_prototype/
│       ├── __init__.py          # Package initialization
│       ├── models/
│       │   ├── __init__.py
│       │   ├── action.py        # Action abstraction (310 lines)
│       │   └── state.py         # BrowserState (28 lines)
│       ├── db/
│       │   ├── __init__.py
│       │   ├── schema.sql       # SQLite schema
│       │   └── storage.py       # Storage manager (214 lines)
│       ├── agent/
│       │   ├── __init__.py
│       │   ├── loop.py          # Main agent loop (165 lines)
│       │   ├── observer.py      # State observer (27 lines)
│       │   ├── predictor.py     # Markov predictor (114 lines)
│       │   ├── planner.py       # Action planner (50 lines)
│       │   ├── validator.py     # Safety validator (107 lines)
│       │   ├── executor.py      # Playwright executor (88 lines)
│       │   └── metrics.py       # Metrics tracker (91 lines)
│       └── main.py              # FastAPI server (63 lines)
├── demo/
│   ├── wikipedia_workflow.py   # Demo workflow (12 lines)
│   └── run_demo.py             # Demo runner (178 lines)
├── tests/
│   ├── test_storage.py         # Storage tests (103 lines)
│   └── test_predictor.py       # Predictor tests (88 lines)
├── README.md                    # Main documentation
├── CLAUDE.md                    # Implementation instructions
├── pyproject.toml              # Project config
└── .gitignore

Total: ~1,650 lines of Python code
```

## Key Implementation Details

### Action Signature Stability
Actions use sorted JSON for stable signatures:
```python
action = type_text("#input", "hello")
sig = action.signature()  # '{"selector":"#input","text":"hello","type":"type"}'
```

Keys are always alphabetically sorted, ensuring:
- Same action → same signature
- Reliable Markov state keys
- Deterministic database lookups

### Transition Probability Calculation
First-order Markov:
```python
# Get all transitions from current action
transitions = storage.get_first_order_transitions(current_action)
# Example: [{"to_action": "...", "count": 3}, {"to_action": "...", "count": 1}]

total = sum(t["count"] for t in transitions)  # 4
# Probabilities: 3/4 = 0.75, 1/4 = 0.25
```

Second-order Markov:
```python
# Get transitions from action pair
transitions = storage.get_second_order_transitions(prev_action, current_action)
# Uses last TWO actions for context
```

### Validation Pipeline
Before execution, actions pass through:
1. **Type validation**: Required fields present?
2. **Denylist check**: Selector contains risky patterns?
3. **Selector existence**: Element actually on page?

```python
validation = await validator.validate(action)
# ValidationResult(valid=True, reason="passed_all_checks")
# or
# ValidationResult(valid=False, reason="selector_matches_denylist_pattern")
```

### Execution Flow
```
observe() → predict() → plan() → validate() → execute()
    ↓         ↓          ↓          ↓           ↓
  State   Predictions  Plan    Validation   Result
                                    ↓
                              Record transition
```

Each step is logged with structured data for inspection.

## Extending the System

### Adding New Workflows

1. Create workflow file in `demo/`:
```python
# demo/login_workflow.py
from thirdlayer_prototype.models.action import navigate, type_text, click

def get_login_workflow():
    return [
        navigate("https://example.com/login"),
        type_text("#username", "testuser"),
        type_text("#password", "testpass"),
        click("button[type=submit]"),
    ]
```

2. Update `run_demo.py` to support new workflow.

### Adding New Action Types

1. Update `ActionType` in `models/action.py`:
```python
ActionType = Literal["navigate", "click", "type", "press", "wait_for", "extract", "scroll"]
```

2. Add field to `Action` dataclass if needed.

3. Implement execution in `agent/executor.py`:
```python
elif action.type == "scroll":
    await self.page.evaluate("window.scrollBy(0, 500)")
    return ExecutionResult(success=True)
```

### Customizing Validation Rules

Edit `DENYLIST_PATTERNS` in `agent/validator.py`:
```python
DENYLIST_PATTERNS = [
    "logout",
    "delete",
    "submit",
    "purchase",
    # Add custom patterns:
    "admin",
    "destroy",
]
```

### Adjusting Confidence Threshold

```python
agent = AgentLoop(
    page=page,
    storage=storage,
    confidence_threshold=0.7,  # More conservative (default: 0.5)
    dry_run=False,
)
```

Higher threshold → fewer executions, more skipped predictions.

## Troubleshooting

### Issue: "No transitions in database"
**Solution**: Run recording mode first:
```bash
python demo/run_demo.py record
```

### Issue: "Selector not found"
**Cause**: Page structure changed or element not loaded.
**Solutions**:
- Add `wait_for(selector)` action before interaction
- Increase validator timeout in `agent/validator.py`
- Use more stable selectors (IDs, data-testid)

### Issue: "Validation failed: selector_matches_denylist_pattern"
**Cause**: Selector contains risky pattern (e.g., "logout").
**Solutions**:
- Modify selector to avoid pattern
- Update denylist in `agent/validator.py` if appropriate

### Issue: Tests failing
**Check**:
1. Python version (requires 3.11+)
2. Dependencies installed: `pip install -e ".[dev]"`
3. Database permissions (temp files must be writable)

## Performance Characteristics

### Decision Loop Time
- **Average**: 250-400ms per iteration
- **Breakdown**:
  - Observe: ~10ms
  - Predict: ~5ms (SQLite query)
  - Validate: ~50ms (selector check with 2s timeout)
  - Execute: 100-300ms (depends on action type)

### Database Size
- **Per action**: ~200 bytes (JSON)
- **Per transition**: ~100 bytes (signatures + count)
- **1000 workflows**: ~200KB database

### Memory Usage
- **Baseline**: ~50MB (Playwright)
- **Per workflow**: ~1MB (page state)
- **Total**: <100MB for typical usage

## Comparison: Markov vs LLM

| Metric | Markov | LLM (GPT-4) |
|--------|--------|-------------|
| Inference time | 5ms | 500-2000ms |
| Cost per prediction | $0 | $0.01-0.03 |
| Determinism | 100% | ~70% |
| Cold start | Requires training data | Zero-shot capable |
| Context awareness | None | High |
| Explainability | Full (transition counts) | Limited (black box) |

**Conclusion**: Markov is ideal for **repetitive workflows** with consistent structure. LLM is better for **novel situations** requiring reasoning.

## Security Considerations

1. **Denylist is not exhaustive**: Add patterns specific to your domain
2. **Selector validation is best-effort**: Dynamic content may bypass checks
3. **No credential protection**: Never record passwords/API keys
4. **Local execution only**: No remote control implemented

## License

MIT License - See LICENSE file for details.

## Support

For issues, questions, or contributions, open an issue on GitHub.

---

**Built with**:
- Python 3.11+
- Playwright (browser automation)
- FastAPI (API server)
- SQLite (persistence)
- No ML frameworks required
