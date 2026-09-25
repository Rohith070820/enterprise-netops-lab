import ipaddress


def test_dependencies_import():
    import networkx, pandas, plotly, streamlit  # noqa: F401


def test_package_imports():
    import netops
    assert netops.__version__ == "0.1.0"


def test_ip_math_is_real():
    # VLAN 10 (Engineering) uses 10.10.10.0/24; the gateway is the first usable host.
    eng = ipaddress.ip_network("10.10.10.0/24")
    assert eng.num_addresses == 256
    assert str(next(eng.hosts())) == "10.10.10.1"
    assert ipaddress.ip_address("10.10.20.5") not in eng
