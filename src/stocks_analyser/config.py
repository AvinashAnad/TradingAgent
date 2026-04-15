from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    app_mode: str
    tickertape_base_url: str
    tickertape_timeout_seconds: int
    tickertape_page_size: int
    max_stocks: int
    schedule_interval_minutes: int
    min_signal_score: int
    max_pe: float
    min_promoter_holding: float
    min_revenue_growth: float
    min_profit_growth: float
    sell_signal_score: int
    stop_loss_pct: float
    take_profit_pct: float
    dhan_client_id: str
    dhan_access_token: str
    dhan_base_url: str
    dhan_health_endpoint: str
    dhan_order_endpoint: str
    dhan_exchange_segment: str
    dhan_product_type: str
    dhan_order_type: str
    dhan_validity: str
    dhan_symbol_security_map: str
    default_trade_quantity: int
    sqlite_path: str
    llm_crosscheck_mode: str
    nvidia_api_key: str
    nvidia_base_url: str
    nvidia_model: str
    nvidia_timeout_seconds: int
    nvidia_temperature: float
    nvidia_max_tokens: int

    @staticmethod
    def _env_int(name: str, default: int) -> int:
        value = os.getenv(name)
        if value is None or value == "":
            return default
        return int(value)

    @staticmethod
    def _env_float(name: str, default: float) -> float:
        value = os.getenv(name)
        if value is None or value == "":
            return default
        return float(value)

    @classmethod
    def load(cls, env_file: str = ".env") -> "Settings":
        env_path = Path(env_file)
        if env_path.exists():
            load_dotenv(env_path)
        else:
            load_dotenv()

        return cls(
            app_mode=os.getenv("APP_MODE", "dev"),
            tickertape_base_url=os.getenv("TICKERTAPE_BASE_URL", "https://api.tickertape.in"),
            tickertape_timeout_seconds=cls._env_int("TICKERTAPE_TIMEOUT_SECONDS", 20),
            tickertape_page_size=cls._env_int("TICKERTAPE_PAGE_SIZE", 500),
            max_stocks=cls._env_int("MAX_STOCKS", 100),
            schedule_interval_minutes=cls._env_int("SCHEDULE_INTERVAL_MINUTES", 60),
            min_signal_score=cls._env_int("MIN_SIGNAL_SCORE", 3),
            max_pe=cls._env_float("MAX_PE", 40.0),
            min_promoter_holding=cls._env_float("MIN_PROMOTER_HOLDING", 35.0),
            min_revenue_growth=cls._env_float("MIN_REVENUE_GROWTH", 0.0),
            min_profit_growth=cls._env_float("MIN_PROFIT_GROWTH", 0.0),
            sell_signal_score=cls._env_int("SELL_SIGNAL_SCORE", 1),
            stop_loss_pct=cls._env_float("STOP_LOSS_PCT", 0.15),
            take_profit_pct=cls._env_float("TAKE_PROFIT_PCT", 0.35),
            dhan_client_id=os.getenv("DHAN_CLIENT_ID", ""),
            dhan_access_token=os.getenv("DHAN_ACCESS_TOKEN", ""),
            dhan_base_url=os.getenv("DHAN_BASE_URL", "https://api.dhan.co"),
            dhan_health_endpoint=os.getenv("DHAN_HEALTH_ENDPOINT", "/fundlimit"),
            dhan_order_endpoint=os.getenv("DHAN_ORDER_ENDPOINT", "/orders"),
            dhan_exchange_segment=os.getenv("DHAN_EXCHANGE_SEGMENT", "NSE_EQ"),
            dhan_product_type=os.getenv("DHAN_PRODUCT_TYPE", "CNC"),
            dhan_order_type=os.getenv("DHAN_ORDER_TYPE", "MARKET"),
            dhan_validity=os.getenv("DHAN_VALIDITY", "DAY"),
            dhan_symbol_security_map=os.getenv("DHAN_SYMBOL_SECURITY_MAP", "{}"),
            default_trade_quantity=cls._env_int("DEFAULT_TRADE_QUANTITY", 1),
            sqlite_path=os.getenv("SQLITE_PATH", "stocks_analyser.db"),
            llm_crosscheck_mode=os.getenv("LLM_CROSSCHECK_MODE", "off"),
            nvidia_api_key=os.getenv("NVIDIA_API_KEY", ""),
            nvidia_base_url=os.getenv(
                "NVIDIA_BASE_URL",
                "https://integrate.api.nvidia.com/v1/chat/completions",
            ),
            nvidia_model=os.getenv("NVIDIA_MODEL", "meta/llama-3.1-70b-instruct"),
            nvidia_timeout_seconds=cls._env_int("NVIDIA_TIMEOUT_SECONDS", 20),
            nvidia_temperature=cls._env_float("NVIDIA_TEMPERATURE", 0.1),
            nvidia_max_tokens=cls._env_int("NVIDIA_MAX_TOKENS", 300),
        )
