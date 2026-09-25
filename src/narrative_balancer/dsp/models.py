"""DSP Tension Balancer models and data structures."""

from typing import List, Optional
import numpy as np
from pydantic import BaseModel, Field, ConfigDict
from src.narrative_balancer.models import Beat, BeatType, CorrectionAction


class TensionSignal(BaseModel):
    """Numerical representation of tension values along episode timeline."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    episodes: List[int] = Field(..., description="Episode indices")
    values: List[float] = Field(..., description="Tension values (0.0 - 10.0)")

    def to_numpy(self) -> np.ndarray:
        """Convert tension values to NumPy array."""
        return np.array(self.values, dtype=np.float64)


class SagDetection(BaseModel):
    """Detection result for mid-story tension sagging (中だるみ)."""
    model_config = ConfigDict(extra="ignore")

    start_episode: int = Field(..., description="Start episode of sag window")
    end_episode: int = Field(..., description="End episode of sag window")
    detected_episode: int = Field(..., description="Target episode needing intervention")
    spectral_flatness: float = Field(..., description="Calculated spectral flatness score")
    low_freq_ratio: float = Field(..., description="Low frequency energy ratio")
    is_sag: bool = Field(..., description="Whether sagging criteria was triggered")
    reason: str = Field(default="", description="Diagnostic details")


class ImpulseConfig(BaseModel):
    """Parameters for synthetic midpoint impulse curve."""
    length: int = Field(default=5, ge=1, le=20)
    peak: float = Field(default=9.0, ge=1.0, le=10.0)
    decay: float = Field(default=0.7, ge=0.1, le=0.99)
    shape: str = Field(default="exponential_decay", description="Shape type of impulse")


class DSPConfig(BaseModel):
    """Configuration for DSP Tension Balancer."""
    window_size: int = Field(default=8, ge=3, le=20, description="Sliding window size in episodes")
    flatness_threshold: float = Field(default=0.6, ge=0.0, le=1.0, description="Threshold above which curve is considered flat")
    low_freq_ratio_threshold: float = Field(default=0.65, ge=0.0, le=1.0, description="Threshold for low frequency dominance")
    min_tension_clip: float = Field(default=1.0, ge=0.0, le=10.0)
    max_tension_clip: float = Field(default=10.0, ge=0.0, le=10.0)
    impulse: ImpulseConfig = Field(default_factory=ImpulseConfig)
