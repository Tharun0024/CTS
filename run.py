import os
import sys
import argparse
import subprocess

def run_command(command: str):
    """Utility to run shell commands and stream output."""
    print(f"\nExecuting: {command}")
    try:
        # Use shell=True for windows compatibility
        res = subprocess.run(command, shell=True, check=True)
        return res.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Master Runner for Prior Authorization Policy Retrieval RAG System"
    )
    
    parser.add_argument(
        "--build-index",
        action="store_true",
        help="Run normalization, chunking, and index building scripts."
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Execute the Pytest test suite."
    )
    parser.add_argument(
        "--evaluate",
        action="store_true",
        help="Run the policy retrieval evaluation script."
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run system benchmarks (latencies, RAM/CPU, storage sizes)."
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Start the FastAPI prior authorization triage API service."
    )
    
    args = parser.parse_args()
    
    # If no flags are passed, show help
    if not any(vars(args).values()):
        parser.print_help()
        sys.exit(0)
        
    success = True
    
    if args.build_index:
        print("\n=== STEP: BUILDING SEARCH INDEXES ===")
        success = success and run_command("python -m scripts.build_index")
        
    if args.test:
        print("\n=== STEP: RUNNING PYTEST SUITE ===")
        success = success and run_command("python -m pytest")
        
    if args.evaluate:
        print("\n=== STEP: RUNNING EVALUATION SUITE ===")
        success = success and run_command("python -m scripts.evaluate")
        
    if args.benchmark:
        print("\n=== STEP: RUNNING BENCHMARKS ===")
        success = success and run_command("python -m scripts.benchmark")
        
    if args.serve:
        print("\n=== STEP: STARTING FASTAPI TRIAGE SERVICE ===")
        # Run uvicorn on localhost port 8000
        run_command("uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload")
        
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
