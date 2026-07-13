
from typing import List

from pydantic import BaseModel, ValidationError


class TestModel(BaseModel):
    name: str
    age: int
    tags: List[str]

# Mocking OutputSanitizer.format_validation_error
class OutputSanitizer:
    @staticmethod
    def format_validation_error(ve: ValidationError) -> str:
        """PydanticのValidationErrorをAIが理解しやすい日本語に変換する"""
        type_map = {
            "missing":     "が不足しています。必ず含めてください。",
            "string_type": "は文字列である必要があります。",
            "int_type":    "は整数である必要があります。",
            "enum":        "は指定された選択肢から選ぶ必要があります。",
        }
        msgs = []
        for err in ve.errors():
            loc  = ".".join(str(x) for x in err["loc"])
            # type は err.get("type") で取得
            err_type = err.get("type", "")
            msg  = type_map.get(err_type, f"にエラーがあります（原因: {err['msg']}）")
            msgs.append(f"・項目 '{loc}' {msg}")
        return "\n".join(msgs)

def test():
    try:
        # Trigger validation error
        TestModel(name=123, tags="not a list")
    except ValidationError as ve:
        formatted = OutputSanitizer.format_validation_error(ve)
        print("Formatted Error Message:")
        print(formatted)

if __name__ == "__main__":
    test()

