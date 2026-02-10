#!/bin/bash
# 증권사 리포트 수집 스크립트

set -e

cd "$(dirname "$0")/.."

echo "[$(date)] 증권사 리포트 수집 시작"

/Library/Developer/CommandLineTools/usr/bin/python3 -c "
from dotenv import load_dotenv
load_dotenv()

from src.storage.database import init_db
from src.collectors.research_report_collector import ResearchReportCollector
from src.utils.helpers import load_config
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/research_report.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

try:
    logger.info('증권사 리포트 수집 시작')
    
    config = load_config()
    db = init_db(config)
    
    collector = ResearchReportCollector(config, db)
    count = collector.collect()  # 전체 종목
    
    logger.info(f'수집 완료: {count}건')
    
except Exception as e:
    logger.error(f'수집 실패: {e}')
    raise
"

echo "[$(date)] 증권사 리포트 수집 완료"
