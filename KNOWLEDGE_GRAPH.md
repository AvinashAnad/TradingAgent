# Knowledge Graph Setup (Graphify)

This project can be converted into a navigable knowledge graph using graphify.

## Why this is useful

- Faster architecture understanding with community/grouped modules.
- Detection of key files and central dependency nodes.
- Better question answering over project structure and rationale.

## Outputs you will get

After a successful run, graphify writes artifacts to:

- graphify-out/GRAPH_REPORT.md
- graphify-out/graph.json
- graphify-out/graph.html

Optional exports include GraphML, SVG, and Neo4j Cypher.

## Prerequisites

- Python 3.10+
- pip available in your environment
- graphify package: graphifyy

Install:

```bash
pip install graphifyy
```

## Run on this repo

From the repository root:

```bash
graphify install --platform codex
graphify hook install
```

Then in your coding assistant:

```text
/graphify .
```

Alternative terminal-first operations:

```bash
graphify query "show data flow between config and strategy"
graphify explain "StockAnalyserEngine"
graphify path "TickertapeClient" "Strategy"
```

## Keep graph updated

For code-only updates without full semantic rebuild:

```bash
graphify update .
```

For full refresh after major documentation/design changes:

```text
/graphify . --update
```

## Optional exports

```text
/graphify . --graphml
/graphify . --svg
/graphify . --neo4j
```

## Suggested .graphifyignore

Use `.graphifyignore` to skip noisy/generated paths. A starter file is included in this repo.
