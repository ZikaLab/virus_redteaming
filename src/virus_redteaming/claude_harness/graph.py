"""One-node LangGraph that sends a prompt to a chat client."""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from virus_redteaming.claude_harness.protocols import ChatTurn


class PingState(TypedDict):
    """Prompt traveling into the node and the reply traveling out."""

    prompt: str
    reply: str


PingGraph = StateGraph[PingState, None, PingState, PingState]


def build_ping_graph(chat: ChatTurn) -> PingGraph:
    """Return an uncompiled graph. ``ClaudePing`` compiles it."""

    def respond(state: PingState) -> PingState:
        return {"prompt": state["prompt"], "reply": chat.complete(state["prompt"])}

    graph: PingGraph = StateGraph(PingState)
    graph.add_node("claude", respond)
    graph.add_edge(START, "claude")
    graph.add_edge("claude", END)
    return graph
