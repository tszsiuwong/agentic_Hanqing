// GCD Controller + Datapath
module gcd (clk, rst_n, start, a, b, done, result);
  input clk, rst_n, start;
  input [7:0] a, b;
  output done;
  output [7:0] result;

  wire [7:0] mux_a_out, mux_b_out, sub_out, cmp_lt;
  wire a_eq_b, ld_a, ld_b, sel;

  gcd_ctrl U_CTRL (
    .clk(clk), .rst_n(rst_n), .start(start),
    .a_eq_b(a_eq_b), .a_lt_b(cmp_lt),
    .ld_a(ld_a), .ld_b(ld_b), .sel(sel), .done(done)
  );
  mux2x8 U_MUX_A (.in0(a), .in1(sub_out), .sel(sel), .out(mux_a_out));
  mux2x8 U_MUX_B (.in0(b), .in1(sub_out), .sel(sel), .out(mux_b_out));
  reg8   U_REG_A (.clk(clk), .ld(ld_a), .d(mux_a_out), .q(sub_out));
  reg8   U_REG_B (.clk(clk), .ld(ld_b), .d(mux_b_out), .q(result));
  cmp8   U_CMP   (.a(sub_out), .b(result), .eq(a_eq_b), .lt(cmp_lt));
endmodule

module gcd_ctrl (clk, rst_n, start, a_eq_b, a_lt_b, ld_a, ld_b, sel, done);
  input clk, rst_n, start, a_eq_b, a_lt_b;
  output ld_a, ld_b, sel, done;
  wire idle, calc, ns_idle, ns_calc;

  AND2X1 U1 (.A(idle), .B(start), .Y(ns_calc));
  AND2X1 U2 (.A(calc), .B(a_eq_b), .Y(ns_idle));
  NAND2X1 U3 (.A(calc), .B(a_eq_b), .Y(done_n));
  INVX1 U4 (.A(done_n), .Y(done));
  INVX1 U5 (.A(rst_n), .Y(rst));
  NOR2X1 U6 (.A(idle), .B(rst), .Y(ld_a));
  NOR2X1 U7 (.A(calc), .B(rst), .Y(sel));
  INVX1 U8 (.A(sel), .Y(ld_b));
  DFFRX1 U_STATE0 (.CK(clk), .RN(rst_n), .D(ns_idle), .Q(idle), .QN());
  DFFRX1 U_STATE1 (.CK(clk), .RN(rst_n), .D(ns_calc), .Q(calc), .QN());
endmodule

module mux2x8 (in0, in1, sel, out);
  input [7:0] in0, in1;
  input sel;
  output [7:0] out;
  MUX2X1 U0 (.A(in0[0]), .B(in1[0]), .S(sel), .Y(out[0]));
  MUX2X1 U1 (.A(in0[1]), .B(in1[1]), .S(sel), .Y(out[1]));
  MUX2X1 U2 (.A(in0[2]), .B(in1[2]), .S(sel), .Y(out[2]));
  MUX2X1 U3 (.A(in0[3]), .B(in1[3]), .S(sel), .Y(out[3]));
  MUX2X1 U4 (.A(in0[4]), .B(in1[4]), .S(sel), .Y(out[4]));
  MUX2X1 U5 (.A(in0[5]), .B(in1[5]), .S(sel), .Y(out[5]));
  MUX2X1 U6 (.A(in0[6]), .B(in1[6]), .S(sel), .Y(out[6]));
  MUX2X1 U7 (.A(in0[7]), .B(in1[7]), .S(sel), .Y(out[7]));
endmodule

module reg8 (clk, ld, d, q);
  input clk, ld;
  input [7:0] d;
  output [7:0] q;
  wire [7:0] mux_out, nq;
  MUX2X1 UM0 (.A(q[0]), .B(d[0]), .S(ld), .Y(mux_out[0]));
  MUX2X1 UM1 (.A(q[1]), .B(d[1]), .S(ld), .Y(mux_out[1]));
  MUX2X1 UM2 (.A(q[2]), .B(d[2]), .S(ld), .Y(mux_out[2]));
  MUX2X1 UM3 (.A(q[3]), .B(d[3]), .S(ld), .Y(mux_out[3]));
  MUX2X1 UM4 (.A(q[4]), .B(d[4]), .S(ld), .Y(mux_out[4]));
  MUX2X1 UM5 (.A(q[5]), .B(d[5]), .S(ld), .Y(mux_out[5]));
  MUX2X1 UM6 (.A(q[6]), .B(d[6]), .S(ld), .Y(mux_out[6]));
  MUX2X1 UM7 (.A(q[7]), .B(d[7]), .S(ld), .Y(mux_out[7]));
  DFFRX1 U0 (.CK(clk), .RN(1'b1), .D(mux_out[0]), .Q(q[0]), .QN(nq[0]));
  DFFRX1 U1 (.CK(clk), .RN(1'b1), .D(mux_out[1]), .Q(q[1]), .QN(nq[1]));
  DFFRX1 U2 (.CK(clk), .RN(1'b1), .D(mux_out[2]), .Q(q[2]), .QN(nq[2]));
  DFFRX1 U3 (.CK(clk), .RN(1'b1), .D(mux_out[3]), .Q(q[3]), .QN(nq[3]));
  DFFRX1 U4 (.CK(clk), .RN(1'b1), .D(mux_out[4]), .Q(q[4]), .QN(nq[4]));
  DFFRX1 U5 (.CK(clk), .RN(1'b1), .D(mux_out[5]), .Q(q[5]), .QN(nq[5]));
  DFFRX1 U6 (.CK(clk), .RN(1'b1), .D(mux_out[6]), .Q(q[6]), .QN(nq[6]));
  DFFRX1 U7 (.CK(clk), .RN(1'b1), .D(mux_out[7]), .Q(q[7]), .QN(nq[7]));
endmodule

module cmp8 (a, b, eq, lt);
  input [7:0] a, b;
  output eq, lt;
  wire [7:0] diff;
  wire [6:0] borrow;
  wire sign;
  XOR2X1 U0 (.A(a[0]), .B(b[0]), .Y(diff[0]));
  FAX1   U1 (.A(a[1]), .B(~b[1]), .CI(borrow[0]), .S(diff[1]), .CO(borrow[0]));
  FAX1   U2 (.A(a[2]), .B(~b[2]), .CI(borrow[1]), .S(diff[2]), .CO(borrow[1]));
  FAX1   U3 (.A(a[3]), .B(~b[3]), .CI(borrow[2]), .S(diff[3]), .CO(borrow[2]));
  FAX1   U4 (.A(a[4]), .B(~b[4]), .CI(borrow[3]), .S(diff[4]), .CO(borrow[3]));
  FAX1   U5 (.A(a[5]), .B(~b[5]), .CI(borrow[4]), .S(diff[5]), .CO(borrow[4]));
  FAX1   U6 (.A(a[6]), .B(~b[6]), .CI(borrow[5]), .S(diff[6]), .CO(borrow[5]));
  FAX1   U7 (.A(a[7]), .B(~b[7]), .CI(borrow[6]), .S(sign), .CO(borrow[6]));
  INVX1  U8 (.A(sign), .Y(lt));
  NOR8X1 U9 (.A(diff[0]), .B(diff[1]), .C(diff[2]), .D(diff[3]),
              .E(diff[4]), .F(diff[5]), .G(diff[6]), .H(sign), .Y(eq));
endmodule
