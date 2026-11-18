#!/usr/bin/env python3
"""Lint the RTL and run the testbenches with Verilator.

    python tb/run.py lint                     lint every module under rtl/
    python tb/run.py sim                      build and run every tb_*.sv under tb/
    python tb/run.py sim tb_ub tb_mxu         only these benches
    python tb/run.py sim tb_mxu -- +seed=7    pass plusargs to the simulation

A bench passes when it exits cleanly and prints a line that is PASS or starts with SKIP.
Builds go to build/sim/<bench>/. Benches run from the repository root, so vector paths
start with vectors/.
"""
import argparse
import os
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUILD = ROOT / "build" / "sim"

# OSS CAD Suite on Windows ships a native binary beside the Perl launcher.
VERILATOR = os.environ.get("VERILATOR") or (
    "verilator_bin" if os.name == "nt" and shutil.which("verilator_bin") else "verilator"
)
if os.name == "nt" and "VERILATOR_ROOT" not in os.environ:
    executable = shutil.which(VERILATOR)
    if executable:
        support = pathlib.Path(executable).resolve().parents[1] / "share" / "verilator"
        if support.is_dir():
            os.environ["VERILATOR_ROOT"] = support.as_posix()

# Packages must come first on the command line.
RTL_PKGS = ["rtl/mxu/mxu_pkg.sv"]
TB_PKGS = ["tb/common/tb_pkg.sv"]

# Parameter sets per bench. A bench not listed runs once with its defaults.
# Parameters declared `bit` in the RTL go in BIT_PARAMS so they are passed as 1'b0 / 1'b1.
BIT_PARAMS = {"PIPE"}
PARAMS = {
    "tb_source_edges": [{"W": w} for w in (1, 8, 64, 280)],
    "tb_pe": [{"PIPE": 0}, {"PIPE": 1}],
    "tb_mxu": [{"T": t, "PIPE": p} for t in (4, 8) for p in (0, 1)],
}


def sv_files(folder, skip):
    files = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / folder).rglob("*.sv"))
    return [f for f in files if f not in skip]


def rtl_files():
    return RTL_PKGS + sv_files("rtl", RTL_PKGS)


def common_files():
    return TB_PKGS + sv_files("tb/common", TB_PKGS)


def benches():
    common = ROOT / "tb" / "common"
    return sorted(p for p in (ROOT / "tb").rglob("tb_*.sv") if common not in p.parents)


def run(cmd, **kw):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, **kw)


def lint():
    failed = []
    files = rtl_files()
    for f in files:
        if f in RTL_PKGS:
            continue
        top = pathlib.Path(f).stem
        r = run([VERILATOR, "--lint-only", "--top-module", top] + files)
        ok = r.returncode == 0
        print(f"{'ok  ' if ok else 'FAIL'}  {f}")
        if not ok:
            print(r.stdout + r.stderr)
            failed.append(f)
    return failed


def sim(names, plusargs, build_only=False):
    results = []
    for bench in benches():
        name = bench.stem
        if names and name not in names:
            continue
        for params in PARAMS.get(name, [{}]):
            tag = name + "".join(f"_{k}{v}" for k, v in params.items())
            mdir = BUILD / tag
            mdir.mkdir(parents=True, exist_ok=True)
            cmd = [VERILATOR, "--binary", "--timing", "--timescale", "1ns/1ps",
                   "-j", "4", "--top-module", name, "-Mdir", mdir.as_posix(),
                   "-o", "sim.exe" if os.name == "nt" else "sim"]
            cmd += [f"-G{k}=1'b{v}" if k in BIT_PARAMS else f"-G{k}={v}"
                    for k, v in params.items()]
            cmd += rtl_files() + common_files() + [bench.relative_to(ROOT).as_posix()]
            r = run(cmd)
            if r.returncode != 0:
                print(r.stdout + r.stderr)
                results.append((tag, "BUILD FAIL"))
                continue
            if build_only:
                results.append((tag, "BUILD OK"))
                continue
            try:
                r = run([str(mdir / ("sim.exe" if os.name == "nt" else "sim"))] + plusargs,
                        timeout=300)
            except (OSError, subprocess.TimeoutExpired) as exc:
                print(f"{tag}: simulation could not complete: {exc}")
                results.append((tag, "RUN ERROR"))
                continue
            lines = [l.strip() for l in r.stdout.splitlines()]
            if r.returncode != 0:
                verdict = "FAIL"
            elif any(l.startswith("SKIP") for l in lines):
                verdict = "SKIP"
            elif "PASS" in lines:
                verdict = "PASS"
            else:
                verdict = "NO VERDICT"
            # Retain PASS/coverage evidence in CI logs, not just the summary verdict.
            if verdict != "SKIP":
                print(r.stdout + r.stderr)
            results.append((tag, verdict))
    for tag, verdict in results:
        print(f"{verdict:10}  {tag}")
    if names and not results:
        print("no bench matched", names)
        return ["none"]
    return [t for t, v in results if v not in ("PASS", "SKIP", "BUILD OK")]


def main():
    argv = sys.argv[1:]
    plusargs = []
    if "--" in argv:
        i = argv.index("--")
        argv, plusargs = argv[:i], argv[i + 1:]
    ap = argparse.ArgumentParser(description="Verilator lint and bench runner")
    ap.add_argument("cmd", choices=["lint", "sim"])
    ap.add_argument("benches", nargs="*")
    ap.add_argument("--build-only", action="store_true",
                    help="compile simulation binaries without executing them")
    args = ap.parse_args(argv)
    if args.cmd == "lint" and args.build_only:
        ap.error("--build-only applies only to sim")
    failed = lint() if args.cmd == "lint" else sim(args.benches, plusargs, args.build_only)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

