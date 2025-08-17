from __future__ import annotations
import duckdb, pandas as pd, os
from ..config import Settings

class SQLStore:
    def __init__(self, settings: Settings):
        self.path = settings.duckdb_path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.con = duckdb.connect(self.path)
        self._init_tables()

    def _init_tables(self):
        self.con.execute("""
        CREATE TABLE IF NOT EXISTS financial_orders (
            order_id BIGINT,
            customer TEXT,
            amount DOUBLE,
            currency TEXT,
            ts TIMESTAMP,
            status TEXT
        );
        """)
        self.con.execute("""
        CREATE TABLE IF NOT EXISTS device_metrics (
            device_id TEXT,
            status TEXT,
            uptime_minutes DOUBLE,
            location TEXT,
            ts TIMESTAMP
        );
        """)

    def insert_financial(self, df: pd.DataFrame):
        self.con.register("df_fin", df)
        self.con.execute("INSERT INTO financial_orders SELECT * FROM df_fin")

    def insert_devices(self, df: pd.DataFrame):
        self.con.register("df_dev", df)
        self.con.execute("INSERT INTO device_metrics SELECT * FROM df_dev")

    def query(self, sql: str):
        df = self.con.execute(sql).fetch_df()
        return df