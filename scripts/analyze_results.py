import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

RESULTS_JSONL = os.path.join('results','structured_results.jsonl')
SUMMARY_CSV = os.path.join('results','structured_summary.csv')
PLOTS_DIR = os.path.join('results','plots')
os.makedirs(PLOTS_DIR, exist_ok=True)


def load_records(jsonl_path):
    rows = []
    if not os.path.exists(jsonl_path):
        print(f"No results file: {jsonl_path}")
        return pd.DataFrame()
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return pd.DataFrame(rows)


def compute_metrics(df):
    # Ensure fields
    df['is_correct'] = df['is_correct'].astype(bool)
    df['predicted_self_judgment'] = df['predicted_self_judgment'].fillna('').astype(str)
    df['reason_length'] = pd.to_numeric(df.get('reason_length', 0), errors='coerce').fillna(0).astype(int)

    # agreement: whether model's self_judgment equals actual correctness
    def judgment_matches(row):
        sj = row['predicted_self_judgment']
        if sj not in ['correct','incorrect']:
            return False
        return (sj == 'correct') == row['is_correct']

    df['self_judgment_matches'] = df.apply(judgment_matches, axis=1)

    # group metrics by model/strategy/language/category
    group_cols = ['model','strategy','language','category']
    agg = df.groupby(group_cols).agg(
        n_samples=('is_correct','size'),
        accuracy=('is_correct','mean'),
        self_judgment_agreement=('self_judgment_matches','mean'),
        avg_reason_length=('reason_length','mean'),
        median_reason_length=('reason_length','median')
    ).reset_index()
    return df, agg


def plot_metrics(agg):
    # accuracy heatmap per model x strategy for each language
    for lang in agg['language'].unique():
        sub = agg[agg['language']==lang]
        if sub.empty:
            continue
        pivot = sub.pivot_table(index='model', columns='strategy', values='accuracy')
        plt.figure(figsize=(8, max(2, pivot.shape[0]*0.5)))
        sns.heatmap(pivot, annot=True, fmt='.2f', cmap='viridis')
        plt.title(f'Accuracy heatmap ({lang})')
        out = os.path.join(PLOTS_DIR, f'accuracy_heatmap_{lang}.png')
        plt.tight_layout()
        plt.savefig(out)
        plt.close()

    # self_judgment agreement bar
    for lang in agg['language'].unique():
        sub = agg[agg['language']==lang]
        plt.figure(figsize=(10,4))
        sns.barplot(data=sub, x='strategy', y='self_judgment_agreement', hue='model')
        plt.ylim(0,1)
        plt.title(f'Self-judgment agreement by strategy ({lang})')
        out = os.path.join(PLOTS_DIR, f'self_judgment_agreement_{lang}.png')
        plt.tight_layout()
        plt.savefig(out)
        plt.close()

    # reason length distribution
    plt.figure(figsize=(8,4))
    sns.histplot(data=agg, x='avg_reason_length', bins=20)
    plt.title('Average reason length distribution (per group)')
    out = os.path.join(PLOTS_DIR, 'avg_reason_length_dist.png')
    plt.tight_layout()
    plt.savefig(out)
    plt.close()


def main():
    df = load_records(RESULTS_JSONL)
    if df.empty:
        print('No records to analyze.')
        return
    df, agg = compute_metrics(df)
    agg.to_csv(os.path.join('results','analysis_summary_by_group.csv'), index=False, encoding='utf-8-sig')
    # overall metrics
    overall = df.groupby(['model','language']).agg(
        total_samples=('is_correct','size'),
        accuracy=('is_correct','mean'),
        self_judgment_agreement=('self_judgment_matches','mean')
    ).reset_index()
    overall.to_csv(os.path.join('results','analysis_overall_by_model_lang.csv'), index=False, encoding='utf-8-sig')
    plot_metrics(agg)
    print('Analysis complete. Outputs in results/ (CSV and plots).')

if __name__ == '__main__':
    main()
