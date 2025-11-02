---
name: Bash Environment Configuration for Termux
description: Set up modular bash configuration files (~/.bash_env, ~/.bash_alias, ~/.bashrc) for Termux development environment. Configure environment variables, PATH, Java/Android/NDK paths, editor settings, and shell behavior. Use when initializing bash environment or updating PATH variables.
---

# Bash Environment Configuration for Termux

## Overview
This skill creates a modular bash configuration system:
- **~/.bash_env** - Environment variables (JAVA_HOME, ANDROID_SDK_ROOT, paths, etc.)
- **~/.bash_alias** - Aliases (pbcopy/pbpaste for clipboard)
- **~/.bashrc** - Sources the above files on shell startup

This approach keeps configuration organized and maintainable.

## Configuration Files

### ~/.bash_env
Contains environment variables for:
- Java/JDK paths (JAVA_HOME)
- Android SDK paths (ANDROID_SDK_ROOT, ANDROID_HOME)
- Android NDK paths (ANDROID_NDK_HOME, NDK_HOME)
- Tool PATHs
- Editor preferences (EDITOR, VISUAL)
- Locale and locale settings
- History configuration
- Color support

### ~/.bash_alias
Minimal aliases file containing:
- `pbcopy` - Copy to clipboard (Termux-specific)
- `pbpaste` - Paste from clipboard (Termux-specific)

Uses termux-clipboard-set/get instead of xclip (xclip doesn't work on Termux).

### ~/.bashrc
Shell initialization file that:
- Sources ~/.bash_env if it exists
- Sources ~/.bash_alias if it exists
- Allows additional .bashrc customizations

## Installation Steps

### Step 1: Create ~/.bash_env
```bash
cat > ~/.bash_env << 'EOF'
# Termux Environment Variables

# Java and JDK
export JAVA_HOME=/data/data/com.termux/files/usr/lib/jvm/java-21-openjdk
export PATH=$JAVA_HOME/bin:$PATH

# Android SDK
export ANDROID_SDK_ROOT=$TERMUX_HOME/.local/share/android/sdk
export ANDROID_HOME=$ANDROID_SDK_ROOT
export PATH=$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$PATH
export PATH=$ANDROID_SDK_ROOT/build-tools/35.0.0:$PATH
export PATH=$ANDROID_SDK_ROOT/platform-tools:$PATH

# Android NDK (Termux-compatible)
export ANDROID_NDK_HOME=$ANDROID_SDK_ROOT/android-ndk-r27b
export NDK_HOME=$ANDROID_NDK_HOME
export PATH=$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-aarch64/bin:$PATH

# Editor preferences
export EDITOR=nvim
export VISUAL=nvim

# History settings
export HISTSIZE=10000
export HISTFILESIZE=10000
export HISTCONTROL=ignoredups:erasedups
export HISTTIMEFORMAT="%d/%m/%y %T "

# Color support
export LS_COLORS='di=1;36:ex=1;32:ln=1;31:*.tar=1;33:*.gz=1;33:'
export CLICOLOR=1

# Locale
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
EOF
```

### Step 2: Create ~/.bash_alias
```bash
cat > ~/.bash_alias << 'EOF'
# Clipboard aliases (macOS-style for Termux)
alias pbcopy='termux-clipboard-set'
alias pbpaste='termux-clipboard-get'
EOF
```

### Step 3: Create or Update ~/.bashrc
```bash
cat > ~/.bashrc << 'EOF'
if [ -f ~/.bash_env ]; then
    . ~/.bash_env
fi
if [ -f ~/.bash_alias ]; then
    . ~/.bash_alias
fi
EOF
```

### Step 4: Reload Configuration
```bash
source ~/.bashrc
```

### Step 5: Verify
```bash
echo $JAVA_HOME
echo $ANDROID_SDK_ROOT
which aapt2 adb
```

## Environment Variables Explained

### Java Paths
- `JAVA_HOME` - Points to Java 21 installation
- Used by: Gradle, Android build tools, IDEs
- Version-specific: Update if using different Java version

### Android Paths
- `ANDROID_SDK_ROOT` / `ANDROID_HOME` - SDK root directory
- `ANDROID_SDK_ROOT/cmdline-tools/latest/bin` - sdkmanager, avdmanager
- `ANDROID_SDK_ROOT/build-tools/35.0.0` - aapt2, aidl, zipalign, dexdump
- `ANDROID_SDK_ROOT/platform-tools` - adb, fastboot

### NDK Paths
- `ANDROID_NDK_HOME` / `NDK_HOME` - NDK root directory
- `ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-aarch64/bin` - Compilers (clang, clang++)
- Used by: CMake builds, native compilation

### Shell Behavior
- `EDITOR` / `VISUAL` - Default editor (nvim)
- `HISTSIZE` - Commands to remember in memory (10000)
- `HISTFILESIZE` - Commands to save to history file (10000)
- `HISTCONTROL` - Don't save duplicate commands (ignoredups:erasedups)
- `HISTTIMEFORMAT` - Include timestamp in history

### Locale
- `LANG` / `LC_ALL` - UTF-8 for proper character encoding
- Important for: Non-ASCII filenames, internationalized text

## PATH Order

Tools are added to PATH in this order (first match wins):
1. Java: `$JAVA_HOME/bin`
2. cmdline-tools: `$ANDROID_SDK_ROOT/cmdline-tools/latest/bin`
3. Build-tools: `$ANDROID_SDK_ROOT/build-tools/35.0.0`
4. Platform-tools: `$ANDROID_SDK_ROOT/platform-tools`
5. NDK toolchain: `$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-aarch64/bin`
6. System default PATH

## Clipboard Aliases

Termux has unique clipboard handling:
- Uses `termux-clipboard-set` to copy
- Uses `termux-clipboard-get` to paste
- Provides macOS-style aliases for familiarity

Example usage:
```bash
echo "Hello" | pbcopy
pbpaste  # outputs: Hello

# With tools
aapt2 version | pbcopy
```

## Customization

### Adding More Aliases
Edit ~/.bash_alias and add:
```bash
alias ll='ls -lah'
alias gs='git status'
```

### Adding More Environment Variables
Edit ~/.bash_env and add:
```bash
export MY_VAR=value
```

### Conditional Settings
Use conditionals in ~/.bash_env:
```bash
if [ -f ~/.local/share/some/file ]; then
    export CUSTOM_PATH=~/.local/share/some/path
fi
```

## Troubleshooting

### Variables not set
- Verify file exists: `ls -la ~/.bash_env ~/.bash_alias ~/.bashrc`
- Reload: `source ~/.bashrc`
- Check: `echo $JAVA_HOME`

### PATH not including tools
- Check order in ~/.bash_env
- Verify tool directories exist: `ls ~/.local/share/android/sdk/build-tools/35.0.0/`
- Test: `which aapt2`

### Aliases not working
- Reload: `source ~/.bash_alias`
- Non-interactive shells won't load aliases (use in ~/.bash_env if needed)
- Interactive shells load ~/.bashrc automatically

## Dependencies

**Requires first**:
- Bash shell installed (default in Termux)
- termux-clipboard-set/get available (for pbcopy/pbpaste)

**Enables**:
- Android SDK access via PATH
- Java tool access
- NDK compiler access
- Convenient clipboard operations
- Consistent shell experience

## Related Skills
- `android-sdk-setup` - Sets up SDK at path referenced in ~/.bash_env
- `android-ndk-setup` - Sets up NDK at path referenced in ~/.bash_env
- `kotlin-lsp-setup` - May add additional PATH entries
