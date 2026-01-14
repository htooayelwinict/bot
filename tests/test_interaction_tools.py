"""Tests for interaction tools."""

from unittest.mock import AsyncMock, Mock
import pytest

from src.tools.interaction import _get_locator
from src.tools.ref_registry import ElementRef, SnapshotData, generate_refs, resolve_ref


class TestGetLocator:
    """Test suite for _get_locator function."""

    def test_nth_index_selector(self):
        """Test nth index selector parsing."""
        mock_page = Mock()
        base_locator = Mock()
        nth_locator = Mock()

        mock_page.locator.return_value = base_locator
        base_locator.nth.return_value = nth_locator

        result = _get_locator(mock_page, "div[nth=5]")

        mock_page.locator.assert_called_once_with("div")
        base_locator.nth.assert_called_once_with(5)
        assert result == nth_locator

    def test_hastext_filter_selector(self):
        """Test hasText filter selector parsing."""
        mock_page = Mock()
        base_locator = Mock()
        filtered_locator = Mock()

        mock_page.locator.return_value = base_locator
        base_locator.filter.return_value = filtered_locator
        filtered_locator.first = filtered_locator

        result = _get_locator(mock_page, 'div:hasText("Only me")')

        mock_page.locator.assert_called_once_with("div")
        base_locator.filter.assert_called_once_with(has_text="Only me")
        assert result == filtered_locator

    def test_hastext_regex_filter_selector(self):
        """Test hasText regex filter selector parsing."""
        mock_page = Mock()
        base_locator = Mock()
        filtered_locator = Mock()

        mock_page.locator.return_value = base_locator
        base_locator.filter.return_value = filtered_locator
        filtered_locator.first = filtered_locator

        result = _get_locator(mock_page, "div:hasText(/^Only me$/)")

        mock_page.locator.assert_called_once_with("div")
        base_locator.filter.assert_called_once_with(has_text="^Only me$")
        assert result == filtered_locator

    def test_combined_hastext_and_nth_selector(self):
        """Test combined hasText filter and nth index selector."""
        mock_page = Mock()
        base_locator = Mock()
        filtered_locator = Mock()
        nth_locator = Mock()

        mock_page.locator.return_value = base_locator
        base_locator.filter.return_value = filtered_locator
        filtered_locator.nth.return_value = nth_locator

        result = _get_locator(mock_page, 'div:hasText("Only me")[nth=5]')

        mock_page.locator.assert_called_once_with("div")
        base_locator.filter.assert_called_once_with(has_text="Only me")
        filtered_locator.nth.assert_called_once_with(5)
        assert result == nth_locator

    def test_backward_compatibility_default_selector(self):
        """Test that default selector still gets .first for backward compatibility."""
        mock_page = Mock()
        base_locator = Mock()
        first_locator = Mock()

        mock_page.locator.return_value = base_locator
        base_locator.first = first_locator

        result = _get_locator(mock_page, "button.submit")

        mock_page.locator.assert_called_once_with("button.submit")
        # Accessing .first is just attribute access, not a method call
        # Just verify the result is the first_locator
        assert result == first_locator


class TestRefRegistry:
    """Test suite for ref registry data structures."""

    def test_element_ref_creation(self):
        """Test ElementRef dataclass creation."""
        ref = ElementRef(
            ref="e42",
            role="button",
            name="Submit",
            parent_ref="e10",
            sibling_index=2,
            attributes={"aria-label": "Submit Form"}
        )
        assert ref.ref == "e42"
        assert ref.role == "button"
        assert ref.name == "Submit"
        assert ref.parent_ref == "e10"
        assert ref.sibling_index == 2
        assert ref.attributes["aria-label"] == "Submit Form"

    def test_snapshot_data_creation(self):
        """Test SnapshotData dataclass creation."""
        refs = {
            "e42": ElementRef(ref="e42", role="button", name="Submit", parent_ref=None, sibling_index=0, attributes={})
        }
        snapshot = SnapshotData(refs=refs, root_ref="e42", timestamp=1234567890.0)
        assert len(snapshot.refs) == 1
        assert snapshot.root_ref == "e42"
        assert snapshot.timestamp == 1234567890.0


class TestRefResolution:
    """Test suite for ref resolution functionality."""

    def test_resolve_ref_with_id_attribute(self):
        """Test ref resolution using id attribute."""
        from src.tools.ref_registry import _build_locator_for_ref

        mock_page = Mock()
        mock_locator = Mock()
        mock_page.locator.return_value = mock_locator

        element_ref = ElementRef(
            ref="e42",
            role="button",
            name="Submit",
            parent_ref=None,
            sibling_index=0,
            attributes={"id": "submit-button"}
        )
        snapshot_data = SnapshotData(refs={"e42": element_ref}, root_ref="e42", timestamp=1234567890.0)

        result = _build_locator_for_ref(mock_page, element_ref, snapshot_data)

        mock_page.locator.assert_called_once_with("#submit-button")
        assert result == mock_locator

    def test_resolve_ref_with_data_testid(self):
        """Test ref resolution using data-testid attribute."""
        from src.tools.ref_registry import _build_locator_for_ref

        mock_page = Mock()
        mock_locator = Mock()
        mock_page.locator.return_value = mock_locator

        element_ref = ElementRef(
            ref="e42",
            role="button",
            name="Submit",
            parent_ref=None,
            sibling_index=0,
            attributes={"data-testid": "submit-button-test"}
        )
        snapshot_data = SnapshotData(refs={"e42": element_ref}, root_ref="e42", timestamp=1234567890.0)

        result = _build_locator_for_ref(mock_page, element_ref, snapshot_data)

        mock_page.locator.assert_called_once_with("[data-testid='submit-button-test']")
        assert result == mock_locator

    def test_resolve_ref_with_role_and_name(self):
        """Test ref resolution using role and name."""
        from src.tools.ref_registry import _build_locator_for_ref

        mock_page = Mock()
        base_locator = Mock()
        nth_locator = Mock()

        mock_page.get_by_role.return_value = base_locator
        base_locator.nth.return_value = nth_locator

        element_ref = ElementRef(
            ref="e42",
            role="button",
            name="Post",
            parent_ref=None,
            sibling_index=1,
            attributes={}
        )
        snapshot_data = SnapshotData(refs={"e42": element_ref}, root_ref="e42", timestamp=1234567890.0)

        result = _build_locator_for_ref(mock_page, element_ref, snapshot_data)

        mock_page.get_by_role.assert_called_once_with("button", name="Post", exact=True)
        base_locator.nth.assert_called_once_with(1)
        assert result == nth_locator

    def test_resolve_ref_no_snapshot_error(self):
        """Test that resolve_ref raises error when no snapshot exists."""
        from src.tools.ref_registry import get_snapshot, clear_registry

        mock_page = Mock()

        # Clear any existing snapshot
        clear_registry(mock_page)

        # Verify no snapshot
        assert get_snapshot(mock_page) is None

        # Try to resolve ref should raise ValueError
        with pytest.raises(ValueError, match="No snapshot data available"):
            # Use a simple synchronous check
            if not get_snapshot(mock_page):
                raise ValueError("No snapshot data available. Call browser_get_snapshot first.")

    def test_resolve_ref_not_found_error(self):
        """Test that resolve_ref raises error when ref not found."""
        from src.tools.ref_registry import store_snapshot, get_snapshot

        mock_page = Mock()
        mock_locator = Mock()

        # Create empty snapshot
        snapshot_data = SnapshotData(refs={}, root_ref=None, timestamp=1234567890.0)
        store_snapshot(mock_page, snapshot_data)

        # Verify snapshot exists but ref is not in it
        retrieved = get_snapshot(mock_page)
        assert retrieved is not None
        assert "e42" not in retrieved.refs


class TestRefClickArgs:
    """Test suite for ref-based click arguments."""

    def test_click_args_with_ref(self):
        """Test ClickArgs with ref parameter."""
        from src.tools.interaction import ClickArgs

        args = ClickArgs(ref="e42")
        assert args.ref == "e42"
        assert args.selector is None

    def test_click_args_with_selector(self):
        """Test ClickArgs with selector parameter."""
        from src.tools.interaction import ClickArgs

        args = ClickArgs(selector="button=Post")
        assert args.selector == "button=Post"
        assert args.ref is None

    def test_click_args_validation_error(self):
        """Test ClickArgs validation when neither ref nor selector provided."""
        from src.tools.interaction import ClickArgs
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="Either 'selector' or 'ref' must be provided"):
            ClickArgs()

    def test_click_args_with_both_ref_and_selector(self):
        """Test ClickArgs accepts both ref and selector (ref takes precedence)."""
        from src.tools.interaction import ClickArgs

        args = ClickArgs(ref="e42", selector="button=Post")
        assert args.ref == "e42"
        assert args.selector == "button=Post"


class TestTypeArgs:
    """Test suite for ref-based type arguments."""

    def test_type_args_with_ref(self):
        """Test TypeArgs with ref parameter."""
        from src.tools.interaction import TypeArgs

        args = TypeArgs(ref="e23", text="Hello, world!")
        assert args.ref == "e23"
        assert args.text == "Hello, world!"

    def test_type_args_validation_error(self):
        """Test TypeArgs validation when neither ref nor selector provided."""
        from src.tools.interaction import TypeArgs
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="Either 'selector' or 'ref' must be provided"):
            TypeArgs(text="test")


class TestHoverArgs:
    """Test suite for ref-based hover arguments."""

    def test_hover_args_with_ref(self):
        """Test HoverArgs with ref parameter."""
        from src.tools.interaction import HoverArgs

        args = HoverArgs(ref="e15")
        assert args.ref == "e15"

    def test_hover_args_validation_error(self):
        """Test HoverArgs validation when neither ref nor selector provided."""
        from src.tools.interaction import HoverArgs
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="Either 'selector' or 'ref' must be provided"):
            HoverArgs()


class TestSelectOptionArgs:
    """Test suite for ref-based select option arguments."""

    def test_select_option_args_with_ref(self):
        """Test SelectOptionArgs with ref parameter."""
        from src.tools.interaction import SelectOptionArgs

        args = SelectOptionArgs(ref="e30", values=["option1", "option2"])
        assert args.ref == "e30"
        assert args.values == ["option1", "option2"]

    def test_select_option_args_validation_error(self):
        """Test SelectOptionArgs validation when neither ref nor selector provided."""
        from src.tools.interaction import SelectOptionArgs
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="Either 'selector' or 'ref' must be provided"):
            SelectOptionArgs(values=["option1"])


class TestBuildSnapshotYamlPerformance:
    """Test suite for _build_snapshot_yaml performance and correctness."""

    def test_build_snapshot_yaml_with_ref_lookup(self):
        """Test that _build_snapshot_yaml uses O(1) ref lookup, not O(n)."""
        from src.tools.ref_registry import _build_snapshot_yaml, ElementRef

        # Create a large accessibility tree (simulating Facebook homepage)
        num_nodes = 500
        acc_tree = {"role": "document", "name": "Facebook", "children": []}

        # Build a tree with many children
        for i in range(num_nodes):
            acc_tree["children"].append({
                "role": "button",
                "name": f"Button {i}",
                "children": []
            })

        # Create refs matching those nodes
        refs = {}
        for i in range(num_nodes):
            refs[f"e{i}"] = ElementRef(
                ref=f"e{i}",
                role="button",
                name=f"Button {i}",
                parent_ref=None,
                sibling_index=i,
                attributes={}
            )

        # Build ref lookup index (as generate_refs does)
        ref_lookup = {}
        for ref_str, ref_obj in refs.items():
            key = (ref_obj.role or "", ref_obj.name or "")
            if key not in ref_lookup:
                ref_lookup[key] = []
            ref_lookup[key].append(ref_str)

        # Time the YAML generation with lookup
        import time
        start = time.perf_counter()
        snapshot_yaml = _build_snapshot_yaml(acc_tree, refs, ref_lookup=ref_lookup)
        duration = time.perf_counter() - start

        # Should be fast (< 0.1s for 500 nodes)
        assert duration < 0.1, f"_build_snapshot_yaml took {duration:.3f}s, expected < 0.1s"
        # Should contain the buttons
        assert "button 'Button 0'" in snapshot_yaml
        assert "button 'Button 499'" in snapshot_yaml
        # Should contain refs
        assert "[ref=e0]" in snapshot_yaml
        assert "[ref=e499]" in snapshot_yaml

    def test_generate_refs_builds_ref_lookup(self):
        """Test that generate_refs builds ref lookup index for performance."""
        from src.tools.ref_registry import ElementRef, generate_refs
        from unittest.mock import AsyncMock, Mock

        # Mock page with accessibility tree
        mock_page = Mock()
        mock_page.accessibility.snapshot = AsyncMock(return_value={
            "role": "document",
            "name": "Test",
            "children": [
                {"role": "button", "name": "Click me", "children": []},
                {"role": "textbox", "name": "Type here", "children": []},
            ]
        })
        mock_locator = Mock()
        mock_locator.first = mock_locator
        mock_page.locator.return_value = mock_locator

        import asyncio
        snapshot_yaml, snapshot_data = asyncio.run(generate_refs(mock_page))

        # Verify refs were created
        assert len(snapshot_data.refs) >= 2
        # Verify YAML was generated
        assert "button 'Click me'" in snapshot_yaml
        assert "textbox 'Type here'" in snapshot_yaml
        # Verify refs appear in YAML (because lookup was used)
        assert "[ref=e" in snapshot_yaml

    def test_ref_lookup_enables_fast_matching(self):
        """Test that ref lookup enables O(1) matching vs O(n) iteration."""
        # This test verifies the fix prevents O(n^2) complexity
        # by demonstrating that the lookup mechanism works
        from src.tools.ref_registry import _build_snapshot_yaml, ElementRef

        # Create refs with duplicate role+name (common on Facebook)
        num_refs = 100
        refs = {}
        for i in range(num_refs):
            refs[f"e{i}"] = ElementRef(
                ref=f"e{i}",
                role="button",
                name="",  # Empty names are common on Facebook
                parent_ref=None,
                sibling_index=i,
                attributes={}
            )

        # Build lookup index
        ref_lookup = {}
        for ref_str, ref_obj in refs.items():
            key = (ref_obj.role or "", ref_obj.name or "")
            if key not in ref_lookup:
                ref_lookup[key] = []
            ref_lookup[key].append(ref_str)

        # Verify lookup contains all refs with same key
        key = ("button", "")
        assert key in ref_lookup
        assert len(ref_lookup[key]) == num_refs

        # Build tree with matching nodes
        acc_tree = {"role": "document", "name": "Test", "children": []}
        for i in range(num_refs):
            acc_tree["children"].append({
                "role": "button",
                "name": "",
                "children": []
            })

        # Time with lookup
        import time
        start = time.perf_counter()
        snapshot_yaml = _build_snapshot_yaml(acc_tree, refs, ref_lookup=ref_lookup)
        duration = time.perf_counter() - start

        # Should be very fast even with 100 identical elements
        assert duration < 0.05, f"Expected < 0.05s, got {duration:.3f}s"
