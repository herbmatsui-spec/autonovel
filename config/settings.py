from schemas.config import GlobalConfigModel


class ConfigManager:
    _instance: GlobalConfigModel = None

    @classmethod
    def get_config(cls) -> GlobalConfigModel:
        if cls._instance is None:
            cls._instance = GlobalConfigModel.load()
        return cls._instance

