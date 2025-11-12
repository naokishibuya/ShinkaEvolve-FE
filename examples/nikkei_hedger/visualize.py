"""Quick visualization utilities for Nikkei hedging scenarios."""
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from .scenarios import load_scenario


def plot_paths(path: str | Path, max_paths: int = 10) -> None:
    scenario = load_scenario(path)
    steps, total = scenario.spots.shape
    count = min(max_paths, total)
    xs = np.arange(steps)
    plt.figure(figsize=(10, 5))
    for col in range(count):
        plt.plot(xs, scenario.spots[:, col], alpha=0.7)
    plt.title(f"Spot paths ({count}/{total})")
    plt.xlabel("Step")
    plt.ylabel("Nikkei level")
    plt.tight_layout()
    plt.show()


def plot_vols(path: str | Path, max_paths: int = 10) -> None:
    scenario = load_scenario(path)
    steps, total = scenario.vols.shape
    count = min(max_paths, total)
    xs = np.arange(steps)
    plt.figure(figsize=(10, 4))
    for col in range(count):
        plt.plot(xs, scenario.vols[:, col], alpha=0.7)
    plt.title(f"Instantaneous vol paths ({count}/{total})")
    plt.xlabel("Step")
    plt.ylabel("Vol")
    plt.tight_layout()
    plt.show()
