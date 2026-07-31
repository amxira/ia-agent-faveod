"""LangGraph orchestration for Agent 3.

Graph:
  START -> collect_events -> (Send fan-out, one parallel branch per event)
          each branch: process_event (scrape + NER + enrich + score)
  process_event -> END (leads accumulate into the shared state)
"""

from __future__ import annotations

import logging

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from event_mapper import config
from event_mapper.ingest.registry import fetch_all
from event_mapper.ner.extractor import SpeakerExtractor
from event_mapper.pipeline import EventPipeline
from event_mapper.state import EventBranchState, MapperState
from tender_hunter.ingest.proxy import make_proxy_provider
from tender_hunter.llm.client import LLMClient

log = logging.getLogger(__name__)


class Components:
    """Wired singletons shared across graph nodes."""

    def __init__(self, source: str | None = None, llm: LLMClient | None = None):
        self.source = (source or config.EVENT_SOURCE).strip().lower()
        self.llm = llm or LLMClient()
        self.extractor = SpeakerExtractor(self.llm)
        self.pipeline = EventPipeline(self.extractor, self.llm, proxy=_proxy_config())
        self.proxy = _proxy_config()


def _proxy_config() -> dict | None:
    provider = make_proxy_provider()
    if provider is None:
        return None
    return provider.get_proxy()


def build_graph(components: Components):
    builder = StateGraph(MapperState)

    def collect_node(state: MapperState) -> dict:
        events = fetch_all(source=components.source)
        log.info("collected %d event(s) via %r", len(events), components.source)
        return {"events": events}

    def process_node(state: EventBranchState) -> dict:
        cards = components.pipeline.run(state["event"])
        return {"leads": cards}

    def fan_out(state: MapperState) -> list[Send]:
        return [Send("process_event", {"event": e}) for e in state["events"]]

    builder.add_node("collect_events", collect_node)
    builder.add_node("process_event", process_node)
    builder.add_edge(START, "collect_events")
    builder.add_conditional_edges("collect_events", fan_out, ["process_event"])
    builder.add_edge("process_event", END)
    return builder.compile()


def build_components(source: str | None = None, llm: LLMClient | None = None) -> Components:
    return Components(source, llm)


def run_once(components: Components | None = None) -> dict:
    """Compile the graph and invoke it; returns the final state."""
    components = components or build_components()
    graph = build_graph(components)
    return graph.invoke({"events": [], "leads": []})
