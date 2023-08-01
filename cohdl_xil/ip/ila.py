from __future__ import annotations
from dataclasses import dataclass

import cohdl
from cohdl_xil import ip_block
from cohdl_xil._common.vivado_project import get_active_project


@dataclass
class _DbgConnection:
    type: type
    wrapped_name: str
    local_name: str
    ip_name: str


def ila(clk: cohdl.std.Clock, probes: dict):
    get_active_project().write_debug_probes()

    ip_ports = {"clk": cohdl.Port.input(cohdl.Bit)}
    wrapper_ports = {"wrapped_clk": cohdl.Port.input(cohdl.Bit)}
    wrapper_con = {"wrapped_clk": clk.signal()}

    properties = {
        "CONFIG.ALL_PROBE_SAME_MU": "false",
        "CONFIG.C_NUM_OF_PROBES": str(len(probes)),
    }

    dbg_connections: list[_DbgConnection] = []

    for nr, (name, value) in enumerate(probes.items()):
        val_type = value.type
        wrapped_name = f"wrapped_{name}"
        local_name = name
        ip_name = f"probe{nr}"

        wrapper_ports[wrapped_name] = cohdl.Port.input(val_type)
        wrapper_con[wrapped_name] = value

        if issubclass(val_type, cohdl.Bit):
            width = 1

            ip_ports[ip_name] = cohdl.Port.input(cohdl.BitVector[1])

        else:
            width = value.width

            ip_ports[ip_name] = cohdl.Port.input(cohdl.BitVector[width])

        dbg_connections.append(
            _DbgConnection(val_type, wrapped_name, local_name, ip_name)
        )
        properties[f"CONFIG.C_PROBE{nr}_WIDTH"] = str(width)

    def architecture(self):
        ip_connections = {"clk": self.wrapped_clk}

        for con in dbg_connections:
            if issubclass(con.type, cohdl.Bit):
                local_signal = cohdl.Signal[cohdl.BitVector[1]](name=con.local_name)

                # concurrent_context required because introductions
                # of prefix wrapper in std.concurrent causes problems with
                # capture lazy flag
                @cohdl.concurrent_context
                def con_logic():
                    local_signal[0] <<= getattr(self, con.wrapped_name)

            else:
                local_signal = cohdl.Signal[con.type](name=con.local_name)

                @cohdl.concurrent_context
                def con_logic():
                    local_signal.next = getattr(self, con.wrapped_name)

            ip_connections[con.ip_name] = local_signal

        ip = ip_block(
            name="ila",
            vendor="xilinx.com",
            library="ip",
            version="6.2",
            module_name="ila",
            ports=ip_ports,
            properties=properties,
        )

        ip(**ip_connections)

    ip_wrapper = type(
        "IP_wrapper", (cohdl.Entity,), {**wrapper_ports, "architecture": architecture}
    )

    ip_wrapper(**wrapper_con)
