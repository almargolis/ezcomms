import queue

from ezcomms import vnavs_comms


def test_queue_bounded_basic_put_get():
    q = vnavs_comms.QueueBounded(maxsize=10)
    q.put("a")
    q.put("b")
    assert q.get_nowait() == "a"
    assert q.get_nowait() == "b"


def test_queue_bounded_drop_oldest_on_overflow():
    q = vnavs_comms.QueueBounded(maxsize=3)
    q.put("a")
    q.put("b")
    q.put("c")
    q.put("d")  # drops "a"
    assert q.get_nowait() == "b"
    assert q.get_nowait() == "c"
    assert q.get_nowait() == "d"


def test_queue_bounded_drop_count_tracking():
    q = vnavs_comms.QueueBounded(maxsize=2)
    q.put("a")
    q.put("b")
    assert q.drop_count == 0
    q.put("c")  # drops "a"
    assert q.drop_count == 1
    q.put("d")  # drops "b"
    assert q.drop_count == 2


def test_queue_bounded_empty_raises():
    q = vnavs_comms.QueueBounded(maxsize=5)
    try:
        q.get_nowait()
        assert False, "Should have raised queue.Empty"
    except queue.Empty:
        pass


def test_queue_bounded_heavy_overflow():
    """100 messages into size-10 queue: 90 drops, gets start at 90."""
    q = vnavs_comms.QueueBounded(maxsize=10)
    for i in range(100):
        q.put(i)
    assert q.drop_count == 90
    # Remaining items should be 90..99
    for expected in range(90, 100):
        assert q.get_nowait() == expected
    try:
        q.get_nowait()
        assert False, "Should have raised queue.Empty"
    except queue.Empty:
        pass
