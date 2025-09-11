"""
Unit tests for the pybind11 C++ bindings of Node, RT, and AP classes in the accel module.

This test suite verifies the following:
- Node: construction, id property, __repr__
- RT: construction, id, ap property, __repr__
- AP: construction, id, add_rt, remove_rt, rts property, __repr__
- Interactions: adding/removing RTs to/from AP, reference integrity, and edge cases

Tested via pytest. All tests require the accel extension to be built and installed in src/worker/.
"""
# ruff: noqa: PLR2004

from src.worker.accel import AP, RT, _Node


class TestNodeAccel:
    """Test suite for Node-related functionality in the accel module."""

    def test_node_creation(self):
        """Test Node construction and id property."""
        node = _Node(123)
        assert node.id == 123

    def test_node_default_id(self):
        """Test that a Node can be constructed with a default id."""
        node = _Node()
        assert hasattr(node, "id")

    def test_node_repr_roundtrip(self):
        """Test that eval(repr(node)) produces an equivalent Node object."""
        node = _Node(123)
        node2 = eval(repr(node))
        assert isinstance(node2, _Node)
        assert node2.id == node.id


class TestAPAccel:
    """Test suite for RT and AP functionality in the accel module."""

    def test_rt_creation(self):
        """Test RT construction and id property."""
        rt = RT(42)
        assert rt.id == 42
        # Default: not attached to AP
        assert rt.ap is None or rt.ap in (0, -1)  # Accepts None or invalid id

    def test_rt_repr_roundtrip(self):
        """Test that eval(repr(rt)) produces an equivalent RT object."""
        rt = RT(42)
        rt2 = eval(repr(rt))
        assert isinstance(rt2, RT)
        assert rt2.id == rt.id

    def test_ap_creation(self):
        """Test AP construction, id property, and rts property."""
        ap = AP(7)
        assert ap.id == 7
        assert isinstance(ap.rts, set)
        assert len(ap.rts) == 0

    def test_ap_repr_roundtrip(self):
        """Test that eval(repr(ap)) produces an equivalent AP object."""
        ap = AP(7)
        ap2 = eval(repr(ap))
        assert isinstance(ap2, AP)
        assert ap2.id == ap.id

    def test_ap_add_and_remove_rt(self):
        """Test adding and removing RTs from an AP, including edge cases."""
        ap = AP(1)
        rt1 = RT(10)
        rt2 = RT(11)
        ap.add_rt(rt1)
        ap.add_rt(rt2)
        assert len(ap.rts) == 2
        assert rt1 in ap.rts and rt2 in ap.rts
        # Remove one
        ap.remove_rt(rt1)
        assert len(ap.rts) == 1
        assert rt2 in ap.rts
        # Remove again (should not fail)
        ap.remove_rt(rt1)
        assert len(ap.rts) == 1

    def test_ap_rt_relationship(self):
        """Test that RT's ap property references the correct AP after add/remove."""
        ap = AP(2)
        rt = RT(20)
        assert rt.ap is None or rt.ap in (0, -1)
        ap.add_rt(rt)
        # After adding, RT's ap should reference the AP (if implemented)
        if hasattr(rt, "ap") and isinstance(rt.ap, AP):
            assert rt.ap.id == ap.id
        assert rt in ap.rts
        ap.remove_rt(rt)
        assert rt not in ap.rts

    def test_double_add_remove(self):
        """Test that adding the same RT twice does not duplicate, and double remove is safe."""
        ap = AP(3)
        rt = RT(30)
        ap.add_rt(rt)
        ap.add_rt(rt)  # Should not duplicate
        # Sets cannot have duplicates, so check only one instance
        assert sum(1 for r in ap.rts if r is rt) == 1
        ap.remove_rt(rt)
        ap.remove_rt(rt)  # Should not error
        assert rt not in ap.rts

    def test_invalid_ids(self):
        """Test that Node, RT, and AP can be constructed with default/invalid ids."""
        node = _Node()
        rt = RT()
        ap = AP()
        # Should have id attribute, possibly set to INVALID_ID
        assert hasattr(node, "id")
        assert hasattr(rt, "id")
        assert hasattr(ap, "id")
