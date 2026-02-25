# browser workflow predictor prototype for ThirdLayer

- observes structured actions 
- learns workflow transitions (Markov baseline)
- predicts next steps
- browser automation using Playwright

## features
- markov predictor (top-K + confidence)
- logs to SQLite
- FastAPI endpoints: /metrics, /transations/top

## how to run: 
1. run `python -m venv .venv && source .venv/bin/activate`
2. run `pip install -e ".[dev]"`
3. run `playwright install`
4. run `python demo/run_demo.py`
5. run `uvicorn flowpredict.main:app --reload`