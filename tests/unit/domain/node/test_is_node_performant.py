from distributedinference.domain.node import is_node_performant


def test_0_0():
    assert not is_node_performant.execute(0, 0)


def test_1_0():
    assert not is_node_performant.execute(1, 0)


def test_0_1():
    assert not is_node_performant.execute(0, 1)
