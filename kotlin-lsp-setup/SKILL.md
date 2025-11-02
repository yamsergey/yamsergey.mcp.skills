---
name: Kotlin Language Server Setup for Termux
description: Install and configure Kotlin Language Server (kotlin-lsp) for IDE-like support in Neovim. Downloads from fwcd/kotlin-language-server, installs Termux-compatible libfilewatcher, and integrates with neovim-lspconfig. Use when adding Kotlin development support to Neovim.
---

# Kotlin Language Server Setup for Termux

## Overview
This skill installs Kotlin Language Server, enabling IDE-like features in Neovim:
- Code completion and autocompletion
- Diagnostics and error messages
- Go to definition / Find references
- Hover documentation
- Code formatting
- Symbol navigation

## Prerequisites
- Neovim with LazyVim already installed
- bash-environment-config skill completed (for PATH)
- neovim-lazyvim-setup skill completed
- ~300MB free storage
- curl and unzip installed

## What Gets Installed

### Kotlin Language Server
- **Version**: 0.253.10629
- **Purpose**: IDE-like support for Kotlin files
- **Location**: `~/.local/share/kotlin-lsp/`
- **Binary**: `kotlin-lsp.sh` wrapper script
- **Download**: https://github.com/fwcd/kotlin-language-server/releases

### Termux-Compatible libfilewatcher
- **Purpose**: File watching for Kotlin LSP (Kotlin LSP dependency)
- **Location**: `~/.local/share/kotlin-lsp/native/Linux-AArch64/`
- **Filename**: `libfilewatcher_jni.so`
- **Why needed**: Termux requires special build for aarch64
- **Source**: https://github.com/lzhiyong/libfilewatcher

### Command Symlink
- **Creates**: `/data/data/com.termux/files/usr/bin/kotlin-lsp`
- **Purpose**: Makes kotlin-lsp available in PATH as a command

## Installation Steps

### Step 1: Create Kotlin LSP Directory
```bash
mkdir -p ~/.local/share/kotlin-lsp/native/Linux-AArch64
cd ~/.local/share/kotlin-lsp
```

### Step 2: Download Kotlin Language Server
```bash
curl -L -o kotlin-lsp.zip https://github.com/fwcd/kotlin-language-server/releases/download/0.253.10629/server.zip
unzip -q kotlin-lsp.zip
rm kotlin-lsp.zip
```

### Step 3: Download Termux-Compatible libfilewatcher
```bash
curl -L -o native/Linux-AArch64/libfilewatcher_jni.so \
  https://github.com/lzhiyong/libfilewatcher/releases/download/1.0/libfilewatcher_jni.so
```

### Step 4: Create Command Symlink
```bash
ln -sf ~/.local/share/kotlin-lsp/bin/kotlin-language-server.sh \
  /data/data/com.termux/files/usr/bin/kotlin-lsp
```

### Step 5: Verify Installation
```bash
kotlin-lsp --version
```

Should output Kotlin LSP version information.

## Neovim Integration

### Add to Neovim Configuration

Create `~/.config/nvim/lua/plugins/kotlin.lua`:

```lua
return {
  {
    "mfussenegger/nvim-lspconfig",
    opts = {
      servers = {
        kotlin_language_server = {
          cmd = { "kotlin-lsp" },
          root_dir = function(fname)
            return require("lspconfig").util.root_pattern("build.gradle", "settings.gradle", ".git")(fname)
          end,
        },
      },
    },
  },
}
```

### Install in Neovim
Open a `.kt` file in Neovim, it will automatically detect and configure the LSP.

Verify with:
```vim
:LspInfo
```

Should show:
```
Clients:
    kotlin_language_server (id: 1) -- Running
```

## Directory Structure

```
~/.local/share/kotlin-lsp/
├── bin/
│   ├── kotlin-language-server.sh
│   └── kotlin-language-server (executable)
├── lib/
│   └── (jar files and dependencies)
├── native/
│   └── Linux-AArch64/
│       └── libfilewatcher_jni.so  (Termux-compatible)
└── server/
    └── (additional server files)

/data/data/com.termux/files/usr/bin/
└── kotlin-lsp -> ~/.local/share/kotlin-lsp/bin/kotlin-language-server.sh (symlink)
```

## Features Provided

### Code Completion
- Type-aware autocompletion
- Import suggestions
- Snippet support

### Diagnostics
- Real-time error highlighting
- Warning and info messages
- Lint-like checks

### Navigation
- Go to definition: `gd`
- Find references: `gr`
- Symbol navigation: `<Space>ss`

### Documentation
- Hover to see docs: `K`
- Parameter hints on function calls

### Formatting
- Format code: `<Space>cf` (with LazyVim)
- Respects Kotlin style conventions

## Kotlin Development Workflow

### Create Kotlin File
```bash
nvim MyClass.kt
```

### Write Kotlin Code
```kotlin
class MyClass {
    fun greet(name: String): String = "Hello, $name!"
}
```

### Use LSP Features
- Type hints show automatically
- Press `K` to see documentation
- Press `gd` to go to definition
- Press `gr` to find references

### Compile Kotlin (if Gradle installed)
```bash
gradle build
```

## Configuration Details

### How Kotlin LSP Finds Gradle Projects
Root directory is detected by looking for:
- `build.gradle` - Gradle build file
- `settings.gradle` - Gradle settings
- `.git` - Git repository root

LSP will start from the nearest of these files.

### Environment Used
- `JAVA_HOME` - Must be set (configured in bash-environment-config)
- `ANDROID_SDK_ROOT` - Optional, for Android Kotlin projects
- `KOTLIN_HOME` - Automatically detected from LSP installation

## Troubleshooting

### kotlin-lsp command not found
- Verify symlink: `ls -la /data/data/com.termux/files/usr/bin/kotlin-lsp`
- Verify installation: `ls ~/.local/share/kotlin-lsp/bin/kotlin-language-server.sh`
- Check permissions: Should be executable
- Run in new shell: `bash -i -c "which kotlin-lsp"`

### LSP not starting in Neovim
- Check kotlin.lua exists: `ls ~/.config/nvim/lua/plugins/kotlin.lua`
- Verify JAVA_HOME: `echo $JAVA_HOME`
- Check LSP status: `:LspInfo` in Neovim
- View error log: `:LspLog` in Neovim

### libfilewatcher missing errors
- Verify file exists: `ls ~/.local/share/kotlin-lsp/native/Linux-AArch64/libfilewatcher_jni.so`
- Check for Termux-specific build: Downloaded from lzhiyong, not official
- File should be ~1.5MB

### Slow autocompletion
- This is normal on first use (building caches)
- Subsequent completions are faster
- Check Neovim LSP performance: `:LspLog`

### Can't find Gradle project root
- Ensure build.gradle or settings.gradle exists
- Or initialize git repo: `git init`
- LSP searches up directory tree for root markers

### JAVA_HOME not found
- Verify Java is installed: `java -version`
- Check bash-environment-config was completed
- Source shell: `source ~/.bash_env`

## Performance Notes

### First Launch
- First time opening .kt file may take 10-30 seconds
- LSP is indexing your project
- Subsequent launches are faster

### Caching
- LSP caches project information
- Cache stored in project directory
- Delete .gradle/kotlin to force rebuild

### Memory Usage
- Kotlin LSP uses some memory (~300-500MB typical)
- Check with: `ps aux | grep kotlin-lsp`
- Monitor on low-RAM devices

## Dependencies

**Requires first**:
- neovim-lazyvim-setup skill (editor and plugins)
- bash-environment-config skill (for PATH and JAVA_HOME)

**Depends on**:
- JAVA_HOME configured (from bash-environment-config)
- Neovim 0.9+ with LSP support
- kotlin-lsp command in PATH

**Enables**:
- Kotlin file editing with IDE features
- Integration with Gradle builds
- Android Kotlin development in Neovim
- Project-wide refactoring

## Related Skills
- `neovim-lazyvim-setup` - Editor configuration
- `bash-environment-config` - Environment setup
- `android-sdk-setup` - For Android Kotlin projects
- `gradle-setup` - For Gradle-based Kotlin projects

## Resources

- Kotlin Language Server: https://github.com/fwcd/kotlin-language-server
- Kotlin Docs: https://kotlinlang.org/docs/
- Neovim LSP: https://neovim.io/doc/user/lsp.html
- LazyVim: https://www.lazyvim.org/
