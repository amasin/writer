import sys
import os
# ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from orchestrator import WriterAgentOrchestrator

if __name__ == '__main__':
    orch = WriterAgentOrchestrator()
    result = orch.orchestrate("Artificial Intelligence", output_title_only=False)
    print("--- RESULT ---")
    print(result)
