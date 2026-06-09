import subprocess
import time
import sys

processes = []

def start_process(command, name):
    print(f"Starting {name} with command: {command}...")
    p = subprocess.Popen(command, shell=True)
    processes.append((p, name))
    return p

try:
    # 1. Start Registry
    start_process("uv run python -m registry", "Registry")
    time.sleep(2)

    # 2. Start Leaf Agents
    start_process("uv run python -m tax_agent", "Tax Agent")
    start_process("uv run python -m compliance_agent", "Compliance Agent")
    time.sleep(3)

    # 3. Start Law Agent (Orchestrator)
    start_process("uv run python -m law_agent", "Law Agent")
    time.sleep(3)

    # 4. Start Customer Agent (Entry point)
    start_process("uv run python -m customer_agent", "Customer Agent")
    
    print("\nAll services started successfully!")
    print("Run test client in another terminal: uv run python test_client.py")
    print("Press Ctrl+C to terminate all processes...\n")
    
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\nTerminating all services...")
    for p, name in processes:
        print(f"Stopping {name}...")
        p.terminate()
        p.wait()
    print("All services stopped.")
