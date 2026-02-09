"""데이터 수집기 기본 클래스"""
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any

from src.storage.database import Database
from src.storage.models import PipelineRun

logger = logging.getLogger("marketsense")


class BaseCollector(ABC):
    """모든 데이터 수집기의 기본 클래스"""

    def __init__(self, config: Dict[str, Any], db: Database):
        self.config = config
        self.db = db
        self.pipeline_name = self.__class__.__name__

    @abstractmethod
    def collect(self, tickers: list = None, **kwargs):
        """데이터 수집 실행"""
        pass

    def _start_run(self, session) -> PipelineRun:
        """파이프라인 실행 기록 시작"""
        run = PipelineRun(
            pipeline_name=self.pipeline_name,
            status="running",
            started_at=datetime.utcnow(),
        )
        session.add(run)
        session.flush()
        logger.info(f"[{self.pipeline_name}] 파이프라인 시작 (run_id={run.id})")
        return run

    def _finish_run(self, run: PipelineRun, records: int = 0, error: str = None):
        """파이프라인 실행 기록 완료"""
        run.finished_at = datetime.utcnow()
        run.records_collected = records
        if error:
            run.status = "failed"
            run.error_message = error
            logger.error(f"[{self.pipeline_name}] 실패: {error}")
        else:
            run.status = "success"
            logger.info(f"[{self.pipeline_name}] 완료: {records}건 수집")
