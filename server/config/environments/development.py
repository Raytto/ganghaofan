from ..settings import Settings

class DevelopmentSettings(Settings):
    debug: bool = True
    database_url: str = "duckdb:///server/data/ganghaofan_dev.duckdb"