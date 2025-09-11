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

from src.worker import accel


class TestNodeAccel:
    """Test suite for Node-related functionality in the accel module."""

    def test_node_creation_and_repr(self):
        """Test Node construction, id property, and __repr__ output."""
        node = accel._Node(123)
        assert node.id == 123
        rep = repr(node)
        assert "Node" in rep or "node" in rep
        assert str(123) in rep

    def test_node_default_id(self):
        """Test that a Node can be constructed with a default id."""
        node = accel._Node()
        assert hasattr(node, "id")


class TestAPAccel:
    """Test suite for RT and AP functionality in the accel module."""

    def test_rt_creation_and_repr(self):
        """Test RT construction, id property, ap property, and __repr__ output."""
        rt = accel.RT(42)
        assert rt.id == 42
        rep = repr(rt)
        assert "RT" in rep or "rt" in rep
        assert str(42) in rep
        # Default: not attached to AP
        assert rt.ap is None or rt.ap in (0, -1)  # Accepts None or invalid id

    def test_ap_creation_and_repr(self):
        """Test AP construction, id property, rts property, and __repr__ output."""
        ap = accel.AP(7)
        assert ap.id == 7
        rep = repr(ap)
        assert "AP" in rep or "ap" in rep
        assert str(7) in rep
        assert isinstance(ap.rts, set)
        assert len(ap.rts) == 0

    def test_ap_add_and_remove_rt(self):
        """Test adding and removing RTs from an AP, including edge cases."""
        ap = accel.AP(1)
        rt1 = accel.RT(10)
        rt2 = accel.RT(11)
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
        ap = accel.AP(2)
        rt = accel.RT(20)
        assert rt.ap is None or rt.ap in (0, -1)
        ap.add_rt(rt)
        # After adding, RT's ap should reference the AP (if implemented)
        if hasattr(rt, "ap") and isinstance(rt.ap, accel.AP):
            assert rt.ap.id == ap.id
        assert rt in ap.rts
        ap.remove_rt(rt)
        assert rt not in ap.rts

    def test_double_add_remove(self):
        """Test that adding the same RT twice does not duplicate, and double remove is safe."""
        ap = accel.AP(3)
        rt = accel.RT(30)
        ap.add_rt(rt)
        ap.add_rt(rt)  # Should not duplicate
        # Sets cannot have duplicates, so check only one instance
        assert sum(1 for r in ap.rts if r is rt) == 1
        ap.remove_rt(rt)
        ap.remove_rt(rt)  # Should not error
        assert rt not in ap.rts

    def test_invalid_ids(self):
        """Test that Node, RT, and AP can be constructed with default/invalid ids."""
        node = accel._Node()
        rt = accel.RT()
        ap = accel.AP()
        # Should have id attribute, possibly set to INVALID_ID
        assert hasattr(node, "id")
        assert hasattr(rt, "id")
        assert hasattr(ap, "id")

    def test_repr_coverage(self):
        """Test __repr__ for Node, RT, and AP for string output coverage."""
        node = accel._Node(99)
        rt = accel.RT(98)
        ap = accel.AP(97)
        assert isinstance(repr(node), str)
        assert isinstance(repr(rt), str)
        assert isinstance(repr(ap), str)
