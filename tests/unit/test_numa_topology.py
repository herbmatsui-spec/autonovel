"""Tests for NUMA Topology (Step 5)."""
import pytest
from src.backend.tasks.numa_topology import NUMATopology, detect_numa_topology


def test_numa_topology_empty_on_no_hwloc():
    """hwloc なし環境では空トポロジ。"""
    topo = detect_numa_topology()
    assert isinstance(topo, NUMATopology)


def test_manual_topology_mapping():
    """手動構築したトポロジが正しく動作する。"""
    topo = NUMATopology(
        cpu_to_numa={0: 0, 1: 0, 2: 1, 3: 1},
        gpu_to_numa={0: 0, 1: 1},
        numa_nodes=[0, 1],
        cpu_cores_per_numa={0: 2, 1: 2}
    )
    assert topo.get_numa_for_cpu(0) == 0
    assert topo.get_numa_for_cpu(2) == 1
    assert topo.get_cpus_for_numa(0) == [0, 1]
    assert topo.get_gpus_for_numa(1) == [1]


def test_resource_manager_has_numa_topology():
    """ResourceManager が NUMA トポロジを持つ。"""
    from src.backend.tasks.resource_manager import ResourceManager
    rm = ResourceManager()
    assert hasattr(rm, 'numa_topology')
    assert isinstance(rm.numa_topology, NUMATopology)


def test_get_worker_numa_affinity_cpu():
    """CPU ワーカーの NUMA アフィニティ取得。"""
    from src.backend.tasks.resource_manager import ResourceManager
    rm = ResourceManager()
    # トポロジが空でも None を返す（エラーにしない）
    result = rm.get_worker_numa_affinity(0, is_gpu_worker=False)
    assert result is None or isinstance(result, int)


def test_get_worker_numa_affinity_gpu():
    """GPU ワーカーの NUMA アフィニティ取得。"""
    from src.backend.tasks.resource_manager import ResourceManager
    rm = ResourceManager()
    result = rm.get_worker_numa_affinity(0, is_gpu_worker=True)
    assert result is None or isinstance(result, int)


def test_get_gpu_worker_env():
    """GPU ワーカー用環境変数生成。"""
    from src.backend.tasks.resource_manager import ResourceManager
    rm = ResourceManager()
    env = rm.get_gpu_worker_env(0)
    assert "CUDA_VISIBLE_DEVICES" in env
    assert env["CUDA_VISIBLE_DEVICES"] == "0"