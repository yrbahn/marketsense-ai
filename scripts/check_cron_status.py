#!/usr/bin/env python3
"""
Cron 작업 실행 상태 체크
매일 저녁 실행하여 오늘 실행되어야 할 작업들이 정상적으로 완료되었는지 확인
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.database import Database
from sqlalchemy import text


def check_today_status():
    """오늘 데이터 수집 상태 확인"""
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    db = Database('postgresql://yrbahn@localhost:5432/marketsense')
    
    issues = []
    
    with db.get_session() as session:
        # 1. 뉴스 데이터 확인
        news_count = session.execute(text("""
            SELECT COUNT(*)
            FROM news_articles
            WHERE DATE(published_at) = :today
        """), {"today": today}).fetchone()[0]
        
        if news_count < 100:  # 최소 100개 뉴스 기대
            issues.append(f"⚠️ 뉴스 데이터 부족: {news_count}개 (기대: 100+)")
        
        # 2. 주가 데이터 확인 (오늘 또는 어제 - 주말 고려)
        price_count = session.execute(text("""
            SELECT COUNT(DISTINCT stock_id)
            FROM price_data
            WHERE date >= :yesterday
        """), {"yesterday": yesterday}).fetchone()[0]
        
        if price_count < 2000:  # 최소 2000종목 기대
            issues.append(f"⚠️ 주가 데이터 부족: {price_count}종목 (기대: 2000+)")
        
        # 3. 리포트 데이터 확인 (이번 주)
        week_start = today - timedelta(days=today.weekday())
        report_count = session.execute(text("""
            SELECT COUNT(*)
            FROM research_reports
            WHERE report_date >= :week_start
        """), {"week_start": week_start}).fetchone()[0]
        
        # 4. 블로그 데이터 확인
        blog_count = session.execute(text("""
            SELECT COUNT(*)
            FROM blog_posts
            WHERE post_date = :today
        """), {"today": today}).fetchone()[0]
        
        if blog_count < 50:  # 최소 50개 블로그 기대
            issues.append(f"⚠️ 블로그 데이터 부족: {blog_count}개 (기대: 50+)")
    
    # 결과 생성
    if issues:
        message = f"🚨 **MarketSenseAI 데이터 수집 문제**\n\n"
        message += f"📅 {today}\n\n"
        for issue in issues:
            message += f"{issue}\n"
        message += f"\n💡 확인이 필요합니다!"
        return message
    else:
        # 성공 메시지 (간단하게)
        message = f"✅ MarketSenseAI 정상 작동\n"
        message += f"📅 {today}\n"
        message += f"📰 뉴스: {news_count}개\n"
        message += f"📈 주가: {price_count}종목\n"
        message += f"📝 블로그: {blog_count}개"
        return message


if __name__ == "__main__":
    result = check_today_status()
    print(result)
