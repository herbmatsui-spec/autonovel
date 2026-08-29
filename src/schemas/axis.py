from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class AxisType(str, Enum):
    OUTPUT_MODE = "output_mode"
    THEME = "theme"
    GENRE = "genre"
    WORLDVIEW = "worldview"
    AUDIENCE = "audience"
    ERA = "era"
    ENDING_STYLE = "ending_style"
    NARRATOR = "narrator"
    CHARACTERS = "characters"
    UNIVERSAL_INPUT = "universal_input"
    SUPPLEMENTAL_NOTE = "supplemental_note"


# Each axis value can be a string, a list of strings, or null
AxisValue = Union[str, List[str], None]


class Axis(BaseModel):
    """Single axis configuration."""
    axis_type: AxisType = Field(..., description="Type of the axis")
    value: AxisValue = Field(None, description="Current value for this axis")
    locked: bool = Field(False, description="Whether this axis is locked from randomisation")
    default: AxisValue = Field(None, description="Default value used for reset")


class PromptContract(BaseModel):
    """Aggregated contract sent to the LLM."""
    output_mode: str = Field(..., description="Selected output mode key")
    axes: Dict[AxisType, Axis] = Field(default_factory=dict, description="All axis configurations")

    def to_compiled_prompt(self) -> str:
        """Placeholder – actual rendering is delegated to the compiler service."""
        # The compiler service will use Jinja2 templates per output_mode.
        raise NotImplementedError("Use PromptCompilerService.compile(self)")