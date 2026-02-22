#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Generate self-contained HTML visualization from IC simulation JSON artifacts.

Outputs HTML (not JSON). See compose_report.py for JSON output.

Usage:
    python visualize.py --dir ./ic-sim-acme-corp/
    python visualize.py --dir ./ic-sim-acme-corp/ -o report.html

Output: Raw HTML to stdout (or file with -o).
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
    "startup_profile.json",
    "fund_profile.json",
    "conflict_check.json",
    "discussion.json",
    "score_dimensions.json",
]

OPTIONAL_ARTIFACTS = [
    "prior_artifacts.json",
    "partner_assessment_visionary.json",
    "partner_assessment_operator.json",
    "partner_assessment_analyst.json",
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


# ---------------------------------------------------------------------------
# HTML safety helpers
# ---------------------------------------------------------------------------


def _esc(text: Any) -> str:
    """HTML-escape any value, safe for both text content and attributes."""
    return html.escape(str(text), quote=True)


def _num(value: Any, default: float = 0.0) -> float:
    """Coerce to finite float, returning default for non-numeric / non-finite."""
    try:
        result = float(value)
        if not math.isfinite(result):
            return default
        return result
    except (TypeError, ValueError):
        return default


def _smart_truncate(text: str, max_len: int = 250) -> str:
    """Truncate text at sentence boundary within max_len, falling back to word boundary."""
    if len(text) <= max_len:
        return text
    truncated = text[:max_len]
    best = -1
    for sep in (".", "!", "?"):
        pos = truncated.rfind(sep)
        if pos > best:
            best = pos
    if best > max_len // 3:
        return text[: best + 1]
    last_space = truncated.rfind(" ")
    if last_space > max_len // 3:
        return text[:last_space] + "..."
    return text[: max_len - 3] + "..."


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CANONICAL_CATEGORIES = [
    "Team",
    "Market",
    "Product",
    "Business Model",
    "Financials",
    "Risk",
    "Fund Fit",
]

_CANONICAL_PARTNERS = ["visionary", "operator", "analyst"]

_VERDICT_COLORS: dict[str, str] = {
    "invest": "#10b981",
    "more_diligence": "#f59e0b",
    "pass": "#ef4444",
    "hard_pass": "#ef4444",
}

_STATUS_COLORS: dict[str, str] = {
    "strong_conviction": "#10b981",
    "moderate_conviction": "#f59e0b",
    "concern": "#ef4444",
    "dealbreaker": "#b91c1c",
    "not_applicable": "#9ca3af",
}

_SEVERITY_COLORS: dict[str, str] = {
    "clear": "#10b981",
    "manageable": "#f59e0b",
    "blocking": "#ef4444",
}


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------


def _css() -> str:
    """Return the full CSS block for the report."""
    return """
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                         "Helvetica Neue", Arial, sans-serif;
            background: #0f172a; color: #e2e8f0; line-height: 1.6;
            padding: 2rem; max-width: 1100px; margin: 0 auto;
        }
        h1 { color: #21a2e3; font-size: 1.8rem; margin-bottom: 0.25rem; }
        h2 {
            color: #94a3b8; font-size: 1.2rem; margin: 2rem 0 1rem;
            border-bottom: 1px solid #1e293b; padding-bottom: 0.5rem;
        }
        .subtitle { color: #64748b; font-size: 0.9rem; margin-bottom: 2rem; }
        .chart-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem; }
        .chart-box {
            background: #1e293b; border-radius: 12px; padding: 1.5rem;
            border: 1px solid #334155;
        }
        .chart-box.full { grid-column: 1 / -1; }
        .partner-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }
        .partner-card {
            border-radius: 10px; padding: 1rem; border-left: 4px solid;
            background: #1e293b;
        }
        .partner-card h3 { font-size: 1rem; margin-bottom: 0.25rem; }
        .partner-card .verdict { font-size: 0.85rem; font-weight: 600; margin-bottom: 0.5rem; }
        .partner-card .rationale { font-size: 0.8rem; color: #94a3b8; }
        .badge {
            display: inline-block; padding: 0.25rem 0.75rem; border-radius: 9999px;
            font-size: 0.8rem; font-weight: 600; color: #fff;
        }
        .conflict-table { width: 100%; border-collapse: collapse; margin-top: 1rem; font-size: 0.85rem; }
        .conflict-table th { text-align: left; color: #94a3b8; padding: 0.5rem; border-bottom: 1px solid #334155; }
        .conflict-table td { padding: 0.5rem; border-bottom: 1px solid #1e293b; }
        .placeholder { color: #64748b; font-style: italic; padding: 2rem; text-align: center; }
        .footer {
            margin-top: 3rem; padding-top: 1rem;
            border-top: 1px solid #1e293b; color: #475569;
            font-size: 0.75rem; text-align: center;
        }
        .footer a { color: #21a2e3; text-decoration: none; }
        .chart-box h2 { border-bottom-color: #334155; margin-top: 0; }
        svg { max-width: 100%; height: auto; }
        @media (max-width: 768px) {
            body { padding: 1rem; }
            .chart-grid { grid-template-columns: 1fr; }
            .partner-grid { grid-template-columns: 1fr; }
        }
    </style>
"""


# ---------------------------------------------------------------------------
# Placeholder helper
# ---------------------------------------------------------------------------


def _placeholder(message: str) -> str:
    """Render a placeholder div for missing/corrupt/stub data."""
    return f'<div class="placeholder">{_esc(message)}</div>'


def _artifact_placeholder(
    data: dict[str, Any] | None,
    artifact_name: str,
) -> str | None:
    """Return placeholder HTML if artifact is not usable, else None."""
    if data is None:
        return _placeholder(f"{artifact_name} not available")
    if data is _CORRUPT:
        return _placeholder("Data unavailable")
    if _is_stub(data):
        reason = data.get("reason", "Skipped")
        return _placeholder(f"{artifact_name} skipped: {_esc(reason)}")
    return None


# ---------------------------------------------------------------------------
# Chart 1: Conviction Gauge (semi-circle)
# ---------------------------------------------------------------------------


def _chart_conviction_gauge(score_dims: dict[str, Any] | None) -> str:
    """Render semi-circle conviction gauge SVG."""
    ph = _artifact_placeholder(score_dims, "Score dimensions")
    if ph is not None:
        return f'<div class="chart-box"><h2>Conviction Gauge</h2>{ph}</div>'

    summary = _as_dict(score_dims.get("summary"))  # type: ignore[union-attr]
    conviction = _num(summary.get("conviction_score"), 0.0)
    verdict = str(summary.get("verdict", "unknown")).strip().lower()

    # Clamp 0-100
    conviction = max(0.0, min(100.0, conviction))

    # SVG parameters
    cx, cy, r = 150.0, 130.0, 100.0
    # Semi-circle: 180 degrees from left to right (pi to 0)
    # Score angle
    score_frac = conviction / 100.0
    score_angle = math.pi * (1.0 - score_frac)

    # Arc endpoint for the score
    end_x = cx + r * math.cos(score_angle)
    end_y = cy - r * math.sin(score_angle)

    # Zone boundaries: 50% and 75%
    z50_angle = math.pi * (1.0 - 0.5)
    z75_angle = math.pi * (1.0 - 0.75)

    z50_x = cx + r * math.cos(z50_angle)
    z50_y = cy - r * math.sin(z50_angle)
    z75_x = cx + r * math.cos(z75_angle)
    z75_y = cy - r * math.sin(z75_angle)

    # Start of arc (left)
    start_x = cx - r
    start_y = cy

    # End of arc (right)
    arc_end_x = cx + r
    arc_end_y = cy

    verdict_color = _VERDICT_COLORS.get(verdict, "#9ca3af")
    verdict_label = _esc(verdict.replace("_", " ").title())

    # Large arc flag for score fill
    large_arc = 1 if score_frac > 0.5 else 0

    svg_parts = [
        '<svg viewBox="0 0 300 170" xmlns="http://www.w3.org/2000/svg">',
        # Background arc zones: red (0-50%), yellow (50-75%), green (75-100%)
        # Red zone: full semi-circle background
        f'<path d="M {start_x:.2f} {start_y:.2f} A {r:.2f} {r:.2f} 0 1 1 {arc_end_x:.2f} {arc_end_y:.2f}"',
        '  fill="none" stroke="#ef4444" stroke-width="18" stroke-opacity="0.25"/>',
        # Yellow zone: from 50% to 75%
        f'<path d="M {z50_x:.2f} {z50_y:.2f} A {r:.2f} {r:.2f} 0 0 1 {z75_x:.2f} {z75_y:.2f}"',
        '  fill="none" stroke="#f59e0b" stroke-width="18" stroke-opacity="0.25"/>',
        # Green zone: from 75% to 100%
        f'<path d="M {z75_x:.2f} {z75_y:.2f} A {r:.2f} {r:.2f} 0 0 1 {arc_end_x:.2f} {arc_end_y:.2f}"',
        '  fill="none" stroke="#10b981" stroke-width="18" stroke-opacity="0.25"/>',
    ]

    # Score fill arc
    if conviction > 0.5:  # avoid degenerate arc
        svg_parts.append(
            f'<path d="M {start_x:.2f} {start_y:.2f} A {r:.2f} {r:.2f} 0'
            f' {large_arc} 1 {end_x:.2f} {end_y:.2f}"'
            f' fill="none" stroke="{_esc(verdict_color)}" stroke-width="18"'
            f' stroke-linecap="round"/>'
        )

    # Score text
    svg_parts.append(
        f'<text x="{cx:.2f}" y="{cy - 15:.2f}" text-anchor="middle"'
        f' font-size="36" font-weight="bold" fill="{_esc(verdict_color)}">'
        f"{conviction:.1f}</text>"
    )
    # Verdict label
    svg_parts.append(
        f'<text x="{cx:.2f}" y="{cy + 10:.2f}" text-anchor="middle"'
        f' font-size="14" fill="#94a3b8">{verdict_label}</text>'
    )
    svg_parts.append("</svg>")

    svg = "\n".join(svg_parts)
    ai_note = (
        '<div style="color:#64748b;font-size:0.75rem;text-align:center;'
        'margin-top:0.5rem;font-style:italic;">AI-generated assessment</div>'
    )
    return f'<div class="chart-box"><h2>Conviction Gauge</h2>{svg}{ai_note}</div>'


# ---------------------------------------------------------------------------
# Chart 2: Category Radar Chart (7-point spider)
# ---------------------------------------------------------------------------


def _category_weighted_score(by_cat: dict[str, Any], cat: str) -> float:
    """Compute weighted score for a category: strong=1.0, moderate=0.5, others=0."""
    counts = _as_dict(by_cat.get(cat))
    strong = _num(counts.get("strong_conviction"), 0.0)
    moderate = _num(counts.get("moderate_conviction"), 0.0)
    concern = _num(counts.get("concern"), 0.0)
    db = _num(counts.get("dealbreaker"), 0.0)
    na = _num(counts.get("not_applicable"), 0.0)
    applicable = strong + moderate + concern + db
    if applicable <= 0:
        # All N/A or empty
        if na > 0:
            return 0.0
        return 0.0
    weighted = strong * 1.0 + moderate * 0.5
    return round(weighted / applicable * 100.0, 2)


def _chart_category_radar(score_dims: dict[str, Any] | None) -> str:
    """Render 7-point radar/spider chart SVG."""
    ph = _artifact_placeholder(score_dims, "Score dimensions")
    if ph is not None:
        return f'<div class="chart-box"><h2>Category Radar</h2>{ph}</div>'

    summary = _as_dict(score_dims.get("summary"))  # type: ignore[union-attr]
    by_cat = _as_dict(summary.get("by_category"))

    # Ordered categories with their scores
    categories = list(_CANONICAL_CATEGORIES)
    # Append any unknown categories alphabetically
    extra = sorted(set(by_cat.keys()) - set(categories))
    categories.extend(extra)

    scores = [_category_weighted_score(by_cat, cat) for cat in categories]
    n = len(categories)
    if n == 0:
        return f'<div class="chart-box"><h2>Category Radar</h2>{_placeholder("No categories")}</div>'

    # SVG parameters — wide viewBox to avoid label clipping
    cx, cy = 230.0, 160.0
    max_r = 100.0

    svg_lines: list[str] = ['<svg viewBox="0 0 460 330" xmlns="http://www.w3.org/2000/svg">']

    # Angle offset: start from top (-90 degrees)
    def _angle(i: int) -> float:
        return 2 * math.pi * i / n - math.pi / 2

    # Draw grid rings at 25%, 50%, 75%, 100%
    for pct in [0.25, 0.5, 0.75, 1.0]:
        ring_r = max_r * pct
        points = []
        for i in range(n):
            a = _angle(i)
            px = cx + ring_r * math.cos(a)
            py = cy + ring_r * math.sin(a)
            points.append(f"{px:.2f},{py:.2f}")
        svg_lines.append(f'<polygon points="{" ".join(points)}" fill="none" stroke="#334155" stroke-width="0.5"/>')

    # Draw axis lines
    for i in range(n):
        a = _angle(i)
        ex = cx + max_r * math.cos(a)
        ey = cy + max_r * math.sin(a)
        svg_lines.append(
            f'<line x1="{cx:.2f}" y1="{cy:.2f}" x2="{ex:.2f}" y2="{ey:.2f}" stroke="#334155" stroke-width="0.5"/>'
        )

    # Data polygon
    data_points: list[str] = []
    point_coords: list[tuple[float, float, float]] = []  # (px, py, score)
    for i in range(n):
        a = _angle(i)
        frac = _num(scores[i], 0.0) / 100.0
        frac = max(0.05, min(1.0, frac))  # 5% floor prevents center collapse
        px = cx + max_r * frac * math.cos(a)
        py = cy + max_r * frac * math.sin(a)
        data_points.append(f"{px:.2f},{py:.2f}")
        point_coords.append((px, py, scores[i]))

    svg_lines.append(
        f'<polygon points="{" ".join(data_points)}"'
        f' fill="#21a2e3" fill-opacity="0.2" stroke="#21a2e3" stroke-width="2"/>'
    )

    # Data points (dots) and per-point score labels
    for i in range(n):
        px, py, score_val = point_coords[i]
        svg_lines.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="3" fill="#21a2e3"/>')
        # Score label near each data point (offset outward slightly)
        a = _angle(i)
        label_offset = 12.0
        lx = px + label_offset * math.cos(a)
        ly = py + label_offset * math.sin(a)
        anchor = "middle"
        if math.cos(a) > 0.3:
            anchor = "start"
        elif math.cos(a) < -0.3:
            anchor = "end"
        svg_lines.append(
            f'<text x="{lx:.2f}" y="{ly:.2f}" text-anchor="{anchor}"'
            f' font-size="8" fill="#21a2e3" font-weight="600">'
            f"{score_val:.0f}%</text>"
        )

    # Labels
    for i in range(n):
        a = _angle(i)
        label_r = max_r + 20
        lx = cx + label_r * math.cos(a)
        ly = cy + label_r * math.sin(a)
        anchor = "middle"
        if math.cos(a) > 0.3:
            anchor = "start"
        elif math.cos(a) < -0.3:
            anchor = "end"
        score_str = f"{scores[i]:.0f}%"
        svg_lines.append(
            f'<text x="{lx:.2f}" y="{ly:.2f}" text-anchor="{anchor}"'
            f' font-size="10" fill="#94a3b8">'
            f"{_esc(categories[i])}</text>"
        )
        svg_lines.append(
            f'<text x="{lx:.2f}" y="{ly + 12:.2f}" text-anchor="{anchor}"'
            f' font-size="9" fill="#64748b">{_esc(score_str)}</text>'
        )

    svg_lines.append("</svg>")
    svg = "\n".join(svg_lines)
    note = (
        '<div style="color:#64748b;font-size:0.7rem;margin-top:0.25rem;">'
        "Values below 5% rendered at 5% for readability.</div>"
    )
    return f'<div class="chart-box"><h2>Category Radar</h2>{svg}{note}</div>'


# ---------------------------------------------------------------------------
# Chart 3: Category Breakdown (horizontal stacked bars)
# ---------------------------------------------------------------------------


def _chart_category_bars(score_dims: dict[str, Any] | None) -> str:
    """Render horizontal stacked bar chart SVG for category breakdowns."""
    ph = _artifact_placeholder(score_dims, "Score dimensions")
    if ph is not None:
        return f'<div class="chart-box full"><h2>Category Breakdown</h2>{ph}</div>'

    summary = _as_dict(score_dims.get("summary"))  # type: ignore[union-attr]
    by_cat = _as_dict(summary.get("by_category"))

    categories = list(_CANONICAL_CATEGORIES)
    extra = sorted(set(by_cat.keys()) - set(categories))
    categories.extend(extra)

    bar_height = 24.0
    bar_gap = 8.0
    label_width = 110.0
    bar_width = 400.0
    y_start = 10.0
    total_height = y_start + len(categories) * (bar_height + bar_gap) + 40
    total_w = label_width + bar_width + 30

    svg_lines: list[str] = [f'<svg viewBox="0 0 {total_w:.0f} {total_height:.0f}" xmlns="http://www.w3.org/2000/svg">']

    status_order = [
        "strong_conviction",
        "moderate_conviction",
        "concern",
        "dealbreaker",
        "not_applicable",
    ]
    status_labels = {
        "strong_conviction": "Strong",
        "moderate_conviction": "Moderate",
        "concern": "Concern",
        "dealbreaker": "Dealbreaker",
        "not_applicable": "N/A",
    }

    for ci, cat in enumerate(categories):
        counts = _as_dict(by_cat.get(cat))
        total = sum(_num(counts.get(s), 0.0) for s in status_order)
        y = y_start + ci * (bar_height + bar_gap)

        # Category label
        svg_lines.append(
            f'<text x="{label_width - 8:.2f}" y="{y + bar_height / 2 + 4:.2f}"'
            f' text-anchor="end" font-size="11" fill="#e2e8f0">'
            f"{_esc(cat)}</text>"
        )

        # Stacked segments
        x_offset = label_width
        for status in status_order:
            count = _num(counts.get(status), 0.0)
            if total > 0 and count > 0:
                seg_w = (count / total) * bar_width
                color = _STATUS_COLORS.get(status, "#9ca3af")
                svg_lines.append(
                    f'<rect x="{x_offset:.2f}" y="{y:.2f}"'
                    f' width="{seg_w:.2f}" height="{bar_height:.2f}"'
                    f' fill="{_esc(color)}" rx="2"/>'
                )
                # Count label inside bar if segment is wide enough
                if seg_w > 20:
                    svg_lines.append(
                        f'<text x="{x_offset + seg_w / 2:.2f}"'
                        f' y="{y + bar_height / 2 + 4:.2f}"'
                        f' text-anchor="middle" font-size="10"'
                        f' fill="#fff">{int(count)}</text>'
                    )
                x_offset += seg_w

    # Legend
    legend_y = y_start + len(categories) * (bar_height + bar_gap) + 10
    lx = label_width
    for status in status_order:
        color = _STATUS_COLORS.get(status, "#9ca3af")
        label = status_labels.get(status, status)
        svg_lines.append(f'<rect x="{lx:.2f}" y="{legend_y:.2f}" width="10" height="10" fill="{_esc(color)}" rx="2"/>')
        svg_lines.append(
            f'<text x="{lx + 14:.2f}" y="{legend_y + 9:.2f}" font-size="9" fill="#94a3b8">{_esc(label)}</text>'
        )
        lx += len(label) * 6.5 + 24

    svg_lines.append("</svg>")
    svg = "\n".join(svg_lines)
    return f'<div class="chart-box full"><h2>Category Breakdown</h2>{svg}</div>'


# ---------------------------------------------------------------------------
# Chart 4: Partner Verdicts Cards
# ---------------------------------------------------------------------------


def _chart_partner_verdicts(discussion: dict[str, Any] | None) -> str:
    """Render partner verdict cards."""
    ph = _artifact_placeholder(discussion, "Discussion")
    if ph is not None:
        return f'<div class="chart-box full"><h2>Partner Verdicts</h2>{ph}</div>'

    verdicts_list = _as_list(discussion.get("partner_verdicts"))  # type: ignore[union-attr]

    # Index by partner role (normalize to lowercase/stripped for matching)
    by_partner: dict[str, dict[str, Any]] = {}
    for pv in verdicts_list:
        if isinstance(pv, dict):
            role = str(pv.get("partner", "")).strip().lower()
            if role:  # skip empty partner roles
                by_partner[role] = pv

    # Build ordered list: canonical partners first, then any extras alphabetically
    ordered_partners = list(_CANONICAL_PARTNERS)
    extra = sorted(set(by_partner.keys()) - set(ordered_partners))
    ordered_partners.extend(extra)

    cards: list[str] = []
    for partner in ordered_partners:
        pv = by_partner.get(partner)
        if pv is None:
            cards.append(
                '<div class="partner-card" style="border-color: #334155;">'
                f"<h3>{_esc(partner.title())}</h3>"
                '<div class="verdict" style="color: #64748b;">No verdict</div>'
                "</div>"
            )
            continue

        verdict = str(pv.get("verdict", "unknown")).strip().lower()
        rationale = str(pv.get("rationale", ""))
        color = _VERDICT_COLORS.get(verdict, "#9ca3af")
        verdict_label = _esc(verdict.replace("_", " ").title())

        rationale = _smart_truncate(rationale)

        cards.append(
            f'<div class="partner-card" style="border-color: {_esc(color)};">'
            f"<h3>{_esc(partner.title())}</h3>"
            f'<div class="verdict" style="color: {_esc(color)};">'
            f"{verdict_label}</div>"
            f'<div class="rationale">{_esc(rationale)}</div>'
            f"</div>"
        )

    subtitle = (
        '<div style="color:#64748b;font-size:0.8rem;margin-bottom:0.75rem;'
        'font-style:italic;">AI-simulated partner perspectives '
        "— not actual investor views</div>"
    )
    inner = f'<div class="partner-grid">{"".join(cards)}</div>'
    return f'<div class="chart-box full"><h2>Partner Verdicts</h2>{subtitle}{inner}</div>'


# ---------------------------------------------------------------------------
# Chart 5: Conflict Summary
# ---------------------------------------------------------------------------


def _chart_conflict_summary(conflict: dict[str, Any] | None) -> str:
    """Render conflict summary badge + table."""
    ph = _artifact_placeholder(conflict, "Conflict check")
    if ph is not None:
        return f'<div class="chart-box full"><h2>Conflict Check</h2>{ph}</div>'

    summary = _as_dict(conflict.get("summary"))  # type: ignore[union-attr]
    severity = str(summary.get("overall_severity", "unknown")).strip().lower()
    badge_color = _SEVERITY_COLORS.get(severity, "#9ca3af")

    parts: list[str] = [f'<span class="badge" style="background: {_esc(badge_color)};">{_esc(severity.title())}</span>']

    conflicts = _as_list(conflict.get("conflicts"))  # type: ignore[union-attr]
    if conflicts:
        rows: list[str] = []
        for c in conflicts:
            if not isinstance(c, dict):
                continue
            company = _esc(str(c.get("company", "?")))
            ctype = _esc(str(c.get("type", "?")))
            csev = str(c.get("severity", "?")).strip().lower()
            csev_color = _SEVERITY_COLORS.get(csev, "#9ca3af")
            rows.append(
                f"<tr><td>{company}</td><td>{ctype}</td>"
                f'<td style="color: {_esc(csev_color)};">'
                f"{_esc(csev.title())}</td></tr>"
            )
        parts.append(
            '<table class="conflict-table">'
            "<tr><th>Company</th><th>Type</th><th>Severity</th></tr>"
            f"{''.join(rows)}</table>"
        )

    inner = "".join(parts)
    return f'<div class="chart-box full"><h2>Conflict Check</h2>{inner}</div>'


# ---------------------------------------------------------------------------
# Summary bar (between title and charts)
# ---------------------------------------------------------------------------


def _section_summary_bar(
    startup: dict[str, Any] | None,
    score_dims: dict[str, Any] | None,
    discussion: dict[str, Any] | None = None,
) -> str:
    """Render a compact text summary bar between title and charts."""
    if not _usable(startup) and not _usable(score_dims) and not _usable(discussion):
        return ""

    parts: list[str] = []

    if _usable(startup):
        one_liner = str(startup.get("one_liner", ""))
        sector = str(startup.get("sector", ""))
        if one_liner:
            parts.append(f'<div style="color:#e2e8f0;font-size:0.95rem;">{_esc(one_liner)}</div>')
        if sector:
            parts.append(f'<div style="color:#64748b;font-size:0.85rem;">Sector: {_esc(sector)}</div>')

    if _usable(discussion):
        verdict_spans: list[str] = []
        for pv in _as_list(discussion.get("partner_verdicts")):
            if not isinstance(pv, dict):
                continue
            name = str(pv.get("partner", "")).strip().title()
            verdict = str(pv.get("verdict", "")).lower().replace(" ", "_")
            if not name:
                continue
            color = _VERDICT_COLORS.get(verdict, "#9ca3af")
            label = verdict.replace("_", " ").title()
            verdict_spans.append(f'<span style="color:{color};">{_esc(name)}: {_esc(label)}</span>')
        if verdict_spans:
            parts.append(f'<div style="font-size:0.85rem;margin-top:0.25rem;">{" · ".join(verdict_spans)}</div>')

    if _usable(score_dims):
        summary = _as_dict(score_dims.get("summary"))
        strong = int(_num(summary.get("strong_conviction"), 0))
        moderate = int(_num(summary.get("moderate_conviction"), 0))
        concern = int(_num(summary.get("concern"), 0))
        db = int(_num(summary.get("dealbreaker"), 0))
        breakdown = (
            f'<span style="color:#10b981;">{strong} strong</span>'
            f' · <span style="color:#f59e0b;">{moderate} moderate</span>'
            f' · <span style="color:#ef4444;">{concern} concern</span>'
            f' · <span style="color:#b91c1c;">{db} dealbreaker</span>'
        )
        parts.append(f'<div style="font-size:0.85rem;margin-top:0.25rem;">{breakdown}</div>')

    if not parts:
        return ""

    inner = "\n".join(parts)
    return (
        '<div style="background:#1e293b;border-radius:10px;padding:1rem 1.5rem;'
        'margin-bottom:1.5rem;border:1px solid #334155;">'
        f"{inner}</div>"
    )


# ---------------------------------------------------------------------------
# Full HTML composition
# ---------------------------------------------------------------------------


def compose_html(dir_path: str) -> str:
    """Load artifacts and compose the full HTML document."""
    all_names = REQUIRED_ARTIFACTS + OPTIONAL_ARTIFACTS
    artifacts: dict[str, dict[str, Any] | None] = {}
    for name in all_names:
        artifacts[name] = _load_artifact(dir_path, name)

    startup = artifacts.get("startup_profile.json")
    score_dims = artifacts.get("score_dimensions.json")
    discussion = artifacts.get("discussion.json")
    conflict = artifacts.get("conflict_check.json")

    # Title
    if _usable(startup):
        company = _esc(str(startup.get("company_name", "Unknown")))
        date = _esc(str(startup.get("simulation_date", "")))
        stage = _esc(str(startup.get("stage", "unknown")).replace("_", " ").title())
        title_html = (
            f'<h1>IC Simulation: {company}</h1><div class="subtitle">{date} | {stage}</div>'
            '<div class="subtitle">Generated by '
            '<a href="https://github.com/lool-ventures/founder-skills">founder skills</a>'
            ' by <a href="https://lool.vc">lool ventures</a>'
            " — IC Simulation Agent</div>"
        )
    else:
        title_html = (
            "<h1>IC Simulation Report</h1>"
            '<div class="subtitle">Generated by '
            '<a href="https://github.com/lool-ventures/founder-skills">founder skills</a>'
            ' by <a href="https://lool.vc">lool ventures</a>'
            " — IC Simulation Agent</div>"
        )

    # Charts
    gauge = _chart_conviction_gauge(score_dims)
    radar = _chart_category_radar(score_dims)
    bars = _chart_category_bars(score_dims)
    partners = _chart_partner_verdicts(discussion)
    conflicts = _chart_conflict_summary(conflict)

    if _usable(startup):
        page_title = f"IC Simulation: {_esc(str(startup.get('company_name', 'Report')))}"
    else:
        page_title = "IC Simulation Report"

    summary_bar = _section_summary_bar(startup, score_dims, discussion)

    body = f"""
{title_html}
{summary_bar}
<div class="chart-grid">
{gauge}
{radar}
</div>
{bars}
{partners}
{conflicts}
<div class="footer">
  Generated by <a href="https://github.com/lool-ventures/founder-skills">founder skills</a>
  by <a href="https://lool.vc">lool ventures</a> — IC Simulation Agent
</div>
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>{page_title}</title>
{_css()}
</head>
<body>
{body}
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def _write_output(data: str, output_path: str | None) -> None:
    """Write HTML string to file or stdout."""
    if output_path:
        abs_path = os.path.abspath(output_path)
        parent = os.path.dirname(abs_path)
        if parent == "/":
            print(
                f"Error: output path resolves to root directory: {output_path}",
                file=sys.stderr,
            )
            sys.exit(1)
        os.makedirs(parent, exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(data)
    else:
        sys.stdout.write(data)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    p = argparse.ArgumentParser(description="Generate HTML visualization from IC simulation artifacts")
    p.add_argument(
        "-d",
        "--dir",
        required=True,
        help="Directory containing JSON artifacts",
    )
    p.add_argument(
        "--pretty",
        action="store_true",
        help="Accepted for compatibility (no-op)",
    )
    p.add_argument(
        "-o",
        "--output",
        help="Write HTML to file instead of stdout",
    )
    return p.parse_args()


def main() -> None:
    """Entry point."""
    args = parse_args()

    if not os.path.isdir(args.dir):
        print(f"Error: directory not found: {args.dir}", file=sys.stderr)
        sys.exit(1)

    html_out = compose_html(args.dir)
    _write_output(html_out, args.output)


if __name__ == "__main__":
    main()
