from netops.packet_walk import PUBLIC_IP, packet_walk


def test_internet_walk_goes_up_every_layer_and_is_natted():
    steps = packet_walk("fin-pc-1", "www.example.com")
    order = [s.split()[0] for s in steps]
    assert order == ["DNS", "ARP", "SEND", "ACCESS-1", "DIST-1", "CORE", "EDGE", "INTERNET"]
    assert any("NAT" in s and PUBLIC_IP in s for s in steps)
    assert f"sees the sender as {PUBLIC_IP}" in steps[-1]


def test_cross_subnet_traffic_arps_for_the_gateway():
    arp = next(s for s in packet_walk("fin-pc-1", "finance.corp.local") if s.startswith("ARP"))
    assert "10.10.20.1" in arp and "gateway" in arp


def test_each_router_hop_decrements_ttl():
    steps = packet_walk("fin-pc-1", "www.example.com")
    assert "TTL -> 63" in next(s for s in steps if s.startswith("DIST-1"))
    assert "TTL -> 61" in next(s for s in steps if s.startswith("EDGE"))


def test_internal_traffic_is_never_natted():
    steps = packet_walk("fin-pc-1", "finance.corp.local")
    assert not any("NAT" in s for s in steps)
    assert steps[-1].startswith("fin-srv") and "10.10.20.21" in steps[-1]


def test_same_subnet_traffic_is_only_switched_not_routed():
    steps = packet_walk("eng-srv", "finance.corp.local")
    assert not any("L3" in s for s in steps)
    assert "TTL=64" in next(s for s in steps if s.startswith("SEND"))