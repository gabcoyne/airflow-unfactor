# PROJECT.md — airflow-unfactor

> *"Airflow is for airports. Welcome to modern orchestration."*

## Overview

An MCP (Model Context Protocol) server that converts Apache Airflow DAGs to Prefect flows using AI-assisted analysis. Educates users on Prefect's advantages while producing clean, idiomatic Python code.

## Philosophy

- **Liberation, not migration** — Help users escape Airflow's complexity
- **Educational** — Comments explain *why* Prefect does it better, not just *what* changed  
- **Complete** — Handle all operators, not just the easy ones
- **TDD** — Every feature starts with a failing test
- **Beads** — Task tracking with `bd` for structured, agent-friendly development

## Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | Python 3.11+ | Match Prefect's target |
| Protocol | MCP SDK | Agent-native interface |
| Task Tracking | Beads (`bd`) | Dependency-aware graph for AI agents |
| Testing | pytest + hypothesis | TDD with property-based testing |
| AI Backend | Model-agnostic | Claude, GPT, or local models |
| Package Manager | uv | Fast, modern Python tooling |

See PROJECT.md for full specification.