import cohdl
import pathlib
import sys

from cohdl.utility import MakeTarget
from cohdl_xil._common.vivado_project import get_active_project, write_file_if_changed
from cohdl_xil._common.tcl_writer import TclWriter


_used_module_names = []


def ip_block(
    name,
    vendor,
    library,
    version,
    module_name,
    properties: dict[str, str],
    ports: dict[str, cohdl.Port],
    dependencies: list[str] | None = None,
) -> type[cohdl.Entity]:
    if dependencies is None:
        dependencies = []

    if module_name in _used_module_names:
        cnt = 1
        while f"{module_name}_{cnt}" in _used_module_names:
            cnt += 1

        module_name = f"{module_name}_{cnt}"

    for port_name, value in ports.items():
        if value.name() is None:
            value._name = port_name

    active_project = get_active_project()
    paths = active_project.paths

    out_ip_path = paths.dir_output_ip
    xci_path = f"{out_ip_path}/{module_name}/{module_name}.xci"
    tcl_path = f"{paths.dir_generated_ip}/{module_name}.tcl"

    tcl = TclWriter()

    tcl.write_cmd("set_part", active_project._part_id)

    tcl.write_cmd(
        "create_ip",
        name=name,
        vendor=vendor,
        library=library,
        version=version,
        module_name=module_name,
        dir=paths.relative_to_build(out_ip_path),
    )

    for prop_name, value in properties.items():
        tcl.write_cmd("set_property", prop_name, value, f"[get_ips {module_name}]")

    tcl.write_cmd(
        "generate_target",
        "all",
        f"[get_files {paths.relative_to_build(xci_path)}]",
        "-force",
    )

    tcl.write_cmd("synth_ip", f"[get_ips {module_name}]")

    write_file_if_changed(tcl_path, tcl.write_string())

    # place log and journal files in separate vivado
    # directory because out_ip_path/module_name should not exist
    # before generate_target is executed
    build_log_path = f"{out_ip_path}/build_log/{module_name}"
    pathlib.Path(build_log_path).mkdir(parents=True, exist_ok=True)
    build_log_path = paths.relative_to_build(build_log_path)

    # determine current python path
    # and use it as an interpreter for cohdl_make_util.py
    # used for cleanup before new build
    python_path = pathlib.Path(sys.executable).as_posix()

    active_project.root_target.add_dependency(
        MakeTarget(
            paths.relative_to_build(xci_path),
            [
                f"{python_path} cohdl_make_util.py remove_old {paths.relative_to_build(tcl_path)} {paths.relative_to_build(xci_path)} {paths.relative_to_build(f'{out_ip_path}/{module_name}')}",
                f"vivado -mode batch -source {paths.relative_to_build(tcl_path)} -journal {build_log_path}/vivado.jou -log {build_log_path}/vivado.log",
            ],
            dep=[paths.relative_to_build(tcl_path), *dependencies],
        )
    )

    active_project.add_ip(xci_path)

    return type(
        module_name,
        (cohdl.Entity,),
        ports,
        extern=True,
        attributes={"vhdl_library": "work"},
    )


class IpBase:
    def __init__(
        self,
        name,
        vendor,
        library,
        version,
        module_name,
        properties: dict[str, str] = {},
        ports: dict[str, cohdl.Port] = {},
        signals: dict[str, cohdl.Signal] = {},
    ) -> None:
        self.name = name
        self.vendor = vendor
        self.library = library
        self.version = version
        self.module_name = module_name
        self.properties = {**properties}
        self.ports = {**ports}
        self.signals = {**signals}

    def print(self):
        print("-------------------------")
        print(f"name = {self.name}")
        print(f"vendor = {self.vendor}")
        print(f"library = {self.library}")
        print(f"version = {self.version}")
        print(f"module_name = {self.module_name}")

        print(f" >>> PROPERTIERS")

        for name, value in self.properties.items():
            print(f"  {name} = {value}")

        print(f" >>> PORTS")

        for name, value in self.ports.items():
            print(f"  {name} = {value}")

    def set_property(self, name: str, value: str):
        self.properties[name] = value

    def add_port(self, port, signal):
        name = port.name()
        self.ports[name] = port
        self.signals[name] = signal

    def instantiate(self):
        ip = ip_block(
            name=self.name,
            vendor=self.vendor,
            library=self.library,
            version=self.version,
            module_name=self.module_name,
            properties=self.properties,
            ports=self.ports,
        )

        ip(**self.signals)
