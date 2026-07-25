from typing import Any, Dict

from pydantic import BaseModel, Field


class T(BaseModel):
    d: Dict[str, Any] = Field(default_factory=dict)


print("ok", T(d={"a": 1}).d)
print("ok", T(d={"a": 1}).d)
