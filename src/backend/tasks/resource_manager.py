"""System Resource Monitoring and Dynamic Worker Pool Sizing (Step 37)."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from src.backend.tasks.dag_models import TaskResourceRequirement
from src.backend.tasks.numa_topology import NUMATopology, detect_numa_topology, detect_gpu_numa_py3nvml

logger = logging.getLogger(__name__)

try:
    import psutil
except Exception:
    psutil = None

try:
    import torch
except Exception:
    torch = None


class ResourceManager:
    """Monitors system CPU, RAM, and GPU resources to dynamically size task workers."""

    def __init__(
        self,
        max_cpu_ratio: float = 0.8,
        max_ram_ratio: float = 0.8,
        default_gpu_vram_mb: int = 4096,
        numa_topology: NUMATopology | None = None,
    ) -> None:
        self.max_cpu_ratio = max_cpu_ratio
        self.max_ram_ratio = max_ram_ratio
        self.default_gpu_vram_mb = default_gpu_vram_mb

        # NUMA topology (Step 5)
        self.numa_topology = numa_topology or detect_numa_topology()
        # py3nvml で GPU 補完
        if not self.numa_topology.gpu_to_numa:
            gpu_numa = detect_gpu_numa_py3nvml()
            self.numa_topology.gpu_to_numa.update(gpu_numa)

    def get_cpu_cores(self) -> float:
        """Get total available CPU cores."""
        return float(os.cpu_count() or 4)

    def get_available_ram_mb(self) -> int:
        """Get available physical memory in MB."""
        if psutil is not None:
            try:
                mem = psutil.virtual_memory()
                return int(mem.available / (1024 * 1024))
            except Exception as e:
                logger.debug(f"psutil memory check failed: {e}")
        return 4096  # 4GB fallback

    def get_gpu_vram_mb(self) -> int:
        """Get available GPU VRAM in MB if PyTorch CUDA is enabled."""
        if torch is not None:
            try:
                if torch.cuda.is_available():
                    device = torch.cuda.current_device()
                    free_bytes, total_bytes = torch.cuda.mem_get_info(device)
                    return int(free_bytes / (1024 * 1024))
            except Exception as e:
                logger.debug(f"PyTorch CUDA check failed: {e}")
        return 0

    def get_available_resources(self) -> TaskResourceRequirement:
        """Return snapshot of current available resources."""
        return TaskResourceRequirement(
            cpu_cores=round(self.get_cpu_cores() * self.max_cpu_ratio, 1),
            ram_mb=int(self.get_available_ram_mb() * self.max_ram_ratio),
            gpu_mem_mb=self.get_gpu_vram_mb(),
        )

    def calculate_worker_pool_limits(self) -> dict[str, int]:
        """Calculate dynamic concurrency limits for LLM and Image generation workers."""
        cores = self.get_cpu_cores()
        ram_mb = self.get_available_ram_mb()
        gpu_mb = self.get_gpu_vram_mb()

        # LLMワーカー: CPUコア数の80%（最小1、最大16）
        llm_workers = max(1, min(16, int(cores * self.max_cpu_ratio)))

        # 画像生成ワーカー: GPU VRAMがあれば 4GBごとに1ワーカー、無ければCPUベースで最大2
        if gpu_mb >= 2048:
            image_workers = max(1, min(4, int(gpu_mb / 3000)))
        else:
            image_workers = max(1, min(2, int(cores / 4)))

        # RAM制限によるクリッピング (1タスクあたり最低500MB必要と仮定)
        max_by_ram = max(1, int(ram_mb / 500))
        llm_workers = min(llm_workers, max_by_ram)

        return {
            "llm_workers": llm_workers,
            "image_workers": image_workers,
            "max_parallel_tasks": llm_workers + image_workers,
        }

    def can_schedule(
        self,
        task_req: TaskResourceRequirement,
        active_allocations: TaskResourceRequirement,
    ) -> bool:
        """Check if a new task's resource requirement can fit into remaining system limits."""
        available = self.get_available_resources()
        if (active_allocations.cpu_cores + task_req.cpu_cores) > available.cpu_cores:
            return False
        if (active_allocations.ram_mb + task_req.ram_mb) > available.ram_mb:
            return False
        if task_req.gpu_mem_mb > 0:
            if available.gpu_mem_mb == 0 or (active_allocations.gpu_mem_mb + task_req.gpu_mem_mb) > available.gpu_mem_mb:
                return False
        return True

    def get_worker_numa_affinity(self, worker_index: int, is_gpu_worker: bool = False) -> Optional[int]:
        """ワーカーインデックスから推奨 NUMA ノード取得。"""
        if is_gpu_worker:
            gpu_idx = worker_index % max(1, len(self.numa_topology.gpu_to_numa))
            return self.numa_topology.get_numa_for_gpu(gpu_idx)
        else:
            # CPU ワーカー: ラウンドロビンで NUMA 分散
            numa_nodes = self.numa_topology.numa_nodes
            if not numa_nodes:
                return None
            return numa_nodes[worker_index % len(numa_nodes)]

    def get_gpu_worker_env(self, gpu_index: int) -> Dict[str, str]:
        """GPU ワーカー用環境変数 (CUDA_VISIBLE_DEVICES + NUMA) 生成。"""
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = str(gpu_index)
        
        numa = self.numa_topology.get_numa_for_gpu(gpu_index)
        if numa is not None:
            # numactl でメモリ割当制御
            env["NUMACTL_ARGS"] = f"--membind={numa} --cpunodebind={numa}"
        
        return env


__all__ = ["ResourceManager"]
