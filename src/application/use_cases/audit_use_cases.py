"""Audit Use Cases."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from src.domain.repositories.audit_repository import IAuditRepository
from src.domain.repositories.unit_of_work import IUnitOfWork
from src.domain.value_objects.ids import NovelId, AuditId
from src.domain.entities.audit import AuditFinding, AuditResult, AuditCategory, AuditSeverity, AuditType
from src.application.dtos.audit_dto import (
    AuditRequestDTO,
    AuditResponseDTO,
    AuditListItemDTO,
    AuditHistoryFilterDTO,
)
from src.application.dtos.common import PaginationDTO, PaginatedResponseDTO


@dataclass
class RequestAuditUseCase:
    """Use case for requesting a new audit."""

    audit_repo: IAuditRepository
    uow: IUnitOfWork

    async def execute(self, dto: AuditRequestDTO) -> AuditResponseDTO:
        async with self.uow:
            audit = AuditResult.create(
                novel_id=NovelId.from_string(dto.novel_id),
                episode_number=0,  # 小説全体監査のためデフォルト0
                audit_type=AuditType.LOGICAL if dto.audit_type == "logical" else
                           AuditType.STYLE if dto.audit_type == "style" else
                           AuditType.COMPREHENSIVE if dto.audit_type == "full" else
                           AuditType.QUICK,
            )
            # 監査実行は非同期ワーカーに委譲されるため、初期レコードを作成・保存する
            saved = await self.audit_repo.save(audit)
            await self.uow.commit()
        return AuditResponseDTO.from_entity(saved)


@dataclass
class GetAuditUseCase:
    """Use case for getting an audit by ID."""

    audit_repo: IAuditRepository

    async def execute(self, audit_id: str) -> Optional[AuditResponseDTO]:
        aid = AuditId.from_string(audit_id)
        audit = await self.audit_repo.get_by_id(aid)
        return AuditResponseDTO.from_entity(audit) if audit else None


@dataclass
class ListAuditsUseCase:
    """Use case for listing audits with pagination and filters."""

    audit_repo: IAuditRepository

    async def execute(
        self,
        pagination: PaginationDTO,
        filters: Optional[AuditHistoryFilterDTO] = None,
    ) -> PaginatedResponseDTO[AuditListItemDTO]:
        limit = pagination.limit
        offset = pagination.offset

        # フィルタリング機能はリポジトリ拡張時に反映
        audits = await self.audit_repo.list_all(limit, offset)
        total = await self.audit_repo.count()

        items = [AuditListItemDTO.from_entity(a) for a in audits]
        return PaginatedResponseDTO(items=items, total=total, limit=limit, offset=offset)


@dataclass
class AddAuditFindingUseCase:
    """Use case for adding a finding to an audit."""

    audit_repo: IAuditRepository
    uow: IUnitOfWork

    async def execute(
        self,
        audit_id: str,
        category: str,
        severity: str,
        description: str,
        episode_number: int,
        evidence_past: str = "",
        evidence_current: str = "",
        constraint_for_next: str = "",
    ) -> AuditResponseDTO:
        aid = AuditId.from_string(audit_id)
        async with self.uow:
            audit = await self.audit_repo.get_by_id(aid)
            if not audit:
                raise ValueError(f"Audit {audit_id} not found")

            # Map strings to domain enums
            try:
                audit_category = AuditCategory(category.upper())
            except ValueError:
                audit_category = AuditCategory.INCONSISTENCY  # default

            try:
                audit_severity = AuditSeverity(severity.lower())
            except ValueError:
                audit_severity = AuditSeverity.MEDIUM  # default

            finding = AuditFinding.create(
                category=audit_category,
                severity=audit_severity,
                description=description,
                episode_number=episode_number,
                evidence_past=evidence_past,
                evidence_current=evidence_current,
                constraint_for_next=constraint_for_next,
            )
            audit.add_finding(finding)
            saved = await self.audit_repo.save(audit)
            await self.uow.commit()
        return AuditResponseDTO.from_entity(saved)


@dataclass
class RemoveAuditFindingUseCase:
    """Use case for removing a finding from an audit."""

    audit_repo: IAuditRepository
    uow: IUnitOfWork

    async def execute(self, audit_id: str, finding_id: str) -> bool:
        aid = AuditId.from_string(audit_id)
        fid = AuditId.from_string(finding_id)
        async with self.uow:
            audit = await self.audit_repo.get_by_id(aid)
            if not audit:
                return False
            removed = audit.remove_finding(fid)
            if removed:
                await self.audit_repo.save(audit)
                await self.uow.commit()
            return removed


@dataclass
class CompleteAuditUseCase:
    """Use case for completing an audit."""

    audit_repo: IAuditRepository
    uow: IUnitOfWork

    async def execute(self, audit_id: str, summary: str) -> bool:
        aid = AuditId.from_string(audit_id)
        async with self.uow:
            audit = await self.audit_repo.get_by_id(aid)
            if not audit:
                return False
            audit.complete(summary)
            await self.audit_repo.save(audit)
            await self.uow.commit()
        return True


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass
