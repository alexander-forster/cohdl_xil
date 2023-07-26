from .tcl_writer import TclWriter
from cohdl.utility import MakeTarget

import os
from pathlib import Path
import shutil


class VivadoProject:
    def __init__(self):
        self.tcl = TclWriter()

    #
    #
    #

    def write_line(self, line: str = ""):
        self.tcl.write_line(line)

    def write_comment(self, comment: str | list[str]):
        if isinstance(comment, list):
            for line in comment:
                self.write_comment(line)
        else:
            self.write_line(f"# {comment}")

    def set_part(self, part_id: str):
        self.tcl.write_cmd("set_part", part_id)

    def read_vhdl(self, path: str, library: str | None = None):
        self.tcl.write_cmd("read_vhdl", path)

    def read_ip(self, path: str):
        self.tcl.write_cmd("read_ip", path)

    def read_xdc(self, path: str):
        self.tcl.write_cmd("read_xdc", path)

    def synth_design(self, top_entity: str):
        self.tcl.write_cmd("synth_design", "-top", top_entity)

    def opt_design(self):
        self.tcl.write_cmd("opt_design")

    def place_design(self):
        self.tcl.write_cmd("place_design")

    def phys_opt_design(self):
        self.tcl.write_cmd("phys_opt_design")

    def route_design(self):
        self.tcl.write_cmd("route_design")

    def write_bitstream(self, path):
        self.tcl.write_cmd("write_bitstream", "-force", path)

    def write_debug_probes(self, path):
        self.tcl.write_cmd("write_debug_probes", "-force", path)

    def report_timing_summary(self, path):
        self.tcl.write_cmd(
            "report_timing_summary",
            "-delay_type max",
            "-report_unconstrained",
            "-check_timing_verbose",
            "-max_paths 10",
            "-input_pins",
            "-file",
            path,
        )

    def report_power(self, path):
        self.tcl.write_cmd("report_power", "-file", path)

    def report_bus_skew(self, path):
        self.tcl.write_cmd("report_bus_skew", "-file", path)

    def report_ram_utilization(self, path):
        self.tcl.write_cmd("report_ram_utilization", "-file", path)

    def report_route_status(self, path):
        self.tcl.write_cmd("report_route_status", "-file", path)

    #
    #
    #

    def open_hw_manager(self):
        self.tcl.write_cmd("open_hw_manager")

    def connect_hw_server(self, allow_non_jtag: bool = False):
        args = []

        if allow_non_jtag:
            args.append("-allow_non_jtag")

        self.tcl.write_cmd("connect_hw_server", *args)

    def open_hw_target(self):
        self.tcl.write_cmd("open_hw_target")

    def current_hw_device(self, *args):
        self.tcl.write_cmd("current_hw_device", *args)

    def refresh_hw_device(self, *args):
        self.tcl.write_cmd("refresh_hw_device", *args)

    def set_property(self, name, value, objects):
        self.tcl.write_cmd("set_property", name, value, objects)

    def program_hw_devices(self, devices):
        self.tcl.write_cmd("program_hw_devices", devices)

    #
    #
    #

    def write_tcl(self, file=None):
        self.tcl.print(file)


class Project:
    class ProjPaths:
        def __init__(self, build_dir):
            self.dir_build = build_dir
            self.dir_generated = f"{build_dir}/generated"
            self.dir_generated_vhdl = f"{build_dir}/generated/vhdl"
            self.dir_generated_ip = f"{build_dir}/generated/ip_scripts"
            self.dir_generated_constraints = f"{build_dir}/generated/constraints"
            self.dir_output = f"{build_dir}/output"
            self.dir_output_ip = f"{build_dir}/output/ip"
            self.dir_output_reports = f"{build_dir}/output/reports"
            self.dir_output_impl = f"{build_dir}/output/impl"
            self.dir_output_build_log = f"{build_dir}/output/build_log"

            self.makefile = f"{build_dir}/Makefile"
            self.project_tcl = f"{build_dir}/generated/project.tcl"
            self.project_constraints = f"{build_dir}/generated/constraints/project.xdc"
            self.program_tcl = f"{build_dir}/generated/program.tcl"
            self.vivado_log = f"{build_dir}/output/build_log/vivado.log"
            self.vivado_journal = f"{build_dir}/output/build_log/vivado.jou"
            self.vivado_programmer_log = (
                f"{build_dir}/output/build_log/vivado_programmer.log"
            )
            self.vivado_programmer_journal = (
                f"{build_dir}/output/build_log/vivado_programmer.jou"
            )

        def create_dirs(self):
            for path in [
                self.dir_build,
                self.dir_generated,
                self.dir_generated_constraints,
                self.dir_generated_vhdl,
                self.dir_generated_ip,
                self.dir_output,
                self.dir_output_ip,
                self.dir_output_reports,
                self.dir_output_impl,
                self.dir_output_build_log,
            ]:
                Path(path).mkdir(parents=True, exist_ok=True)

        def relative(self, name: str):
            return self.relative_to_build(getattr(self, name))

        def relative_to_build(self, path: str) -> str:
            return str(Path(path).relative_to(self.dir_build))

    class BuildStage:
        def __init__(self, name):
            self.commands: list[str] = []

        def add_front(self, command):
            ...

        def add_back(self, command):
            ...

    class BuildStages:
        def __init__(self):
            self.setup = Project.BuildStage()
            self.synth = Project.BuildStage()
            self.route = Project.BuildStage()
            self.impl = Project.BuildStage()

    def __init__(
        self,
        top_entity_name: str,
        part_id: str,
        build_dir,
        proj_name: str | None = None,
    ):
        self._top_entity_name = top_entity_name
        self._proj_name = proj_name if proj_name is not None else top_entity_name
        self._part_id = part_id

        self.paths = Project.ProjPaths(build_dir)
        self.paths.create_dirs()

        self._vhdl_files = []
        self._constraint_files = []
        self._ip_files = []

        self._write_debug_probes = False

        proj_tcl = self.paths.relative_to_build(self.paths.project_tcl)
        paths = self.paths

        self.root_target = MakeTarget(
            "all",
            [
                f"vivado -mode batch -source {proj_tcl} -journal {paths.relative('vivado_journal')} -log {paths.relative('vivado_log')}"
            ],
            phony=True,
        )

    def add_vhdl(self, vhdl_path):
        self._vhdl_files.append(vhdl_path)

    def add_constraints(self, xdc_path):
        self._constraint_files.append(xdc_path)

    def add_ip(self, xci_path):
        self._ip_files.append(xci_path)

    def write_debug_probes(self):
        self._write_debug_probes = True

    def write(self):
        paths = self.paths

        bitstream_path = f"{paths.dir_output_impl}/{self._proj_name}.bit"
        bitstream_target = MakeTarget(
            bitstream_path, commands=[], dep=[self.root_target]
        )

        program_tcl = self.paths.relative_to_build(self.paths.program_tcl)
        program_target = MakeTarget(
            "program",
            [
                f"vivado -mode batch -source {program_tcl} -journal {paths.relative('vivado_programmer_journal')} -log {paths.relative('vivado_programmer_log')}"
            ],
            phony=True,
        )

        self.root_target.generate_makefile(
            program_target, bitstream_target, path=paths.makefile
        )

        util_file = f"{os.path.dirname(__file__)}/cohdl_make_util.py"
        shutil.copy(util_file, f"{paths.dir_build}/cohdl_make_util.py")

        #
        # define vivado project
        #

        vivado = VivadoProject()

        vivado.write_comment(
            [
                "auto generated file",
                "do not edit manually",
            ]
        )

        vivado.write_line()
        vivado.write_comment("setup project")
        vivado.set_part(self._part_id)

        for vhdl_path in self._vhdl_files:
            vivado.read_vhdl(paths.relative_to_build(vhdl_path))

        for xdc_path in self._constraint_files:
            vivado.read_xdc(paths.relative_to_build(xdc_path))

        for ip_path in self._ip_files:
            vivado.read_ip(paths.relative_to_build(ip_path))

        vivado.write_line()
        vivado.write_comment("synthesize design")

        vivado.synth_design(self._top_entity_name)

        vivado.report_timing_summary(
            paths.relative_to_build(f"{paths.dir_output_reports}/syn_timing.rpt")
        )
        vivado.report_power(
            paths.relative_to_build(f"{paths.dir_output_reports}/syn_power.rpt")
        )

        vivado.opt_design()
        vivado.place_design()
        vivado.phys_opt_design()

        vivado.write_line()
        vivado.write_comment("route design")
        vivado.route_design()

        vivado.write_line()
        vivado.write_comment("write bitstream file")

        vivado.write_bitstream(paths.relative_to_build(bitstream_path))

        vivado.report_timing_summary(
            paths.relative_to_build(f"{paths.dir_output_reports}/imp_timing.rpt")
        )
        vivado.report_power(
            paths.relative_to_build(f"{paths.dir_output_reports}/imp_power.rpt")
        )
        vivado.report_bus_skew(
            paths.relative_to_build(f"{paths.dir_output_reports}/imp_bus_skew.rpt")
        )
        vivado.report_ram_utilization(
            paths.relative_to_build(f"{paths.dir_output_reports}/imp_ram_util.rpt")
        )

        vivado.report_route_status(
            paths.relative_to_build(f"{paths.dir_output_reports}/imp_route_status.rpt")
        )

        if self._write_debug_probes:
            vivado.write_debug_probes(
                paths.relative_to_build(
                    f"{paths.dir_output_impl}/{self._proj_name}.ltx"
                )
            )

        vivado.write_line()
        vivado.write_comment("exit after comlete build")

        with open(paths.project_tcl, "w") as file:
            vivado.write_tcl(file)

        #
        # define vivado fpga programmer script
        #

        programmer = VivadoProject()

        programmer.write_comment(
            [
                "auto generated file",
                "do not edit manually",
            ]
        )

        programmer.write_line()
        programmer.open_hw_manager()
        programmer.connect_hw_server(allow_non_jtag=True)
        programmer.open_hw_target()

        # TODO
        # setup with multiple hw devices not yet supported
        programmer.current_hw_device("[get_hw_devices]")
        programmer.refresh_hw_device(
            "-update_hw_probes false", "[lindex [get_hw_devices] 0]"
        )

        programmer.write_line()
        programmer.set_property("PROBES.FILE", "{}", "[get_hw_devices]")
        programmer.set_property("FULL_PROBES.FILE", "{}", "[get_hw_devices]")
        programmer.set_property(
            "PROGRAM.FILE", paths.relative_to_build(bitstream_path), "[get_hw_devices]"
        )

        programmer.write_line()
        programmer.program_hw_devices("[get_hw_devices]")

        with open(paths.program_tcl, "w") as file:
            programmer.write_tcl(file)


_active_project: None | Project = None


def set_active_project(proj: Project):
    global _active_project
    _active_project = proj


def get_active_project() -> Project:
    assert _active_project is not None
    return _active_project


def write_file_if_changed(file_path, content):
    """
    check if content matches the content of the given file
    only update the file if changes where found
    (used for files, that are targets/prerequisits in Makefiles)

    returns true if file was updated
    """

    if Path(file_path).exists():
        with open(file_path) as file:
            if content == file.read():
                return False

    with open(file_path, "w") as file:
        file.write(content)
    return True
