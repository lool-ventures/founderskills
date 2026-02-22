#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Generate self-contained HTML visualization from deck review JSON artifacts.

Outputs HTML (not JSON). See compose_report.py for JSON output.

Usage:
    python visualize.py --dir ./deck-review-acme-corp/
    python visualize.py --dir ./deck-review-acme-corp/ -o report.html
"""

from __future__ import annotations

import argparse
import html
import json
import math
import os
import sys
from typing import Any, TypeGuard

# ---------------------------------------------------------------------------
# Artifact loading infrastructure
# ---------------------------------------------------------------------------

_CORRUPT: dict[str, Any] = {"__corrupt__": True}

REQUIRED_ARTIFACTS = [
    "deck_inventory.json",
    "stage_profile.json",
    "slide_reviews.json",
    "checklist.json",
]


def _load_artifact(dir_path: str, name: str) -> dict[str, Any] | None:
    """Load a JSON artifact. Returns None if missing, _CORRUPT if unparseable."""
    path = os.path.join(dir_path, name)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)  # type: ignore[no-any-return]
    except (json.JSONDecodeError, OSError):
        return _CORRUPT


def _is_stub(data: dict[str, Any] | None) -> bool:
    """Check if artifact is a stub (intentionally skipped)."""
    return isinstance(data, dict) and data.get("skipped") is True


def _usable(data: dict[str, Any] | None) -> TypeGuard[dict[str, Any]]:
    """Check if artifact is loaded, not corrupt, and not a stub."""
    return data is not None and data is not _CORRUPT and not _is_stub(data)


def _as_list(value: Any) -> list[Any]:
    """Coerce to list -- returns [] if not a list."""
    return value if isinstance(value, list) else []


def _as_dict(value: Any) -> dict[str, Any]:
    """Coerce to dict -- returns {} if not a dict."""
    return value if isinstance(value, dict) else {}


def _write_output(data: str, output_path: str | None) -> None:
    """Write raw HTML string to file or stdout."""
    if output_path:
        abs_path = os.path.abspath(output_path)
        parent = os.path.dirname(abs_path)
        if parent == "/":
            print(f"Error: output path resolves to root directory: {output_path}", file=sys.stderr)
            sys.exit(1)
        os.makedirs(parent, exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(data)
    else:
        sys.stdout.write(data)


# ---------------------------------------------------------------------------
# HTML safety helpers
# ---------------------------------------------------------------------------


def _esc(text: Any) -> str:
    """Escape text for safe HTML embedding."""
    return html.escape(str(text), quote=True)


def _num(value: Any, default: float = 0.0) -> float:
    """Safely convert to finite float."""
    try:
        result = float(value)
        if not math.isfinite(result):
            return default
        return result
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Color scheme
# ---------------------------------------------------------------------------

_COLOR_PRIMARY = "#21a2e3"
_COLOR_PASS = "#10b981"
_COLOR_WARN = "#f59e0b"
_COLOR_FAIL = "#ef4444"
_COLOR_NA = "#9ca3af"

# ---------------------------------------------------------------------------
# Framework type humanization
# ---------------------------------------------------------------------------

_FRAMEWORK_LABELS: dict[str, str] = {
    "purpose_traction": "Purpose",
    "problem": "Problem",
    "why_now": "Why Now",
    "solution_product": "Solution",
    "traction_kpis": "Traction",
    "market": "Market",
    "competition": "Competition",
    "business_model_pricing": "Business Model",
    "gtm": "Go-to-Market",
    "unit_economics": "Unit Economics",
    "team": "Team",
    "financials": "Financials",
    "ask_milestones": "Ask & Milestones",
    "extra": "Extra",
    "appendix": "Appendix",
}


def _humanize_framework(raw: str) -> str:
    """Convert maps_to value to human-readable label."""
    return _FRAMEWORK_LABELS.get(raw, raw.replace("_", " ").title())


# ---------------------------------------------------------------------------
# Canonical category order
# ---------------------------------------------------------------------------

_CANONICAL_CATEGORIES = [
    "Narrative Flow",
    "Slide Content",
    "Stage Fit",
    "Design & Readability",
    "Common Mistakes",
    "AI Company",
    "Diligence Readiness",
]


def _ordered_categories(by_category: dict[str, Any]) -> list[str]:
    """Return categories in canonical order, with unknown categories appended alphabetically."""
    canonical_set = set(_CANONICAL_CATEGORIES)
    unknown = sorted(k for k in by_category if k not in canonical_set)
    return [c for c in _CANONICAL_CATEGORIES if c in by_category] + unknown


# ---------------------------------------------------------------------------
# Placeholder helper
# ---------------------------------------------------------------------------


def _placeholder(message: str) -> str:
    """Return a styled placeholder div."""
    return f'<div class="placeholder">{_esc(message)}</div>'


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------


def _css() -> str:
    """Return the inline CSS for the report."""
    return """
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f0f14;
            color: #e4e4e7;
            line-height: 1.6;
            padding: 2rem;
            max-width: 960px;
            margin: 0 auto;
        }
        header {
            text-align: center;
            margin-bottom: 2rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid #27272a;
        }
        header h1 {
            font-size: 1.75rem;
            color: #21a2e3;
            margin-bottom: 0.25rem;
        }
        header .subtitle {
            font-size: 0.9rem;
            color: #71717a;
        }
        main { display: flex; flex-direction: column; gap: 2rem; }
        .chart-section {
            background: #18181b;
            border: 1px solid #27272a;
            border-radius: 12px;
            padding: 1.5rem;
        }
        .chart-section h2 {
            font-size: 1.1rem;
            color: #a1a1aa;
            margin-bottom: 1rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .chart-container {
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .placeholder {
            text-align: center;
            color: #71717a;
            padding: 2rem;
            font-style: italic;
        }
        footer {
            text-align: center;
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid #27272a;
            color: #52525b;
            font-size: 0.8rem;
        }
        footer a, header a { color: #21a2e3; text-decoration: none; }
        footer a:hover, header a:hover { text-decoration: underline; }
        svg text { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
    """


# ---------------------------------------------------------------------------
# Chart 1: Score Gauge (semi-circle)
# ---------------------------------------------------------------------------


def _chart_score_gauge(checklist: dict[str, Any] | None) -> str:
    """Render a semi-circle score gauge SVG.

    Uses stroked arcs inside an annular-semicircle clipPath.  The first
    and last zone arcs (and the score arc) extend 2% past the baseline
    so the clip hides endpoint artifacts.
    """
    if checklist is None:
        return _placeholder("No data available")
    if checklist is _CORRUPT:
        return _placeholder("Data unavailable")
    if _is_stub(checklist):
        reason = _esc(checklist.get("reason", "Skipped"))
        return _placeholder(f"Skipped: {reason}")

    summary = _as_dict(checklist.get("summary"))
    score_pct = _num(summary.get("score_pct"), 0.0)
    raw_status = str(summary.get("overall_status", "unknown")).strip()
    overall_status = _esc(raw_status.replace("_", " ").title())

    # Clamp score to 0-100
    score_pct = max(0.0, min(100.0, score_pct))

    # SVG dimensions
    w, h = 300, 180
    cx, cy = _num(w / 2), _num(h - 20)
    r = _num(110)
    band_w = 18
    outer_r = _num(r + band_w / 2)  # 119
    inner_r = _num(r - band_w / 2)  # 101

    def _angle(pct: float) -> float:
        """Convert percentage to angle (radians). 0%=pi, 100%=0."""
        return math.pi * (1 - _num(pct) / 100.0)

    def _arc_path(start_pct: float, end_pct: float) -> str:
        """SVG arc path along the centre radius."""
        a1, a2 = _angle(start_pct), _angle(end_pct)
        x1 = _num(cx + r * math.cos(a1))
        y1 = _num(cy - r * math.sin(a1))
        x2 = _num(cx + r * math.cos(a2))
        y2 = _num(cy - r * math.sin(a2))
        large = 1 if abs(end_pct - start_pct) > 50 else 0
        return f"M {x1:.2f} {y1:.2f} A {r:.2f} {r:.2f} 0 {large} 1 {x2:.2f} {y2:.2f}"

    # ClipPath: annular semicircle — the exact visible gauge shape
    clip = (
        f'<defs><clipPath id="gc">'
        f'<path d="M {_num(cx - outer_r):.2f} {cy:.2f} '
        f"A {outer_r:.2f} {outer_r:.2f} 0 1 1 "
        f"{_num(cx + outer_r):.2f} {cy:.2f} "
        f"L {_num(cx + inner_r):.2f} {cy:.2f} "
        f"A {inner_r:.2f} {inner_r:.2f} 0 1 0 "
        f'{_num(cx - inner_r):.2f} {cy:.2f} Z"/>'
        f"</clipPath></defs>"
    )

    # Zone arcs — exact ranges, clipPath handles baseline edges
    zones = [
        (0, 50, _COLOR_FAIL),
        (50, 70, _COLOR_WARN),
        (70, 85, "#34d399"),
        (85, 100, _COLOR_PASS),
    ]
    arcs = []
    for z_start, z_end, color in zones:
        arcs.append(
            f'<path d="{_esc(_arc_path(z_start, z_end))}" fill="none" '
            f'stroke="{_esc(color)}" stroke-width="{band_w}" '
            f'opacity="0.25"/>'
        )

    # Needle
    needle_angle = _angle(score_pct)
    nx = _num(cx + (inner_r - 20) * math.cos(needle_angle))
    ny = _num(cy - (inner_r - 20) * math.sin(needle_angle))
    needle = (
        f'<line x1="{cx:.2f}" y1="{cy:.2f}" x2="{nx:.2f}" y2="{ny:.2f}" '
        f'stroke="{_esc(_COLOR_PRIMARY)}" stroke-width="3" '
        f'stroke-linecap="round"/>'
        f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="5" '
        f'fill="{_esc(_COLOR_PRIMARY)}"/>'
    )

    # Score text
    score_text = (
        f'<text x="{cx:.2f}" y="{_num(cy - 30):.2f}" '
        f'text-anchor="middle" font-size="28" font-weight="700" '
        f'fill="#e4e4e7">{_esc(f"{score_pct:.0f}")}%</text>'
        f'<text x="{cx:.2f}" y="{_num(cy - 8):.2f}" '
        f'text-anchor="middle" font-size="13" '
        f'fill="#a1a1aa">{overall_status}</text>'
    )

    # Threshold labels
    labels = ""
    label_r = _num(outer_r + 12)
    for pct, label in [(0, "0"), (50, "50"), (70, "70"), (85, "85"), (100, "100")]:
        a = _angle(pct)
        lx = _num(cx + label_r * math.cos(a))
        ly = _num(cy - label_r * math.sin(a))
        labels += (
            f'<text x="{lx:.2f}" y="{ly:.2f}" text-anchor="middle" font-size="9" fill="#71717a">{_esc(label)}</text>'
        )

    clipped = f'{clip}<g clip-path="url(#gc)">{"".join(arcs)}</g>'

    svg = (
        f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" '
        f'width="{w}" height="{h}">'
        f"{clipped}"
        f"{needle}"
        f"{score_text}"
        f"{labels}"
        f"</svg>"
    )
    return f'<div class="chart-container">{svg}</div>'


# ---------------------------------------------------------------------------
# Chart 2: Category Radar Chart (7-point spider)
# ---------------------------------------------------------------------------


def _chart_radar(checklist: dict[str, Any] | None) -> str:
    """Render a 7-point radar/spider chart SVG."""
    if checklist is None:
        return _placeholder("No data available")
    if checklist is _CORRUPT:
        return _placeholder("Data unavailable")
    if _is_stub(checklist):
        reason = _esc(checklist.get("reason", "Skipped"))
        return _placeholder(f"Skipped: {reason}")

    summary = _as_dict(checklist.get("summary"))
    by_category = _as_dict(summary.get("by_category"))

    if not by_category:
        return _placeholder("No category data available")

    categories = _ordered_categories(by_category)
    n = len(categories)
    if n == 0:
        return _placeholder("No category data available")

    # Compute pass rates
    pass_rates: list[float] = []
    for cat in categories:
        counts = _as_dict(by_category.get(cat))
        p = _num(counts.get("pass"), 0)
        f = _num(counts.get("fail"), 0)
        w = _num(counts.get("warn"), 0)
        denom = p + f + w
        if denom > 0:
            pass_rates.append(_num((p / denom) * 100.0))
        else:
            pass_rates.append(0.0)

    # SVG dimensions — wide viewBox to avoid label clipping
    vw, vh = 460, 360
    cx = _num(vw / 2)
    cy = _num(vh / 2)
    max_r = _num(100)

    # Build grid rings (25%, 50%, 75%, 100%)
    grid_lines = ""
    for pct in [25, 50, 75, 100]:
        ring_r = _num(max_r * pct / 100)
        points_str = ""
        for i in range(n):
            angle = _num(2 * math.pi * i / n - math.pi / 2)
            px = _num(cx + ring_r * math.cos(angle))
            py = _num(cy + ring_r * math.sin(angle))
            points_str += f"{px:.2f},{py:.2f} "
        grid_lines += f'<polygon points="{_esc(points_str.strip())}" fill="none" stroke="#27272a" stroke-width="1"/>'

    # Axis lines
    axis_lines = ""
    for i in range(n):
        angle = _num(2 * math.pi * i / n - math.pi / 2)
        ax = _num(cx + max_r * math.cos(angle))
        ay = _num(cy + max_r * math.sin(angle))
        axis_lines += (
            f'<line x1="{cx:.2f}" y1="{cy:.2f}" x2="{ax:.2f}" y2="{ay:.2f}" stroke="#27272a" stroke-width="1"/>'
        )

    # Data polygon
    data_points_str = ""
    for i in range(n):
        angle = _num(2 * math.pi * i / n - math.pi / 2)
        dr = _num(max_r * pass_rates[i] / 100.0)
        dx = _num(cx + dr * math.cos(angle))
        dy = _num(cy + dr * math.sin(angle))
        data_points_str += f"{dx:.2f},{dy:.2f} "

    data_polygon = (
        f'<polygon points="{_esc(data_points_str.strip())}" '
        f'fill="{_esc(_COLOR_PRIMARY)}" fill-opacity="0.25" '
        f'stroke="{_esc(_COLOR_PRIMARY)}" stroke-width="2"/>'
    )

    # Data points (dots)
    data_dots = ""
    for i in range(n):
        angle = _num(2 * math.pi * i / n - math.pi / 2)
        dr = _num(max_r * pass_rates[i] / 100.0)
        dx = _num(cx + dr * math.cos(angle))
        dy = _num(cy + dr * math.sin(angle))
        data_dots += f'<circle cx="{dx:.2f}" cy="{dy:.2f}" r="4" fill="{_esc(_COLOR_PRIMARY)}"/>'

    # Category labels
    labels = ""
    for i in range(n):
        angle = _num(2 * math.pi * i / n - math.pi / 2)
        label_r = _num(max_r + 24)
        lx = _num(cx + label_r * math.cos(angle))
        ly = _num(cy + label_r * math.sin(angle))
        anchor = "middle"
        if abs(math.cos(angle)) > 0.3:
            anchor = "start" if math.cos(angle) > 0 else "end"
        rate_str = f"{pass_rates[i]:.0f}%"
        labels += (
            f'<text x="{lx:.2f}" y="{ly:.2f}" text-anchor="{_esc(anchor)}" '
            f'font-size="10" fill="#a1a1aa">'
            f"{_esc(categories[i])}</text>"
            f'<text x="{lx:.2f}" y="{_num(ly + 13):.2f}" text-anchor="{_esc(anchor)}" '
            f'font-size="9" fill="#71717a">{_esc(rate_str)}</text>'
        )

    svg = (
        f'<svg viewBox="0 0 {vw} {vh}" xmlns="http://www.w3.org/2000/svg" '
        f'width="{vw}" height="{vh}">'
        f"{grid_lines}"
        f"{axis_lines}"
        f"{data_polygon}"
        f"{data_dots}"
        f"{labels}"
        f"</svg>"
    )
    return f'<div class="chart-container">{svg}</div>'


# ---------------------------------------------------------------------------
# Chart 3: Category Breakdown (horizontal stacked bars)
# ---------------------------------------------------------------------------


def _chart_category_breakdown(checklist: dict[str, Any] | None) -> str:
    """Render horizontal stacked bars for category breakdown."""
    if checklist is None:
        return _placeholder("No data available")
    if checklist is _CORRUPT:
        return _placeholder("Data unavailable")
    if _is_stub(checklist):
        reason = _esc(checklist.get("reason", "Skipped"))
        return _placeholder(f"Skipped: {reason}")

    summary = _as_dict(checklist.get("summary"))
    by_category = _as_dict(summary.get("by_category"))

    if not by_category:
        return _placeholder("No category data available")

    categories = _ordered_categories(by_category)
    n = len(categories)
    if n == 0:
        return _placeholder("No category data available")

    # SVG dimensions
    label_width = 150
    bar_width = 400
    bar_height = 24
    gap = 8
    padding_top = 10
    total_width = label_width + bar_width + 20
    total_height = _num(padding_top + n * (bar_height + gap) + 40)

    bars_svg = ""
    for idx, cat in enumerate(categories):
        counts = _as_dict(by_category.get(cat))
        p = _num(counts.get("pass"), 0)
        f = _num(counts.get("fail"), 0)
        w = _num(counts.get("warn"), 0)
        na = _num(counts.get("not_applicable"), 0)
        total = p + f + w + na

        y = _num(padding_top + idx * (bar_height + gap))

        # Label
        bars_svg += (
            f'<text x="{_num(label_width - 8):.2f}" y="{_num(y + bar_height / 2 + 4):.2f}" '
            f'text-anchor="end" font-size="11" fill="#a1a1aa">{_esc(cat)}</text>'
        )

        if total <= 0:
            # Empty bar
            bars_svg += (
                f'<rect x="{_num(label_width):.2f}" y="{y:.2f}" '
                f'width="{_num(bar_width):.2f}" height="{_num(bar_height):.2f}" '
                f'rx="4" fill="#27272a"/>'
            )
            continue

        # Background
        bars_svg += (
            f'<rect x="{_num(label_width):.2f}" y="{y:.2f}" '
            f'width="{_num(bar_width):.2f}" height="{_num(bar_height):.2f}" '
            f'rx="4" fill="#27272a"/>'
        )

        # Stacked segments: pass, warn, fail, NA
        segments = [
            (p, _COLOR_PASS),
            (w, _COLOR_WARN),
            (f, _COLOR_FAIL),
            (na, _COLOR_NA),
        ]
        x_offset = _num(label_width)
        for seg_val, seg_color in segments:
            if seg_val <= 0:
                continue
            seg_width = _num(bar_width * seg_val / total)
            bars_svg += (
                f'<rect x="{x_offset:.2f}" y="{y:.2f}" '
                f'width="{seg_width:.2f}" height="{_num(bar_height):.2f}" '
                f'fill="{_esc(seg_color)}"/>'
            )
            x_offset = _num(x_offset + seg_width)

    # Legend
    legend_y = _num(padding_top + n * (bar_height + gap) + 10)
    legend_items = [
        ("Pass", _COLOR_PASS),
        ("Warn", _COLOR_WARN),
        ("Fail", _COLOR_FAIL),
        ("N/A", _COLOR_NA),
    ]
    lx = _num(label_width)
    legend_svg = ""
    for label, color in legend_items:
        legend_svg += (
            f'<rect x="{lx:.2f}" y="{legend_y:.2f}" width="12" height="12" rx="2" '
            f'fill="{_esc(color)}"/>'
            f'<text x="{_num(lx + 16):.2f}" y="{_num(legend_y + 10):.2f}" '
            f'font-size="10" fill="#a1a1aa">{_esc(label)}</text>'
        )
        lx = _num(lx + 60)

    svg = (
        f'<svg viewBox="0 0 {total_width} {total_height}" xmlns="http://www.w3.org/2000/svg" '
        f'width="{total_width}" height="{total_height:.0f}">'
        f"{bars_svg}"
        f"{legend_svg}"
        f"</svg>"
    )
    return f'<div class="chart-container">{svg}</div>'


# ---------------------------------------------------------------------------
# Chart 4: Slide Map (diverging bar chart)
# ---------------------------------------------------------------------------


def _chart_slide_map(
    reviews: dict[str, Any] | None,
    inventory: dict[str, Any] | None = None,
    stage_profile: dict[str, Any] | None = None,
) -> str:
    """Render a diverging bar chart — strengths extend right, weaknesses extend left."""
    if reviews is None:
        return _placeholder("No data available")
    if reviews is _CORRUPT:
        return _placeholder("Data unavailable")
    if _is_stub(reviews):
        reason = _esc(reviews.get("reason", "Skipped"))
        return _placeholder(f"Skipped: {reason}")

    review_list = _as_list(reviews.get("reviews"))
    if not review_list:
        return _placeholder("No slide reviews available")

    # Build slide data indexed by slide number (keep first occurrence)
    slide_data: dict[int, dict[str, Any]] = {}
    for review in review_list:
        if not isinstance(review, dict):
            continue
        num = int(_num(review.get("slide_number"), 0))
        if num <= 0:
            continue
        if num not in slide_data:
            slide_data[num] = {
                "strengths": len(_as_list(review.get("strengths"))),
                "weaknesses": len(_as_list(review.get("weaknesses"))),
                "recommendations": len(_as_list(review.get("recommendations"))),
                "maps_to": str(review.get("maps_to", "")),
            }

    if not slide_data:
        return _placeholder("No slide data available")

    # Build missing slides list
    missing_slides: list[dict[str, str]] = []
    for ms in _as_list(reviews.get("missing_slides")):
        if isinstance(ms, dict) and ms.get("expected_type"):
            missing_slides.append(
                {
                    "expected_type": str(ms["expected_type"]),
                    "importance": str(ms.get("importance", "")),
                }
            )

    # Build ordered row list: interleave present slides and missing slides
    # using expected_framework ordering when available
    rows: list[dict[str, Any]] = []

    expected_framework = _as_list(_as_dict(stage_profile).get("expected_framework")) if _usable(stage_profile) else []

    if expected_framework:
        slides_by_type: dict[str, list[int]] = {}
        for num, info in sorted(slide_data.items()):
            mt = info["maps_to"]
            slides_by_type.setdefault(mt, []).append(num)

        missing_types = {ms["expected_type"] for ms in missing_slides}
        missing_by_type = {ms["expected_type"]: ms for ms in missing_slides}
        placed_slides: set[int] = set()

        for framework_type in expected_framework:
            if framework_type in slides_by_type:
                for num in slides_by_type[framework_type]:
                    rows.append({"type": "present", "num": num, **slide_data[num]})
                    placed_slides.add(num)
            elif framework_type in missing_types:
                ms = missing_by_type[framework_type]
                rows.append(
                    {
                        "type": "missing",
                        "expected_type": ms["expected_type"],
                        "importance": ms["importance"],
                    }
                )

        for num in sorted(slide_data.keys()):
            if num not in placed_slides:
                rows.append({"type": "present", "num": num, **slide_data[num]})

        placed_missing = {r.get("expected_type") for r in rows if r["type"] == "missing"}
        for ms in missing_slides:
            if ms["expected_type"] not in placed_missing:
                rows.append(
                    {
                        "type": "missing",
                        "expected_type": ms["expected_type"],
                        "importance": ms["importance"],
                    }
                )
    else:
        for num in sorted(slide_data.keys()):
            rows.append({"type": "present", "num": num, **slide_data[num]})
        for ms in missing_slides:
            rows.append(
                {
                    "type": "missing",
                    "expected_type": ms["expected_type"],
                    "importance": ms["importance"],
                }
            )

    if not rows:
        return _placeholder("No slide data available")

    # Compute bar scaling
    max_count = 1
    for row in rows:
        if row["type"] == "present":
            max_count = max(max_count, row["strengths"], row["weaknesses"])

    # SVG dimensions
    label_w = 180
    bar_area_w = 400
    rec_w = 70
    row_h = 32
    row_gap = 4
    padding_top = 10
    padding_bottom = 40
    center_x = _num(label_w + bar_area_w / 2)
    half_bar = _num(bar_area_w / 2)
    total_w = label_w + bar_area_w + rec_w
    total_h = _num(padding_top + len(rows) * (row_h + row_gap) + padding_bottom)
    min_bar_for_inner_label = 30  # px — labels go inside bar when wide enough

    svg_parts: list[str] = []

    # Center axis line
    svg_parts.append(
        f'<line x1="{center_x:.1f}" y1="{padding_top}" '
        f'x2="{center_x:.1f}" y2="{_num(total_h - padding_bottom):.1f}" '
        f'stroke="#3f3f46" stroke-width="1"/>'
    )

    for idx, row in enumerate(rows):
        y = _num(padding_top + idx * (row_h + row_gap))
        mid_y = _num(y + row_h / 2)
        text_y = _num(mid_y + 4)

        # Zebra striping
        if idx % 2 == 1:
            svg_parts.append(
                f'<rect x="0" y="{y:.1f}" width="{total_w}" height="{row_h}" fill="#27272a" fill-opacity="0.5" rx="4"/>'
            )

        if row["type"] == "present":
            num = row["num"]
            maps_to = row.get("maps_to", "")
            label = _humanize_framework(maps_to) if maps_to else ""
            s_count = row["strengths"]
            w_count = row["weaknesses"]
            r_count = row["recommendations"]

            label_text = f"{num}"
            if label:
                label_text += f" \u00b7 {label}"
            svg_parts.append(
                f'<text x="{_num(label_w - 8):.1f}" y="{text_y:.1f}" '
                f'text-anchor="end" font-size="11" fill="#a1a1aa">'
                f"{_esc(label_text)}</text>"
            )

            if s_count > 0:
                bar_w = _num(half_bar * s_count / max_count)
                svg_parts.append(
                    f'<rect x="{center_x:.1f}" y="{_num(y + 4):.1f}" '
                    f'width="{bar_w:.1f}" height="{_num(row_h - 8):.1f}" '
                    f'rx="3" fill="{_esc(_COLOR_PASS)}"/>'
                )
                if bar_w >= min_bar_for_inner_label:
                    # Label inside bar (white text, right-aligned within bar)
                    svg_parts.append(
                        f'<text x="{_num(center_x + bar_w - 6):.1f}" y="{text_y:.1f}" '
                        f'text-anchor="end" font-size="10" fill="#fff" '
                        f'font-weight="600">{s_count}</text>'
                    )
                else:
                    # Label outside bar (colored text)
                    svg_parts.append(
                        f'<text x="{_num(center_x + bar_w + 4):.1f}" y="{text_y:.1f}" '
                        f'font-size="10" fill="{_esc(_COLOR_PASS)}" '
                        f'font-weight="600">{s_count}</text>'
                    )

            if w_count > 0:
                bar_w = _num(half_bar * w_count / max_count)
                svg_parts.append(
                    f'<rect x="{_num(center_x - bar_w):.1f}" y="{_num(y + 4):.1f}" '
                    f'width="{bar_w:.1f}" height="{_num(row_h - 8):.1f}" '
                    f'rx="3" fill="{_esc(_COLOR_FAIL)}"/>'
                )
                if bar_w >= min_bar_for_inner_label:
                    # Label inside bar (white text, left-aligned within bar)
                    svg_parts.append(
                        f'<text x="{_num(center_x - bar_w + 6):.1f}" y="{text_y:.1f}" '
                        f'font-size="10" fill="#fff" '
                        f'font-weight="600">{w_count}</text>'
                    )
                else:
                    # Label outside bar (colored text)
                    svg_parts.append(
                        f'<text x="{_num(center_x - bar_w - 4):.1f}" y="{text_y:.1f}" '
                        f'text-anchor="end" font-size="10" fill="{_esc(_COLOR_FAIL)}" '
                        f'font-weight="600">{w_count}</text>'
                    )

            if r_count > 0:
                rec_x = _num(label_w + bar_area_w + 14)
                svg_parts.append(
                    f'<text x="{rec_x:.1f}" y="{text_y:.1f}" '
                    f'font-size="10" fill="#71717a">'
                    f"{r_count} rec{'s' if r_count != 1 else ''}</text>"
                )

        elif row["type"] == "missing":
            expected_type = row.get("expected_type", "")
            importance = row.get("importance", "")
            label = _humanize_framework(expected_type) if expected_type else "Unknown"

            svg_parts.append(
                f'<text x="{_num(label_w - 8):.1f}" y="{text_y:.1f}" '
                f'text-anchor="end" font-size="11" fill="#52525b">'
                f"\u2014 \u00b7 {_esc(label)}</text>"
            )

            svg_parts.append(
                f'<line x1="{label_w}" y1="{mid_y:.1f}" '
                f'x2="{_num(label_w + bar_area_w):.1f}" y2="{mid_y:.1f}" '
                f'stroke="#52525b" stroke-width="1" stroke-dasharray="6,4"/>'
            )

            if importance:
                badge_label = importance.replace("_", " ")
                rec_x = _num(label_w + bar_area_w + 14)
                svg_parts.append(
                    f'<text x="{rec_x:.1f}" y="{text_y:.1f}" '
                    f'font-size="9" fill="#52525b" font-style="italic">'
                    f"{_esc(badge_label)}</text>"
                )

    # Legend
    legend_y = _num(total_h - padding_bottom + 16)
    legend_items: list[tuple[str, str, str]] = [
        (_COLOR_PASS, "rect", "Strengths"),
        (_COLOR_FAIL, "rect", "Weaknesses"),
        ("#52525b", "dash", "Missing expected slide"),
    ]
    lx = _num(label_w)
    legend_svg = ""
    for color, shape, label in legend_items:
        if shape == "rect":
            legend_svg += (
                f'<rect x="{lx:.1f}" y="{_num(legend_y - 8):.1f}" width="12" height="12" rx="2" fill="{_esc(color)}"/>'
            )
        else:
            legend_svg += (
                f'<line x1="{lx:.1f}" y1="{_num(legend_y - 2):.1f}" '
                f'x2="{_num(lx + 12):.1f}" y2="{_num(legend_y - 2):.1f}" '
                f'stroke="{_esc(color)}" stroke-width="2" stroke-dasharray="4,3"/>'
            )
        legend_svg += (
            f'<text x="{_num(lx + 16):.1f}" y="{legend_y:.1f}" font-size="10" fill="#a1a1aa">{_esc(label)}</text>'
        )
        lx = _num(lx + len(label) * 7 + 32)

    svg = (
        f'<svg viewBox="0 0 {total_w} {total_h:.0f}" '
        f'xmlns="http://www.w3.org/2000/svg" '
        f'width="{total_w}" height="{total_h:.0f}">'
        f"{''.join(svg_parts)}"
        f"{legend_svg}"
        f"</svg>"
    )
    return f'<div class="chart-container">{svg}</div>'


# ---------------------------------------------------------------------------
# HTML composition
# ---------------------------------------------------------------------------


def compose_html(dir_path: str) -> str:
    """Load artifacts and compose complete HTML report."""
    artifacts: dict[str, dict[str, Any] | None] = {}
    for name in REQUIRED_ARTIFACTS:
        artifacts[name] = _load_artifact(dir_path, name)

    inventory = artifacts.get("deck_inventory.json")
    checklist = artifacts.get("checklist.json")
    reviews = artifacts.get("slide_reviews.json")

    # Company name for title
    company_name = "Unknown Company"
    if _usable(inventory):
        company_name = str(inventory.get("company_name", "Unknown Company"))

    # Build header
    header_parts = [f"<h1>Deck Review: {_esc(company_name)}</h1>"]
    if _usable(inventory):
        date = _esc(inventory.get("review_date", ""))
        total_slides = _esc(str(inventory.get("total_slides", "?")))
        fmt = _esc(inventory.get("input_format", ""))
        header_parts.append(f'<div class="subtitle">{date} | {total_slides} slides | {fmt}</div>')

    header_parts.append(
        '<div class="subtitle">Generated by '
        '<a href="https://github.com/lool-ventures/founder-skills">founder skills</a>'
        ' by <a href="https://lool.vc">lool ventures</a>'
        " — Deck Review Agent</div>"
    )
    header_parts.append(
        '<div class="subtitle" style="font-style:italic;margin-top:0.5rem;">'
        "Scores and assessments are agent-generated against best-practice frameworks</div>"
    )

    header = "<header>" + "".join(header_parts) + "</header>"

    # Build chart sections
    gauge_section = f'<div class="chart-section"><h2>Overall Score</h2>{_chart_score_gauge(checklist)}</div>'

    radar_section = f'<div class="chart-section"><h2>Category Radar</h2>{_chart_radar(checklist)}</div>'

    breakdown_section = (
        f'<div class="chart-section"><h2>Category Breakdown</h2>{_chart_category_breakdown(checklist)}</div>'
    )

    stage_profile = artifacts.get("stage_profile.json")
    slide_map_chart = _chart_slide_map(reviews, inventory, stage_profile)
    slide_map_section = f'<div class="chart-section"><h2>Slide Map</h2>{slide_map_chart}</div>'

    main_content = f"<main>{gauge_section}{radar_section}{breakdown_section}{slide_map_section}</main>"

    footer = (
        "<footer>Generated by "
        '<a href="https://github.com/lool-ventures/founder-skills">founder skills</a>'
        ' by <a href="https://lool.vc">lool ventures</a>'
        " — Deck Review Agent</footer>"
    )

    html_doc = (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '    <meta charset="UTF-8">\n'
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f"    <title>Deck Review: {_esc(company_name)}</title>\n"
        f"    <style>{_css()}</style>\n"
        "</head>\n"
        "<body>\n"
        f"{header}\n"
        f"{main_content}\n"
        f"{footer}\n"
        "</body>\n"
        "</html>\n"
    )

    return html_doc


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    p = argparse.ArgumentParser(description="Generate HTML visualization from deck review artifacts")
    p.add_argument("-d", "--dir", required=True, help="Directory containing JSON artifacts")
    p.add_argument("--pretty", action="store_true", help="Accepted for compatibility (no-op)")
    p.add_argument("-o", "--output", help="Write HTML to file instead of stdout")
    return p.parse_args()


def main() -> None:
    """Entry point."""
    args = parse_args()

    if not os.path.isdir(args.dir):
        print(f"Error: directory not found: {args.dir}", file=sys.stderr)
        sys.exit(1)

    html_output = compose_html(args.dir)
    _write_output(html_output, args.output)


if __name__ == "__main__":
    main()
