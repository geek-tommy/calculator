#!/usr/bin/env python3
"""Check shipped Mach-O files; optionally check process startup on an ARM Mac."""
import argparse
import os
import plistlib
import subprocess
import tempfile
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("app", type=Path)
parser.add_argument("--launch", action="store_true")
args = parser.parse_args()
app = args.app.resolve(strict=True)
with (app / "Contents/Info.plist").open("rb") as stream:
    info = plistlib.load(stream)
if info.get("CFBundleIdentifier") != "local.community.unocalculator.arm64":
    raise SystemExit("Community build must use its own bundle identifier")
executable = app / "Contents/MacOS" / info["CFBundleExecutable"]
if not executable.is_file():
    raise SystemExit(f"Missing main executable: {executable}")
print(f"Bundle identifier: {info.get('CFBundleIdentifier')}")
print(f"Minimum macOS: {info.get('LSMinimumSystemVersion', 'see Info.plist')}")
print(f"App version: {info.get('CFBundleShortVersionString')}")
checked = 0
for path in app.rglob("*"):
    if not path.is_file() or path.is_symlink():
        continue
    description = subprocess.check_output(["file", "-b", str(path)])
    if b"Mach-O" not in description:
        continue
    architectures = subprocess.check_output(["lipo", "-archs", str(path)], text=True).split()
    if architectures != ["arm64"]:
        raise SystemExit(f"Unexpected architecture {architectures}: {path}")
    checked += 1
    print(f"ARM64: {path.relative_to(app)}")
if checked == 0:
    raise SystemExit("No Mach-O binaries found")
print(f"Architecture check passed: {checked} Mach-O binaries, all arm64.")
if args.launch:
    if subprocess.check_output(["uname", "-m"], text=True).strip() != "arm64":
        raise SystemExit("Startup check requires an ARM Mac")
    with tempfile.TemporaryDirectory(prefix="unocalc-localization-") as proof_dir:
        proof = Path(proof_dir) / "loaded-language.txt"
        interaction_proof = Path(proof_dir) / "interaction.txt"
        navigation_proof = Path(proof_dir) / "navigation.txt"
        environment = os.environ | {
            "UNO_CALCULATOR_LOCALIZATION_PROOF": str(proof),
            "UNO_CALCULATOR_INTERACTION_PROOF": str(interaction_proof),
            "UNO_CALCULATOR_NAVIGATION_PROOF": str(navigation_proof),
        }
        with subprocess.Popen([str(executable)], cwd=app.parent, env=environment) as process:
            try:
                result = process.wait(timeout=12)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                print("Startup check passed: process remained alive for 12 seconds.")
                navigation = navigation_proof.read_text(encoding="utf-8") if navigation_proof.exists() else "FAIL: missing navigation proof"
                print(navigation)
                actual = proof.read_text(encoding="utf-8") if proof.exists() else "missing localization proof"
                if actual != "zh-Hans|标准|科学|程序员":
                    raise SystemExit(f"Simplified Chinese resource check failed: {actual}")
                print(f"Simplified Chinese resource check passed: {actual}")
                interaction = interaction_proof.read_text(encoding="utf-8") if interaction_proof.exists() else "missing interaction proof"
                if interaction != "PASS: pressed and hover states return to Normal":
                    raise SystemExit(f"Interaction state check failed: {interaction}")
                print(f"Interaction state check passed: {interaction}")
                if "FAIL:" in navigation or navigation.count("PASS:") != 14:
                    raise SystemExit("Navigation checks failed")
                print("Calculator results and UI still require manual testing.")
            else:
                raise SystemExit(f"App exited during startup with code {result}")
