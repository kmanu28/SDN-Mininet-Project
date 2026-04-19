# SDN-Based Network Control using Mininet and POX

## 📌 Problem Statement

The objective of this project is to implement a Software Defined Networking (SDN) solution using Mininet and a POX controller. The system demonstrates controller-switch interaction, flow rule design using match-action principles, and network behavior analysis.

---

## 🧠 Concepts Used

* Software Defined Networking (SDN)
* OpenFlow Protocol
* Match–Action Flow Rules
* Packet-In Event Handling
* Firewall / Access Control

---

## 🏗️ Topology

* 3 Hosts: h1, h2, h3
* 1 Switch: s1
* Remote Controller: POX

---

## ⚙️ Setup Instructions

### 1. Start Controller

```bash
cd ~/cn orange/pox
./pox.py my_controller
```

### 2. Start Mininet

```bash
sudo mn --topo single,3 --controller=remote,ip=127.0.0.1,port=6633 --switch ovsk
```

---

## 🚀 Execution & Testing

### ✅ Test 1: Allowed Communication

```bash
h1 ping -c 5 h2
```

Result: Successful communication

---

### ❌ Test 2: Blocked Communication

```bash
h1 ping -c 5 h3
```

Result: 100% packet loss (blocked)

---

### 📊 Test 3: Throughput (iperf)

```bash
h1 iperf -s &
h2 iperf -c h1
```

Result: Successful bandwidth measurement

---

### 📄 Flow Table

```bash
sudo ovs-ofctl -O OpenFlow10 dump-flows s1
```

---

## 🔥 Functionality

* Learning switch behavior implemented
* Dynamic packet handling using packet_in events
* Firewall rule implemented:

  * Blocks traffic from h1 → h3
* Match–action logic applied using IP-based filtering

---

## 📊 Performance Observation

* Latency measured using ping
* Throughput measured using iperf
* Flow table inspected using ovs-ofctl
* Observed correct forwarding and blocking behavior

---

## 🔍 Validation

* Allowed traffic (h1 → h2) works correctly
* Blocked traffic (h1 → h3) fails as expected
* System behavior remains consistent after restart

---

## 📸 Proof of Execution

Included:

* Ping success (h1 → h2)
* Ping failure (h1 → h3)
* iperf output
* Flow table entries

---

## 📚 References

* Mininet Documentation
* POX Controller Documentation
* OpenFlow Specification

---

## ✅ Conclusion

This project demonstrates SDN-based network control using a centralized controller. It highlights flexible traffic management using match-action rules and dynamic behavior control.
