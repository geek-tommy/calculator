#!/usr/bin/env python3
"""Check shipped Mach-O files; optionally check process startup on an ARM Mac."""
import argparse
import plistlib
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("app", type=Path)
parser.add_argument("--launch", action="store_true")
args = parser.parse_args()
app = args.app.resolve(strict=True)
with (app / "Contents/Info.plist").open("rb") as stream:
    info = plistlib.load(stream)
executable = app / "Contents/MacOS" / info["CFBundleExecutable"]
if not executable.is_file():
    raise SystemExit(f"Missing main executable: {executable}")
print(f"Bundle identifier: {info.get('CFBundleIdentifier')}")
print(f"Minimum macOS: {info.get('LSMinimumSystemVersion', 'see Info.plist')}")
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
    with subprocess.Popen([str(executable)], cwd=app.parent) as process:
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
            print("Calculator results and UI still require manual testing.")
        else:
            raise SystemExit(f"App exited during startup with code {result}")
