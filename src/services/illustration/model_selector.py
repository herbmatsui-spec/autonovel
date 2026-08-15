"""IllustrationRequest から実際のImagenモデルIDを解決する。

AUTO の場合はコンテキスト（種別・安全レベル）から自動選択し、
それ以外は明示されたtierキーをカタログから解決する。
モデルIDは src 内に持たず、必ず config.imagen_models を経由する。
"""

from config.imagen_models import get_imagen_model_id, select_imagen_model
from src.models.illustration import IllustrationModel, IllustrationRequest


def _type_value(illo_type) -> str:
    try:
        return illo_type.value
    except AttributeError:
        return str(getattr(illo_type, "value", illo_type))


def _safety_value(safety) -> str:
    try:
        return safety.value
    except AttributeError:
        return str(getattr(safety, "value", safety))


def _model_value(model) -> str:
    try:
        return model.value
    except AttributeError:
        return str(getattr(model, "value", model))


def is_r15(safety) -> bool:
    """SafetyLevel が R15_CONTENT かどうかを判定する。"""
    return _safety_value(safety) == "R15_CONTENT"


def resolve_model_id(model: IllustrationModel) -> str:
    """明示的tierキーを実モデルIDへ変換（AUTOはデフォルトtierへ）。"""
    if _model_value(model) == "auto":
        from config.imagen_models import DEFAULT_IMAGEN_TIER

        return get_imagen_model_id(DEFAULT_IMAGEN_TIER)
    return get_imagen_model_id(_model_value(model))


def resolve_request_model(request: IllustrationRequest) -> str:
    """リクエストから使用すべきモデルIDを決定（AUTO時は自動選択）。"""
    if _model_value(request.model) == "auto":
        return select_imagen_model(
            _type_value(request.illustration_type),
            safety_level=_safety_value(request.safety_level),
        )
    return get_imagen_model_id(_model_value(request.model))
