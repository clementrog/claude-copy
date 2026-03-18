#!/usr/bin/env python3
"""iTerm2 AutoLaunch script for claude-copy.

Registers three RPC functions that can be bound to keyboard shortcuts:
  - claude_copy_response(session_id)  — copy last text response
  - claude_copy_plan(session_id)      — copy plan file content
  - claude_copy_ask(session_id)       — copy last question + options

Setup:
  1. Enable Python API: Preferences > General > Magic > Enable Python API
  2. Install runtime: Scripts > Manage > Install Python Runtime
  3. Symlink or copy this file to:
     ~/Library/Application Support/iTerm2/Scripts/AutoLaunch/claude_copy.py
  4. Restart iTerm2
  5. Bind keys in Preferences > Keys > Key Bindings:
     Action: "Invoke Script Function"
     - claude_copy_response(session_id: id)
     - claude_copy_plan(session_id: id)
     - claude_copy_ask(session_id: id)
"""
import iterm2
import json
import os
import re
import glob
import subprocess
import logging

LOG_PATH = os.path.expanduser("~/.claude/claude-copy-iterm2.log")
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.DEBUG,
    format="%(asctime)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("claude-copy")


# ── Claude Code transcript helpers ──


def find_session_by_pid(pids):
    sessions_dir = os.path.expanduser("~/.claude/sessions")
    if not os.path.isdir(sessions_dir):
        log.debug("sessions dir not found")
        return None

    session_map = {}
    for f in glob.glob(os.path.join(sessions_dir, "*.json")):
        try:
            with open(f) as fh:
                s = json.load(fh)
                session_map[s["pid"]] = s
        except Exception:
            continue

    log.debug(f"session_map PIDs: {sorted(session_map.keys())}")
    log.debug(f"searching from PIDs: {pids}")

    checked = set()
    to_check = list(pids)
    while to_check:
        pid = to_check.pop()
        if pid in checked or pid <= 1:
            continue
        checked.add(pid)
        if pid in session_map:
            log.debug(f"matched session at pid={pid}")
            return session_map[pid]
        try:
            out = subprocess.check_output(
                ["ps", "-o", "ppid=", "-p", str(pid)],
                stderr=subprocess.DEVNULL,
            )
            ppid = int(out.strip())
            to_check.append(ppid)
        except Exception:
            log.debug(f"ps failed for pid={pid} (process gone)")
            continue

    log.debug(f"no match found. checked: {sorted(checked)}")
    return None


def get_session_lines(session_id, cwd):
    project_slug = cwd.replace("/", "-")
    jsonl_path = os.path.expanduser(
        f"~/.claude/projects/{project_slug}/{session_id}.jsonl"
    )
    if not os.path.isfile(jsonl_path):
        log.debug(f"JSONL not found: {jsonl_path}")
        return []
    with open(jsonl_path) as f:
        return f.readlines()


def extract_last_response(lines):
    for line in reversed(lines):
        obj = json.loads(line)
        if obj.get("type") != "assistant" or obj.get("isSidechain"):
            continue
        content = obj.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue
        texts = []
        for block in content:
            if block.get("type") == "text":
                t = block.get("text", "").strip()
                t = re.sub(
                    r"<system-reminder>.*?</system-reminder>", "", t, flags=re.DOTALL
                ).strip()
                if t:
                    texts.append(t)
        if texts:
            return "\n\n".join(texts)
    return None


def extract_plan(lines):
    for line in reversed(lines):
        obj = json.loads(line)
        if obj.get("type") != "assistant" or obj.get("isSidechain"):
            continue
        content = obj.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue
        for block in reversed(content):
            if block.get("type") != "tool_use":
                continue
            if block.get("name") == "ExitPlanMode":
                plan_text = block.get("input", {}).get("plan", "")
                if plan_text.strip():
                    log.debug(f"found plan in ExitPlanMode ({len(plan_text)} chars)")
                    return plan_text.strip()
            if block.get("name") in ("Write", "Edit"):
                fp = block.get("input", {}).get("file_path", "")
                if "/.claude/plans/" in fp and os.path.isfile(fp):
                    log.debug(f"found plan file: {fp}")
                    with open(fp) as f:
                        return f.read().strip()
    return None


def format_ask(input_data):
    parts = []
    for q in input_data.get("questions", []):
        header = q.get("header", "")
        question = q.get("question", "")
        multi = q.get("multiSelect", False)

        if header:
            parts.append(f"## {header}")
        parts.append(question)
        if multi:
            parts.append("(multiple choice)")
        parts.append("")

        for i, opt in enumerate(q.get("options", []), 1):
            label = opt.get("label", "")
            desc = opt.get("description", "")
            if desc:
                parts.append(f"  {i}. {label} -- {desc}")
            else:
                parts.append(f"  {i}. {label}")
        parts.append("")

    return "\n".join(parts).strip()


def extract_last_ask(lines):
    for line in reversed(lines):
        obj = json.loads(line)
        if obj.get("type") != "assistant" or obj.get("isSidechain"):
            continue
        content = obj.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue
        for block in reversed(content):
            if (
                block.get("type") == "tool_use"
                and block.get("name") == "AskUserQuestion"
            ):
                return format_ask(block.get("input", {}))
    return None


MODE_LABELS = {"text": "Response", "plan": "Plan", "ask": "Questions"}


def copy_to_clipboard(text):
    subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)


def notify(title, message):
    escaped = message.replace("\\", "\\\\").replace('"', '\\"')
    subprocess.Popen(
        ["osascript", "-e", f'display notification "{escaped}" with title "{title}"'],
        stderr=subprocess.DEVNULL,
    )


def do_copy(job_pid, root_pid, mode):
    """Find session, extract content, copy to clipboard. Returns (success, message)."""
    label = MODE_LABELS.get(mode, mode)
    pids = set()
    if job_pid:
        pids.add(int(job_pid))
    if root_pid:
        pids.add(int(root_pid))

    log.debug(f"do_copy mode={mode} jobPid={job_pid} rootPid={root_pid}")

    if not pids:
        return (False, "No PIDs available")

    session = find_session_by_pid(pids)
    if not session:
        return (False, "No Claude Code session in this tab")

    log.debug(f"found session: {session['sessionId'][:12]}... cwd={session['cwd']}")

    lines = get_session_lines(session["sessionId"], session["cwd"])
    if not lines:
        return (False, "Session transcript is empty")

    if mode == "plan":
        result = extract_plan(lines)
    elif mode == "ask":
        result = extract_last_ask(lines)
    else:
        result = extract_last_response(lines)

    if not result:
        return (False, f"No {label.lower()} found")

    copy_to_clipboard(result)
    log.debug(f"copied {len(result)} chars to clipboard")
    return (True, f"{label} copied")


# ── iTerm2 RPC registration ──


async def main(connection):
    app = await iterm2.async_get_app(connection)
    log.info("claude-copy RPC registered")

    async def _do(session_id, mode):
        # Re-fetch app to get fresh state
        app_now = await iterm2.async_get_app(connection)
        window = app_now.current_window
        if not window:
            notify("claude-copy", "No active window")
            return
        iterm_session = window.current_tab.current_session
        if not iterm_session:
            notify("claude-copy", "No active session")
            return
        job_pid = await iterm_session.async_get_variable("jobPid")
        root_pid = await iterm_session.async_get_variable("pid")
        tty = await iterm_session.async_get_variable("tty")
        log.debug(f"_do: mode={mode} session_id={iterm_session.session_id} jobPid={job_pid} pid={root_pid} tty={tty}")
        success, message = do_copy(job_pid, root_pid, mode)
        notify("claude-copy", message)

    @iterm2.RPC
    async def claude_copy_response(session_id=iterm2.Reference("id")):
        await _do(session_id, "text")

    @iterm2.RPC
    async def claude_copy_plan(session_id=iterm2.Reference("id")):
        await _do(session_id, "plan")

    @iterm2.RPC
    async def claude_copy_ask(session_id=iterm2.Reference("id")):
        await _do(session_id, "ask")

    await claude_copy_response.async_register(connection)
    await claude_copy_plan.async_register(connection)
    await claude_copy_ask.async_register(connection)


iterm2.run_forever(main)
