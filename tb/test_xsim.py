"""Run task-08 regressions and X/Z injection with the team's Vivado simulator.

Use a Vivado command prompt, then: python tb/test_xsim.py
All compiler products and logs stay under build/xsim/. Requires xvlog/xelab/xsim.
"""
import shutil
import subprocess
import sys

from run import ROOT, common_files, rtl_files
from test_shared import BENCHES, CASES, negative_ok, positive_ok

WORK = ROOT / "build" / "xsim"
FOUR_STATE_CASES = [
    ("tb_four_state", "negative", case, diagnostic)
    for case, diagnostic in (
        ("known_x", "X/Z at bit"), ("known_z", "X/Z at bit"),
        ("compare_x", "injected: got"),
        ("stream_x", "rule 3"), ("stream_z", "rule 3"),
        ("sink_x", "unknown accepted word"), ("sink_z", "unknown accepted word"),
    )
]


def invoke(tool, args, label):
    executable = shutil.which(tool)
    if not executable:
        raise FileNotFoundError(f"{tool} is unavailable; use the team's Vivado command prompt")
    result = subprocess.run([executable, *args], cwd=WORK, capture_output=True,
                            text=True, timeout=600)
    (WORK / f"{label}.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    return result


def main():
    (WORK / "build").mkdir(parents=True, exist_ok=True)
    benches = ["tb/tests/tb_shared.sv", "tb/tests/tb_axil_master.sv",
               "tb/tests/tb_axis_negative.sv", "tb/tests/tb_source_edges.sv",
               "tb/tests/tb_four_state.sv", "tb/ctrl/out_fifo/tb_out_fifo.sv"]
    sources = [(ROOT / path).as_posix() for path in rtl_files() + common_files() + benches]
    result = invoke("xvlog", ["--sv", *sources], "compile")
    if result.returncode:
        print(result.stdout + result.stderr)
        return 1
    configs = [(bench, bench, []) for bench in BENCHES if bench != "tb_source_edges"]
    configs += [("tb_source_edges", f"tb_source_edges_W{w}", ["-generic_top", f"W={w}"])
                for w in (1, 8, 64, 280)]
    configs += [("tb_four_state", "tb_four_state", [])]
    for bench, snapshot, parameters in configs:
        result = invoke("xelab", [bench, "-s", snapshot, "-timescale", "1ns/1ps", *parameters],
                        f"elaborate_{snapshot}")
        if result.returncode:
            print(result.stdout + result.stderr)
            return 1
        for seed in (1, 7, 29):
            result = invoke("xsim", [snapshot, "-R", "-testplusarg", f"seed={seed}"],
                            f"{snapshot}_seed{seed}")
            print(result.stdout + result.stderr)
            if not positive_ok(result):
                return 1
    for bench, arg, case, diagnostic in CASES + FOUR_STATE_CASES:
        result = invoke("xsim", [bench, "-R", "-testplusarg", f"{arg}={case}"],
                        f"{bench}_{case}")
        if not negative_ok(result, diagnostic):
            print(result.stdout + result.stderr)
            print(f"FAIL expected rejection: {bench}/{case}")
            return 1
        print(f"PASS expected rejection: {bench}/{case}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"FAIL Vivado regression infrastructure: {exc}", file=sys.stderr)
        sys.exit(1)
