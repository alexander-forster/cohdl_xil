from __future__ import annotations

import cohdl
from cohdl import Bit, BitVector, Port, Signal
from cohdl_xil import ip_block


def mig(
    *,
    prj_file_content: str,
    properties: dict[str, str],
    ports: dict[str, Port],
    signals: dict[str, Signal],
    module_name="mig_design",
):
    from cohdl_xil._common.vivado_project import get_active_project

    prj_file_dep = get_active_project().add_dependency(
        "mig_proj_file.prj", prj_file_content, make_unique=True
    )

    assert not "CONFIG.XML_INPUT_FILE" in properties

    properties = {
        **properties,
        "CONFIG.XML_INPUT_FILE": f"[file normalize {prj_file_dep}]",
    }

    ip_block(
        name="mig_7series",
        vendor="xilinx.com",
        library="ip",
        version="4.2",
        module_name=module_name,
        properties=properties,
        ports=ports,
        dependencies=[prj_file_dep],
    )(**signals)
