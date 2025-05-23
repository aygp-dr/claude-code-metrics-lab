#!/usr/bin/env python3
"""
Analyze Claude Code session patterns
"""
import requests
from datetime import datetime, timedelta
from collections import Counter
import json

PROMETHEUS_URL = "http://localhost:9090"

def get_session_patterns(days=7):
    """Analyze session patterns - when do you use Claude most?"""
    query = 'otel_claude_code_session_count_total'
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    response = requests.get(f"{PROMETHEUS_URL}/api/v1/query_range", params={
        'query': f'increase({query}[1h])',
        'start': start_time.isoformat(),
        'end': end_time.isoformat(),
        'step': '1h'
    })
    
    if response.status_code != 200:
        return None
    
    data = response.json()
    
    # Analyze patterns
    hour_counts = Counter()
    day_counts = Counter()
    
    for result in data.get('data', {}).get('result', []):
        for timestamp, value in result['values']:
            if float(value) > 0:
                dt = datetime.fromtimestamp(float(timestamp))
                hour_counts[dt.hour] += 1
                day_counts[dt.strftime('%A')] += 1
    
    return {
        'peak_hours': hour_counts.most_common(5),
        'peak_days': day_counts.most_common(7),
        'total_sessions': sum(hour_counts.values())
    }

def get_token_efficiency():
    """Calculate token efficiency metrics"""
    # Get input vs output token ratio
    input_query = 'sum(otel_claude_code_token_usage_tokens_total{type="input"})'
    output_query = 'sum(otel_claude_code_token_usage_tokens_total{type="output"})'
    
    input_resp = requests.get(f"{PROMETHEUS_URL}/api/v1/query", 
                             params={'query': input_query})
    output_resp = requests.get(f"{PROMETHEUS_URL}/api/v1/query", 
                              params={'query': output_query})
    
    if input_resp.status_code == 200 and output_resp.status_code == 200:
        input_data = input_resp.json()
        output_data = output_resp.json()
        
        input_tokens = float(input_data['data']['result'][0]['value'][1]) if input_data['data']['result'] else 0
        output_tokens = float(output_data['data']['result'][0]['value'][1]) if output_data['data']['result'] else 0
        
        if input_tokens > 0:
            efficiency_ratio = output_tokens / input_tokens
            return {
                'input_tokens': int(input_tokens),
                'output_tokens': int(output_tokens),
                'efficiency_ratio': round(efficiency_ratio, 2),
                'interpretation': 'High efficiency' if efficiency_ratio > 10 else 'Normal efficiency'
            }
    
    return None

if __name__ == "__main__":
    patterns = get_session_patterns()
    if patterns:
        print("Session Patterns (Last 7 Days):")
        print(f"Total sessions: {patterns['total_sessions']}")
        print("\nPeak hours (24h format):")
        for hour, count in patterns['peak_hours']:
            print(f"  {hour:02d}:00 - {count} sessions")
        print("\nPeak days:")
        for day, count in patterns['peak_days']:
            print(f"  {day}: {count} sessions")
    
    efficiency = get_token_efficiency()
    if efficiency:
        print("\nToken Efficiency:")
        print(f"  Input tokens: {efficiency['input_tokens']:,}")
        print(f"  Output tokens: {efficiency['output_tokens']:,}")
        print(f"  Efficiency ratio: {efficiency['efficiency_ratio']}x")
        print(f"  Assessment: {efficiency['interpretation']}")
