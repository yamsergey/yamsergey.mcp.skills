---
name: Android SDK Setup for Termux
description: Set up Android SDK (cmdline-tools, build-tools, platform-tools) with static community builds optimized for Termux/Android aarch64 architecture. Handles downloading, extracting, and configuring static tools from lzhiyong/android-sdk-tools repository. Use when setting up Android development environment or replacing broken Android tools.
---

# Android SDK Setup for Termux

## Overview
This skill sets up Android SDK tools on Termux using static, community-built binaries optimized for Android aarch64. These tools are more reliable than the default Termux packages and avoid compatibility issues with Android 15+.

## Prerequisites
- Termux environment with bash
- curl and unzip installed
- ~2GB free storage
- JAVA_HOME already configured

## What Gets Installed

### cmdline-tools
- **Version**: Latest from Google
- **Purpose**: sdkmanager for downloading platforms and NDK
- **Location**: `~/.local/share/android/sdk/cmdline-tools/latest/`

### Static Build Tools (35.0.2)
Community-built at https://github.com/lzhiyong/android-sdk-tools/releases/download/35.0.2/
- **aapt2** - Android Asset Packaging Tool
- **aapt** - Legacy asset tool
- **aidl** - Android Interface Definition Language compiler
- **zipalign** - APK alignment tool
- **Other tools** - dexdump, split-select, etc.

### Static Platform Tools (35.0.2)
- **adb** - Android Debug Bridge
- **fastboot** - Bootloader flashing tool
- **Other platform utilities**

### Platforms and System Images
- Android API 36 (latest)
- Additional APIs as needed

## Installation Steps

### Step 1: Create SDK Directory Structure
```bash
mkdir -p ~/.local/share/android/sdk
cd ~/.local/share/android/sdk
```

### Step 2: Download and Extract cmdline-tools
```bash
curl -L -o cmdline-tools.zip https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
unzip -q cmdline-tools.zip
mv cmdline-tools latest
rm cmdline-tools.zip
```

### Step 3: Download Android Platforms
```bash
sdkmanager "platforms;android-36"
```

### Step 4: Download Static Android Tools (35.0.2)
```bash
cd ~
curl -L -o android-sdk-tools-static.zip "https://github.com/lzhiyong/android-sdk-tools/releases/download/35.0.2/android-sdk-tools-static-aarch64.zip"
unzip -q android-sdk-tools-static.zip
```

### Step 5: Replace Existing Tools
```bash
# Backup current tools
cp -r ~/.local/share/android/sdk/build-tools/35.0.0 ~/.local/share/android/sdk/build-tools/35.0.0.backup

# Replace build-tools
cp ~/build-tools/* ~/.local/share/android/sdk/build-tools/35.0.0/

# Replace platform-tools
cd ~/.local/share/android/sdk/platform-tools
rm -rf *
cp ~/platform-tools/* .

# Clean up
cd ~ && rm -rf build-tools platform-tools others android-sdk-tools-static.zip
```

### Step 6: Verify Installation
```bash
~/.local/share/android/sdk/build-tools/35.0.0/aapt2 version
~/.local/share/android/sdk/platform-tools/adb version
```

## Configuration
After installation, configure in `~/.bash_env`:
```bash
export ANDROID_SDK_ROOT=$TERMUX_HOME/.local/share/android/sdk
export ANDROID_HOME=$ANDROID_SDK_ROOT
export PATH=$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$PATH
export PATH=$ANDROID_SDK_ROOT/build-tools/35.0.0:$PATH
export PATH=$ANDROID_SDK_ROOT/platform-tools:$PATH
```

And in `~/.gradle/gradle.properties`:
```properties
android.aapt2FromMavenOverride=/data/data/com.termux/files/home/.local/share/android/sdk/build-tools/35.0.0/aapt2
org.gradle.jvmargs=-Xmx4096m
```

## Why Static Tools?

The static builds from lzhiyong/android-sdk-tools are:
1. **Purpose-built for Termux** - No dependency on Termux package versions
2. **Android 15+ compatible** - Tested on current Android versions
3. **Reliable** - Consistent across devices and updates
4. **aarch64 optimized** - Proper native code for ARM64 architecture

Default Termux packages sometimes have issues with:
- Missing dependencies
- Incompatibility with Android 15
- Lagging behind latest builds
- Dynamic linking issues

## Troubleshooting

### aapt2 command not found
- Verify path is in ~/.bash_env: `~/.local/share/android/sdk/build-tools/35.0.0`
- Source environment: `source ~/.bash_env`
- Test: `~/.local/share/android/sdk/build-tools/35.0.0/aapt2 version`

### Build-tools/35.0.0 directory doesn't exist
- Check if using different version: `ls ~/.local/share/android/sdk/build-tools/`
- Update paths if using different version

### Permission denied errors
- Check permissions: `ls -la ~/.local/share/android/sdk/build-tools/35.0.0/aapt2`
- Should be executable: `-rwx------`

## Dependencies

**Requires first**:
- Bash environment setup (.bash_env created)
- JAVA_HOME configured
- Java 21 installed

**Depends on**:
- bash-environment-config skill (for .bash_env file)

**Enables**:
- gradle-android-build skill (uses configured aapt2)
- ndk-setup skill (works with same SDK)
- kotlin-lsp-setup skill (uses SDK paths)

## Related Skills
- `bash-environment-config` - Sets up ~/.bash_env with paths
- `android-ndk-setup` - Installs SDK tools and platforms
- `gradle-setup` - Configures Gradle for Termux Android builds
