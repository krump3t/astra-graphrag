#!/usr/bin/env python
"""Debug script to see COMPLETE prompt sent to LLM."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.langgraph.workflow import build_stub_workflow
from services.config import get_settings

# Run a single query
workflow = build_stub_workflow()
result = workflow("What petrophysical curves are available for well 15_9-13?", None)

# Load the prompt template
settings = get_settings()
prompt_path = ROOT / "configs" / "prompts" / "base_prompt.txt"
with open(prompt_path) as f:
    prompt_template = f.read()

# Build actual prompt
context = "\n".join(result.retrieved)
question = "What petrophysical curves are available for well 15_9-13?"
actual_prompt = prompt_template.replace("{{context}}", context).replace("{{question}}", question)

print("="*80)
print("COMPLETE PROMPT SENT TO LLM:")
print("="*80)
print(actual_prompt[:3000])  # First 3000 chars
print("\n... (truncated)")

print("\n" + "="*80)
print("LLM RESPONSE:")
print("="*80)
print(result.response)
