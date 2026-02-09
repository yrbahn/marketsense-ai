"""유틸리티 함수"""
import os
import yaml
import logging
from typing import Dict, Any, List


def load_config(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def setup_logger(name: str = "marketsense", level: str = "INFO", log_file: str = None) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    if logger.handlers:
        return logger

    fmt = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger


def get_sp500_tickers() -> List[str]:
    """S&P 500 종목 리스트 가져오기 (Wikipedia)"""
    import pandas as pd
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    tables = pd.read_html(url)
    df = tables[0]
    return df["Symbol"].str.replace(".", "-", regex=False).tolist()


def get_sp100_tickers() -> List[str]:
    """S&P 100 종목 리스트 가져오기"""
    import pandas as pd
    url = "https://en.wikipedia.org/wiki/S%26P_100"
    tables = pd.read_html(url)
    df = tables[2]  # S&P 100 테이블
    return df["Symbol"].str.replace(".", "-", regex=False).tolist()


def chunk_list(lst: list, chunk_size: int) -> list:
    """리스트를 chunk_size 단위로 분할"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]
