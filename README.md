# cohdl_xil

`cohdl_xil` is build on top of the Python to VHDL compiler [CoHDL](https://github.com/alexander-forster/cohdl) and automates the process of turning CoHDL designs into bitstreams for Xilinx FPGAs.

## features

* generate Makefiles and tcl scripts to make bitstreams from CoHDL designs without Vivados GUI
* instantiate Xilinx IP cores in CoHDL
    
    * instantiates IP cores in generated VHDL
    * adds tcl scripts describing IP cores to the Makefile project
* so far only a single FPGA type supported (Artix7 xc7a100tcsg324)
* board abstraction for the Nexys A7 development board

At this point `cohdl_xil` is mostly a prove of concept. It is not tested in any way beyond running the example designs on a Nexys A7 development board.

---
## getting started

`cohdl_xil` requires Python3.10 or higher and CoHDL. To synthesize designs into a bitstream you will also need `make` and the Vivado command line tools.

You can install `cohdl_xil` it by running

```shell
python3.10 -m pip install git+https://github.com/alexander-forster/cohdl_xil.git#egg=cohdl_xil
```

in a terminal window and should then be able to build the example designs. Each example generates a `build/` directory containing a Makefile and tcl scripts. Running `make` from `build/` starts the synthesis and produces a bitstream file in `build/output/impl/`.