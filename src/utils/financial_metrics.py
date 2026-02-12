"""재무 지표 계산 및 추세 분석"""
from typing import List, Dict, Any, Optional
from datetime import datetime


def format_quarterly_metrics_horizontal(statements: List[Any]) -> str:
    """모든 지표를 4분기 연속으로 가로로 표시
    
    Args:
        statements: 재무제표 리스트 (최신순 정렬됨)
    
    Returns:
        지표별 4분기 추세 텍스트
    """
    if len(statements) < 4:
        return ""
    
    lines = ["\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"]
    lines.append("📊 4분기 연속 모든 지표 추세 (지표별 가로 배치)")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    # 분기 레이블 생성
    periods = []
    for stmt in reversed(statements[:4]):
        year = stmt.period_end.year
        quarter = (stmt.period_end.month - 1) // 3 + 1
        periods.append(f"{year}-Q{quarter}")
    
    lines.append(f"\n기간: {' → '.join(periods)}")
    lines.append("")
    
    # === 손익계산서 ===
    lines.append("【손익계산서】")
    
    # 매출액
    revenues = []
    for stmt in reversed(statements[:4]):
        if stmt.raw_data and stmt.raw_data.get('revenue'):
            revenues.append(f"{stmt.raw_data['revenue']/100000000:.0f}억")
        else:
            revenues.append("N/A")
    if any(r != "N/A" for r in revenues):
        lines.append(f"  📈 매출액: {' → '.join(revenues)}")
    
    # 영업이익
    op_incomes = []
    for stmt in reversed(statements[:4]):
        if stmt.raw_data and stmt.raw_data.get('operating_income'):
            op_incomes.append(f"{stmt.raw_data['operating_income']/100000000:.0f}억")
        else:
            op_incomes.append("N/A")
    if any(oi != "N/A" for oi in op_incomes):
        lines.append(f"  💰 영업이익: {' → '.join(op_incomes)}")
    
    # 당기순이익
    net_incomes = []
    for stmt in reversed(statements[:4]):
        if stmt.raw_data and stmt.raw_data.get('net_income'):
            net_incomes.append(f"{stmt.raw_data['net_income']/100000000:.0f}억")
        else:
            net_incomes.append("N/A")
    if any(ni != "N/A" for ni in net_incomes):
        lines.append(f"  💵 당기순이익: {' → '.join(net_incomes)}")
    
    # 영업이익률
    op_margins = []
    for stmt in reversed(statements[:4]):
        if stmt.raw_data and stmt.raw_data.get('operating_margin'):
            op_margins.append(f"{stmt.raw_data['operating_margin']:.1f}%")
        else:
            op_margins.append("N/A")
    if any(om != "N/A" for om in op_margins):
        lines.append(f"  📊 영업이익률: {' → '.join(op_margins)}")
    
    # 순이익률
    net_margins = []
    for stmt in reversed(statements[:4]):
        if stmt.raw_data and stmt.raw_data.get('net_margin'):
            net_margins.append(f"{stmt.raw_data['net_margin']:.1f}%")
        else:
            net_margins.append("N/A")
    if any(nm != "N/A" for nm in net_margins):
        lines.append(f"  💹 순이익률: {' → '.join(net_margins)}")
    
    # === 재무상태표 ===
    lines.append("\n【재무상태표】")
    
    # 자산총계
    total_assets = []
    for stmt in reversed(statements[:4]):
        if stmt.raw_data and stmt.raw_data.get('total_assets'):
            total_assets.append(f"{stmt.raw_data['total_assets']/100000000:.0f}억")
        else:
            total_assets.append("N/A")
    if any(ta != "N/A" for ta in total_assets):
        lines.append(f"  🏦 자산총계: {' → '.join(total_assets)}")
    
    # 부채총계
    total_liabs = []
    for stmt in reversed(statements[:4]):
        if stmt.raw_data and stmt.raw_data.get('total_liabilities'):
            total_liabs.append(f"{stmt.raw_data['total_liabilities']/100000000:.0f}억")
        else:
            total_liabs.append("N/A")
    if any(tl != "N/A" for tl in total_liabs):
        lines.append(f"  📋 부채총계: {' → '.join(total_liabs)}")
    
    # 자본총계
    total_equity = []
    for stmt in reversed(statements[:4]):
        if stmt.raw_data and stmt.raw_data.get('total_equity'):
            total_equity.append(f"{stmt.raw_data['total_equity']/100000000:.0f}억")
        else:
            total_equity.append("N/A")
    if any(te != "N/A" for te in total_equity):
        lines.append(f"  💼 자본총계: {' → '.join(total_equity)}")
    
    # 부채비율
    debt_ratios = []
    for stmt in reversed(statements[:4]):
        if stmt.raw_data and stmt.raw_data.get('debt_ratio'):
            debt_ratios.append(f"{stmt.raw_data['debt_ratio']:.1f}%")
        else:
            debt_ratios.append("N/A")
    if any(dr != "N/A" for dr in debt_ratios):
        lines.append(f"  ⚖️ 부채비율: {' → '.join(debt_ratios)}")
    
    # === 현금흐름표 ===
    lines.append("\n【현금흐름표】")
    
    # 영업활동 현금흐름
    operating_cfs = []
    for stmt in reversed(statements[:4]):
        if stmt.raw_data and stmt.raw_data.get('operating_cash_flow'):
            cf_val = stmt.raw_data['operating_cash_flow'] / 100000000
            operating_cfs.append(f"{cf_val:+.0f}억")
        else:
            operating_cfs.append("N/A")
    if any(ocf != "N/A" for ocf in operating_cfs):
        lines.append(f"  💸 영업활동CF: {' → '.join(operating_cfs)}")
    
    # 투자활동 현금흐름
    investing_cfs = []
    for stmt in reversed(statements[:4]):
        if stmt.raw_data and stmt.raw_data.get('investing_cash_flow'):
            cf_val = stmt.raw_data['investing_cash_flow'] / 100000000
            investing_cfs.append(f"{cf_val:+.0f}억")
        else:
            investing_cfs.append("N/A")
    if any(icf != "N/A" for icf in investing_cfs):
        lines.append(f"  🏗️ 투자활동CF: {' → '.join(investing_cfs)}")
    
    # 재무활동 현금흐름
    financing_cfs = []
    for stmt in reversed(statements[:4]):
        if stmt.raw_data and stmt.raw_data.get('financing_cash_flow'):
            cf_val = stmt.raw_data['financing_cash_flow'] / 100000000
            financing_cfs.append(f"{cf_val:+.0f}억")
        else:
            financing_cfs.append("N/A")
    if any(fcf != "N/A" for fcf in financing_cfs):
        lines.append(f"  🏛️ 재무활동CF: {' → '.join(financing_cfs)}")
    
    # 잉여현금흐름 (FCF)
    fcfs = []
    for stmt in reversed(statements[:4]):
        if (stmt.raw_data and 
            stmt.raw_data.get('operating_cash_flow') and 
            stmt.raw_data.get('investing_cash_flow')):
            fcf = (stmt.raw_data['operating_cash_flow'] + 
                   stmt.raw_data['investing_cash_flow']) / 100000000
            fcfs.append(f"{fcf:+.0f}억")
        else:
            fcfs.append("N/A")
    if any(f != "N/A" for f in fcfs):
        lines.append(f"  💎 잉여현금흐름(FCF): {' → '.join(fcfs)}")
    
    # === 수익성 지표 ===
    lines.append("\n【수익성 지표】")
    
    # ROE
    roes = []
    for stmt in reversed(statements[:4]):
        if stmt.raw_data and stmt.raw_data.get('roe'):
            roes.append(f"{stmt.raw_data['roe']:.1f}%")
        else:
            roes.append("N/A")
    if any(r != "N/A" for r in roes):
        lines.append(f"  📊 ROE: {' → '.join(roes)}")
    
    # ROA
    roas = []
    for stmt in reversed(statements[:4]):
        if stmt.raw_data and stmt.raw_data.get('roa'):
            roas.append(f"{stmt.raw_data['roa']:.1f}%")
        else:
            roas.append("N/A")
    if any(r != "N/A" for r in roas):
        lines.append(f"  📈 ROA: {' → '.join(roas)}")
    
    # === 증감률 분석 ===
    growth_rates = calculate_growth_rates(statements)
    
    if growth_rates.get('qoq'):
        lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("【전분기 대비 (QoQ) 증감률】")
        qoq = growth_rates['qoq']
        if 'revenue' in qoq:
            lines.append(f"  • 매출: {qoq['revenue']:+.1f}%")
        if 'operating_income' in qoq:
            lines.append(f"  • 영업이익: {qoq['operating_income']:+.1f}%")
        if 'net_income' in qoq:
            lines.append(f"  • 순이익: {qoq['net_income']:+.1f}%")
        if 'operating_cash_flow' in qoq:
            lines.append(f"  • 영업CF: {qoq['operating_cash_flow']:+.1f}%")
        
        # 비율 차이
        if 'roe_diff' in qoq:
            lines.append(f"  • ROE 변화: {qoq['roe_diff']:+.1f}%p")
        if 'operating_margin_diff' in qoq:
            lines.append(f"  • 영업이익률 변화: {qoq['operating_margin_diff']:+.1f}%p")
    
    if growth_rates.get('yoy'):
        lines.append("\n【전년 동기 대비 (YoY) 증감률】")
        yoy = growth_rates['yoy']
        if 'revenue' in yoy:
            lines.append(f"  • 매출: {yoy['revenue']:+.1f}%")
        if 'operating_income' in yoy:
            lines.append(f"  • 영업이익: {yoy['operating_income']:+.1f}%")
        if 'net_income' in yoy:
            lines.append(f"  • 순이익: {yoy['net_income']:+.1f}%")
        if 'operating_cash_flow' in yoy:
            lines.append(f"  • 영업CF: {yoy['operating_cash_flow']:+.1f}%")
    
    if growth_rates.get('trend'):
        lines.append("\n【4분기 추세 판단】")
        for metric, trend in growth_rates['trend'].items():
            metric_name = {
                'revenue': '매출',
                'operating_income': '영업이익',
                'net_income': '순이익',
                'roe': 'ROE',
                'operating_margin': '영업이익률',
                'operating_cash_flow': '영업CF'
            }.get(metric, metric)
            lines.append(f"  • {metric_name}: {trend}")
    
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    return '\n'.join(lines)


def calculate_growth_rates(statements: List[Any]) -> Dict[str, Any]:
    """4분기 연속 데이터에서 YoY, QoQ 증감률 계산"""
    if len(statements) < 2:
        return {}
    
    result = {
        'qoq': {},
        'yoy': {},
        'trend': {}
    }
    
    # QoQ 계산
    if len(statements) >= 2:
        latest = statements[0]
        prev = statements[1]
        result['qoq'] = _calculate_change(latest, prev)
    
    # YoY 계산
    if len(statements) >= 5:
        latest = statements[0]
        year_ago = statements[4]
        result['yoy'] = _calculate_change(latest, year_ago)
    
    # 4분기 추세 분석
    if len(statements) >= 4:
        result['trend'] = _analyze_trend(statements[:4])
    
    return result


def _calculate_change(current: Any, previous: Any) -> Dict[str, float]:
    """두 기간 사이의 증감률 계산"""
    changes = {}
    
    if not (current.raw_data and previous.raw_data):
        return changes
    
    metrics = [
        'revenue', 'operating_income', 'net_income',
        'total_assets', 'total_equity', 'operating_cash_flow',
        'investing_cash_flow', 'financing_cash_flow'
    ]
    
    for metric in metrics:
        curr_val = current.raw_data.get(metric)
        prev_val = previous.raw_data.get(metric)
        
        if curr_val and prev_val and prev_val != 0:
            change_pct = ((curr_val - prev_val) / abs(prev_val)) * 100
            changes[metric] = round(change_pct, 1)
    
    # 비율 지표는 차이
    ratio_metrics = ['roe', 'roa', 'operating_margin', 'net_margin', 'debt_ratio']
    
    for metric in ratio_metrics:
        curr_val = current.raw_data.get(metric)
        prev_val = previous.raw_data.get(metric)
        
        if curr_val is not None and prev_val is not None:
            diff = curr_val - prev_val
            changes[metric + '_diff'] = round(diff, 1)
    
    return changes


def _analyze_trend(statements: List[Any]) -> Dict[str, str]:
    """4분기 추세 분석"""
    trends = {}
    
    metrics = ['revenue', 'operating_income', 'net_income', 'roe', 'operating_margin', 'operating_cash_flow']
    
    for metric in metrics:
        values = []
        for stmt in statements:
            if stmt.raw_data and stmt.raw_data.get(metric) is not None:
                values.append(stmt.raw_data[metric])
        
        if len(values) >= 3:
            increasing = sum(1 for i in range(len(values)-1) if values[i] > values[i+1])
            decreasing = sum(1 for i in range(len(values)-1) if values[i] < values[i+1])
            
            if increasing >= 2:
                trends[metric] = "📈 상승 추세"
            elif decreasing >= 2:
                trends[metric] = "📉 하락 추세"
            else:
                trends[metric] = "➡️ 횡보"
    
    return trends


def calculate_additional_metrics(statement: Any) -> Dict[str, Any]:
    """추가 재무 지표 계산"""
    metrics = {}
    
    if not statement.raw_data:
        return metrics
    
    data = statement.raw_data
    
    # 유동비율
    if data.get('current_assets') and data.get('current_liabilities'):
        current_ratio = (data['current_assets'] / data['current_liabilities']) * 100
        metrics['current_ratio'] = round(current_ratio, 1)
    
    # 당좌비율
    if data.get('current_assets') and data.get('inventories') and data.get('current_liabilities'):
        quick_assets = data['current_assets'] - data['inventories']
        quick_ratio = (quick_assets / data['current_liabilities']) * 100
        metrics['quick_ratio'] = round(quick_ratio, 1)
    
    # 자기자본비율
    if data.get('total_equity') and data.get('total_assets'):
        equity_ratio = (data['total_equity'] / data['total_assets']) * 100
        metrics['equity_ratio'] = round(equity_ratio, 1)
    
    # 이자보상배율
    if data.get('operating_income') and data.get('interest_expense') and data['interest_expense'] > 0:
        interest_coverage = data['operating_income'] / data['interest_expense']
        metrics['interest_coverage'] = round(interest_coverage, 2)
    
    # 잉여현금흐름 (FCF)
    if data.get('operating_cash_flow') and data.get('investing_cash_flow'):
        fcf = data['operating_cash_flow'] + data['investing_cash_flow']
        metrics['free_cash_flow'] = fcf
        metrics['free_cash_flow_billions'] = round(fcf / 100000000, 1)
    
    # 현금창출 품질
    if data.get('operating_cash_flow') and data.get('net_income') and data['net_income'] > 0:
        cf_to_ni_ratio = (data['operating_cash_flow'] / data['net_income']) * 100
        metrics['cf_to_ni_ratio'] = round(cf_to_ni_ratio, 1)
    
    # 현금흐름 마진
    if data.get('operating_cash_flow') and data.get('revenue') and data['revenue'] > 0:
        cf_margin = (data['operating_cash_flow'] / data['revenue']) * 100
        metrics['cf_margin'] = round(cf_margin, 1)
    
    return metrics


# 기존 함수와의 호환성을 위한 별칭
format_quarterly_trend = format_quarterly_metrics_horizontal
