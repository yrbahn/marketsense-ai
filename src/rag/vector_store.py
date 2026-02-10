#!/usr/bin/env python3
"""RAG Vector Store - ChromaDB 기반

뉴스, 재무제표, 리포트를 벡터화하여 검색 가능하게 만듦
"""
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

logger = logging.getLogger("marketsense")


class VectorStore:
    """벡터 저장소 (ChromaDB)"""
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        """초기화
        
        Args:
            persist_directory: ChromaDB 저장 경로
        """
        self.persist_directory = persist_directory
        
        # ChromaDB 클라이언트
        self.client = chromadb.Client(Settings(
            persist_directory=persist_directory,
            anonymized_telemetry=False
        ))
        
        # 한국어 임베딩 모델
        logger.info("임베딩 모델 로딩 중... (sentence-transformers)")
        self.embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        logger.info("임베딩 모델 로딩 완료")
        
        # 컬렉션 초기화
        self._init_collections()
    
    def _init_collections(self):
        """컬렉션 초기화"""
        # 뉴스 컬렉션
        try:
            self.news_collection = self.client.get_collection("news")
            logger.info("기존 뉴스 컬렉션 로드")
        except:
            self.news_collection = self.client.create_collection(
                name="news",
                metadata={"description": "Stock news articles"}
            )
            logger.info("새 뉴스 컬렉션 생성")
        
        # 재무제표 컬렉션
        try:
            self.financials_collection = self.client.get_collection("financials")
            logger.info("기존 재무 컬렉션 로드")
        except:
            self.financials_collection = self.client.create_collection(
                name="financials",
                metadata={"description": "Financial statements"}
            )
            logger.info("새 재무 컬렉션 생성")
        
        # 공시 컬렉션
        try:
            self.disclosures_collection = self.client.get_collection("disclosures")
            logger.info("기존 공시 컬렉션 로드")
        except:
            self.disclosures_collection = self.client.create_collection(
                name="disclosures",
                metadata={"description": "Corporate disclosures"}
            )
            logger.info("새 공시 컬렉션 생성")
        
        # 리포트 컬렉션
        try:
            self.reports_collection = self.client.get_collection("reports")
            logger.info("기존 리포트 컬렉션 로드")
        except:
            self.reports_collection = self.client.create_collection(
                name="reports",
                metadata={"description": "Research reports"}
            )
            logger.info("새 리포트 컬렉션 생성")
    
    def add_news(self, articles: List[Dict[str, Any]]):
        """뉴스 추가
        
        Args:
            articles: 뉴스 기사 리스트
                [{'id': str, 'ticker': str, 'title': str, 'content': str, 
                  'published_at': datetime, ...}]
        """
        if not articles:
            return
        
        # 텍스트 준비
        ids = []
        documents = []
        metadatas = []
        
        for article in articles:
            # ID
            article_id = f"news_{article['id']}"
            ids.append(article_id)
            
            # 문서 (제목 + 본문)
            text = f"{article.get('title', '')} {article.get('content', '')}"
            documents.append(text)
            
            # 메타데이터
            metadata = {
                'ticker': article.get('ticker', ''),
                'source': article.get('source', ''),
                'published_at': article.get('published_at', '').isoformat() if isinstance(article.get('published_at'), datetime) else str(article.get('published_at', '')),
                'url': article.get('url', '')
            }
            metadatas.append(metadata)
        
        # 임베딩 생성
        logger.info(f"뉴스 {len(documents)}개 임베딩 중...")
        embeddings = self.embedding_model.encode(documents, show_progress_bar=True).tolist()
        
        # ChromaDB에 추가
        self.news_collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        
        logger.info(f"뉴스 {len(articles)}개 벡터화 완료")
    
    def add_financials(self, statements: List[Dict[str, Any]]):
        """재무제표 추가
        
        Args:
            statements: 재무제표 리스트
                [{'id': str, 'ticker': str, 'period': str, 'summary': str, ...}]
        """
        if not statements:
            return
        
        ids = []
        documents = []
        metadatas = []
        
        for stmt in statements:
            # ID
            stmt_id = f"fin_{stmt['id']}"
            ids.append(stmt_id)
            
            # 문서 (재무 요약)
            text = stmt.get('summary', '')
            documents.append(text)
            
            # 메타데이터
            metadata = {
                'ticker': stmt.get('ticker', ''),
                'period': stmt.get('period', ''),
                'statement_type': stmt.get('statement_type', '')
            }
            metadatas.append(metadata)
        
        # 임베딩
        logger.info(f"재무제표 {len(documents)}개 임베딩 중...")
        embeddings = self.embedding_model.encode(documents, show_progress_bar=True).tolist()
        
        # 추가
        self.financials_collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        
        logger.info(f"재무제표 {len(statements)}개 벡터화 완료")
    
    def search_news(
        self,
        query: str,
        ticker: Optional[str] = None,
        date_after: Optional[str] = None,
        top_k: int = 10
    ) -> List[Dict]:
        """뉴스 검색
        
        Args:
            query: 검색 쿼리
            ticker: 종목 코드 (필터링)
            date_after: 이 날짜 이후 뉴스만 (ISO format: YYYY-MM-DD)
            top_k: 반환 개수
            
        Returns:
            관련 뉴스 리스트
        """
        # 쿼리 임베딩
        query_embedding = self.embedding_model.encode([query]).tolist()[0]
        
        # 필터 조건 구성
        where = None
        if ticker and date_after:
            where = {
                "$and": [
                    {"ticker": ticker},
                    {"published_at": {"$gte": date_after}}
                ]
            }
        elif ticker:
            where = {"ticker": ticker}
        elif date_after:
            where = {"published_at": {"$gte": date_after}}
        
        results = self.news_collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where
        )
        
        # 포맷
        news_items = []
        if results['ids']:
            for i in range(len(results['ids'][0])):
                news_items.append({
                    'id': results['ids'][0][i],
                    'text': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None
                })
        
        return news_items
    
    def search_financials(
        self,
        query: str,
        ticker: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict]:
        """재무제표 검색
        
        Args:
            query: 검색 쿼리
            ticker: 종목 코드 (필터링)
            top_k: 반환 개수
            
        Returns:
            관련 재무제표 리스트
        """
        query_embedding = self.embedding_model.encode([query]).tolist()[0]
        
        where = {"ticker": ticker} if ticker else None
        
        results = self.financials_collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where
        )
        
        fin_items = []
        if results['ids']:
            for i in range(len(results['ids'][0])):
                fin_items.append({
                    'id': results['ids'][0][i],
                    'text': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None
                })
        
        return fin_items
    
    def add_disclosures(self, disclosures: List[Dict[str, Any]]):
        """공시 추가
        
        Args:
            disclosures: 공시 리스트
                [{'id': str, 'stock_id': int, 'ticker': str, 'report_nm': str, 
                  'rcept_dt': date, 'disclosure_type': str, ...}]
        """
        if not disclosures:
            return
        
        ids = []
        documents = []
        metadatas = []
        
        for disc in disclosures:
            # ID
            disc_id = f"disc_{disc['id']}"
            ids.append(disc_id)
            
            # 문서 (보고서명)
            text = f"{disc.get('disclosure_type', '')} {disc.get('report_nm', '')}"
            documents.append(text)
            
            # 메타데이터
            metadata = {
                'ticker': disc.get('ticker', ''),
                'disclosure_type': disc.get('disclosure_type', ''),
                'rcept_dt': str(disc.get('rcept_dt', ''))
            }
            metadatas.append(metadata)
        
        # 임베딩
        logger.info(f"공시 {len(documents)}개 임베딩 중...")
        embeddings = self.embedding_model.encode(documents, show_progress_bar=True).tolist()
        
        # 추가
        self.disclosures_collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        
        logger.info(f"공시 {len(disclosures)}개 벡터화 완료")
    
    def add_reports(self, reports: List[Dict[str, Any]]):
        """리포트 추가
        
        Args:
            reports: 리포트 리스트
                [{'id': str, 'stock_id': int, 'ticker': str, 'title': str, 
                  'firm': str, 'report_date': date, ...}]
        """
        if not reports:
            return
        
        ids = []
        documents = []
        metadatas = []
        
        for report in reports:
            # ID
            report_id = f"report_{report['id']}"
            ids.append(report_id)
            
            # 문서 (증권사 + 제목)
            text = f"{report.get('firm', '')} {report.get('title', '')}"
            documents.append(text)
            
            # 메타데이터
            metadata = {
                'ticker': report.get('ticker', ''),
                'firm': report.get('firm', ''),
                'report_date': str(report.get('report_date', ''))
            }
            metadatas.append(metadata)
        
        # 임베딩
        logger.info(f"리포트 {len(documents)}개 임베딩 중...")
        embeddings = self.embedding_model.encode(documents, show_progress_bar=True).tolist()
        
        # 추가
        self.reports_collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        
        logger.info(f"리포트 {len(reports)}개 벡터화 완료")
    
    def search_disclosures(
        self,
        query: str,
        ticker: Optional[str] = None,
        top_k: int = 10
    ) -> List[Dict]:
        """공시 검색
        
        Args:
            query: 검색 쿼리
            ticker: 종목 코드 (필터링)
            top_k: 반환 개수
            
        Returns:
            관련 공시 리스트
        """
        query_embedding = self.embedding_model.encode([query]).tolist()[0]
        
        where = {"ticker": ticker} if ticker else None
        
        results = self.disclosures_collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where
        )
        
        items = []
        if results['ids']:
            for i in range(len(results['ids'][0])):
                items.append({
                    'id': results['ids'][0][i],
                    'text': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None
                })
        
        return items
    
    def search_reports(
        self,
        query: str,
        ticker: Optional[str] = None,
        top_k: int = 10
    ) -> List[Dict]:
        """리포트 검색
        
        Args:
            query: 검색 쿼리
            ticker: 종목 코드 (필터링)
            top_k: 반환 개수
            
        Returns:
            관련 리포트 리스트
        """
        query_embedding = self.embedding_model.encode([query]).tolist()[0]
        
        where = {"ticker": ticker} if ticker else None
        
        results = self.reports_collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where
        )
        
        items = []
        if results['ids']:
            for i in range(len(results['ids'][0])):
                items.append({
                    'id': results['ids'][0][i],
                    'text': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None
                })
        
        return items
    
    def get_stats(self) -> Dict:
        """통계 조회
        
        Returns:
            {'news_count': int, 'financials_count': int, 
             'disclosures_count': int, 'reports_count': int}
        """
        return {
            'news_count': self.news_collection.count(),
            'financials_count': self.financials_collection.count(),
            'disclosures_count': self.disclosures_collection.count(),
            'reports_count': self.reports_collection.count()
        }


def main():
    """테스트"""
    import sys
    
    # 벡터 저장소 초기화
    vs = VectorStore()
    
    # 통계
    stats = vs.get_stats()
    print(f"뉴스: {stats['news_count']}개")
    print(f"재무: {stats['financials_count']}개")
    
    # 검색 테스트
    if len(sys.argv) > 1:
        query = ' '.join(sys.argv[1:])
        print(f"\n검색: {query}")
        
        news = vs.search_news(query, top_k=5)
        print(f"\n관련 뉴스 {len(news)}개:")
        for item in news:
            print(f"  - {item['text'][:100]}...")


if __name__ == "__main__":
    main()
