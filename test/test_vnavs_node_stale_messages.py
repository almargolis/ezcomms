import json
import time

from ezcomms import vnavs_node as vmqtt
from ezcomms import vnavs_mqtt_clients


# --- Helper to create a VnavsNode without connecting to a broker ---


def _make_node(subscriptions):
    """Create a VnavsNode via object.__new__ with minimal setup."""
    node = object.__new__(vmqtt.VnavsNode)
    node._last_send_times = {}
    node.confirmation_pending = {}
    node.subscriptions = {}
    node.verbose = False
    for sub in subscriptions:
        node.subscriptions[sub.topic] = sub
    return node


def _make_message(topic, payload_dict):
    """Create a FastMqttMessage with JSON-encoded payload."""
    return vnavs_mqtt_clients.FastMqttMessage(
        topic=topic,
        payload=json.dumps(payload_dict),
    )


# --- Synchronous (last_payload) tests ---


def test_stale_sync_message_not_stored():
    """Stale message should NOT be stored as last_payload."""
    sub = vmqtt.Subscription("test/topic", stale_threshold=5.0)
    node = _make_node([sub])
    payload = {"data": "old", "_sendTime": time.time() - 10.0, "_sender": "s"}
    msg = _make_message("test/topic", payload)
    node.on_message(None, None, msg)
    assert sub.last_payload is None


def test_fresh_sync_message_stored():
    """Fresh message should be stored as last_payload."""
    sub = vmqtt.Subscription("test/topic", stale_threshold=5.0)
    node = _make_node([sub])
    payload = {"data": "new", "_sendTime": time.time() - 1.0, "_sender": "s"}
    msg = _make_message("test/topic", payload)
    node.on_message(None, None, msg)
    assert sub.last_payload is not None
    assert sub.last_payload["data"] == "new"


# --- Async (handler) tests ---


def test_stale_async_message_handler_not_invoked():
    """Stale message should NOT invoke async handler."""
    received = []
    sub = vmqtt.Subscription(
        "test/async",
        handler=lambda p: received.append(p),
        async_delivery=True,
        stale_threshold=5.0,
    )
    node = _make_node([sub])
    payload = {"_sendTime": time.time() - 20.0, "_sender": "s"}
    msg = _make_message("test/async", payload)
    node.on_message(None, None, msg)
    assert len(received) == 0


def test_fresh_async_message_handler_invoked():
    """Fresh message should invoke async handler."""
    received = []
    sub = vmqtt.Subscription(
        "test/async",
        handler=lambda p: received.append(p),
        async_delivery=True,
        stale_threshold=5.0,
    )
    node = _make_node([sub])
    payload = {"val": 42, "_sendTime": time.time() - 0.5, "_sender": "s"}
    msg = _make_message("test/async", payload)
    node.on_message(None, None, msg)
    assert len(received) == 1
    assert received[0]["val"] == 42


# --- No _sendTime (backward compat) ---


def test_no_sendtime_always_delivered():
    """Messages without _sendTime should always be delivered."""
    sub = vmqtt.Subscription("test/topic", stale_threshold=5.0)
    node = _make_node([sub])
    payload = {"data": "compat"}
    msg = _make_message("test/topic", payload)
    node.on_message(None, None, msg)
    assert sub.last_payload is not None
    assert sub.last_payload["data"] == "compat"


# --- stale_threshold=None disables check ---


def test_stale_threshold_none_skips_check():
    """stale_threshold=None means staleness check is skipped."""
    sub = vmqtt.Subscription("test/topic", stale_threshold=None)
    node = _make_node([sub])
    # Very old message should still be delivered
    payload = {"data": "ancient", "_sendTime": time.time() - 9999.0, "_sender": "s"}
    msg = _make_message("test/topic", payload)
    node.on_message(None, None, msg)
    assert sub.last_payload is not None
    assert sub.last_payload["data"] == "ancient"


# --- Future message rejection ---


def test_future_message_rejected():
    """Message with _sendTime >2s in the future should be rejected."""
    sub = vmqtt.Subscription("test/topic", stale_threshold=5.0)
    node = _make_node([sub])
    payload = {"data": "future", "_sendTime": time.time() + 10.0, "_sender": "s"}
    msg = _make_message("test/topic", payload)
    node.on_message(None, None, msg)
    assert sub.last_payload is None


def test_slightly_future_message_accepted():
    """Message with _sendTime <2s in the future should be accepted."""
    sub = vmqtt.Subscription("test/topic", stale_threshold=5.0)
    node = _make_node([sub])
    payload = {"data": "ok", "_sendTime": time.time() + 1.0, "_sender": "s"}
    msg = _make_message("test/topic", payload)
    node.on_message(None, None, msg)
    assert sub.last_payload is not None
    assert sub.last_payload["data"] == "ok"


# --- Per-subscription threshold ---


def test_per_subscription_threshold():
    """Different topics can have different stale_threshold values."""
    sub_fast = vmqtt.Subscription("fast/topic", stale_threshold=2.0)
    sub_slow = vmqtt.Subscription("slow/topic", stale_threshold=30.0)
    node = _make_node([sub_fast, sub_slow])

    # 5s old message: stale for fast (threshold=2), fresh for slow (threshold=30)
    send_time = time.time() - 5.0
    msg_fast = _make_message(
        "fast/topic", {"_sendTime": send_time, "_sender": "s"}
    )
    msg_slow = _make_message(
        "slow/topic", {"_sendTime": send_time, "_sender": "s"}
    )
    node.on_message(None, None, msg_fast)
    node.on_message(None, None, msg_slow)

    assert sub_fast.last_payload is None  # rejected
    assert sub_slow.last_payload is not None  # accepted


# --- Boundary test ---


def test_boundary_just_past_threshold_rejected():
    """Message just past stale_threshold should be rejected."""
    sub = vmqtt.Subscription("test/topic", stale_threshold=5.0)
    node = _make_node([sub])
    payload = {"_sendTime": time.time() - 5.01, "_sender": "s"}
    msg = _make_message("test/topic", payload)
    node.on_message(None, None, msg)
    assert sub.last_payload is None


def test_boundary_just_under_threshold_accepted():
    """Message just under stale_threshold should be accepted."""
    sub = vmqtt.Subscription("test/topic", stale_threshold=5.0)
    node = _make_node([sub])
    payload = {"data": "ok", "_sendTime": time.time() - 4.9, "_sender": "s"}
    msg = _make_message("test/topic", payload)
    node.on_message(None, None, msg)
    assert sub.last_payload is not None


# --- Clock-skew tracking ---


def test_clock_jump_warning(capsys):
    """CLOCK JUMP warning printed when consecutive _sendTime jumps >60s."""
    sub = vmqtt.Subscription("test/topic", stale_threshold=None)
    node = _make_node([sub])
    now = time.time()
    # First message from sender
    msg1 = _make_message("test/topic", {"_sendTime": now, "_sender": "cam"})
    node.on_message(None, None, msg1)
    # Second message with >60s jump
    msg2 = _make_message(
        "test/topic", {"_sendTime": now + 100.0, "_sender": "cam"}
    )
    node.on_message(None, None, msg2)
    assert "CLOCK JUMP" in capsys.readouterr().out


def test_no_clock_jump_for_normal_progression(capsys):
    """No CLOCK JUMP warning for normal time progression."""
    sub = vmqtt.Subscription("test/topic", stale_threshold=None)
    node = _make_node([sub])
    now = time.time()
    msg1 = _make_message("test/topic", {"_sendTime": now, "_sender": "cam"})
    node.on_message(None, None, msg1)
    msg2 = _make_message(
        "test/topic", {"_sendTime": now + 5.0, "_sender": "cam"}
    )
    node.on_message(None, None, msg2)
    assert "CLOCK JUMP" not in capsys.readouterr().out
