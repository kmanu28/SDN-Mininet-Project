#!/usr/bin/env python3
"""Automated validation for the hybrid SDN router and firewall."""

import subprocess
import time

from mininet.cli import CLI
from mininet.log import setLogLevel

from topo import build_net


def separator(title):
    print("\n" + "=" * 60)
    print("  {}".format(title))
    print("=" * 60 + "\n")


def dump_flows(switch_name):
    result = subprocess.run(
        ['ovs-ofctl', 'dump-flows', switch_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False
    )
    return result.stdout


def scenario_1_routing(net):
    separator("SCENARIO 1: Expected Connectivity (Static Routing)")
    h1, h2, h3 = net.get('h1', 'h2', 'h3')

    pairs = [
        (h1, '10.0.0.2', 'h1 -> h2 (Allowed)'),
        (h1, '10.0.0.3', 'h1 -> h3 (Allowed)'),
        (h3, '10.0.0.1', 'h3 -> h1 (Allowed)'),
    ]

    all_passed = True
    for src, dst_ip, label in pairs:
        result = src.cmd("ping -c 3 -W 1 {}".format(dst_ip))
        passed = '0% packet loss' in result
        if not passed:
            all_passed = False
        print("  [{}] {}".format('PASS' if passed else 'FAIL', label))

    print("\n  Result: {}".format(
        'ALL PASSED' if all_passed else 'SOME FAILED'
    ))
    return all_passed


def scenario_2_firewall(net):
    separator("SCENARIO 2: Expected Blocking (Firewall Rules)")
    h2, h3 = net.get('h2', 'h3')

    pairs = [
        (h2, '10.0.0.3', 'h2 -> h3 (Blocked)'),
        (h3, '10.0.0.2', 'h3 -> h2 (Blocked)')
    ]

    all_passed = True
    for src, dst_ip, label in pairs:
        result = src.cmd("ping -c 3 -W 1 {}".format(dst_ip))
        passed = '100% packet loss' in result or '0 received' in result
        if not passed:
            all_passed = False
        print("  [{}] {}".format('PASS' if passed else 'FAIL', label))

    print("\n  Result: {}".format(
        'ALL PASSED' if all_passed else 'SOME FAILED'
    ))
    return all_passed


def scenario_3_flow_validation():
    separator("SCENARIO 3: Flow Table Validation")

    checks = [
        ('s1', 'nw_src=10.0.0.1,nw_dst=10.0.0.3', 's1 forwards h1 -> h3'),
        ('s2', 'nw_src=10.0.0.2,nw_dst=10.0.0.3', 's2 has the h2 -> h3 block rule'),
        ('s3', 'nw_src=10.0.0.3,nw_dst=10.0.0.1', 's3 forwards h3 -> h1'),
    ]

    all_passed = True
    for switch_name, expected_text, label in checks:
        flow_table = dump_flows(switch_name)
        passed = expected_text in flow_table
        if not passed:
            all_passed = False
        print("  [{}] {}".format('PASS' if passed else 'FAIL', label))

    print("\n  Result: {}".format(
        'ALL PASSED' if all_passed else 'SOME FAILED'
    ))
    return all_passed


def scenario_4_throughput(net):
    separator("SCENARIO 4: Throughput Observation (iperf)")
    h1, h3 = net.get('h1', 'h3')

    # Start iperf server on h3 in the background using Mininet's sendCmd
    h3.sendCmd('iperf -s')
    time.sleep(1)

    # Run iperf client from h1 to h3
    result = h1.cmd('iperf -c 10.0.0.3 -t 5')

    # Stop the iperf server on h3
    h3.sendInt()
    h3.waitOutput()

    passed = 'Mbits/sec' in result or 'Gbits/sec' in result
    print(result.strip())
    print("  [{}] h1 -> h3 throughput measured successfully".format(
        'PASS' if passed else 'FAIL'
    ))
    return passed


import os
import atexit

def cleanup():
    # Kill mininet and pox if they are still lingering
    subprocess.run(['mn', '-c'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(['fuser', '-k', '6633/tcp'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if __name__ == '__main__':
    setLogLevel('warning')
    print("\n=== Automated SDN Hybrid Evaluation Suite ===")
    
    print("  [1/4] Cleaning previous state...")
    cleanup()
    atexit.register(cleanup)

    print("  [2/4] Starting POX Controller in background...")
    # When running with sudo, ~ expands to /root. We want the original user's home folder.
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
    time.sleep(2)  # Give POX a moment to start listening

    print("  [3/4] Building Topology and connecting to Controller...")
    net = build_net()
    net.start()
    
    print("  [4/4] Waiting for Flow Rules to be installed...")
    time.sleep(5)  # Crucial: switches need time to receive rules from controller

    routing_ok = scenario_1_routing(net)
    firewall_ok = scenario_2_firewall(net)
    flows_ok = scenario_3_flow_validation()
    throughput_ok = scenario_4_throughput(net)

    print("\n====== FINAL SUMMARY ======")
    print("  Routing Validation  : {}".format('PASS' if routing_ok else 'FAIL'))
    print("  Firewall Validation : {}".format('PASS' if firewall_ok else 'FAIL'))
    print("  Flow Validation     : {}".format('PASS' if flows_ok else 'FAIL'))
    print("  Throughput Test     : {}".format('PASS' if throughput_ok else 'FAIL'))

    print("\n  Dropping into Mininet CLI for interaction...")
    CLI(net)
    
    print("\n  Shutting down...")
    net.stop()
    pox_process.terminate()