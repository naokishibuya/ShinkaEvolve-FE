"""Evolution runner for Nikkei-225 hedging experiments."""
import argparse
import subprocess
import sys
from pathlib import Path
from shinka.core.runner import EvolutionConfig, EvolutionRunner
from shinka.database.dbase import DatabaseConfig
from shinka.launch import LocalJobConfig


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ShinkaEvolve on Nikkei hedging task")
    parser.add_argument("--results_dir", default="results/nikkei_hedger")
    parser.add_argument("--scenario_dir", default="examples/nikkei_hedger/.scenarios/nikkei_day21")
    parser.add_argument("--strike", type=float, default=33000.0)
    parser.add_argument("--maturity_days", type=int, default=21)
    parser.add_argument("--hedge_ratio", type=float, default=1.0)
    parser.add_argument("--rebalance_steps", type=int, default=1)
    parser.add_argument("--transaction_cost_bps", type=float, default=5.0)
    parser.add_argument("--runs", type=int, default=None)
    parser.add_argument("--holdout_scenario_dir", default=None)
    parser.add_argument("--holdout_runs", type=int, default=None)
    args = parser.parse_args()

    evo_config = EvolutionConfig(
        init_program_path="examples/nikkei_hedger/initial.py",
        results_dir=args.results_dir,
        patch_types=["diff", "full"],
        patch_type_probs=[0.6, 0.4],
        num_generations=30,
        max_parallel_jobs=2,
        max_patch_resamples=2,
        max_patch_attempts=2,
        job_type="local",
        language="python",
        llm_models=["ollama::codellama:7b"],
        llm_kwargs=dict(temperatures=[0.0, 0.4], max_tokens=2048),
        embedding_model="ollama::nomic-embed-text",
        code_embed_sim_threshold=0.995,
        meta_rec_interval=10,
        meta_llm_models=["ollama::codellama:7b"],
        meta_llm_kwargs=dict(temperatures=[0.0], max_tokens=1024),
    )

    db_config = DatabaseConfig(
        db_path=str(Path(args.results_dir) / "evolution_db.sqlite"),
        num_islands=2,
        archive_size=40,
        elite_selection_ratio=0.3,
        num_archive_inspirations=4,
        num_top_k_inspirations=2,
        migration_interval=10,
        migration_rate=0.1,
        island_elitism=True,
        parent_selection_strategy="weighted",
        parent_selection_lambda=10.0,
    )

    extra_cmd_args: dict[str, str | float | int] = {
        "scenario_dir": args.scenario_dir,
        "strike": args.strike,
        "maturity_days": args.maturity_days,
        "hedge_ratio": args.hedge_ratio,
        "rebalance_steps": args.rebalance_steps,
        "transaction_cost_bps": args.transaction_cost_bps,
    }
    if args.runs is not None:
        extra_cmd_args["runs"] = args.runs

    job_config = LocalJobConfig(
        eval_program_path="examples/nikkei_hedger/evaluate.py",
        extra_cmd_args=extra_cmd_args,
    )

    runner = EvolutionRunner(
        evo_config=evo_config,
        job_config=job_config,
        db_config=db_config,
        verbose=True,
    )
    runner.run()

    if args.holdout_scenario_dir:
        best_program = Path(args.results_dir) / "best" / "main.py"
        if best_program.exists():
            holdout_dir = Path(args.results_dir) / "holdout_eval"
            holdout_dir.mkdir(parents=True, exist_ok=True)
            eval_cmd = [
                sys.executable,
                "examples/nikkei_hedger/evaluate.py",
                "--program_path",
                str(best_program),
                "--results_dir",
                str(holdout_dir),
                "--scenario_dir",
                args.holdout_scenario_dir,
                "--strike",
                str(args.strike),
                "--maturity_days",
                str(args.maturity_days),
                "--hedge_ratio",
                str(args.hedge_ratio),
                "--rebalance_steps",
                str(args.rebalance_steps),
                "--transaction_cost_bps",
                str(args.transaction_cost_bps),
            ]
            if args.holdout_runs is not None:
                eval_cmd.extend(["--runs", str(args.holdout_runs)])
            subprocess.run(eval_cmd, check=True)
        else:
            print("Best program not found; skipping holdout evaluation.", file=sys.stderr)


if __name__ == "__main__":
    main()
