"""역사적 데이터 백필 스크립트

kospi-3s-trader를 위한 과거 1년치 가격 데이터 수집
"""
import sys
import logging
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.storage.database import Database
from src.collectors.dynamics_collector import DynamicsCollector
import yaml

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("backfill")


def main():
    """메인 실행"""
    # 설정 로드
    config_path = project_root / "config" / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
    else:
        config = {}
    
    # 데이터베이스 연결
    db_url = "postgresql://yrbahn@localhost:5432/marketsense"
    db = Database(db_url)
    
    # TOP 50 종목 리스트 (kospi-3s-trader config.yaml에서 가져옴)
    top50_tickers = [
        "005930", "000660", "373220", "207940", "005380", "000270", "006400", "051910",
        "035420", "035720", "105560", "055550", "096770", "005490", "028260", "034730",
        "032830", "012330", "086790", "015760", "033780", "010130", "009150", "316140",
        "005935", "000810", "003670", "006800", "009540", "010120", "010140", "011200",
        "012450", "024110", "034020", "042660", "042700", "064350", "068270", "086280",
        "086520", "138040", "196170", "247540", "267250", "267260", "272210", "298040",
        "329180", "402340"
    ]
    
    logger.info("=" * 60)
    logger.info("역사적 데이터 백필 시작")
    logger.info("=" * 60)
    logger.info(f"대상 종목: {len(top50_tickers)}개")
    logger.info(f"수집 기간: 최근 365일")
    logger.info(f"시작 시간: {datetime.now()}")
    logger.info("=" * 60)
    
    # DynamicsCollector 생성 (lookback_days=365로 설정)
    config['dynamics'] = config.get('dynamics', {})
    config['dynamics']['lookback_days'] = 365  # 1년치 데이터
    
    collector = DynamicsCollector(config, db)
    
    # 데이터 수집 실행
    try:
        logger.info("데이터 수집 시작...")
        collector.collect(tickers=top50_tickers)
        logger.info("✅ 데이터 수집 완료!")
        
    except Exception as e:
        logger.error(f"❌ 데이터 수집 실패: {e}")
        raise
    
    logger.info("=" * 60)
    logger.info(f"종료 시간: {datetime.now()}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
