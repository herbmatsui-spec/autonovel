"""Default Auto Workflow DAG Builder."""

from __future__ import annotations

from typing import Any, Optional

from src.core.dag.dag import DAGNode, DAGPipeline


class DefaultAutoWorkflowBuilder:
    """Builder for constructing standard AutoNovel DAG workflows."""

    def __init__(
        self,
        llm_factory: Optional[Any] = None,
        vector_store_factory: Optional[Any] = None,
        image_provider_factory: Optional[Any] = None,
    ) -> None:
        self.llm_factory = llm_factory
        self.vector_store_factory = vector_store_factory
        self.image_provider_factory = image_provider_factory

    def build(self) -> DAGPipeline:
        """Build and return a DAG pipeline configured with default nodes."""
        pipeline = DAGPipeline()
        pipeline.add_node(DAGNode(name="init_context"))
        pipeline.add_node(DAGNode(name="plan_generation"))
        pipeline.add_node(DAGNode(name="episode_writing"))
        pipeline.add_node(DAGNode(name="audit_and_validation"))
        return pipeline
