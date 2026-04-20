# Hybrid SDN Router and Firewall using POX

## Problem Statement
This project implements an SDN-based solution using Mininet and a POX controller for the assignment rubric. It demonstrates:

- controller-switch interaction through OpenFlow
- explicit match-action flow rules
- routing for allowed traffic
- firewall blocking for restricted traffic
- network validation using `ping`, `iperf`, and flow-table inspection

The policy enforced by the controller is:

- allow `h1 <-> h2`
- allow `h1 <-> h3`
- block `h2 <-> h3`

## Topology

Hosts:

- `h1` - `10.0.0.1/24`
- `h2` - `10.0.0.2/24`
- `h3` - `10.0.0.3/24`

Switches:

- `s1`
- `s2`
- `s3`

Controller:

- POX on `127.0.0.1:6633`

```text
h1 --- s1 --- s2 --- s3 --- h3
               |
              h2
```

## Repository Files

- `router.py` - POX controller module
- `topo.py` - Mininet topology launcher
- `test.py` - automated validation script
- `screenshots/` - proof of execution for the final submission

## How the Controller Works

The controller installs three types of rules:

1. `priority=100` firewall rules to drop blocked IPv4 traffic between `h2` and `h3`
2. `priority=10` static routing rules for allowed traffic
3. `priority=0` table-miss rules that send unmatched packets to the controller

ARP traffic is handled in `packet_in` so the controller can forward requests to the correct switch port without unnecessary flooding.

## Ubuntu Setup

### 1. Install dependencies

```bash
sudo apt update
sudo apt install -y mininet openvswitch-switch git python3 iperf
```

### 2. Install POX

```bash
git clone https://github.com/noxrepo/pox.git ~/pox
```

### 3. Copy the controller module into POX

From this repository directory:

```bash
cp router.py ~/pox/ext/
```

## How to Run

Open two terminals on Ubuntu.

### Terminal 1: start the controller

```bash
cd ~/pox
./pox.py log.level --INFO router
```

### Terminal 2: start the topology

From this repository directory:

```bash
sudo python3 topo.py
```

This opens the Mininet CLI after the network starts.

## Manual Verification Commands

Run these commands in the Mininet CLI:

```bash
h1 ping -c 3 h2
h1 ping -c 3 h3
h2 ping -c 3 h3
h3 ping -c 3 h2
h3 iperf -s &
h1 iperf -t 5 -c 10.0.0.3
sh ovs-ofctl dump-flows s2
```

Expected results:

- `h1 -> h2` succeeds
- `h1 -> h3` succeeds
- `h2 -> h3` fails
- `h3 -> h2` fails
- `iperf` between `h1` and `h3` reports throughput
- `dump-flows` on `s2` shows both routing and firewall entries

## Automated Testing

Start the POX controller first, then run:

```bash
sudo python3 test.py
```

The script checks:

- allowed routing paths
- blocked firewall paths
- expected flow-table entries
- throughput measurement with `iperf`

## Expected Output

When the project is running correctly:

- POX logs switch connections for `s1`, `s2`, and `s3`
- POX installs drop rules for `10.0.0.2 <-> 10.0.0.3`
- allowed host pairs show `0% packet loss`
- blocked host pairs show `100% packet loss`
- `ovs-ofctl dump-flows s2` contains both route matches and firewall matches

## Proof of Execution

The `screenshots/` directory contains:

- successful ping results
- blocked ping results
- flow-table output
- `iperf` throughput output

These screenshots can be referenced in the final GitHub submission.

## Cleanup

If Mininet state remains after a run:

```bash
sudo mn -c
```

## References

- Mininet walkthrough: http://mininet.org/walkthrough/
- POX documentation: https://noxrepo.github.io/pox-doc/html/
- OpenFlow 1.0 specification