from __future__ import annotations
import matplotlib
# Use non-interactive backend suitable for servers
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

def plot_table(df, x, y, kind: str = "bar", out_dir: str = "./charts") -> str:
    os.makedirs(out_dir, exist_ok=True)
    fname = f"chart_{abs(hash((tuple(df.columns), kind, x, y, len(df))))}.png"
    fpath = os.path.join(out_dir, fname)

    plt.figure()
    if kind == "line":
        plt.plot(df[x], df[y])
    elif kind == "scatter":
        plt.scatter(df[x], df[y])
    elif kind == "area":
        plt.fill_between(df[x], df[y], step="pre")
    else:
        plt.bar(df[x], df[y])
    plt.xlabel(x); plt.ylabel(y)
    plt.tight_layout(); plt.savefig(fpath); plt.close()
    return fpath