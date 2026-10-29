#!/bin/bash
set -euo pipefail
# Isolate object files so failed builds never mix architectures.
source_dir="$(cd "$(dirname "$0")" && pwd)"
sdk_path="$(xcrun --sdk macosx --show-sdk-path)"
build_dir="$(mktemp -d "${TMPDIR:-/tmp}/unocalc-native.XXXXXX")"
trap 'rm -rf "$build_dir"' EXIT
if [[ $# -eq 0 ]]; then
    set -- x86_64 arm64
fi
for arch in "$@"; do
    case "$arch" in
        arm64|x86_64) ;;
        *) echo "Unsupported architecture: $arch" >&2; exit 2 ;;
    esac
    objects_dir="$build_dir/$arch"
    output_dir="$source_dir/../Calculator.Mobile/MacCatalyst/NativeReferences/$arch"
    mkdir -p "$objects_dir" "$output_dir"
    (
        cd "$objects_dir"
        xcrun --sdk macosx clang++ \
            -target "$arch-apple-ios15.0-macabi" \
            -isysroot "$sdk_path" -std=c++17 -stdlib=libc++ \
            -O2 -fvisibility=default -I"$source_dir" -c \
            "$source_dir"/CEngine/*.cpp \
            "$source_dir"/Ratpack/*.cpp \
            "$source_dir"/*.cpp
        xcrun --sdk macosx libtool -static ./*.o -o "$output_dir/libCalcManager.a"
    )
    lipo "$output_dir/libCalcManager.a" -verify_arch "$arch"
    echo "Built CalcManager ($arch)"
done
