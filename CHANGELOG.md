# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-02-22

### Highlights

First release of founder-skills — a Claude Cowork plugin with three AI coaching agents
for startup founders. Market Sizing builds defensible TAM/SAM/SOM analysis with external
validation and sensitivity testing. Deck Review scores pitch decks against 35 best-practice
criteria calibrated by fundraising stage. IC Simulation recreates a VC Investment Committee
discussion with three partner archetypes debating the startup across 28 scored dimensions.

### Added

- Market Sizing Agent with 4 scripts: `market_sizing.py` (TAM/SAM/SOM calculator), `sensitivity.py` (assumption stress-testing with confidence-based auto-widening), `checklist.py` (22-item self-check), and `compose_report.py` (report assembly with cross-artifact validation).
- Deck Review Agent with 2 scripts: `checklist.py` (35-criteria scoring across 7 categories) and `compose_report.py` (report assembly with cross-artifact validation).
- IC Simulation Agent with 4 scripts: `fund_profile.py` (fund profile validation), `detect_conflicts.py` (portfolio conflict validation), `score_dimensions.py` (28-dimension conviction scoring across 7 categories), and `compose_report.py` (report assembly with 13 cross-artifact validation checks).
- Three partner archetypes (Visionary, Operator, Analyst) with independent sub-agent assessments and orchestrated debate.
- Fund-specific mode with WebSearch-backed fund research and real partner mapping.
- Cross-agent integration: IC simulation imports prior market-sizing and deck-review artifacts with staleness detection.
- SKILL.md files for all three skills (`/founder-skills:market-sizing`, `/founder-skills:deck-review`, `/founder-skills:ic-sim` slash commands).
- Agent skill preloading (`skills:` frontmatter) for all three agents.
- SessionStart hook for environment setup (`CLAUDE_PLUGIN_ROOT` persistence).
- Dev tooling: ruff (lint + format), mypy (type checking), pytest (testing), GitHub Actions CI, pre-commit hooks.
- 123 regression tests across all three skills.
