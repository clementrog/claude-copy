# claude-copy

Copy Claude Code output to your clipboard with a keyboard shortcut. No text selection needed.

When you're running Claude Code in your terminal and want to grab a response, a plan, or a set of questions — just hit a shortcut and paste wherever you need it.

## Shortcuts

| Shortcut | What it copies |
|---|---|
| `Cmd+Shift+C` | Last text response |
| `Cmd+Shift+P` | Plan (full `.md` content) |
| `Cmd+Shift+A` | Last question + all answer options |

**Tab-aware**: if you have multiple Claude Code sessions across tabs, the shortcut always copies from the tab you're looking at.

## Supported terminals

| Terminal | Status | How |
|---|---|---|
| **Kitty** | Supported | Remote control API (`kitten @ ls`) |
| **iTerm2** | Supported | Python API + RPC functions |
| Ghostty | Not yet | Waiting on remote control API ([#8797](https://github.com/ghostty-org/ghostty/discussions/8797)) |
| Zed / macOS Terminal | Not yet | No terminal plugin API available |

## Quick start

```bash
git clone https://github.com/clmusic/claude-copy.git
cd claude-copy
./install.sh
```

The installer detects which terminal(s) you have and sets up accordingly.

---

## Kitty

### What the installer does

1. Copies `claude-copy-last` to `~/.local/bin/`
2. Prints the config snippet to add to `~/.config/kitty/kitty.conf`

### Config to add

```conf
allow_remote_control yes
listen_on            unix:/tmp/kitty-{kitty_pid}

map cmd+shift+c launch --type=background sh -c '~/.local/bin/claude-copy-last | pbcopy'
map cmd+shift+p launch --type=background sh -c '~/.local/bin/claude-copy-last --plan | pbcopy'
map cmd+shift+a launch --type=background sh -c '~/.local/bin/claude-copy-last --ask | pbcopy'
```

Restart Kitty after adding these lines.

### Linux

Replace `pbcopy` with your clipboard tool:

```conf
# X11
map ctrl+shift+c launch --type=background sh -c '~/.local/bin/claude-copy-last | xclip -selection clipboard'

# Wayland
map ctrl+shift+c launch --type=background sh -c '~/.local/bin/claude-copy-last | wl-copy'
```

---

## iTerm2

### What the installer does

Copies `claude_copy.py` to `~/Library/Application Support/iTerm2/Scripts/AutoLaunch/` so it starts automatically with iTerm2.

### Manual steps after install

1. **Enable Python API**
   Preferences → General → Magic → check *Enable Python API*

2. **Install Python Runtime**
   Scripts menu → Manage → Install Python Runtime

3. **Restart iTerm2**

4. **Bind keys**
   Preferences → Keys → Key Bindings → click **+**

   | Shortcut | Action | Function |
   |---|---|---|
   | `Cmd+Shift+C` | Invoke Script Function | `claude_copy_response(session_id: id)` |
   | `Cmd+Shift+P` | Invoke Script Function | `claude_copy_plan(session_id: id)` |
   | `Cmd+Shift+A` | Invoke Script Function | `claude_copy_ask(session_id: id)` |

---

## How it works

Claude Code stores session transcripts as JSONL files in `~/.claude/projects/` and maps running sessions to PIDs in `~/.claude/sessions/`.

The script:

1. Asks the terminal which process is running in the focused tab
2. Walks up the process tree until it finds a matching Claude Code session
3. Reads that session's JSONL transcript
4. Extracts the requested content (last response, plan file, or question block)
5. Pipes it to the clipboard

Plans are stored as separate `.md` files in `~/.claude/plans/`. The script finds the plan path from the transcript and reads the file directly.

## CLI usage

```bash
claude-copy-last              # prints last response to stdout
claude-copy-last --plan       # prints plan
claude-copy-last --ask        # prints questions + options

claude-copy-last --help       # usage info
```

Pipe to `pbcopy` yourself, or use the keyboard shortcuts.

## Requirements

- Python 3.8+
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- Kitty or iTerm2 on macOS (Linux supported for Kitty)

## License

MIT
