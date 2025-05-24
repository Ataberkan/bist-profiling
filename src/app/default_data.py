"""
Default data module.
"""

from src.app.models import Cluster

def create_default_clusters(session):
    """
    Adds default cluster data to the database.
    """
    default_clusters = [
        Cluster(
            id=0,
            name="Balanced Volatility, Moderate Risk",
            color="#3b82f6",  # Primary Blue
            avg_volatility=1.43,
            avg_change=0.18,
            avg_beta=1.12,
            risk_return_ratio=0.15,
            summary="Stocks in this cluster show a stable profile with balanced volatility and moderate risk level.",
            investor_profile="Balanced"
        ),
        Cluster(
            id=1,
            name="Low Volatility, Stable",
            color="#22c55e",  # Success Green
            avg_volatility=2.18,
            avg_change=-0.67,
            avg_beta=0.85,
            risk_return_ratio=-0.38,
            summary="Stocks in this cluster show low volatility and stable performance.",
            investor_profile="Conservative"
        ),
        Cluster(
            id=2,
            name="High Volatility, High Risk",
            color="#f59e0b",  # Warning Orange
            avg_volatility=3.61,
            avg_change=-1.20,
            avg_beta=1.95,
            risk_return_ratio=-0.32,
            summary="Stocks in this cluster show an aggressive profile with high volatility and high risk level.",
            investor_profile="Aggressive"
        ),
        Cluster(
            id=3,
            name="Positive Return, Moderate Volatility",
            color="#ef4444",  # Danger Red
            avg_volatility=2.14,
            avg_change=0.58,
            avg_beta=1.55,
            risk_return_ratio=0.46,
            summary="Stocks in this cluster show a growth-oriented profile with positive returns and moderate volatility.",
            investor_profile="Growth Oriented"
        )
    ]
    
    for cluster in default_clusters:
        session.add(cluster)
    
    session.commit()
    print("Default clusters created.") 