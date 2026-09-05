from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class EroticGate:
    """Erotic gate value object to consolidate erotic feature state.

    Previously, enable_erotic, enable_nsfw, nsfw_enabled, and erotic_intensity
    were scattered in 5 places. This object is the single source of truth.
    """
    enabled: bool           # NSFW overall permission (UI: NSFW/erotic content toggle)
    intensity: int          # 1-5 (UI: erotic intensity slider)

    def is_active(self) -> bool:
        """Determine if erotic content is active for a scene."""
        return self.enabled and self.intensity > 0

    @classmethod
    def disabled(cls) -> "EroticGate":
        return cls(enabled=False, intensity=0)

    @classmethod
    def from_context(cls, ctx: dict | None) -> "EroticGate":
        """Build EroticGate from context dict for backward compatibility.

        Old keys (enable_erotic, enable_nsfw, nsfw_enabled) are all aggregated
        into enabled. intensity is taken from erotic_intensity.
        """
        if not ctx:
            return cls.disabled()
        enabled = bool(
            ctx.get("enable_erotic")
            or ctx.get("enable_nsfw")
            or ctx.get("nsfw_enabled")
            or ctx.get("is_nsfw_enabled")
        )
        intensity = int(ctx.get("erotic_intensity", 0) or 0)
        return cls(enabled=enabled, intensity=intensity)
