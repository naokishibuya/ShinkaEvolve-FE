"""We can also use shinka_visualize --port 8888 to visualize the results in a browser."""
import argparse
import matplotlib.pyplot as plt
from shinka.plots import plot_improvement
from shinka.utils import load_programs_to_df


parser = argparse.ArgumentParser(description="Visualize Nikkei Shock Evolution Results")
parser.add_argument("results_dir", type=str, help="Path to results directory")
args = parser.parse_args()

# Load results
df = load_programs_to_df(f"{args.results_dir}/evolution_db.sqlite")

# Quick stats
print(f"Best score: {df[df['correct']]['combined_score'].max():.3f}")
print(f"Total programs: {len(df)}")
print(f"Success rate: {df['correct'].mean():.1%}")

# Inspect best program
best = df[df['correct']].nlargest(1, 'combined_score').iloc[0]
print(f"\nBest program (Gen {best['generation']}):")
print(f"Score: {best['combined_score']:.3f}")
print(f"Patch: {best['patch_name']}")
print(f"\nFeedback:\n{best['text_feedback']}")

# Visualize
fig, ax = plt.subplots(figsize=(12, 8))
plot_improvement(df, fig=fig, ax=ax)
plt.show()
