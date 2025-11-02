---
name: Android NDK Setup for Termux
description: Set up Android Native Development Kit (NDK) on Termux using Termux-compatible version r27b. Downloads from lzhiyong/termux-ndk repository, extracts, and configures paths. Use when setting up native Android development or C/C++ compilation for Android.
---

# Android NDK Setup for Termux

## Overview
This skill installs Android NDK r27b, a Termux-compatible version of the Native Development Kit. The official Android NDK does not work on Termux; this version is purpose-built for aarch64 Termux environments.

## Why Termux-Compatible NDK?

The official Android NDK:
- Expects Linux x86_64/arm64 host architecture
- Incompatible with Termux's environment
- Won't execute on aarch64 Termux

The Termux-compatible NDK from lzhiyong:
- Built specifically for aarch64 Android
- Contains correct toolchain binaries for Termux
- Supports C/C++ compilation targeting Android

## Prerequisites
- Termux environment
- curl and unzip installed
- ~1.5GB free storage
- Android SDK already set up (optional but recommended)

## Installation Steps

### Step 1: Download NDK
```bash
cd ~/.local/share/android/sdk
curl -L -o android-ndk-r27b.zip https://github.com/lzhiyong/termux-ndk/releases/download/android-ndk-r27b/android-ndk-r27b-linux-aarch64.zip
unzip -q android-ndk-r27b.zip
rm android-ndk-r27b.zip
```

### Step 2: Verify Installation
```bash
ls -la ~/.local/share/android/sdk/android-ndk-r27b/toolchains/llvm/prebuilt/linux-aarch64/bin/
```

Should show compilers like:
- aarch64-linux-android-clang
- aarch64-linux-android-clang++
- clang
- clang++

### Step 3: Configure Paths in ~/.bash_env
```bash
# Android NDK (Termux-compatible)
export ANDROID_NDK_HOME=$ANDROID_SDK_ROOT/android-ndk-r27b
export NDK_HOME=$ANDROID_NDK_HOME
export PATH=$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-aarch64/bin:$PATH
```

### Step 4: Verify Configuration
```bash
source ~/.bash_env
which clang
clang --version
aarch64-linux-android-clang --version
```

## Directory Structure
```
~/.local/share/android/sdk/android-ndk-r27b/
├── toolchains/
│   └── llvm/
│       └── prebuilt/
│           └── linux-aarch64/
│               ├── bin/          (compilers and tools)
│               ├── lib/
│               └── include/
├── platforms/
├── sources/
│   ├── android/
│   ├── cxx-stl/
│   └── third_party/
└── build/
```

## Environment Variables

After setup, these are available:
- `$ANDROID_NDK_HOME` - Points to NDK root
- `$NDK_HOME` - Alias for ANDROID_NDK_HOME
- `$PATH` includes NDK toolchain binaries

## Compiler Information

### Available Compilers
- **clang/clang++** - Modern LLVM-based compilers
- **aarch64-linux-android-clang** - For Android aarch64 targets
- **armv7a-linux-android-clang** - For Android ARMv7 targets
- **x86_64-linux-android-clang** - For Android x86_64 targets

### API Level Configuration
Specify target API when compiling:
```bash
clang -target aarch64-linux-android30 main.c -o main
```

## Common Compilation Commands

### Simple C Program
```bash
clang -target aarch64-linux-android30 program.c -o program
```

### C++ with STL
```bash
clang++ -target aarch64-linux-android30 program.cpp -stdlib=libc++ -o program
```

### With OpenSSL or other libraries
```bash
clang -target aarch64-linux-android30 -I$ANDROID_SDK_ROOT/platforms/android-36/arch-arm64/usr/include \
  program.c -o program
```

## Troubleshooting

### clang command not found
- Verify NDK path: `ls ~/.local/share/android/sdk/android-ndk-r27b/toolchains/llvm/prebuilt/linux-aarch64/bin/`
- Source ~/.bash_env: `source ~/.bash_env`
- Add to PATH if needed

### Permission denied
- Check executable bit: `ls -la ~/.local/share/android/sdk/android-ndk-r27b/toolchains/llvm/prebuilt/linux-aarch64/bin/clang`
- Should be executable (-rwx)

### Compilation errors with Android API
- Check available platforms: `ls ~/.local/share/android/sdk/platforms/`
- Adjust target API: `-target aarch64-linux-android36`

## Dependencies

**Requires first**:
- Android SDK setup (for SDK structure)
- Bash environment config (for ~/.bash_env)

**Depends on**:
- `bash-environment-config` skill
- `android-sdk-setup` skill (optional, but recommended)

**Enables**:
- Native C/C++ compilation for Android
- LLVM-based toolchain access
- Integration with Gradle native builds

## Related Skills
- `android-sdk-setup` - Installs SDK tools and platforms
- `bash-environment-config` - Sets up environment variables
- `gradle-setup` - Configures Gradle with NDK support
