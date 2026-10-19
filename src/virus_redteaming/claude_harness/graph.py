"""One-node LangGraph that sends a prompt to a chat client."""

from typing import NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph

from virus_redteaming.claude_harness.protocols import ChatTurn


class PingState(TypedDict):
    """Prompt traveling into the node and the reply traveling out."""

    prompt: str
    reply: str
    file_id: NotRequired[str | None]


PingGraph = StateGraph[PingState, None, PingState, PingState]


def build_ping_graph(chat: ChatTurn) -> PingGraph:
    """Return an uncompiled graph. ``ClaudePing`` compiles it."""

    def respond(state: PingState) -> PingState:
        file_id = state.get("file_id")
        prompt = state["prompt"]
        if file_id:
            reply = chat.complete(prompt, file_id=file_id)
        else:
            reply = chat.complete(prompt)
        return {"prompt": prompt, "reply": reply}

    graph: PingGraph = StateGraph(PingState)
    graph.add_node("claude", respond)
    graph.add_edge(START, "claude")
    graph.add_edge("claude", END)
    return graph
