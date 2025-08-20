from ..settings import Settings

class ProductionSettings(Settings):
    debug: bool = False
    # 生产环境特定配置