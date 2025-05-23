#!/usr/bin/env python3
"""
Analyze Claude Code costs and project future expenses
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

PROMETHEUS_URL = "http://localhost:9090"

# Claude pricing (as of 2025)
PRICING = {
    'claude-3-5-haiku-20241022': {
        'input': 0.001,   # per 1K tokens
        'output': 0.005,  # per 1K tokens
    },
    'claude-3-opus-20240229': {
        'input': 0.015,
        'output': 0.075,
    },
    'claude-3-sonnet-20240229': {
        'input': 0.003,
        'output': 0.015,
    }
}

def get_cost_metrics(days=30):
    """Fetch cost metrics from Prometheus"""
    query = 'otel_claude_code_cost_usage_USD_total'
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    response = requests.get(f"{PROMETHEUS_URL}/api/v1/query_range", params={
        'query': f'sum by (model) ({query})',
        'start': start_time.isoformat(),
        'end': end_time.isoformat(),
        'step': '1d'
    })
    
    if response.status_code != 200:
        return None
    
    return response.json()

def analyze_cost_trends(data):
    """Analyze cost trends and project future costs"""
    if not data or 'data' not in data:
        return None
    
    results = []
    for series in data['data']['result']:
        model = series['metric'].get('model', 'unknown')
        values = series['values']
        
        # Convert to DataFrame
        df = pd.DataFrame(values, columns=['timestamp', 'cost'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        df['cost'] = df['cost'].astype(float)
        df['model'] = model
        
        results.append(df)
    
    if results:
        return pd.concat(results, ignore_index=True)
    return None

def project_monthly_cost(df):
    """Project monthly costs based on current usage"""
    if df is None or df.empty:
        return {}
    
    # Calculate daily average
    df['date'] = df['timestamp'].dt.date
    daily_costs = df.groupby(['date', 'model'])['cost'].max().reset_index()
    
    # Calculate daily increase
    daily_avg = daily_costs.groupby('model')['cost'].diff().mean()
    
    projections = {}
    for model in daily_costs['model'].unique():
        model_data = daily_costs[daily_costs['model'] == model]
        if not model_data.empty:
            current_cost = model_data['cost'].iloc[-1]
            daily_increase = daily_avg if pd.notna(daily_avg) else 0
            projected_monthly = current_cost + (daily_increase * 30)
            projections[model] = {
                'current': current_cost,
                'daily_avg_increase': daily_increase,
                'projected_monthly': projected_monthly
            }
    
    return projections

def visualize_costs(df):
    """Create cost visualization"""
    if df is None or df.empty:
        return
    
    plt.figure(figsize=(12, 6))
    
    for model in df['model'].unique():
        model_data = df[df['model'] == model]
        plt.plot(model_data['timestamp'], model_data['cost'], 
                label=model, marker='o')
    
    plt.xlabel('Date')
    plt.ylabel('Cost (USD)')
    plt.title('Claude Code Costs Over Time')
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('exports/cost_trends.png')
    plt.close()

if __name__ == "__main__":
    data = get_cost_metrics()
    df = analyze_cost_trends(data)
    
    if df is not None:
        projections = project_monthly_cost(df)
        print("Cost Projections:")
        for model, proj in projections.items():
            print(f"\n{model}:")
            print(f"  Current total: ${proj['current']:.4f}")
            print(f"  Daily average increase: ${proj['daily_avg_increase']:.4f}")
            print(f"  Projected monthly: ${proj['projected_monthly']:.2f}")
        
        visualize_costs(df)
        print("\nCost trend chart saved to exports/cost_trends.png")
