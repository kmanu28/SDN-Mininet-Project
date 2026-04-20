#!/usr/bin/env python3
"""Mininet topology for the hybrid SDN router and firewall demo."""

from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink


CONTROLLER_IP = '127.0.0.1'
CONTROLLER_PORT = 6633


def build_net():
    """Create the Mininet topology without starting the CLI."""
    net = Mininet(
        controller=RemoteController,
        switch=OVSSwitch,
        link=TCLink,
        autoSetMacs=True
    )

    info("*** Adding remote controller at %s:%s\n" % (CONTROLLER_IP, CONTROLLER_PORT))
    net.addController(
        'c0',
        controller=RemoteController,
        ip=CONTROLLER_IP,
        port=CONTROLLER_PORT
    )

    info("*** Adding switches\n")
    s1 = net.addSwitch('s1', protocols='OpenFlow10')
    s2 = net.addSwitch('s2', protocols='OpenFlow10')
    s3 = net.addSwitch('s3', protocols='OpenFlow10')

    info("*** Adding hosts\n")
    h1 = net.addHost('h1', ip='10.0.0.1/24', mac='00:00:00:00:00:01')
    h2 = net.addHost('h2', ip='10.0.0.2/24', mac='00:00:00:00:00:02')
    h3 = net.addHost('h3', ip='10.0.0.3/24', mac='00:00:00:00:00:03')

    info("*** Adding links\n")
    # Host links first — determines port numbering on each switch
    net.addLink(h1, s1)   # s1: port 1 = h1
    net.addLink(h2, s2)   # s2: port 1 = h2
    net.addLink(h3, s3)   # s3: port 1 = h3
    # Switch-to-switch links
    net.addLink(s1, s2)   # s1: port 2 = s2  |  s2: port 2 = s1
    net.addLink(s2, s3)   # s2: port 3 = s3  |  s3: port 2 = s2

    return net


def create_topology():
    net = build_net()

    info("*** Starting network\n")
    net.start()

    info("\n*** Topology Ready ***\n")
    info("    h1 (10.0.0.1) --- s1 --- s2 --- s3 --- h3 (10.0.0.3)\n")
    info("                              |              \n")
    info("                         h2 (10.0.0.2)      \n\n")

    info("*** IMPORTANT TESTING COMMANDS ***\n")
    info("  [Allowed Traffic] h1 ping h3\n")
    info("  [Blocked Traffic] h2 ping h3\n")
    info("  [Bandwidth Test] h3 iperf -s & / h1 iperf -c 10.0.0.3 -t 5\n")
    info("  [Inspect s2 flows] sh ovs-ofctl dump-flows s2\n\n")

    CLI(net)

    info("*** Stopping network\n")
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    create_topology()
