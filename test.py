#!/usr/bin/env python3
"""
Automated Test Script - Static Routing SDN Project
==================================================
Run this INSTEAD of topo.py — it starts the topology,
runs both test scenarios automatically, then drops into Mininet CLI.

Usage:
    sudo python3 test.py
"""

import time
import subprocess
import os
import atexit
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.link import TCLink
from mininet.log import setLogLevel, info
from mininet.cli import CLI

def separator(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")

def dump_flows(switch_name):
    """Return flow table string for a switch."""
    result = subprocess.run(
        f"ovs-ofctl dump-flows {switch_name}",
        shell=True, capture_output=True, text=True
    )
    return result.stdout.strip()

def count_static_rules(switch_name):
    """Count priority=10 rules (our static routes)."""
    flows = dump_flows(switch_name)
    return sum(1 for line in flows.splitlines() if 'priority=10' in line)

def delete_flows(switch_name):
    subprocess.run(f"ovs-ofctl del-flows {switch_name}", shell=True)

def build_net():
    net = Mininet(
        controller=RemoteController,
        switch=OVSSwitch,
        link=TCLink,
        autoSetMacs=True
    )
    net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)

    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')
    s3 = net.addSwitch('s3')

    h1 = net.addHost('h1', ip='10.0.0.1/24', mac='00:00:00:00:00:01')
    h2 = net.addHost('h2', ip='10.0.0.2/24', mac='00:00:00:00:00:02')
    h3 = net.addHost('h3', ip='10.0.0.3/24', mac='00:00:00:00:00:03')

    # Host links first to match expected port numbering in router.py
    net.addLink(h1, s1)
    net.addLink(h2, s2)
    net.addLink(h3, s3)
    net.addLink(s1, s2)
    net.addLink(s2, s3)

    return net


def scenario_1(net):
    separator("SCENARIO 1: Routing & Firewall Validation")

    h1, h2, h3 = net.get('h1', 'h2', 'h3')

    # (source_node, destination_ip, label, expected_to_pass)
    test_cases = [
        (h1, '10.0.0.2', 'h1 -> h2 (Allowed)', True),
        (h1, '10.0.0.3', 'h1 -> h3 (Allowed)', True),
        (h2, '10.0.0.1', 'h2 -> h1 (Allowed)', True),
        (h2, '10.0.0.3', 'h2 -> h3 (Blocked)', False),
        (h3, '10.0.0.1', 'h3 -> h1 (Allowed)', True),
        (h3, '10.0.0.2', 'h3 -> h2 (Blocked)', False),
    ]

    all_passed = True
    for src, dst_ip, label, expected_pass in test_cases:
        result = src.cmd(f"ping -c 3 -W 2 {dst_ip}")
        
        if expected_pass:
            passed = '0% packet loss' in result
        else:
            # For blocked traffic, we expect 100% loss or 'Destination Host Unreachable'
            passed = '100% packet loss' in result or '0 received' in result

        if not passed:
            all_passed = False
        
        status = "PASS" if passed else "FAIL"
        # Extract rtt line if available
        rtt = [l for l in result.splitlines() if 'rtt' in l or 'round-trip' in l]
        rtt_str = rtt[0].strip() if rtt else "no rtt"
        print(f"  [{status}] {label}  |  {rtt_str}")

    print(f"\n  Scenario 1: {'ALL TESTS PASSED ✓' if all_passed else 'SOME TESTS FAILED ✗'}")
    return all_passed


def scenario_2(net):
    separator("SCENARIO 2: Regression — Delete & Reinstall Flow Rules")

    h1, h3 = net.get('h1', 'h3')
    switches = ['s1', 's2', 's3']

    # Step 1: Show flow counts before deletion
    print("[Step 1] Static rule counts BEFORE deletion:")
    before_counts = {}
    for sw in switches:
        c = count_static_rules(sw)
        before_counts[sw] = c
        print(f"  {sw}: {c} static rules (priority=10)")

    # Step 2: Delete all flows
    print("\n[Step 2] Deleting all flow rules from all switches...")
    for sw in switches:
        delete_flows(sw)
    print("  Done — flow tables cleared.")

    # Step 3: Verify connectivity is broken
    print("\n[Step 3] Checking connectivity (should be BROKEN)...")
    result = h1.cmd("ping -c 3 -W 1 10.0.0.3")
    broken = '100% packet loss' in result or '0 received' in result
    print(f"  h1 -> h3: {'BROKEN as expected ✓' if broken else 'Unexpectedly working'}")

    # Step 4: Wait for controller to reinstall (POX reinstalls on next packet_in)
    print("\n[Step 4] Sending a ping to trigger controller reinstall...")
    h1.cmd("ping -c 1 -W 2 10.0.0.3")   # triggers packet_in on all switches
    time.sleep(3)
    print("  Waited 3 seconds for controller to respond...")

    # Step 5: Show flow counts after reinstall
    print("\n[Step 5] Static rule counts AFTER reinstall:")
    after_counts = {}
    for sw in switches:
        c = count_static_rules(sw)
        after_counts[sw] = c
        print(f"  {sw}: {c} static rules (priority=10)")

    # Step 6: Verify connectivity is restored
    print("\n[Step 6] Checking connectivity (should be RESTORED)...")
    result = h1.cmd("ping -c 3 -W 2 10.0.0.3")
    restored = '0% packet loss' in result
    print(f"  h1 -> h3: {'RESTORED ✓' if restored else 'Still broken ✗'}")

    # Step 7: Check same rules came back (path unchanged)
    print("\n[Step 7] Verifying path is UNCHANGED after reinstall:")
    path_same = True
    for sw in switches:
        same = before_counts[sw] == after_counts[sw]
        if not same:
            path_same = False
        print(f"  {sw}: before={before_counts[sw]} after={after_counts[sw]}  {'✓ same' if same else '✗ different'}")

    passed = restored and path_same
    print(f"\n  Scenario 2: {'PASS — path unchanged after reinstall ✓' if passed else 'FAIL ✗'}")
    return passed


def iperf_test(net):
    separator("Throughput Test: iperf h1 -> h3")
    h1, h3 = net.get('h1', 'h3')
    h3.sendCmd('iperf -s')
    time.sleep(1)
    result = h1.cmd('iperf -c 10.0.0.3 -t 5')
    print(result.strip())
    h3.sendInt()
    h3.waitOutput()


def show_flow_tables():
    separator("Final Flow Tables")
    for sw in ['s1', 's2', 's3']:
        print(f"--- {sw} ---")
        flows = dump_flows(sw)
        for line in flows.splitlines():
            if 'priority' in line:
                print(f"  {line.strip()}")
        print()

def cleanup():
    subprocess.run(['mn', '-c'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(['fuser', '-k', '6633/tcp'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if __name__ == '__main__':
    setLogLevel('warning')   # suppress Mininet noise during tests

    print("\n" + "=" * 60)
    print("  Static Routing SDN — Full Validation Suite")
    print("=" * 60)

    print("  [1/3] Cleaning previous state...")
    cleanup()
    atexit.register(cleanup)

    print("  [2/3] Starting POX Controller in background...")
    sudo_user = os.environ.get('SUDO_USER')
    if sudo_user:
        pox_path = f'/home/{sudo_user}/pox/pox.py'
    else:
        pox_path = os.path.expanduser('~/pox/pox.py')
        
    pox_process = subprocess.Popen(
        [pox_path, 'router'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(2)

    print("  [3/3] Building topology...")
    net = build_net()
    net.start()

    print("\n  Waiting 4 seconds for controller to install rules...")
    time.sleep(4)

    # Run scenarios
    s1_result = scenario_1(net)
    s2_result = scenario_2(net)
    iperf_test(net)
    show_flow_tables()

    # Final summary
    separator("FINAL RESULTS")
    print(f"  Scenario 1 — Routing & Firewall  : {'PASS ✓' if s1_result else 'FAIL ✗'}")
    print(f"  Scenario 2 — Regression Test     : {'PASS ✓' if s2_result else 'FAIL ✗'}")
    print()

    # Drop into CLI for manual exploration / demo
    print("  Dropping into Mininet CLI for manual demo...\n")
    CLI(net)

    print("\n  Shutting down...")
    net.stop()
    pox_process.terminate()