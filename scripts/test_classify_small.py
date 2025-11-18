from classify_questions import classify_file_with_model
import os

base = os.path.join(os.path.dirname(__file__), '..', 'data', 'dev')
src = os.path.abspath(os.path.join(base, 'agronomy.csv'))

tgt_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'dev_labeled'))
os.makedirs(tgt_dir, exist_ok=True)
tgt = os.path.join(tgt_dir, 'agronomy.csv')

print(f"Running small classification test: {src} -> {tgt} (first 10 rows)")
# max_examples=10
classify_file_with_model(src, tgt, client=None, max_examples=10)
print('Done')
