#!/bin/bash
set -euo pipefail
repo_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_dir"
if [[ "$(uname -s)" != Darwin ]]; then
    echo "This build requires macOS, Xcode and the .NET Mac Catalyst workload." >&2
    exit 1
fi
command -v dotnet >/dev/null
xcrun --sdk macosx --show-sdk-path
mkdir -p artifacts/logs
bash src/CalcManager/build_catalyst.sh arm64
cd src
dotnet publish Calculator.Mobile/Calculator.Mobile.csproj \
    -f net9.0-maccatalyst -c Release \
    -p:TargetFrameworks=net9.0-maccatalyst \
    -p:RuntimeIdentifier=maccatalyst-arm64 \
    -p:CommunityBuild=true \
    -p:BUILD_SOURCEBRANCH=refs/heads/community-arm64 \
    -bl:"$repo_dir/artifacts/logs/build.binlog" \
    2>&1 | tee "$repo_dir/artifacts/logs/build.log"
cd "$repo_dir"
app_source="src/Calculator.Mobile/bin/Release/net9.0-maccatalyst/maccatalyst-arm64/unocalc.app"
if [[ ! -d "$app_source" ]]; then
    echo "Expected application bundle missing: $app_source" >&2
    exit 1
fi
stage="$(mktemp -d "${TMPDIR:-/tmp}/unocalc-package.XXXXXX")"
trap 'rm -rf "$stage"' EXIT
app="$stage/Uno Calculator ARM.app"
ditto "$app_source" "$app"
mkdir -p "$app/Contents/Resources/OpenSourceLicenses"
cp LICENSE NOTICE.txt "$app/Contents/Resources/OpenSourceLicenses/"
# Adding the notices changes the resource seal. Re-sign the bundle ad-hoc.
codesign --force --sign - --preserve-metadata=entitlements "$app"
python3 scripts/verify-apple-silicon.py "$app" \
    | tee artifacts/logs/architecture-check.log
codesign --verify --deep --strict --verbose=2 "$app"
if [[ "$(uname -m)" == arm64 ]]; then
    python3 scripts/verify-apple-silicon.py "$app" --launch \
        | tee artifacts/logs/startup-check.log
fi
ln -s /Applications "$stage/Applications"
cp docs/apple-silicon/TESTING.md "$stage/Testing.txt"
hdiutil create -volname "Uno Calculator ARM" -srcfolder "$stage" \
    -ov -format UDZO artifacts/Uno-Calculator-arm64.dmg
ditto -c -k --sequesterRsrc --keepParent "$app" artifacts/Uno-Calculator-arm64.zip
shasum -a 256 artifacts/Uno-Calculator-arm64.dmg artifacts/Uno-Calculator-arm64.zip \
    > artifacts/SHA256SUMS.txt
echo "ARM64 packages created under artifacts/. Ad-hoc signature; not notarized."
