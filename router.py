"""
Hybrid Static Router and Firewall controller for POX.

Place this file inside ~/pox/ext/ and run with:
    ./pox.py log.level --INFO router

Topology:
    h1 (10.0.0.1) --- s1 --- s2 --- s3 --- h3 (10.0.0.3)
                               |
                          h2 (10.0.0.2)
"""

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.addresses import IPAddr
from pox.lib.packet.arp import arp

log = core.getLogger()

# --- Firewall Access Control List (Blocked Routes) ---
FIREWALL_RULES = [
    ('10.0.0.2', '10.0.0.3'),  # Block h2 -> h3
    ('10.0.0.3', '10.0.0.2')   # Block h3 -> h2
]

# --- Static IP Routing Table ---
STATIC_ROUTES = {
    # Switch 1
    (1, '10.0.0.1', '10.0.0.2'): 2,
    (1, '10.0.0.1', '10.0.0.3'): 2,
    (1, '10.0.0.2', '10.0.0.1'): 1,
    (1, '10.0.0.3', '10.0.0.1'): 1,

    # Switch 2
    (2, '10.0.0.1', '10.0.0.2'): 1,
    (2, '10.0.0.1', '10.0.0.3'): 3,
    (2, '10.0.0.2', '10.0.0.1'): 2,
    (2, '10.0.0.2', '10.0.0.3'): 3,
    (2, '10.0.0.3', '10.0.0.1'): 2,
    (2, '10.0.0.3', '10.0.0.2'): 1,

    # Switch 3
    (3, '10.0.0.1', '10.0.0.3'): 1,
    (3, '10.0.0.2', '10.0.0.3'): 1,
    (3, '10.0.0.3', '10.0.0.1'): 2,
    (3, '10.0.0.3', '10.0.0.2'): 2,
}

# --- ARP Forwarding Table ---
ARP_ROUTES = {
    (1, '10.0.0.1'): 1, (1, '10.0.0.2'): 2, (1, '10.0.0.3'): 2,
    (2, '10.0.0.1'): 2, (2, '10.0.0.2'): 1, (2, '10.0.0.3'): 3,
    (3, '10.0.0.1'): 2, (3, '10.0.0.2'): 2, (3, '10.0.0.3'): 1,
}

class HybridController(object):

    def __init__(self):
        core.openflow.addListeners(self)
        log.info("Hybrid Router/Firewall Started.")

    def _handle_ConnectionUp(self, event):
        dpid = event.dpid
        log.info("Switch s%s connected. Installing rules...", dpid)

        self._install_table_miss(event.connection)
        self._install_firewall_rules(event.connection, dpid)
        self._install_routing_rules(event.connection, dpid)

    def _send_flow_mod(self, connection, priority, dl_type=None,
                       nw_src=None, nw_dst=None, out_port=None):
        msg = of.ofp_flow_mod()
        msg.priority = priority

        if dl_type is not None:
            msg.match.dl_type = dl_type
        if nw_src is not None:
            msg.match.nw_src = IPAddr(nw_src)
        if nw_dst is not None:
            msg.match.nw_dst = IPAddr(nw_dst)
        if out_port is not None:
            msg.actions.append(of.ofp_action_output(port=out_port))

        connection.send(msg)

    def _install_table_miss(self, connection):
        """Send all unmatched packets to the controller (packet_in)."""
        self._send_flow_mod(
            connection=connection,
            priority=0,
            out_port=of.OFPP_CONTROLLER
        )

    def _install_firewall_rules(self, connection, dpid):
        """Install rules with priority=100 that DROP matched traffic."""
        for src_ip, dst_ip in FIREWALL_RULES:
            self._send_flow_mod(
                connection=connection,
                priority=100,
                dl_type=0x0800,
                nw_src=src_ip,
                nw_dst=dst_ip
            )
            log.info("  [FIREWALL s%s] Blocked %s -> %s", dpid, src_ip, dst_ip)

    def _install_routing_rules(self, connection, dpid):
        """Install rules with priority=10 that FORWARD matched traffic."""
        for (sw_id, src_ip, dst_ip), out_port in STATIC_ROUTES.items():
            if sw_id == dpid:
                self._send_flow_mod(
                    connection=connection,
                    priority=10,
                    dl_type=0x0800,
                    nw_src=src_ip,
                    nw_dst=dst_ip,
                    out_port=out_port
                )
                log.info(
                    "  [ROUTER s%s] Route %s -> %s via port %s",
                    dpid,
                    src_ip,
                    dst_ip,
                    out_port
                )

    def _handle_PacketIn(self, event):
        """Handle packets not matched by the switch flow tables (e.g. ARP)."""
        dpid = event.dpid
        pkt = event.parsed

        if pkt is None or not pkt.parsed:
            return

        arp_pkt = pkt.find('arp')
        if isinstance(arp_pkt, arp):
            target_ip = str(arp_pkt.protodst)
            key = (dpid, target_ip)

            if key in ARP_ROUTES:
                out_port = ARP_ROUTES[key]
                if out_port == event.port:
                    return
                # Tell the switch to output this specific packet
                msg = of.ofp_packet_out()
                msg.data = event.ofp
                msg.in_port = event.port
                msg.actions.append(of.ofp_action_output(port=out_port))
                event.connection.send(msg)
            else:
                log.warning(
                    "Unknown ARP target %s on s%s. Dropping.",
                    target_ip,
                    dpid
                )


def launch():
    core.registerNew(HybridController)
