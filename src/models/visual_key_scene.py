from pydantic import BaseModel

class VisualKeyScene(BaseModel):
    scene_id: int
    description: str
    importance: str

