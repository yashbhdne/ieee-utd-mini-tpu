// X/Z checks require a four-state simulator; two-state runs explicitly skip.
module tb_four_state;
  import tb_pkg::*;
  logic clk = 0, rst = 1, enable = 1;
  logic [63:0] tdata = 0;
  logic tvalid = 0, tready, tlast = 0;
  vec_t value;
  string negative;
  always #5 clk = ~clk;
  axis_check #(.NAME("four_state")) checker_i(.*);
  axis_sink sink(.*);

  initial begin
`ifdef VERILATOR
    $display("SKIP: X/Z injection requires a four-state simulator");
    $finish;
`else
    void'(get_seed());
    repeat (3) @(negedge clk);
    rst = 0;
    repeat (3) @(negedge clk);
    if ($value$plusargs("negative=%s", negative)) begin
      if (negative == "known_x") check_known("injected", vec_t'('x), 64);
      else if (negative == "known_z") check_known("injected", vec_t'('z), 64);
      else if (negative == "compare_x") check("injected", vec_t'('x), '0);
      else if (negative == "stream_x" || negative == "stream_z") begin
        // Keep the sink from racing the protocol checker to report the error.
        sink.set_ready_pct(0);
        repeat (3) @(negedge clk);
        tdata = negative == "stream_x" ? 'x : 'z;
        tvalid = 1;
        repeat (3) @(negedge clk);
      end else if (negative == "sink_x" || negative == "sink_z") begin
        enable = 0;
        tdata = negative == "sink_x" ? 'x : 'z;
        tvalid = 1;
        repeat (3) @(negedge clk);
      end else $fatal(1, "unknown four-state case");
      $fatal(1, "expected rejection did not occur");
    end
    cover_declare("masked_unknowns");
    value = 'x;
    value[63:0] = 64'h1234;
    check_known("ignore upper unknown bits", value, 64);
    cover_hit("masked_unknowns");
    finish_pass();
`endif
  end
endmodule
