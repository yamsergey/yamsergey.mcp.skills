---
name: tmux Terminal Multiplexer Setup for Termux
description: Set up tmux with Catppuccin Mocha theme and TPM (Tmux Plugin Manager). Configure mouse support, 256-color terminal, status bar positioning, and Catppuccin plugin. Use when initializing terminal multiplexer or configuring tmux appearance.
---

# tmux Terminal Multiplexer Setup for Termux

## Overview
This skill installs and configures:
- **tmux** - Terminal multiplexer for multiple windows/panes
- **TPM** - Tmux Plugin Manager for plugin management
- **Catppuccin/tmux** - Mocha color theme for tmux
- **Mouse support** - Click to select panes/windows
- **256-color support** - Full color palette for terminal

## Prerequisites
- Termux environment
- git installed
- tmux installed (via `pkg install tmux`)

## Installation Steps

### Step 1: Install tmux
```bash
pkg install -y tmux
tmux -V
```

### Step 2: Create ~/.tmux.conf
```bash
cat > ~/.tmux.conf << 'EOF'
set -g mouse on
set -g default-terminal "tmux-256color"
set -g status-position top

set -g @plugin 'tmux-plugins/tpm'
set -g @plugin 'catppuccin/tmux'

set -g @catppuccin_flavor "mocha"
set -g @catppuccin_window_status_style "rounded"

run ~/.tmux/plugins/catppuccin/tmux/catppuccin.tmux
run '~/.tmux/plugins/tpm/tpm'
EOF
```

### Step 3: Install TPM
```bash
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
```

### Step 4: Start tmux and Load Plugins
```bash
tmux
```

Inside tmux, press `Ctrl-b` then `Shift-i` (capital I):
```
Tmux plugins manager will install plugins from ~/.tmux.conf
```

Or run externally:
```bash
~/.tmux/plugins/tpm/bin/install_plugins
```

### Step 5: Reload Configuration
```bash
tmux source ~/.tmux.conf
```

## Configuration Details

### Mouse Support
```
set -g mouse on
```
Enables:
- Click to select panes
- Click to select windows in status bar
- Scroll wheel support
- Drag to resize panes

### Terminal Settings
```
set -g default-terminal "tmux-256color"
```
- Enables 256-color support for better syntax highlighting
- Supports modern terminal features
- Compatible with Termux terminal emulator

### Status Bar Position
```
set -g status-position top
```
- Places status bar at top of screen
- Shows window list and tmux status

### Catppuccin Plugin
```
set -g @plugin 'catppuccin/tmux'
set -g @catppuccin_flavor "mocha"
set -g @catppuccin_window_status_style "rounded"
```
- Provides Mocha color theme (dark background)
- Rounded window status indicators
- Consistent with editor/prompt themes

## Default Keybindings

### Window Management
- `Ctrl-b` + `c` - Create new window
- `Ctrl-b` + `n` - Next window
- `Ctrl-b` + `p` - Previous window
- `Ctrl-b` + `0-9` - Select window by number
- `Ctrl-b` + `,` - Rename window
- `Ctrl-b` + `&` - Kill window

### Pane Management
- `Ctrl-b` + `%` - Split pane vertically
- `Ctrl-b` + `"` - Split pane horizontally
- `Ctrl-b` + `o` - Move to next pane
- `Ctrl-b` + `arrow keys` - Navigate panes
- `Ctrl-b` + `x` - Kill pane
- `Ctrl-b` + `z` - Toggle pane zoom

### Session Management
- `Ctrl-b` + `d` - Detach from session
- `tmux new-session -s name` - Create named session
- `tmux attach-session -t name` - Attach to session
- `tmux list-sessions` - List all sessions

### Copy Mode
- `Ctrl-b` + `[` - Enter copy mode (use arrow keys)
- Space - Start selection
- Enter - Copy selection
- `Ctrl-b` + `]` - Paste selection

## Directory Structure

```
~/.tmux/
├── conf/
│   └── (optional custom configs)
└── plugins/
    ├── tpm/
    │   └── tpm script
    └── catppuccin/
        └── tmux/
            └── tmux plugin files
```

## Troubleshooting

### Plugins not installing
- Check TPM directory exists: `ls -la ~/.tmux/plugins/tpm/`
- Verify git cloned successfully
- Inside tmux: `Prefix + Shift + I` (capital I)
- Or run: `~/.tmux/plugins/tpm/bin/install_plugins`

### Catppuccin theme not loading
- Verify plugin line in ~/.tmux.conf: `set -g @plugin 'catppuccin/tmux'`
- Check plugin directory: `ls -la ~/.tmux/plugins/`
- Reload: `tmux source ~/.tmux.conf`

### Colors look wrong
- Ensure terminal supports 256 colors: `echo $TERM`
- Should be: tmux-256color (when inside tmux)
- Verify: `tmux info | grep -i color`

### Mouse not working
- Check config has: `set -g mouse on`
- Some terminal emulators need specific settings
- Try toggling: `Ctrl-b` then `:set mouse on/off`

### Performance issues
- Check for plugin conflicts: `tmux list-plugins` (if using TPM)
- Try with minimal config to isolate issue
- Run `tmux info` to debug

## Customization

### Change Keybindings
Edit ~/.tmux.conf:
```
# Rebind prefix to Ctrl-a
set -g prefix C-a
unbind C-b
bind C-a send-prefix
```

### Add More Plugins
Edit ~/.tmux.conf and add:
```
set -g @plugin 'author/plugin-name'
```

Then install with `Ctrl-b + Shift-I`

### Change Color Scheme
Edit ~/.tmux.conf:
```
set -g @catppuccin_flavor "latte"  # or frappe, macchiato, mocha
```

### Customize Window Status Style
```
set -g @catppuccin_window_status_style "slanted"  # or rounded, custom
```

## Integration with Neovim

### Seamless Pane Navigation
Use vim-tmux-navigator plugin to navigate panes as if they were vim splits:
- Works in Neovim and tmux panes together
- `Ctrl-j/k/l/h` to move between panes/splits

### Clipboard Integration
Both tmux and vim can access system clipboard:
- Use `pbcopy`/`pbpaste` (configured in bash)
- Works across panes and vim buffers

## Common Workflows

### Full-Screen Coding Session
```bash
tmux new-session -s dev

# Inside tmux:
# Create pane for editor
Ctrl-b + %

# Create pane for terminal
Ctrl-b + "

# Zoom editor to see more
Ctrl-b + z
```

### Remote Development
```bash
# Detach locally
Ctrl-b + d

# SSH to remote, reattach
tmux attach-session -t dev
```

### Running Tests While Editing
```bash
# Pane 1: Neovim editor
# Pane 2: Test runner

# Switch: Ctrl-b + o
# Watch test output while coding
```

## Dependencies

**Requires first**:
- Tmux installed
- Git installed

**Enables**:
- Terminal multiplexing
- Multiple windows/panes in single terminal
- Session management
- Persistent sessions (survives terminal close)

**Integrates with**:
- `neovim-lazyvim-setup` - Editor works seamlessly in tmux panes
- `bash-environment-config` - Clipboard aliases work in tmux

## Related Skills
- `neovim-lazyvim-setup` - Editor for use in tmux panes
- `bash-environment-config` - Clipboard operations in tmux
- `starship-prompt-setup` - Modern shell prompt in tmux
