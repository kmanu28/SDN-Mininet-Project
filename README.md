# SDN Router and Firewall using Mininet and POX

## Problem Statement

This project implements an SDN-based solution using Mininet and a POX controller. It demonstrates:

- Controller–switch interaction through OpenFlow
- Explicit match–action flow rule design
- Static routing for allowed traffic across a multi-switch topology
- Firewall blocking for restricted traffic
- Network validation using `ping`, `iperf`, and flow-table inspection

The access policy enforced by the controller:

| Source | Destination | Policy  |
|--------|-------------|---------|
| h1     | h2          | ALLOWED |
| h1     | h3          | ALLOWED |
| h2     | h3          | BLOCKED |
| h3     | h2          | BLOCKED |

---

## Topology

```text
h1 (10.0.0.1) --- s1 --- s2 --- s3 --- h3 (10.0.0.3)
                           |
                      h2 (10.0.0.2)
```

| Node | Address      | Connected to |
|------|-------------|--------------|
| h1   | 10.0.0.1/24 | s1 port 1    |
| h2   | 10.0.0.2/24 | s2 port 1    |
| h3   | 10.0.0.3/24 | s3 port 1    |
| s1   | —           | h1, s2       |
| s2   | —           | h2, s1, s3   |
| s3   | —           | h3, s2       |

Controller: POX on `127.0.0.1:6633`

---

## How the Controller Works

When a switch connects, the controller immediately installs three layers of flow rules:

1. **Priority 100 — Firewall (DROP)**: Drops all IPv4 traffic between `h2` and `h3` in both directions.
2. **Priority 10 — Static Routes (FORWARD)**: Installs forwarding rules for all allowed host pairs across all switches.
3. **Priority 0 — Table Miss**: Sends any unmatched packet to the controller. Used to forward ARP requests to the correct port.

---

## Repository Files

| File | Description |
|------|-------------|
| `router.py` | POX controller — installs firewall and routing rules |
| `topo.py` | Mininet topology — 3 switches, 3 hosts, remote controller |
| `test.py` | Automated test suite — routing, firewall, flow-table, iperf |
| `screenshots/` | Proof of execution for the final submission |

---

## Setup (Ubuntu)

### 1. Install dependencies

```bash
sudo apt update
sudo apt install -y mininet openvswitch-switch git python3 iperf
```

### 2. Install POX

```bash
git clone https://github.com/noxrepo/pox.git ~/pox
```

### 3. Copy the controller into POX

```bash
cp router.py ~/pox/ext/
```

---

## Running the Project

Open **two terminals**.

### Terminal 1 — Start the POX controller

```bash
cd ~/pox
./pox.py log.level --INFO router
```

Leave this running. You will see switch connection logs and rule installation messages.

### Terminal 2 — Start the Mininet topology

```bash
sudo python3 topo.py
```

This launches the network and drops you into the Mininet CLI.

---

## Manual Verification (inside Mininet CLI)

```bash
# Routing — should succeed (0% packet loss)
h1 ping -c 3 h2
h1 ping -c 3 h3

# Firewall — should fail (100% packet loss)
h2 ping -c 3 h3
h3 ping -c 3 h2

# Throughput
h3 iperf -s &
h1 iperf -t 5 -c 10.0.0.3

# Flow table inspection
sh ovs-ofctl dump-flows s2
```

---

## Automated Testing

With the POX controller running in Terminal 1:

```bash
sudo python3 test.py
```

The script runs 4 scenarios automatically:

1. **Routing** — verifies allowed host pairs reach each other
2. **Firewall** — verifies blocked pairs show 100% packet loss
3. **Flow Table** — inspects switch flow tables for correct rule entries
4. **Throughput** — measures bandwidth with iperf between h1 and h3

After the tests it drops into the Mininet CLI for live demo.

---

## Expected Output

From `ovs-ofctl dump-flows s2`:

```
priority=100,ip,nw_src=10.0.0.2,nw_dst=10.0.0.3  actions=drop
priority=100,ip,nw_src=10.0.0.3,nw_dst=10.0.0.2  actions=drop
priority=10, ip,nw_src=10.0.0.1,nw_dst=10.0.0.3  actions=output:3
priority=10, ip,nw_src=10.0.0.1,nw_dst=10.0.0.2  actions=output:1
...
priority=0   actions=CONTROLLER:65535
```

---

## Cleanup

If Mininet state is stuck after a run:

```bash
sudo mn -c
```

---

## References

- Mininet Walkthrough: http://mininet.org/walkthrough/
- POX Documentation: https://noxrepo.github.io/pox-doc/html/
- OpenFlow 1.0 Specification: https://opennetworking.org/wp-content/uploads/2013/04/openflow-spec-v1.0.0.pdf
