"""NUMA/PCIe Topology Detection (Step 5)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(slots=True)
class NUMATopology:
    """NUMA ノードとリソースのマッピング。"""
    cpu_to_numa: Dict[int, int] = field(default_factory=dict)  # logical_core -> numa_node
    gpu_to_numa: Dict[int, int] = field(default_factory=dict)  # gpu_index -> numa_node
    numa_nodes: List[int] = field(default_factory=list)
    cpu_cores_per_numa: Dict[int, int] = field(default_factory=dict)
    
    def get_numa_for_cpu(self, cpu: int) -> Optional[int]:
        return self.cpu_to_numa.get(cpu)
    
    def get_numa_for_gpu(self, gpu: int) -> Optional[int]:
        return self.gpu_to_numa.get(gpu)
    
    def get_cpus_for_numa(self, numa: int) -> List[int]:
        return [c for c, n in self.cpu_to_numa.items() if n == numa]
    
    def get_gpus_for_numa(self, numa: int) -> List[int]:
        return [g for g, n in self.gpu_to_numa.items() if n == numa]


def detect_numa_topology() -> NUMATopology:
    """hwloc (libhwloc) から NUMA トポロジ検出。"""
    try:
        import hwloc
    except ImportError:
        return NUMATopology()  # 空 = 検出失敗
    
    topo = hwloc.Topology()
    result = NUMATopology()
    
    # NUMA ノード列挙
    numa_objs = topo.get_objects_by_type(hwloc.OBJ_NUMANODE)
    result.numa_nodes = [obj.os_index for obj in numa_objs]
    
    # CPU コア -> NUMA マッピング
    pu_objs = topo.get_objects_by_type(hwloc.OBJ_PU)
    for pu in pu_objs:
        numa_ancestor = pu.get_ancestor_by_type(hwloc.OBJ_NUMANODE)
        if numa_ancestor:
            result.cpu_to_numa[pu.os_index] = numa_ancestor.os_index
    
    # GPU -> NUMA マッピング (PCIe 経由)
    # hwloc 2.9+ で GPU オブジェクト対応
    try:
        gpu_objs = topo.get_objects_by_type(hwloc.OBJ_GPU)
        for gpu in gpu_objs:
            numa_ancestor = gpu.get_ancestor_by_type(hwloc.OBJ_NUMANODE)
            if numa_ancestor:
                result.gpu_to_numa[gpu.os_index] = numa_ancestor.os_index
    except AttributeError:
        pass  # GPU オブジェクト未サポート
    
    # NUMA ごとの CPU 数
    for numa in result.numa_nodes:
        result.cpu_cores_per_numa[numa] = len(result.get_cpus_for_numa(numa))
    
    return result


def detect_gpu_numa_py3nvml() -> Dict[int, int]:
    """py3nvml で GPU->NUMA 推定 (PCIe バス情報から)。"""
    try:
        import pynvml
        pynvml.nvmlInit()
    except Exception:
        return {}
    
    gpu_to_numa = {}
    device_count = pynvml.nvmlDeviceGetCount()
    
    for i in range(device_count):
        handle = pynvml.nvmlDeviceGetHandleByIndex(i)
        try:
            pci_info = pynvml.nvmlDeviceGetPciInfo(handle)
            # PCIe ドメイン/バスから NUMA 推定 (Linux: /sys/bus/pci/devices/.../numa_node)
            bus_id = f"{pci_info.domain:04x}:{pci_info.bus:02x}:{pci_info.device:02x}.{pci_info.function}"
            numa_path = f"/sys/bus/pci/devices/{bus_id}/numa_node"
            try:
                with open(numa_path) as f:
                    numa = int(f.read().strip())
                    if numa >= 0:
                        gpu_to_numa[i] = numa
            except Exception:
                pass
        except Exception:
            pass
    
    return gpu_to_numa


__all__ = [
    "NUMATopology",
    "detect_numa_topology",
    "detect_gpu_numa_py3nvml",
]