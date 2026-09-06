"""Unit tests for experiment allocator."""

import pytest

from src.services.experiment_allocator import (
    ExperimentAllocator,
    MultiExperimentAllocator,
    DEFAULT_ALLOCATOR,
    allocate_variant,
)


class TestExperimentAllocator:
    def test_deterministic_allocation(self):
        """Same inputs always produce same variant."""
        allocator = ExperimentAllocator(traffic_fraction=0.5, seed="test")

        v1 = allocator.allocate(123, "literary")
        v2 = allocator.allocate(123, "literary")
        assert v1 == v2

    def test_different_books_different_variants(self):
        """Different book_ids can get different variants."""
        allocator = ExperimentAllocator(traffic_fraction=0.5, seed="test")

        variants = set()
        for book_id in range(100):
            variants.add(allocator.allocate(book_id, "literary"))

        # With 50% traffic, should see both control and experiment
        assert len(variants) >= 2

    def test_traffic_fraction_zero_all_control(self):
        """traffic_fraction=0 puts all in control."""
        allocator = ExperimentAllocator(traffic_fraction=0.0)

        for book_id in range(100):
            variant = allocator.allocate(book_id, "literary")
            assert variant == "literary_v1"  # Control is genre base

    def test_traffic_fraction_one_all_experiment(self):
        """traffic_fraction=1 puts all in experiment (if variants exist)."""
        allocator = ExperimentAllocator(traffic_fraction=1.0)

        for book_id in range(100):
            variant = allocator.allocate(book_id, "literary")
            # Should be experimental variant, not base
            assert variant != "literary_v1"
            assert variant.startswith("literary_")

    def test_unknown_genre_uses_default(self):
        """Unknown genre falls back to default_v1 control."""
        allocator = ExperimentAllocator(traffic_fraction=0.0)

        variant = allocator.allocate(123, "unknown_genre")
        assert variant == "default_v1"

    def test_allocation_info(self):
        """get_allocation_info returns detailed info."""
        allocator = ExperimentAllocator(traffic_fraction=0.1, seed="test")
        info = allocator.get_allocation_info(42, "mystery")

        assert info["book_id"] == 42
        assert info["genre"] == "mystery"
        assert "hash" in info
        assert "bucket" in info
        assert info["experiment_threshold"] == 1000  # 0.1 * 10000
        assert "in_experiment" in info
        assert "allocated_variant" in info

    def test_different_seeds_different_allocations(self):
        """Different seeds produce different allocations (at least for some books)."""
        alloc1 = ExperimentAllocator(traffic_fraction=0.5, seed="seed1")
        alloc2 = ExperimentAllocator(traffic_fraction=0.5, seed="seed2")

        # Check a few books - they should differ for at least some
        different = False
        for book_id in range(10):
            v1 = alloc1.allocate(book_id, "literary")
            v2 = alloc2.allocate(book_id, "literary")
            if v1 != v2:
                different = True
                break
        assert different, "Seeds should produce different allocations for some books"


class TestMultiExperimentAllocator:
    def test_multiple_experiments(self):
        """Can run multiple experiments concurrently."""
        multi = MultiExperimentAllocator()
        multi.add_experiment("exp_a", 1.0, seed="exp_a")  # 100% traffic to force experiment
        multi.add_experiment("exp_b", 1.0, seed="exp_b")

        allocations = multi.allocate(123, "literary")

        assert "exp_a" in allocations
        assert "exp_b" in allocations
        # With 100% traffic, both should be in experiment group
        # Different seeds should give different experimental variants
        assert allocations["exp_a"].startswith("literary_")
        assert allocations["exp_b"].startswith("literary_")

    def test_get_default_allocator(self):
        """get_default_allocator returns first added."""
        multi = MultiExperimentAllocator()
        multi.add_experiment("first", 0.1)
        multi.add_experiment("second", 0.2)

        default = multi.get_default_allocator()
        assert default is multi.experiments["first"]

    def test_empty_multi_returns_default(self):
        """Empty multi allocator returns default 1% allocator."""
        multi = MultiExperimentAllocator()
        default = multi.get_default_allocator()
        assert isinstance(default, ExperimentAllocator)
        assert default.traffic_fraction == 0.01


class TestConvenienceFunction:
    def test_allocate_variant_function(self):
        """Convenience function works."""
        variant = allocate_variant(999, "romance", traffic_fraction=0.0)
        assert variant == "romance_v1"

    def test_allocate_variant_with_experiment(self):
        """Convenience function with experiment traffic for genre with experimental variants."""
        variant = allocate_variant(999, "literary", traffic_fraction=1.0)
        assert variant != "literary_v1"
        assert variant.startswith("literary_")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])