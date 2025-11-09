---
name: Flutter Setup for Termux
description: Install Flutter from Termux-compatible .deb package and configure for Android development with Termux-optimized SDK/NDK (aarch64). Handles NDK symlink configuration for Gradle.
---

# Flutter Setup for Termux

## Overview
This skill sets up Flutter on Termux using the Termux-compatible .deb package and configures it to work with aarch64-optimized Android SDK/NDK from lzhiyong's builds.

## Prerequisites
- Termux environment with bash
- Java 21 installed and configured (JAVA_HOME set)
- Android SDK with Termux-compatible tools installed
- Android NDK r27b (Termux-compatible from lzhiyong)
- ~2GB free storage

## What Gets Installed

### Flutter SDK
- **Version**: 3.35.7 (or current from deb package)
- **Location**: `/data/data/com.termux/files/usr/opt/flutter`
- **Architecture**: aarch64-optimized

### Flutter Tools
- **flutter** command-line tool
- **dart** SDK
- **pub** package manager
- Build system integrations for Android/iOS/Web/Linux/Windows

## Critical Configuration: NDK Symlink

### The Issue
Gradle expects the NDK at a specific versioned path: `$ANDROID_SDK_ROOT/ndk/27.0.12077973/`. When using the Termux-compatible NDK installed at `android-ndk-r27b`, you must create a symlink so Gradle finds it.

### The Solution
```bash
# Create symlink to the actual NDK
ln -s ~/.local/share/android/sdk/android-ndk-r27b \
     ~/.local/share/android/sdk/ndk/27.0.12077973

# Verify:
ls -la ~/.local/share/android/sdk/ndk/
# Should show: 27.0.12077973 -> ~/.local/share/android/sdk/android-ndk-r27b
```

### Configure Flutter Android Project
In your Flutter project's `android/local.properties`, add:
```properties
sdk.dir=/data/data/com.termux/files/home/.local/share/android/sdk
flutter.sdk=/data/data/com.termux/files/usr/opt/flutter
```

## Installation Steps

### Step 1: Verify Flutter .deb Package Location
```bash
# The Flutter .deb package should be in your home directory
ls -lh ~/flutter_*.deb
```

### Step 2: Install Flutter from .deb
```bash
apt install ~/flutter_3.35.7_aarch64.deb
```

### Step 3: Verify Flutter Installation
```bash
flutter --version
dart --version
which flutter dart
```

### Step 4: Run Flutter Doctor
```bash
flutter doctor

# Expected output should show:
# - Flutter SDK version 3.35.7+
# - Dart SDK version 3.9.2+
# - Android toolchain
# - Android license status
```

## Android Configuration for Flutter Projects

### Step 1: Create Flutter Project
```bash
flutter create my_app
cd my_app
```

### Step 2: Configure Build Gradle (if needed)
Most Flutter projects don't need gradle configuration. Only if using native code with CMakeLists.txt:

```gradle
android {
    ndkVersion "27.0.12077973"  // Match your NDK version

    externalNativeBuild {
        cmake {
            path "CMakeLists.txt"
        }
    }
}
```

### Step 3: Verify Android Setup
```bash
flutter doctor -v

# Should show:
# Android SDK: ✓ (configured)
# Android NDK: ✓ (detected)
# Android toolchain: ✓
```

### Step 4: Build and Run
```bash
# Build APK
flutter build apk

# Or run on device
flutter run -d <device-id>
```

## Troubleshooting

### Build fails: "compiler tool not found" during CMake configure
This means the NDK path symlink is missing or broken:
```bash
# Check the symlink:
ls -la ~/.local/share/android/sdk/ndk/27.0.12077973/

# Should point to ~/.local/share/android/sdk/android-ndk-r27b
# If missing or broken, recreate it:
ln -s ~/.local/share/android/sdk/android-ndk-r27b \
     ~/.local/share/android/sdk/ndk/27.0.12077973

# Verify it works
ls ~/.local/share/android/sdk/ndk/27.0.12077973/toolchains/llvm/prebuilt/
```

### Flutter command not found
```bash
# Verify Flutter is installed
dpkg -l | grep flutter

# If not installed, reinstall from deb:
apt install ~/flutter_3.35.7_aarch64.deb

# Verify it's in PATH
which flutter

# If still not found, ensure ~/.bash_env is sourced in ~/.bashrc
source ~/.bash_env
```

### Build fails with gradle errors
```bash
# Run with verbose output for details:
flutter run -v 2>&1 | head -100

# Common issues:
# 1. "compiler tool not found" - Check NDK symlink (see above)
# 2. "No NDK installed" - Verify NDK exists at ~/.local/share/android/sdk/android-ndk-r27b
# 3. Permission errors - Check file permissions
```

### Flutter doctor shows "Android NDK not found"
```bash
# Verify NDK directory exists
ls ~/.local/share/android/sdk/android-ndk-r27b/

# Set NDK paths in ~/.bash_env (if not already set):
export ANDROID_NDK_HOME=$ANDROID_SDK_ROOT/android-ndk-r27b
export NDK_HOME=$ANDROID_NDK_HOME

# Reload and check
source ~/.bash_env
flutter doctor -v
```

## Performance Notes

### First Build is Slow
- Flutter compiles Dart to native code on first build
- Expected time: 3-10 minutes depending on device storage speed
- Subsequent builds are faster (incremental compilation)

### Memory Usage
- Gradle and cmake can use significant memory
- Set in `~/.gradle/gradle.properties`:
```properties
org.gradle.jvmargs=-Xmx2048m
```

### Disk Space
- Flutter SDK: ~500MB
- Android SDK + NDK: ~5GB
- Build artifacts: ~2GB per project
- Total: ~8GB recommended

## Key Differences from Standard Linux

| Issue | Standard Linux | Termux | Solution |
|-------|---|---|---|
| NDK paths | Fixed install paths | Custom paths | Create symlink to versioned path |
| File permissions | Standard Unix | App-restricted | No special handling needed |
| Storage | Separate partitions | Shared /data | Monitor /data space |
| Package manager | apt/yum/etc | apt (Android-focused) | Use Termux-compatible binaries |

## Dependencies

**Requires first**:
- bash-environment-config (for ~/.bash_env with paths)
- android-sdk-setup (for SDK at ~/.local/share/android/sdk)
- android-ndk-setup (for NDK at ~/.local/share/android/sdk/android-ndk-r27b)
- Java 21 (JAVA_HOME configured)

**Depends on**:
- Flutter .deb package in home directory
- Termux-compatible SDK/NDK (from lzhiyong's builds)

**Enables**:
- Flutter Android app development
- Hot reload and hot restart during development
- APK building and device deployment
- Access to all Flutter and Dart packages

## Related Skills
- `bash-environment-config` - Configures ~/.bash_env with paths
- `android-sdk-setup` - Installs Termux-compatible SDK
- `android-ndk-setup` - Installs Termux-compatible NDK
- `neovim-lazyvim-setup` - Code editor for Flutter development
