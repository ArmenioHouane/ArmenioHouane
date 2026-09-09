"""Generate yearly charts for the profile README.

Outputs (committed to the repo):
  assets/wakatime_languages.png  - WakaTime all-time languages (hours) as a bar chart
  assets/timeline_yearly.png     - GitHub commits per year (by year, NOT by quarter)

Env:
  WAKATIME_API_KEY - WakaTime API key (same secret used by waka-readme-stats)
  GH_TOKEN / GITHUB_TOKEN - GitHub token (PAT with `repo` scope preferred)
  GITHUB_USERNAME - defaults to ArmenioHouane

The script never fails the workflow: on any API error it renders a
placeholder chart with the error message so the README images keep working.
"""
from __future__ import annotations

import base64
import datetime as dt
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import requests

USERNAME = os.environ.get("GITHUB_USERNAME", "ArmenioHouane")
WAKA_KEY = os.environ.get("WAKATIME_API_KEY", "")
GH_TOKEN = os.environ.get("GH_TOKEN", "") or os.environ.get("GITHUB_TOKEN", "")

ASSETS = Path(__file__).resolve().parent.parent / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

DARK_BG = "#0d1117"
TEXT_COLOR = "#c9d1d9"
BAR_COLOR = "#58a6ff"


def _style(ax: plt.Axes) -> None:
    ax.set_facecolor(DARK_BG)
    ax.tick_params(colors=TEXT_COLOR)
    for spine in ax.spines.values():
        spine.set_color("#30363d")
    ax.yaxis.label.set_color(TEXT_COLOR)
    ax.xaxis.label.set_color(TEXT_COLOR)
    ax.title.set_color(TEXT_COLOR)


def _placeholder(path: Path, title: str, message: str) -> None:
    fig, ax = plt.subplots(figsize=(8, 3))
    fig.patch.set_facecolor(DARK_BG)
    _style(ax)
    ax.set_title(title)
    ax.text(0.5, 0.5, message, ha="center", va="center", color=TEXT_COLOR, wrap=True)
    ax.set_xticks([])
    ax.set_yticks([])
    fig.tight_layout()
    fig.savefig(path, facecolor=DARK_BG, dpi=120)
    plt.close(fig)
    print(f"placeholder -> {path}: {message}")


def wakatime_languages() -> None:
    """Fetch WakaTime all-time languages and render a bar chart."""
    out = ASSETS / "wakatime_languages.png"
    if not WAKA_KEY:
        _placeholder(out, "WakaTime — tempo por linguagem", "WAKATIME_API_KEY ausente")
        return
    try:
        token = base64.b64encode(f"{WAKA_KEY}:".encode()).decode()
        r = requests.get(
            "https://wakatime.com/api/v1/users/current/stats/all_time",
            headers={"Authorization": f"Basic {token}"},
            timeout=30,
        )
        r.raise_for_status()
        langs = (r.json().get("data") or {}).get("languages") or []
    except Exception as exc:  # keep README images working even on API errors
        _placeholder(out, "WakaTime — tempo por linguagem", f"WakaTime API: {exc}")
        return

    if not langs:
        _placeholder(out, "WakaTime — tempo por linguagem", "Sem dados all-time no WakaTime")
        return

    top = langs[:8]
    names = [l.get("name", "?") for l in top]
    hours = [(l.get("total_seconds", 0) or 0) / 3600 for l in top]

    fig, ax = plt.subplots(figsize=(8, max(3, 0.6 * len(names) + 1.5)))
    fig.patch.set_facecolor(DARK_BG)
    _style(ax)
    y = range(len(names))
    ax.barh(list(y), hours, color=BAR_COLOR)
    ax.set_yticks(list(y))
    ax.set_yticklabels(names)
    ax.invert_yaxis()
    ax.set_xlabel("horas (all-time)")
    ax.set_title("WakaTime — tempo por linguagem")
    for i, h in enumerate(hours):
        ax.text(h, i, f"  {h:,.0f}h", va="center", color=TEXT_COLOR)
    fig.tight_layout()
    fig.savefig(out, facecolor=DARK_BG, dpi=120)
    plt.close(fig)
    print(f"wrote {out} ({len(names)} linguagens)")


def yearly_timeline() -> None:
    """Render GitHub commits per year (year buckets, no quarters)."""
    out = ASSETS / "timeline_yearly.png"
    now = dt.datetime.now(dt.timezone.utc).year
    years = list(range(max(2020, now - 5), now + 1))

    counts: dict[int, int] = {}
    headers = {"Accept": "application/vnd.github+json"}
    if GH_TOKEN:
        headers["Authorization"] = f"Bearer {GH_TOKEN}"
    try:
        with requests.Session() as s:
            s.headers.update(headers)
            for year in years:
                q = f"author:{USERNAME} author-date:{year}-01-01..{year}-12-31"
                r = s.get(
                    "https://api.github.com/search/commits",
                    params={"q": q, "per_page": 1},
                    timeout=30,
                )
                if r.status_code in (401, 403, 422):
                    raise RuntimeError(f"GitHub search commits: {r.status_code}")
                r.raise_for_status()
                counts[year] = int((r.json() or {}).get("total_count", 0))
    except Exception as exc:
        _placeholder(out, "Timeline — commits por ano", f"GitHub API: {exc}")
        return

    fig, ax = plt.subplots(figsize=(8, 3.5))
    fig.patch.set_facecolor(DARK_BG)
    _style(ax)
    labels = [str(y) for y in years]
    values = [counts.get(y, 0) for y in years]
    bars = ax.bar(labels, values, color=BAR_COLOR)
    ax.set_ylabel("commits")
    ax.set_title("Timeline — commits por ano")
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{v}",
                ha="center", va="bottom", color=TEXT_COLOR)
    fig.tight_layout()
    fig.savefig(out, facecolor=DARK_BG, dpi=120)
    plt.close(fig)
    print(f"wrote {out}: {counts}")


if __name__ == "__main__":
    wakatime_languages()
    yearly_timeline()
