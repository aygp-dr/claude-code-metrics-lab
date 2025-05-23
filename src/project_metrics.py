#!/usr/bin/env python3
"""
Aggregate Claude Code metrics by project based on working directory
"""
import os
import json
import requests
from datetime import datetime, timedelta
from collections import defaultdict

PROMETHEUS_URL = "http://localhost:9090"

def get_project_metrics(days=30):
    """Fetch Claude metrics and group by project"""
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    # Query for token usage
    query = 'otel_claude_code_token_usage_tokens_total'
    response = requests.get(f"{PROMETHEUS_URL}/api/v1/query_range", params={
        'query': query,
        'start': start_time.isoformat(),
        'end': end_time.isoformat(),
        'step': '1h'
    })
    
    if response.status_code != 200:
        return None
    
    data = response.json()
    project_metrics = defaultdict(lambda: {
        'tokens': 0,
        'cost': 0.0,
        'sessions': 0,
        'models': defaultdict(int)
    })
    
    # Process results
    for result in data.get('data', {}).get('result', []):
        metric = result['metric']
        # Extract project from session metadata if available
        # For now, aggregate by model
        model = metric.get('model', 'unknown')
        
        for value in result['values']:
            timestamp, token_count = value
            project_metrics['all']['tokens'] += int(float(token_count))
            project_metrics['all']['models'][model] += int(float(token_count))
    
    return dict(project_metrics)

def export_metrics(metrics, output_dir='exports'):
    """Export metrics to JSON file"""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{output_dir}/claude_metrics_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'metrics': metrics
        }, f, indent=2)
    
    print(f"Metrics exported to {filename}")
    return filename

if __name__ == "__main__":
    metrics = get_project_metrics()
    if metrics:
        export_metrics(metrics)
        print(json.dumps(metrics, indent=2))
