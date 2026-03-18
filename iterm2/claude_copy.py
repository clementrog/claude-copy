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


# ── Claude Code transcript helpers (shared logic with claude-copy-last) ──


def find_session_by_pid(pids):
    sessions_dir = os.path.expanduser("~/.claude/sessions")
    if not os.path.isdir(sessions_dir):
        return None

    session_map = {}
    for f in glob.glob(os.path.join(sessions_dir, "*.json")):
        try:
            with open(f) as fh:
                s = json.load(fh)
                session_map[s["pid"]] = s
        except Exception:
            continue

    checked = set()
    to_check = list(pids)
    while to_check:
        pid = to_check.pop()
        if pid in checked or pid <= 1:
            continue
        checked.add(pid)
        if pid in session_map:
            return session_map[pid]
        try:
            out = subprocess.check_output(
                ["ps", "-o", "ppid=", "-p", str(pid)],
                stderr=subprocess.DEVNULL,
            )
            ppid = int(out.strip())
            to_check.append(ppid)
        except Exception:
            continue

    return None


def get_session_lines(session_id, cwd):
    project_slug = cwd.replace("/", "-")
    jsonl_path = os.path.expanduser(
        f"~/.claude/projects/{project_slug}/{session_id}.jsonl"
    )
    if not os.path.isfile(jsonl_path):
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
    plan_path = None
    for line in reversed(lines):
        obj = json.loads(line)
        if obj.get("type") != "assistant" or obj.get("isSidechain"):
            continue
        content = obj.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if block.get("type") != "tool_use":
                continue
            if block.get("name") not in ("Write", "Edit"):
                continue
            fp = block.get("input", {}).get("file_path", "")
            if "/.claude/plans/" in fp:
                plan_path = fp
                break
        if plan_path:
            break

    if plan_path and os.path.isfile(plan_path):
        with open(plan_path) as f:
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
    subprocess.run(
        [
            "osascript", "-e",
            f'display notification "{message}" with title "{title}"',
        ],
        stderr=subprocess.DEVNULL,
    )


def do_copy(job_pid, root_pid, mode):
    """Core logic: find session, extract content, copy to clipboard."""
    label = MODE_LABELS.get(mode, mode)
    pids = set()
    if job_pid:
        pids.add(int(job_pid))
    if root_pid:
        pids.add(int(root_pid))

    if not pids:
        return "No PIDs available"

    session = find_session_by_pid(pids)
    if not session:
        return "No Claude Code session found for this tab"

    lines = get_session_lines(session["sessionId"], session["cwd"])
    if not lines:
        return "Session transcript is empty"

    if mode == "plan":
        result = extract_plan(lines)
    elif mode == "ask":
        result = extract_last_ask(lines)
    else:
        result = extract_last_response(lines)

    if not result:
        return f"No {label.lower()} found"

    copy_to_clipboard(result)
    notify("claude-copy", f"{label} copied")
    return None


# ── iTerm2 RPC registration ──


async def main(connection):
    app = await iterm2.async_get_app(connection)

    @iterm2.RPC
    async def claude_copy_response(session_id=iterm2.Reference("id")):
        session = app.get_session_by_id(session_id)
        if not session:
            return
        job_pid = await session.async_get_variable("jobPid")
        root_pid = await session.async_get_variable("pid")
        err = do_copy(job_pid, root_pid, "text")
        if err:
            notify("claude-copy", err)

    @iterm2.RPC
    async def claude_copy_plan(session_id=iterm2.Reference("id")):
        session = app.get_session_by_id(session_id)
        if not session:
            return
        job_pid = await session.async_get_variable("jobPid")
        root_pid = await session.async_get_variable("pid")
        err = do_copy(job_pid, root_pid, "plan")
        if err:
            notify("claude-copy", err)

    @iterm2.RPC
    async def claude_copy_ask(session_id=iterm2.Reference("id")):
        session = app.get_session_by_id(session_id)
        if not session:
            return
        job_pid = await session.async_get_variable("jobPid")
        root_pid = await session.async_get_variable("pid")
        err = do_copy(job_pid, root_pid, "ask")
        if err:
            notify("claude-copy", err)

    await claude_copy_response.async_register(connection)
    await claude_copy_plan.async_register(connection)
    await claude_copy_ask.async_register(connection)


iterm2.run_forever(main)
