from run_evaluation import run_evaluation

if __name__ == '__main__':
    # Run only for English samples to complete the previous run
    run_evaluation(models=["Qwen/Qwen2-7B-Instruct"], strategies=["zero_shot","few_shot","zero_shot_cot","few_shot_cot"], languages=['en'], samples_per_lang=50, delay=0.6)
