# Run from the repository root with the team's pinned Vivado:
# vivado -mode batch -source hw/synth_out_fifo.tcl
set root [file normalize [file join [file dirname [info script]] ..]]
set reports [file join $root rtl ctrl out_fifo reports]
file mkdir $reports
read_verilog -sv [file join $root rtl ctrl out_fifo out_fifo.sv]
synth_design -top out_fifo -part xc7z007sclg400-1 -mode out_of_context
create_clock -name clk -period 10.000 [get_ports clk]
report_utilization -file [file join $reports utilization_vivado.rpt]
report_timing_summary -file [file join $reports timing_vivado.rpt]
set brams [llength [get_cells -hier -filter {REF_NAME == RAMB36E1}]]
set dsps [llength [get_cells -hier -filter {REF_NAME =~ DSP48*}]]
set latches [llength [get_cells -hier -filter {REF_NAME =~ LD*}]]
set summary [open [file join $reports summary_vivado.rpt] w]
puts $summary "Vivado: [version -short]"
puts $summary "Part: xc7z007sclg400-1"
puts $summary "RAMB36E1: $brams; DSP: $dsps; latches: $latches"
close $summary
if {$brams != 1 || $dsps != 0 || $latches != 0} {
    error "out_fifo resource acceptance failed; inspect utilization_vivado.rpt"
}
puts "PASS: out_fifo resource check (timing report requires separate review)"
