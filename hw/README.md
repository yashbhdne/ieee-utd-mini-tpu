# hw

Vivado block-design scripts (`write_bd_tcl` output), constraints and out-of-context synthesis scripts. Target board Cora Z7-07S, part `xc7z007sclg400-1`, Digilent board files.

IP settings: `docs/architecture.md`, section 7. Each script comes with a few lines here saying how to rebuild the project from a fresh clone; a second person following them is the test.

## Output FIFO verification

Use the team's pinned Vivado version from a Vivado command prompt, starting in the
repository root:

```
python tb/test_xsim.py
vivado -mode batch -source hw/synth_out_fifo.tcl
```

The Python runner compiles the shared package and helpers, runs the shared, AXI-Lite,
FIFO and source-width benches for seeds 1, 7 and 29, and checks the 21 deliberate
failures plus seven X/Z injection cases. Compiler and simulation logs stay under
`build/xsim/`. `tb_four_state` explicitly skips in two-state Verilator simulations;
its X/Z cases must pass in the Vivado simulator before acceptance.

The synthesis script targets `xc7z007sclg400-1`, applies a 10 ns clock, writes actual
utilization/timing reports under `rtl/ctrl/out_fifo/reports/`, and fails unless the
design uses one RAMB36E1, zero DSPs and zero latches. Review the timing report
separately; the script's PASS message establishes resource counts only. Commit the
reports after running with the agreed Vivado version. That version is not recorded
in this repository yet and must be confirmed with the lead.

An additional open-source resource check is available:

```
yosys -s hw/synth_out_fifo.ys
```

It writes `rtl/ctrl/out_fifo/out_fifo_yosys.rpt` and asserts one RAMB36E1 and no DSP48E1.
This is supplementary evidence, not the required Vivado synthesis or timing result.

## Local Windows simulation

The test runner supports the native `verilator_bin.exe` distributed by OSS CAD Suite
and a MinGW C++ compiler/make on PATH. `VERILATOR` can override the executable. Use a
Python installation whose publisher you have verified. For the portable tools in this
workspace, put the `oss-cad-suite/bin`, `oss-cad-suite/lib` and `w64devkit/bin`
directories on the current terminal's PATH. No antivirus exclusions are needed.

```
python tb/run.py lint
python tb/run.py sim --build-only
python tb/test_shared.py
```

`--build-only` reports BUILD OK, not PASS: it compiles without executing the generated
programs. If Windows application control blocks a simulation, leave it blocked and
use an approved environment or GitHub CI for that run. Do not treat a blocked run as
a passing test. Build outputs remain under `build/`; no tools or generated executables
are committed.
