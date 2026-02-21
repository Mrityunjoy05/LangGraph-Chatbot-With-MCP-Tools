import streamlit as st
import asyncio
import threading
import uuid
import json
from datetime import datetime
from langchain_core.messages import AIMessage, ToolMessage, HumanMessage
from langgraph.types import Command

from core.agent_manager import Agent_Manager

# ── Page config ────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.tool-box {
    background: #0d1a2e;
    border-left: 3px solid #58a6ff;
    border-radius: 6px;
    padding: 8px 14px;
    margin: 4px 0;
    font-family: monospace;
    font-size: 13px;
    display: inline-block;
}
.tool-box .tool-name { color: #79c0ff; font-weight: 600; }

.result-box {
    background: #0d1117;
    border-left: 3px solid #58a6ff;
    border-radius: 6px;
    padding: 10px 14px;
    margin: 6px 0;
    font-family: monospace;
    font-size: 12px;
    color: #8b949e;
    white-space: pre-wrap;
    word-break: break-word;
}

.security-box {
    background: #e87272;
    border-left: 3px solid #f85149;
    border-radius: 6px;
    padding: 12px 16px;
    margin: 8px 0;
}
.security-box .sec-title { color: #de150b; font-weight: 700; font-size: 15px; }
</style>
""", unsafe_allow_html=True)

DANGEROUS_TOOLS = {"delete_repository", "create_repository"}

# ══════════════════════════════════════════════════════════════════
# ONE persistent event loop in a background thread
# ══════════════════════════════════════════════════════════════════

def _start_background_loop(loop: asyncio.AbstractEventLoop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

def get_event_loop() -> asyncio.AbstractEventLoop:
    if "_bg_loop" not in st.session_state:
        loop = asyncio.new_event_loop()
        t = threading.Thread(target=_start_background_loop, args=(loop,), daemon=True)
        t.start()
        st.session_state._bg_loop = loop
        st.session_state._bg_thread = t
    return st.session_state._bg_loop

def run_async(coro):
    loop = get_event_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()

# ══════════════════════════════════════════════════════════════════
# Database helpers — read directly from SQLite checkpointer
# ══════════════════════════════════════════════════════════════════

def get_unique_thread_ids() -> list:
    """
    Read all unique thread IDs from DB.
    Collect with timestamps so we can sort oldest→newest,
    then new chats appended to front will always be the most recent.
    """
    try:
        manager = st.session_state.get("manager")
        if not manager:
            return []
        checkpointer = manager.database_manager.checkpointer
        all_checkpoints = checkpointer.list(None)
        # { thread_id: latest_ts }
        tid_ts = {}
        for cp in all_checkpoints:
            tid = cp.config["configurable"]["thread_id"]
            ts = cp.metadata.get("created_at") or ""
            # Keep the latest timestamp per thread
            if tid not in tid_ts or ts > tid_ts[tid]:
                tid_ts[tid] = ts
        # Sort oldest → newest so that prepending new chats keeps newest at top
        sorted_tids = sorted(tid_ts.keys(), key=lambda t: tid_ts[t])
        return sorted_tids
    except Exception:
        return []


def get_thread_title(thread_id: str) -> str:
    """
    Derive a title from the first AIMessage in the thread.
    AI responses are always descriptive — better than using the user's
    short trigger message (e.g. 'hi', 'hello', 'go').
    Falls back to 'New Chat' if nothing found.
    """
    try:
        manager = st.session_state.get("manager")
        if not manager:
            return "New Chat"
        agent = manager.agent
        state = run_async(agent.aget_state({"configurable": {"thread_id": thread_id}}))
        messages = state.values.get("messages", [])
        for msg in messages:
            if isinstance(msg, AIMessage) and msg.content:
                # Take first sentence or first 40 chars — whichever is shorter
                first_sentence = msg.content.strip().split(".")[0].strip()
                title = first_sentence[:40]
                if len(first_sentence) > 40:
                    title += "…"
                return title
        return "New Chat"
    except Exception:
        return "New Chat"


def get_cached_title(thread_id: str) -> str:
    """
    Return cached title or fetch and cache it.
    - Real title already cached → return immediately, no DB call.
    - Title is "New Chat" or missing → always try DB.
      If DB has a real title, cache it permanently.
      If DB also returns "New Chat" (empty thread), just return "New Chat".
    """
    cached = st.session_state["thread_titles"].get(thread_id)

    # Already have a real title — return immediately
    if cached and cached != "New Chat":
        return cached

    # Try fetching from DB for ALL threads (not just active)
    fetched = get_thread_title(thread_id)
    if fetched and fetched != "New Chat":
        # Cache permanently so we never hit DB again for this thread
        st.session_state["thread_titles"][thread_id] = fetched
        return fetched

    return "New Chat"


def load_thread_history(thread_id: str) -> list:
    """
    Load the full message history for a thread from the checkpointer
    and convert to our internal event format for rendering.
    """
    try:
        manager = st.session_state.get("manager")
        if not manager:
            return []
        agent = manager.agent
        state = run_async(agent.aget_state({"configurable": {"thread_id": thread_id}}))
        messages = state.values.get("messages", [])
        events = []
        for msg in messages:
            if isinstance(msg, HumanMessage) and msg.content:
                events.append({"type": "user", "content": msg.content})
            elif isinstance(msg, AIMessage) and msg.content:
                events.append({"type": "ai", "content": msg.content})
            elif isinstance(msg, ToolMessage) and msg.content:
                events.append({
                    "type": "tool_result",
                    "tool_name": getattr(msg, "name", "tool"),
                    "content": msg.content,
                })
        return events
    except Exception as e:
        st.error(f"Error loading thread: {e}")
        return []

# ══════════════════════════════════════════════════════════════════
# Thread management
# ══════════════════════════════════════════════════════════════════

def generate_thread_id() -> str:
    return str(uuid.uuid4())


def add_thread_to_history(thread_id: str):
    if thread_id not in st.session_state["thread_id_history"]:
        # Insert at front so newest chat always appears at top of sidebar
        st.session_state["thread_id_history"].insert(0, thread_id)


def reset_chat():
    """Start a brand-new chat thread."""
    tid = generate_thread_id()
    st.session_state["thread_id"] = tid
    # Add to history list immediately — visible in sidebar right away
    add_thread_to_history(tid)
    st.session_state["session_history"] = []
    # Pre-cache title as "New Chat" so sidebar never calls DB for empty threads
    st.session_state["thread_titles"][tid] = "New Chat"
    st.session_state["pending_confirm"] = None

# ══════════════════════════════════════════════════════════════════
# Session state — initialize all keys before anything else
# ══════════════════════════════════════════════════════════════════

if "manager" not in st.session_state:
    st.session_state.manager = None

# Persistent loop must exist before manager init
get_event_loop()

# Init agent once
if st.session_state.manager is None:
    async def _init():
        m = Agent_Manager()
        await m.initialize()
        return m
    with st.spinner("🔧 Initializing agent…"):
        st.session_state.manager = run_async(_init())

# Now that manager is ready, seed thread history from DB
if "thread_id_history" not in st.session_state:
    st.session_state["thread_id_history"] = get_unique_thread_ids()

if "thread_titles" not in st.session_state:
    st.session_state["thread_titles"] = {}

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = generate_thread_id()

if "session_history" not in st.session_state:
    st.session_state["session_history"] = []

if "pending_confirm" not in st.session_state:
    st.session_state["pending_confirm"] = None

# Make sure the current thread is registered
add_thread_to_history(st.session_state["thread_id"])
if st.session_state["thread_id"] not in st.session_state["thread_titles"]:
    st.session_state["thread_titles"][st.session_state["thread_id"]] = "New Chat"

# ══════════════════════════════════════════════════════════════════
# Agent async core
# ══════════════════════════════════════════════════════════════════

def _parse_node(node: str, output: dict) -> list:
    events = []
    if node == "agent":
        for m in output.get("messages", []):
            if isinstance(m, AIMessage):
                if m.content:
                    events.append({"type": "ai", "content": m.content})
                for tc in getattr(m, "tool_calls", []):
                    events.append({
                        "type": "tool_call",
                        "tool_name": tc["name"],
                        "tool_args": tc["args"],
                        "tool_call_id": tc["id"],
                    })
    elif node == "tools":
        for m in output.get("messages", []):
            if isinstance(m, ToolMessage):
                events.append({
                    "type": "tool_result",
                    "tool_name": getattr(m, "name", "tool"),
                    "content": m.content,
                })
    return events


async def _stream_response(thread_id: str, user_text: str, agent):
    config = {"configurable": {"thread_id": thread_id}}
    events = []

    async for update in agent.astream(
        {"messages": [("user", user_text)]}, config, stream_mode="updates"
    ):
        for node, output in update.items():
            events += _parse_node(node, output)

    state = await agent.aget_state(config)
    if state.next and "tools" in state.next:
        last = state.values["messages"][-1]
        for tc in getattr(last, "tool_calls", []):
            name, args, tid = tc["name"], tc["args"], tc["id"]
            if name == "list_repositories" and args.get("limit", 0) > 10:
                args["limit"] = 10
            if name in DANGEROUS_TOOLS:
                events.append({
                    "type": "confirm_required",
                    "tool_name": name,
                    "tool_args": args,
                    "tool_call_id": tid,
                })
                return events
        async for update in agent.astream(
            Command(resume=True), config, stream_mode="updates"
        ):
            for node, output in update.items():
                events += _parse_node(node, output)

    return events


async def _resume_confirm(thread_id, allowed, tool_call_id, tool_name, agent):
    config = {"configurable": {"thread_id": thread_id}}
    events = []

    if not allowed:
        reject = ToolMessage(
            tool_call_id=tool_call_id,
            name=tool_name,
            content=(
                f"USER DENIED: The human user rejected the {tool_name} action. "
                "Acknowledge this and stop."
            ),
        )
        await agent.aupdate_state(config, {"messages": [reject]}, as_node="tools")
        resume_input = None
    else:
        resume_input = Command(resume=True)

    async for update in agent.astream(resume_input, config, stream_mode="updates"):
        for node, output in update.items():
            events += _parse_node(node, output)

    return events


def stream_response(thread_id, user_text):
    agent = st.session_state.manager.agent
    return run_async(_stream_response(thread_id, user_text, agent))

def resume_confirm(thread_id, allowed, tool_call_id, tool_name):
    agent = st.session_state.manager.agent
    return run_async(_resume_confirm(thread_id, allowed, tool_call_id, tool_name, agent))

# ══════════════════════════════════════════════════════════════════
# Render helpers
# ══════════════════════════════════════════════════════════════════

def render_event(event: dict):
    t = event["type"]
    if t == "user":
        with st.chat_message("user", avatar="👤"):
            st.markdown(event["content"])
    elif t == "ai":
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(event["content"])
    elif t == "tool_call":
        st.markdown(f"""
<div class="tool-box">
  <div class="tool-name">⚙ {event['tool_name']}</div>
</div>""", unsafe_allow_html=True)
    elif t == "tool_result":
        content = str(event["content"])
        if len(content) > 800:
            content = content[:800] + "\n…(truncated)"
        st.markdown(f"""
<div class="result-box">
✓ <strong style="color:#58a6ff">{event['tool_name']}</strong> result:<br><br>{content}
</div>""", unsafe_allow_html=True)
    elif t == "system":
        st.info(event["content"])

# ══════════════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 🤖 AI Agent")
    st.divider()

    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        reset_chat()
        st.rerun()

    st.divider()
    st.subheader("Previous Conversations")
    st.caption(f"Total: {len(st.session_state['thread_id_history'])} conversations")

    for tid in st.session_state["thread_id_history"]:
        chat_title = get_cached_title(tid)
        is_active = tid == st.session_state["thread_id"]
        label = f"💬 {chat_title}" if is_active else f"📝 {chat_title}"

        if st.button(label, key=f"btn_{tid}", use_container_width=True):
            # Load history from DB into session
            messages = load_thread_history(tid)
            st.session_state["thread_id"] = tid
            st.session_state["session_history"] = messages
            st.session_state["pending_confirm"] = None
            st.rerun()

    st.divider()
    st.caption("Powered by LangGraph + MCP")

# ══════════════════════════════════════════════════════════════════
# Main chat area
# ══════════════════════════════════════════════════════════════════

thread_id = st.session_state["thread_id"]

# Rename input at top of chat
current_title = st.session_state["thread_titles"].get(thread_id, "New Chat")
new_title = st.text_input(
    "Rename chat", value=current_title,
    placeholder="Rename this chat…",
    label_visibility="collapsed",
    key="rename_input"
)
if new_title and new_title != current_title:
    st.session_state["thread_titles"][thread_id] = new_title

st.divider()

# Render current session history
for event in st.session_state["session_history"]:
    render_event(event)

# ── Pending HITL confirm ───────────────────────────────────────────
if st.session_state["pending_confirm"]:
    pc = st.session_state["pending_confirm"]
    st.markdown(f"""
<div class="security-box">
  <div class="sec-title">⚠ Security Check — Approval Required</div>
  <p style="color:#cdd9e5; margin: 8px 0">
    Agent wants to run
    <code style="color:#f85149; font-size:14px">{pc['tool_name']}</code>
  </p>
  <pre style="color:#8b949e; font-size:12px">{json.dumps(pc['tool_args'], indent=2)}</pre>
</div>""", unsafe_allow_html=True)

    col1, col2, _ = st.columns([1, 1, 5])
    with col1:
        if st.button("✅ Allow", type="primary", use_container_width=True):
            with st.spinner("Resuming agent…"):
                events = resume_confirm(thread_id, True, pc["tool_call_id"], pc["tool_name"])
            st.session_state["session_history"].append(
                {"type": "system", "content": "✅ Action approved."}
            )
            for e in events:
                st.session_state["session_history"].append(e)
            st.session_state["pending_confirm"] = None
            st.rerun()
    with col2:
        if st.button("❌ Deny", use_container_width=True):
            with st.spinner("Informing agent…"):
                events = resume_confirm(thread_id, False, pc["tool_call_id"], pc["tool_name"])
            st.session_state["session_history"].append(
                {"type": "system", "content": "❌ Action denied by user."}
            )
            for e in events:
                st.session_state["session_history"].append(e)
            st.session_state["pending_confirm"] = None
            st.rerun()
    st.stop()

# ── Chat input ─────────────────────────────────────────────────────
user_input = st.chat_input("Ask the Ai agent anything…")

if user_input:
    # Append user message and rerun immediately so it renders BEFORE the spinner
    if st.session_state.get("_pending_input") != user_input:
        st.session_state["session_history"].append({"type": "user", "content": user_input})
        st.session_state["_pending_input"] = user_input
        st.rerun()

if st.session_state.get("_pending_input"):
    user_input = st.session_state.pop("_pending_input")

    with st.spinner("Agent is thinking…"):
        events = stream_response(thread_id, user_input)

    confirm_event = next((e for e in events if e["type"] == "confirm_required"), None)

    for e in events:
        if e["type"] != "confirm_required":
            st.session_state["session_history"].append(e)

    # Auto-title: set immediately from first AI reply in THIS run — no reload needed
    current_title = st.session_state["thread_titles"].get(thread_id, "New Chat")
    if current_title == "New Chat":
        first_ai = next((e for e in events if e["type"] == "ai" and e.get("content")), None)
        if first_ai:
            raw = first_ai["content"].strip()
            first_sentence = raw.split(".")[0].strip()
            title = first_sentence[:40] + ("…" if len(first_sentence) > 40 else "")
            st.session_state["thread_titles"][thread_id] = title

    if confirm_event:
        st.session_state["pending_confirm"] = {
            "tool_name": confirm_event["tool_name"],
            "tool_args": confirm_event["tool_args"],
            "tool_call_id": confirm_event["tool_call_id"],
        }

    st.rerun()