import os
import sys
from classify_questions import classify_file_with_model

# Ensure siliconflow client path is importable (classify_questions already tries, but ensure here too)
project_client_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'llm-cot-siliconflow-py', 'src'))
if project_client_path not in sys.path:
    sys.path.insert(0, project_client_path)

try:
    from siliconflow_client import SiliconflowClient
    HAVE_SF = True
except Exception as e:
    print(f"Failed to import SiliconflowClient: {e}")
    HAVE_SF = False

if not HAVE_SF:
    raise SystemExit("SiliconflowClient not available. Ensure llm-cot-siliconflow-py/src is present and importable.")

# Initialize client using default model
model_name = "Qwen/Qwen2-7B-Instruct"
client = SiliconflowClient(model_name=model_name)

source_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'dev'))
target_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'dev_labeled'))

os.makedirs(target_dir, exist_ok=True)

files = [f for f in os.listdir(source_dir) if f.endswith('.csv')]
print(f"Found {len(files)} files in {source_dir}. Running pilot (first 10 rows per file) using model {model_name}.")

for f in files:
    src = os.path.join(source_dir, f)
    tgt = os.path.join(target_dir, f)
    print(f"\nProcessing {src} -> {tgt}")
    classify_file_with_model(src, tgt, client=client, max_examples=10)

print('\nPilot classification finished.')
