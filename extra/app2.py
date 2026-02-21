import streamlit as st
import asyncio
import threading
import uuid
import json
import os
from datetime import datetime
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.types import Command

from core.agent_manager import Agent_Manager

# ── Page config ────────────────────────────────────────────────────
st.set_page_config(
    page_title="GitHub AI Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
/* Change 1: Tool call — light blue, name only, no args JSON shown */
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
    background: #1a0a0a;
    border-left: 3px solid #f85149;
    border-radius: 6px;
    padding: 12px 16px;
    margin: 8px 0;
}
.security-box .sec-title { color: #f85149; font-weight: 700; font-size: 15px; }
</style>
""", unsafe_allow_html=True)

DANGEROUS_TOOLS = {"delete_repository", "create_repository"}

# ── Change 3: Persistent chat storage in a local JSON file ─────────
CHATS_FILE = "chats_history.json"

def load_chats() -> dict:
    if os.path.exists(CHATS_FILE):
        try:
            with open(CHATS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_chats(threads: dict):
    try:
        with open(CHATS_FILE, "w", encoding="utf-8") as f:
            json.dump(threads, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════
# ONE persistent event loop in a background thread — never recreated
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

# ── Session state ──────────────────────────────────────────────────
if "manager" not in st.session_state:
    st.session_state.manager = None
if "threads" not in st.session_state:
    # Change 3: Load from disk on first run
    st.session_state.threads = load_chats()
if "active_thread" not in st.session_state:
    st.session_state.active_thread = None
if "pending_confirm" not in st.session_state:
    st.session_state.pending_confirm = None

# ── Agent init ─────────────────────────────────────────────────────
if st.session_state.manager is None:
    async def _init():
        m = Agent_Manager()
        await m.initialize()
        return m
    with st.spinner("🔧 Initializing agent…"):
        st.session_state.manager = run_async(_init())

# ── Agent async functions ──────────────────────────────────────────
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

# ── Render helpers ─────────────────────────────────────────────────
def render_event(event: dict):
    t = event["type"]
    if t == "user":
        with st.chat_message("user", avatar="👤"):
            st.markdown(event["content"])
    elif t == "ai":
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(event["content"])
    elif t == "tool_call":
        # Change 1: Only tool name shown, light blue, no args
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

# ── Thread helpers ─────────────────────────────────────────────────
def new_thread():
    tid = str(uuid.uuid4())[:8]
    st.session_state.threads[tid] = {
        "title": "New Chat",
        "messages": [],
        "created_at": datetime.now().strftime("%b %d, %H:%M"),
    }
    st.session_state.active_thread = tid
    st.session_state.pending_confirm = None
    save_chats(st.session_state.threads)
    return tid

def append_event(tid, event):
    st.session_state.threads[tid]["messages"].append(event)
    save_chats(st.session_state.threads)   # Change 3: save after every event

# ── Sidebar ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🤖 GitHub Agent")
    st.divider()

    if st.button("＋ New Chat", use_container_width=True, type="primary"):
        new_thread()
        st.rerun()

    if st.session_state.threads:
        st.markdown("**Chats**")
        for tid, meta in reversed(list(st.session_state.threads.items())):
            is_active = tid == st.session_state.active_thread
            icon = "▶ " if is_active else ""
            if st.button(
                f"{icon}{meta['title']}",
                key=f"btn_{tid}",
                use_container_width=True,
                help=meta["created_at"],
            ):
                st.session_state.active_thread = tid
                st.session_state.pending_confirm = None
                st.rerun()
    else:
        st.caption("No chats yet.")

    st.divider()
    st.caption("Powered by LangGraph + MCP")

# ── Main area ──────────────────────────────────────────────────────
if not st.session_state.active_thread:
    st.markdown("## 👋 Welcome to GitHub AI Agent")
    st.markdown("Click **＋ New Chat** in the sidebar to begin.")
    st.stop()

thread_id = st.session_state.active_thread
thread_meta = st.session_state.threads[thread_id]

new_title = st.text_input(
    "Chat title", value=thread_meta["title"],
    label_visibility="collapsed", key="chat_title"
)
if new_title != thread_meta["title"]:
    st.session_state.threads[thread_id]["title"] = new_title
    save_chats(st.session_state.threads)

st.caption(f"🕐 {thread_meta['created_at']}  •  Thread `{thread_id}`")
st.divider()

for event in thread_meta["messages"]:
    render_event(event)

# ── Pending HITL confirm ───────────────────────────────────────────
if st.session_state.pending_confirm:
    pc = st.session_state.pending_confirm
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
            append_event(thread_id, {"type": "system", "content": "✅ Action approved."})
            for e in events:
                append_event(thread_id, e)
            st.session_state.pending_confirm = None
            st.rerun()
    with col2:
        if st.button("❌ Deny", use_container_width=True):
            with st.spinner("Informing agent…"):
                events = resume_confirm(thread_id, False, pc["tool_call_id"], pc["tool_name"])
            append_event(thread_id, {"type": "system", "content": "❌ Action denied by user."})
            for e in events:
                append_event(thread_id, e)
            st.session_state.pending_confirm = None
            st.rerun()
    st.stop()

# ── Chat input ─────────────────────────────────────────────────────
user_input = st.chat_input("Ask the GitHub agent anything…")

if user_input:
    append_event(thread_id, {"type": "user", "content": user_input})

    # Change 2: Auto-title from first message (first 8 words, max 40 chars)
    if len(thread_meta["messages"]) == 1:
        words = user_input.strip().split()
        auto_title = " ".join(words[:8])
        if len(auto_title) > 40:
            auto_title = auto_title[:40] + "…"
        st.session_state.threads[thread_id]["title"] = auto_title
        save_chats(st.session_state.threads)

    with st.spinner("Agent is thinking…"):
        events = stream_response(thread_id, user_input)

    confirm_event = next((e for e in events if e["type"] == "confirm_required"), None)

    for e in events:
        if e["type"] != "confirm_required":
            append_event(thread_id, e)

    if confirm_event:
        st.session_state.pending_confirm = {
            "tool_name": confirm_event["tool_name"],
            "tool_args": confirm_event["tool_args"],
            "tool_call_id": confirm_event["tool_call_id"],
        }

    st.rerun()