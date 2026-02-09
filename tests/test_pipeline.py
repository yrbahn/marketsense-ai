"""파이프라인 기본 테스트"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.storage.database import Database
from src.storage.models import Base, Stock, NewsArticle, PriceData, MacroIndicator
from src.utils.helpers import load_config


class TestDatabase:
    """데이터베이스 테스트"""

    def setup_method(self):
        self.db = Database("sqlite:///:memory:")
        self.db.create_tables()

    def test_create_tables(self):
        tables = Base.metadata.tables
        assert "stocks" in tables
        assert "news_articles" in tables
        assert "financial_statements" in tables
        assert "sec_filings" in tables
        assert "earnings_calls" in tables
        assert "price_data" in tables
        assert "technical_indicators" in tables
        assert "macro_reports" in tables
        assert "macro_indicators" in tables
        assert "pipeline_runs" in tables

    def test_add_stock(self):
        with self.db.get_session() as session:
            stock = Stock(ticker="AAPL", name="Apple Inc.", sector="Technology")
            session.add(stock)

        with self.db.get_session() as session:
            found = session.query(Stock).filter_by(ticker="AAPL").first()
            assert found is not None
            assert found.name == "Apple Inc."

    def test_add_news(self):
        with self.db.get_session() as session:
            stock = Stock(ticker="MSFT", name="Microsoft")
            session.add(stock)
            session.flush()

            news = NewsArticle(
                stock_id=stock.id,
                ticker="MSFT",
                title="Test News",
                url="https://example.com/news/1",
                source="test",
            )
            session.add(news)

        with self.db.get_session() as session:
            found = session.query(NewsArticle).first()
            assert found.title == "Test News"

    def test_unique_constraints(self):
        with self.db.get_session() as session:
            stock = Stock(ticker="GOOGL", name="Alphabet")
            session.add(stock)

        with pytest.raises(Exception):
            with self.db.get_session() as session:
                dup = Stock(ticker="GOOGL", name="Alphabet Dup")
                session.add(dup)


class TestConfig:
    def test_load_config(self):
        # config 파일이 있을 때만 테스트
        if os.path.exists("config/config.yaml"):
            config = load_config()
            assert "database" in config
            assert "news" in config
            assert "fundamentals" in config
            assert "dynamics" in config
            assert "macro" in config


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
