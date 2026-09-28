from netops.policy import ACL, Rule, evaluate


def test_departments_reach_only_their_own_server():
    assert evaluate("fin-pc-1", "fin-srv", 443).action == "ALLOW"
    assert evaluate("eng-pc-1", "eng-srv", 443).action == "ALLOW"
    assert evaluate("hr-pc-1", "hr-srv", 443).action == "ALLOW"
    assert evaluate("eng-pc-1", "fin-srv", 443).action == "DENY"


def test_guest_gets_internet_but_nothing_internal():
    assert evaluate("guest-1", "internet", 443).action == "ALLOW"
    v = evaluate("guest-1", "fin-srv", 443)
    assert (v.action, v.rule) == ("DENY", "guest-no-internal")


def test_iot_camera_cannot_reach_finance():
    v = evaluate("iot-cam-1", "fin-srv", 445)
    assert (v.action, v.rule) == ("DENY", "iot-no-internal")


def test_anything_not_allowed_hits_the_implicit_deny():
    assert evaluate("iot-cam-1", "internet", 443).rule == "implicit deny"
    assert evaluate("fin-pc-1", "fin-srv", 22).rule == "implicit deny"   # right server, wrong port


def test_first_match_wins_so_rule_order_matters():
    too_broad_first = [Rule("allow-everything", "ALLOW", ("any",), "any")] + ACL
    assert evaluate("guest-1", "fin-srv", 443, acl=too_broad_first).action == "ALLOW"


def test_same_vlan_traffic_bypasses_the_gateway_acl():
    v = evaluate("eng-srv", "fin-srv", 445)
    assert v.enforced_at.startswith("NOT INSPECTED")