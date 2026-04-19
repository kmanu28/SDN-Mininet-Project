from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.packet import ethernet, ipv4
from pox.lib.util import dpid_to_str

log = core.getLogger()

class MyController(object):
    def __init__(self, connection):
        self.connection = connection
        self.mac_to_port = {}

        connection.addListeners(self)

    def _handle_PacketIn(self, event):
        packet = event.parsed

        if not packet.parsed:
            return

        # Learn MAC address
        self.mac_to_port[packet.src] = event.port

        # 🔥 FIREWALL RULE (BLOCK h1 → h3)
        ip = packet.find('ipv4')
        if ip:
            if str(ip.srcip) == "10.0.0.1" and str(ip.dstip) == "10.0.0.3":
                log.info("Blocked h1 → h3")
                return

        # Normal forwarding
        if packet.dst in self.mac_to_port:
            out_port = self.mac_to_port[packet.dst]
        else:
            out_port = of.OFPP_FLOOD

        msg = of.ofp_packet_out()
        msg.data = event.ofp
        msg.actions.append(of.ofp_action_output(port=out_port))
        self.connection.send(msg)


def launch():
    def start_switch(event):
        log.info("Controlling %s" % (dpid_to_str(event.dpid),))
        MyController(event.connection)

    core.openflow.addListenerByName("ConnectionUp", start_switch)
