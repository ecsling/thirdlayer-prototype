# ThirdLayer Prototype - System Architecture

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                          DEMO RUNNER                                  │
│                                                                        │
│  ┌──────────────┐                           ┌──────────────┐         │
│  │  Recording   │                           │  Prediction  │         │
│  │     Mode     │                           │     Mode     │         │
│  └──────┬───────┘                           └──────┬───────┘         │
│         │                                          │                  │
│         └──────────────────┬───────────────────────┘                  │
└────────────────────────────┼──────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                          AGENT LOOP                                   │
│                                                                        │
│  1. OBSERVE      2. PREDICT      3. PLAN      4. VALIDATE  5. EXECUTE│
│  ┌─────────┐    ┌──────────┐    ┌────────┐   ┌─────────┐ ┌────────┐│
│  │Observer │───▶│Predictor │───▶│Planner │──▶│Validator│▶│Executor││
│  │         │    │          │    │        │   │         │ │        ││
│  │ page.url│    │ top-K    │    │ thresh.│   │denylist │ │Playwrht││
│  │ title   │    │ conf.    │    │ reason │   │selector │ │actions ││
│  └─────────┘    └────┬─────┘    └────────┘   └─────────┘ └───┬────┘│
│                      │                                         │     │
│                      │                                         │     │
│                      ▼                                         ▼     │
│              ┌──────────────┐                         ┌──────────┐  │
│              │   Metrics    │◀────────────────────────│ Record   │  │
│              │              │                         │Transition│  │
│              │ accuracy     │                         └──────────┘  │
│              │ confidence   │                                        │
│              │ exec_rate    │                                        │
│              │ timing       │                                        │
│              └──────────────┘                                        │
└────────────────────────────┼──────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        STORAGE LAYER                                  │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                      SQLite Database                         │    │
│  │                                                               │    │
│  │  ┌──────────────┐  ┌──────────────────┐  ┌────────────────┐│    │
│  │  │   actions    │  │ transitions_1st  │  │ transitions_2nd││    │
│  │  ├──────────────┤  ├──────────────────┤  ├────────────────┤│    │
│  │  │ id           │  │ from_action      │  │ from_action_1  ││    │
│  │  │ signature    │  │ to_action        │  │ from_action_2  ││    │
│  │  │ json         │  │ count            │  │ to_action      ││    │
│  │  │ timestamp    │  │                  │  │ count          ││    │
│  │  │ url          │  │ UNIQUE(from,to)  │  │ UNIQUE(...)    ││    │
│  │  │ success      │  └──────────────────┘  └────────────────┘│    │
│  │  └──────────────┘                                           │    │
│  └─────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         FASTAPI SERVER                                │
│                                                                        │
│  GET /                  GET /metrics           GET /transitions/top  │
│  ├─ service info        ├─ transitions count   ├─ top K transitions  │
│  └─ endpoints list      ├─ recent actions      └─ with counts        │
│                         └─ db path                                    │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Observer
**Purpose**: Capture current browser state  
**Input**: Playwright Page object  
**Output**: BrowserState (url, title, timestamp)  
**Key Method**: `observe() -> BrowserState`  
**Dependencies**: Playwright async API

```python
state = await observer.observe()
# BrowserState(url='https://...', title='...', timestamp=...)
```

---

### 2. Predictor
**Purpose**: Generate candidate next actions using Markov model  
**Input**: Action history, k (top-K)  
**Output**: List[Prediction] sorted by confidence  
**Key Methods**:
- `predict_first_order(current, k)` - P(next | current)
- `predict_second_order(prev, current, k)` - P(next | prev, current)
- `predict(history, k, use_second_order)` - Automatic fallback

**Algorithm**:
```python
# Get transitions from storage
transitions = storage.get_first_order_transitions(current_action)
# Example: [{"to_action": "A", "count": 7}, {"to_action": "B", "count": 3}]

# Calculate probabilities
total = sum(t["count"] for t in transitions)  # 10
predictions = [
    Prediction(action=A, confidence=0.7, source="first_order"),
    Prediction(action=B, confidence=0.3, source="first_order"),
]
```

**Fallback Logic**:
1. Try second-order if history length >= 2
2. If no second-order transitions, use first-order
3. If no first-order transitions, return empty list

---

### 3. Planner
**Purpose**: Select action to execute based on confidence threshold  
**Input**: List[Prediction], threshold  
**Output**: Plan (prediction, should_execute, reason)  
**Key Method**: `plan(predictions) -> Plan`

**Decision Logic**:
```python
if not predictions:
    return Plan(None, False, "no_predictions_available")

top = predictions[0]
if top.confidence < threshold:
    return Plan(top, False, f"confidence_too_low_{top.confidence:.2f}")

return Plan(top, True, f"confidence_above_threshold_{top.confidence:.2f}")
```

**Threshold Tuning**:
- `0.3` - Aggressive (more executions, more errors)
- `0.5` - Balanced (default)
- `0.7` - Conservative (fewer executions, higher accuracy)

---

### 4. Validator
**Purpose**: Filter unsafe/invalid actions before execution  
**Input**: Action, Page  
**Output**: ValidationResult (valid, reason)  
**Key Method**: `validate(action) -> ValidationResult`

**Validation Pipeline**:
1. **Type check**: Required fields present?
2. **Denylist check**: Selector matches risky patterns?
3. **Existence check**: Selector exists on page?

**Denylist Patterns**:
```python
DENYLIST = [
    "logout", "log-out", "sign-out", "signout",
    "delete", "remove",
    "submit", "purchase", "buy", "payment", "checkout",
    "account", "settings", "preferences"
]
```

**Selector Check**:
```python
count = await page.locator(selector).count()
return count > 0  # Element exists
```

---

### 5. Executor
**Purpose**: Perform browser actions via Playwright  
**Input**: Action, Page  
**Output**: ExecutionResult (success, error, extracted_text)  
**Key Method**: `execute(action) -> ExecutionResult`

**Action Handlers**:
```python
if action.type == "navigate":
    await page.goto(action.url, timeout=10000)
elif action.type == "click":
    await page.click(action.selector, timeout=10000)
elif action.type == "type":
    await page.fill(action.selector, action.text, timeout=10000)
elif action.type == "press":
    await page.keyboard.press(action.key)
elif action.type == "wait_for":
    await page.wait_for_selector(action.selector, timeout=10000)
elif action.type == "extract":
    text = await page.locator(action.selector).first.text_content()
    return ExecutionResult(success=True, extracted_text=text)
```

**Error Handling**:
- All operations wrapped in try/except
- Timeouts configurable (default 10s)
- Errors captured as ExecutionResult with error message

---

### 6. Metrics
**Purpose**: Track system performance and accuracy  
**Input**: Event notifications (prediction, execution, etc.)  
**Output**: Metrics snapshot as dictionary  
**Key Methods**:
- `record_prediction(correct)` - Track prediction accuracy
- `record_execution(success)` - Track execution success
- `record_confidence(score)` - Track confidence scores
- `record_unsafe_filtered()` - Track blocked actions
- `record_decision_time(duration)` - Track loop timing

**Tracked Metrics**:
```python
{
    "total_predictions": 4,
    "correct_predictions": 3,
    "prediction_accuracy": 0.75,
    "total_executions": 3,
    "successful_executions": 3,
    "execution_success_rate": 1.0,
    "average_confidence": 0.82,
    "unsafe_filtered": 1,
    "average_decision_time_ms": 310.9,
    "uptime_seconds": 12.4
}
```

---

### 7. Storage
**Purpose**: Persist actions and transitions in SQLite  
**Input**: Actions, transitions  
**Output**: Query results  
**Key Methods**:
- `record_action(action, url, success)` - Log action execution
- `record_transition_first_order(from, to)` - Increment transition count
- `record_transition_second_order(from1, from2, to)` - Increment 2nd-order count
- `get_first_order_transitions(from)` - Query transitions for prediction
- `get_second_order_transitions(from1, from2)` - Query 2nd-order transitions
- `get_top_transitions(k)` - Get most common transitions

**Schema**:
```sql
CREATE TABLE actions (
    id INTEGER PRIMARY KEY,
    action_signature TEXT NOT NULL,
    action_json TEXT NOT NULL,
    timestamp REAL NOT NULL,
    url TEXT,
    success INTEGER DEFAULT 1
);

CREATE TABLE transitions_first_order (
    id INTEGER PRIMARY KEY,
    from_action TEXT NOT NULL,
    to_action TEXT NOT NULL,
    count INTEGER DEFAULT 1,
    UNIQUE(from_action, to_action)
);

CREATE TABLE transitions_second_order (
    id INTEGER PRIMARY KEY,
    from_action_1 TEXT NOT NULL,
    from_action_2 TEXT NOT NULL,
    to_action TEXT NOT NULL,
    count INTEGER DEFAULT 1,
    UNIQUE(from_action_1, from_action_2, to_action)
);
```

**UPSERT Pattern**:
```python
INSERT INTO transitions_first_order (from_action, to_action, count)
VALUES (?, ?, 1)
ON CONFLICT(from_action, to_action)
DO UPDATE SET count = count + 1
```

---

## Data Flow

### Recording Mode
```
User Workflow
    │
    ▼
Execute Actions (manual/scripted)
    │
    ├─ Record action to DB
    │
    └─ Record transition
        │
        ├─ First-order:  (prev → current)
        │
        └─ Second-order: (prev2, prev1 → current)
```

### Prediction Mode
```
Initial Action (manual)
    │
    ▼
Agent Loop Iteration:
    │
    ├─ 1. Observe state (url, title)
    │
    ├─ 2. Predict next action
    │   ├─ Query storage for transitions
    │   ├─ Calculate probabilities
    │   └─ Return top-K predictions
    │
    ├─ 3. Plan execution
    │   └─ Check confidence threshold
    │
    ├─ 4. Validate action
    │   ├─ Check denylist
    │   └─ Verify selector exists
    │
    ├─ 5. Execute (if valid)
    │   ├─ Perform Playwright action
    │   ├─ Record action to DB
    │   └─ Record transition
    │
    └─ 6. Update metrics
        ├─ Prediction accuracy
        ├─ Execution success
        └─ Decision time
```

---

## Markov Model Mathematics

### First-Order Markov Model
```
P(A₃ | A₂) = count(A₂ → A₃) / Σ count(A₂ → *)

Example:
- navigate → type: 10 times
- navigate → click: 5 times
- navigate → press: 5 times
Total: 20

P(type | navigate) = 10/20 = 0.50
P(click | navigate) = 5/20 = 0.25
P(press | navigate) = 5/20 = 0.25
```

### Second-Order Markov Model
```
P(A₄ | A₂, A₃) = count(A₂, A₃ → A₄) / Σ count(A₂, A₃ → *)

Example:
- (navigate, type) → press: 8 times
- (navigate, type) → click: 2 times
Total: 10

P(press | navigate, type) = 8/10 = 0.80
P(click | navigate, type) = 2/10 = 0.20
```

### Confidence Score
The confidence score IS the probability:
```
confidence = count(transition) / count(all_transitions_from_state)
```

High confidence (>0.7) → reliable prediction  
Medium confidence (0.4-0.7) → uncertain  
Low confidence (<0.4) → unreliable (skip execution)

---

## Action Signature Generation

**Critical for determinism**: Actions must have stable, unique signatures.

### Signature Algorithm
```python
def signature(self) -> str:
    # Convert to dict with only non-None fields
    d = {"type": self.type}
    if self.selector: d["selector"] = self.selector
    if self.text: d["text"] = self.text
    if self.url: d["url"] = self.url
    if self.key: d["key"] = self.key
    
    # Sort keys alphabetically
    return json.dumps(d, sort_keys=True)
```

### Examples
```python
navigate("https://example.com")
→ '{"type":"navigate","url":"https://example.com"}'

click("#button")
→ '{"selector":"#button","type":"click"}'

type_text("#input", "hello")
→ '{"selector":"#input","text":"hello","type":"type"}'
```

**Why sorting matters**:
```python
# Without sorting (BAD):
{"type": "click", "selector": "#btn"}  # might become
{"selector": "#btn", "type": "click"}  # different signature!

# With sorting (GOOD):
Always → '{"selector":"#btn","type":"click"}'
```

---

## Performance Characteristics

### Latency Breakdown
```
Total Decision Loop: 250-400ms
├─ observe():        ~10ms   (Playwright API call)
├─ predict():        ~5ms    (SQLite SELECT query)
├─ plan():           <1ms    (simple comparison)
├─ validate():       ~50ms   (selector existence check, 2s timeout)
└─ execute():        100-300ms (depends on action type)
```

### Storage Efficiency
```
Action record:     ~200 bytes (JSON)
Transition record: ~100 bytes (2 signatures + count)

Example DB size:
- 1,000 actions:      200 KB
- 5,000 transitions:  500 KB
Total:                ~700 KB
```

### Memory Usage
```
Baseline:           ~50 MB  (Playwright browser)
Per workflow:       ~1 MB   (page state, history)
SQLite connection:  ~5 MB   (buffer + cache)
Total typical:      <100 MB
```

---

## Known Limitations

### 1. Context Insensitivity
**Problem**: Markov model ignores page content/state  
**Example**: Same action sequence behaves differently on different URLs  
**Mitigation**: Condition transitions on URL patterns (future extension)

### 2. Selector Brittleness
**Problem**: CSS selectors break when page structure changes  
**Example**: `div.class-123` → `div.class-456` after deploy  
**Mitigation**: Use stable selectors (IDs, data-testid, ARIA)

### 3. Cold Start
**Problem**: No predictions until workflow recorded  
**Example**: First time on new site = zero transitions  
**Mitigation**: Seed DB with common patterns or use LLM fallback

### 4. Infinite Loops
**Problem**: Model might predict circular transitions  
**Example**: click → click → click (if misconfigured)  
**Mitigation**: Add max iterations limit and loop detection

### 5. Dynamic Content
**Problem**: Async-loaded elements not present during validation  
**Example**: Selector exists check runs before content loads  
**Mitigation**: Explicit wait_for actions or increase timeouts

---

## Extension Points

### 1. Context-Aware Transitions
```python
# Instead of:
P(next | current)

# Use:
P(next | current, url_pattern)

# Example:
P(click_login | navigate, "*/auth/*") = 0.9
P(click_search | navigate, "*/home/*") = 0.8
```

### 2. Hierarchical Workflows
```python
# Learn workflow boundaries:
workflows = [
    ("login", [navigate, type, type, click]),
    ("search", [navigate, type, press, extract]),
]

# Predict workflow + steps:
P(workflow=search) = 0.7
P(step=press | workflow=search, prev=type) = 0.9
```

### 3. LLM Hybrid
```python
def predict(history):
    markov_pred = markov_predictor.predict(history)
    
    if markov_pred.confidence > 0.7:
        return markov_pred  # Use Markov (fast, cheap)
    else:
        return llm_predictor.predict(history, page_state)  # Use LLM (slow, expensive)
```

### 4. Selector Healing
```python
def execute(action):
    result = await executor.execute(action)
    
    if result.error == "selector_not_found":
        # Use LLM to find updated selector
        new_selector = await llm.find_similar_element(action.selector, page)
        action.selector = new_selector
        return await executor.execute(action)
```

---

## Testing Strategy

### Unit Tests
- ✅ Storage: record, query, counts
- ✅ Predictor: first-order, second-order, fallback
- ✅ Action: serialization, signature stability

### Integration Tests (Future)
- End-to-end workflow recording
- Full agent loop with mock browser
- API endpoint responses

### Property-Based Tests (Future)
- Signature uniqueness
- Probability sum = 1.0
- Transition count monotonicity

---

## Deployment Considerations

### Production Checklist
- [ ] Set confidence threshold based on use case
- [ ] Customize denylist for domain-specific risks
- [ ] Add max iterations limit to prevent infinite loops
- [ ] Implement workflow timeout (e.g., 5 minutes)
- [ ] Add structured logging (JSON lines)
- [ ] Monitor metrics via /metrics endpoint
- [ ] Set up DB backups (thirdlayer.db)
- [ ] Use headless browser for production

### Monitoring Metrics
- Prediction accuracy (target: >80%)
- Execution success rate (target: >95%)
- Average confidence (target: >0.6)
- Unsafe filtered count (watch for spikes)
- Decision time (target: <500ms)

---

## Summary

ThirdLayer Prototype demonstrates a **minimal, deterministic, inspectable** approach to agentic browser automation using first-order and second-order Markov models. The architecture prioritizes:

1. **Separation of concerns** - Clear module boundaries
2. **Determinism** - Same inputs always produce same outputs
3. **Inspectability** - All decisions have explicit reasons
4. **Reliability** - Multiple safety constraints
5. **Performance** - Sub-10ms predictions, <100MB memory

The system is immediately useful for **repetitive workflows** and provides a strong foundation for **hybrid architectures** combining Markov baselines with LLM reasoning for novel situations.
