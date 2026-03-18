# claude-copy

Keyboard shortcuts to copy Claude Code output to your clipboard. No mouse selection needed.

Works by reading Claude Code's session transcripts (`~/.claude/`) and matching the active terminal tab to the correct session via process ID.

## Shortcuts

| Shortcut | What it copies |
|---|---|
| `Cmd+Shift+C` | Last text response |
| `Cmd+Shift+P` | Plan (the full `.md` plan file) |
| `Cmd+Shift+A` | Last question + all answer options |

## Requirements

- **Kitty** or **iTerm2** on macOS
- Python 3.8+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)

## Install

```bash
git clone https://github.com/clmusic/claude-copy.git
cd claude-copy
./install.sh
```

The installer auto-detects your terminal and sets up accordingly.

---

## Kitty setup

The installer copies `claude-copy-last` to `~/.local/bin/` and tells you what to add to `~/.config/kitty/kitty.conf`:

```conf
allow_remote_control yes
listen_on            unix:/tmp/kitty-{kitty_pid}

map cmd+shift+c launch --type=background sh -c '~/.local/bin/claude-copy-last | pbcopy'
map cmd+shift+p launch --type=background sh -c '~/.local/bin/claude-copy-last --plan | pbcopy'
map cmd+shift+a launch --type=background sh -c '~/.local/bin/claude-copy-last --ask | pbcopy'
```

Restart Kitty to apply.

### How it works (Kitty)

1. A keybinding triggers `claude-copy-last` as a background process
2. The script queries Kitty's remote control API (`kitten @ ls`) to find the focused tab's foreground PID
3. It walks up the process tree to match a Claude Code session in `~/.claude/sessions/`
4. It reads the session's JSONL transcript and extracts the requested content
5. Output is piped to `pbcopy`

---

## iTerm2 setup

The installer copies an AutoLaunch Python script to iTerm2's Scripts folder. You then need to:

1. **Enable Python API**: Preferences > General > Magic > Enable Python API
2. **Install runtime**: Scripts > Manage > Install Python Runtime
3. **Restart iTerm2** (so the script auto-launches)
4. **Bind keys**: Preferences > Keys > Key Bindings, click **+**:
   - Set your shortcut (e.g. `Cmd+Shift+C`)
   - Action: **Invoke Script Function**
   - Function: `claude_copy_response(session_id: id)`

| Function to invoke | What it copies |
|---|---|
| `claude_copy_response(session_id: id)` | Last text response |
| `claude_copy_plan(session_id: id)` | Plan |
| `claude_copy_ask(session_id: id)` | Last question + options |

### How it works (iTerm2)

1. A keybinding invokes a registered RPC function in the AutoLaunch script
2. The script reads `jobPid` and `pid` from the focused iTerm2 session
3. Same process-tree walk and JSONL extraction as the Kitty version
4. Result is copied via `pbcopy`

---

## Tab awareness

Both integrations are tab-aware. Each terminal tab runs its own Claude Code session, and the shortcuts always copy from the **focused tab**.

## CLI usage (Kitty)

You can also use `claude-copy-last` directly:

```bash
claude-copy-last | pbcopy           # last response
claude-copy-last --plan | pbcopy    # plan
claude-copy-last --ask | pbcopy     # questions
```

## Terminal support

| Terminal | Status |
|---|---|
| Kitty | Supported |
| iTerm2 | Supported |
| Ghostty | Blocked (no remote control API yet) |
| Zed | Blocked (no terminal plugin API) |
| macOS Terminal | Blocked (no scripting API) |

## License

MIT
