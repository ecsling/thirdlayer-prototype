"""Demo runner for recording and prediction modes."""
import asyncio
import json
import sys
from pathlib import Path
from playwright.async_api import async_playwright

from thirdlayer_prototype.db.storage import Storage
from thirdlayer_prototype.agent.executor import Executor
from thirdlayer_prototype.agent.loop import AgentLoop
from demo.wikipedia_workflow import get_wikipedia_workflow


async def run_recording_mode():
    """Record Wikipedia workflow and store transitions."""
    print("=== RECORDING MODE ===\n")
    
    storage = Storage("thirdlayer.db")
    storage.connect()
    
    workflow = get_wikipedia_workflow()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        executor = Executor(page)
        
        print(f"Recording {len(workflow)} actions...\n")
        
        for i, action in enumerate(workflow):
            print(f"Step {i+1}: {action}")
            result = await executor.execute(action)
            
            if result.success:
                print(f"  ✓ Success")
                if result.extracted_text:
                    print(f"  Extracted: {result.extracted_text[:100]}...")
                
                storage.record_action(action, url=page.url, success=True)
                
                if i > 0:
                    storage.record_transition_first_order(workflow[i-1], action)
                
                if i > 1:
                    storage.record_transition_second_order(workflow[i-2], workflow[i-1], action)
            else:
                print(f"  ✗ Failed: {result.error}")
                storage.record_action(action, url=page.url, success=False)
            
            print()
            await asyncio.sleep(1)
        
        await browser.close()
    
    print(f"Total transitions recorded: {storage.get_total_transition_count()}")
    storage.close()
    print("\n=== RECORDING COMPLETE ===\n")


async def run_prediction_mode():
    """Run agent loop using learned transitions."""
    print("=== PREDICTION MODE ===\n")
    
    storage = Storage("thirdlayer.db")
    storage.connect()
    
    total_transitions = storage.get_total_transition_count()
    if total_transitions == 0:
        print("No transitions in database. Run recording mode first.")
        storage.close()
        return
    
    print(f"Loaded {total_transitions} transitions from database\n")
    
    workflow = get_wikipedia_workflow()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        agent = AgentLoop(
            page=page,
            storage=storage,
            confidence_threshold=0.3,
            dry_run=False,
        )
        
        first_action = workflow[0]
        print(f"Executing initial action: {first_action}")
        executor = Executor(page)
        result = await executor.execute(first_action)
        
        if result.success:
            print(f"  ✓ Success\n")
            agent.add_action_to_history(first_action)
        else:
            print(f"  ✗ Failed: {result.error}\n")
            await browser.close()
            storage.close()
            return
        
        await asyncio.sleep(1)
        
        for i in range(1, len(workflow)):
            ground_truth = workflow[i]
            print(f"\n--- Step {i+1} ---")
            print(f"Ground truth: {ground_truth}")
            
            step_result = await agent.step(
                use_second_order=True,
                ground_truth_action=ground_truth,
            )
            
            if step_result["predictions"]:
                pred = step_result["predictions"][0]
                print(f"Predicted: {pred['action']['type']}")
                print(f"Confidence: {pred['confidence']:.2%}")
                print(f"Match: {step_result.get('ground_truth_match', 'N/A')}")
            else:
                print("No predictions available")
            
            if step_result["plan"]["should_execute"]:
                print(f"Decision: EXECUTE")
                if step_result["validation"]:
                    print(f"Validation: {step_result['validation']['valid']}")
                if step_result["execution"]:
                    exec_result = step_result["execution"]
                    if exec_result.get("attempted"):
                        print(f"Execution: {'SUCCESS' if exec_result['success'] else 'FAILED'}")
                        if not exec_result['success']:
                            print(f"Error: {exec_result.get('error')}")
            else:
                print(f"Decision: SKIP ({step_result['plan']['reason']})")
            
            print(f"Decision time: {step_result['decision_time_ms']:.1f}ms")
            
            await asyncio.sleep(1)
        
        await browser.close()
    
    print("\n=== FINAL METRICS ===")
    metrics = agent.get_metrics()
    print(json.dumps(metrics, indent=2))
    
    storage.close()
    print("\n=== PREDICTION COMPLETE ===\n")


async def main():
    """Main demo entrypoint."""
    if len(sys.argv) < 2:
        print("Usage: python demo/run_demo.py [record|predict]")
        sys.exit(1)
    
    mode = sys.argv[1]
    
    if mode == "record":
        await run_recording_mode()
    elif mode == "predict":
        await run_prediction_mode()
    else:
        print(f"Unknown mode: {mode}")
        print("Usage: python demo/run_demo.py [record|predict]")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
