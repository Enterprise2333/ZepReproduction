"""Smallest online check: two dated episodes, one graph query."""

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from runtime import ROOT, make_graph, prepare_graph


async def main():
    graph, _ = make_graph(ROOT / "data" / f"smoke-{uuid4().hex[:8]}.kuzu")
    try:
        await prepare_graph(graph)
        for i, (date, body) in enumerate(
            [
                ("2024-01-10", "Maya works at Atlas Labs as a designer."),
                ("2024-04-15", "Maya left Atlas Labs and now works at Harbor Studio as a designer."),
            ]
        ):
            result = await graph.add_episode(
                name=f"smoke-{i}",
                episode_body=body,
                source_description="Synthetic test conversation",
                reference_time=datetime.fromisoformat(date).replace(tzinfo=timezone.utc),
            )
            print("added", i, "nodes", len(result.nodes), "edges", len(result.edges), flush=True)
        edges = await graph.search("Where does Maya work now?", num_results=8)
        for edge in edges:
            print("fact", edge.fact, "valid", edge.valid_at, "invalid", edge.invalid_at, flush=True)
    finally:
        await graph.close()


if __name__ == "__main__":
    asyncio.run(main())

