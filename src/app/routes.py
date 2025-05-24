"""
Flask application routes
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
import pandas as pd
import numpy as np
import os
import sys
import matplotlib
matplotlib.use('Agg')  # For matplotlib usage without GUI
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from datetime import datetime, date
from src.app.models import Stock, Cluster
from src.app import db
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import re

# Add main folder to access other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Import data and model modules
from src.models.clustering_model import apply_kmeans, find_optimal_k
from src.analysis.data_analysis_preprocessing import calculate_descriptive_statistics

# Define Blueprint
main_bp = Blueprint('main', __name__)

# Helper functions for CSRF protection
def generate_csrf_token():
    """Generates CSRF token and saves to session"""
    if 'csrf_token' not in session:
        session['csrf_token'] = os.urandom(24).hex()
    return session['csrf_token']

def check_csrf_token(form_token):
    """Checks CSRF token sent with form"""
    session_token = session.get('csrf_token', None)
    return session_token is not None and session_token == form_token

# Decorator for user login control
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('You must log in to view this page.', 'warning')
            return redirect(url_for('main.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Data paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
PRICE_DATA_FILE = os.path.join(DATA_DIR, "price_bist30_historical_data_13052025_7days.csv")
CLUSTERING_RESULTS_FILE = os.path.join(DATA_DIR, "clustering_results.csv")
FEATURE_ENGINEERED_FILE = os.path.join(DATA_DIR, "feature_engineered_data.csv")
PROCESSED_DATA_FILE = os.path.join(DATA_DIR, "processed_bist30_data.csv")

# Cluster color mapping - Compatible with pastel colors
CLUSTER_COLORS = {
    0: "rgba(59, 130, 246, 0.6)",   # Pastel Blue - Balanced Volatility
    1: "rgba(34, 197, 94, 0.6)",    # Pastel Green - Low Volatility  
    2: "rgba(245, 158, 11, 0.6)",   # Pastel Orange - High Volatility
    3: "rgba(239, 68, 68, 0.6)",    # Pastel Red - Positive Return
}

# Cluster descriptions
CLUSTER_DESCRIPTIONS = {
    0: {
        "name": "Balanced Volatility, Moderate Risk",
        "summary": "Stocks in this cluster show a stable profile with balanced volatility and moderate risk level. Banking and technology stocks are predominant.",
        "avg_volatility": 1.43,
        "avg_change": 0.18,
        "avg_beta": 1.12,
        "investor_profile": "Balanced",
        "stocks": ["AKBNK", "ASELS", "GARAN", "HEKTS", "ISCTR", "KOZAL", "PGSUS", "SAHOL", "TCELL", "TTKOM", "TUPRS"]
    },
    1: {
        "name": "Low Volatility, Stable",
        "summary": "Stocks in this cluster show low volatility and stable performance. Suitable for conservative investors.",
        "avg_volatility": 2.18,
        "avg_change": -0.67,
        "avg_beta": 0.85,
        "investor_profile": "Conservative",
        "stocks": ["AEFES", "BIMAS", "CIMSA", "ENKAI", "EREGL", "KRDMD", "MGROS", "PETKM", "SASA", "SISE", "TAVHL", "THYAO", "ULKER"]
    },
    2: {
        "name": "High Volatility, High Risk",
        "summary": "Stocks in this cluster show an aggressive profile with high volatility and high risk level. Suitable for experienced investors.",
        "avg_volatility": 3.61,
        "avg_change": -1.20,
        "avg_beta": 1.95,
        "investor_profile": "Aggressive",
        "stocks": ["ASTOR", "FROTO", "TOASO"]
    },
    3: {
        "name": "Positive Return, Moderate Volatility",
        "summary": "Stocks in this cluster show a growth-oriented profile with positive returns and moderate volatility. Suitable for growth-seeking investors.",
        "avg_volatility": 2.14,
        "avg_change": 0.58,
        "avg_beta": 1.55,
        "investor_profile": "Growth Oriented",
        "stocks": ["EKGYO", "KCHOL", "YKBNK"]
    }
}


@main_bp.route('/')
def index():
    """Homepage."""
    # Average values
    avg_change = db.session.query(db.func.avg(Stock.avg_change)).scalar() or 0
    avg_volatility = db.session.query(db.func.avg(Stock.volatility)).scalar() or 0
    
    # Highest gain and loss
    max_gain_stock = db.session.query(Stock).order_by(Stock.max_gain.desc()).first()
    max_loss_stock = db.session.query(Stock).order_by(Stock.max_loss).first()
    
    # Featured stocks (one from each cluster)
    featured_stocks = db.session.query(Stock).join(Cluster).group_by(Cluster.id).all()
    
    # Get all stocks (for homepage table)
    all_stocks = db.session.query(Stock).join(Cluster).order_by(Stock.code).all()
    
    # Get cluster data with stock counts
    clusters = []
    total_stocks = db.session.query(Stock).count()
    for cluster in db.session.query(Cluster).all():
        stock_count = db.session.query(Stock).filter_by(cluster_id=cluster.id).count()
        cluster_data = {
            'id': cluster.id,
            'name': cluster.name,
            'color': cluster.color,
            'stock_count': stock_count
        }
        clusters.append(cluster_data)
    
    # Get cluster colors
    cluster_colors = {cluster.id: cluster.color for cluster in db.session.query(Cluster).all()}
    
    # Generate CSRF token
    csrf_token = generate_csrf_token()
    
    return render_template('index.html', 
                          update_date=date.today().strftime('%d.%m.%Y'),
                          avg_change=avg_change,  # Send as numeric value
                          avg_volatility=avg_volatility,  # Send as numeric value
                          max_gain=max_gain_stock.max_gain if max_gain_stock else 0,
                          max_gain_stock=max_gain_stock.code if max_gain_stock else "",
                          max_loss=max_loss_stock.max_loss if max_loss_stock else 0,
                          max_loss_stock=max_loss_stock.code if max_loss_stock else "",
                          featured_stocks=featured_stocks,
                          all_stocks=all_stocks,  # Add all stocks
                          clusters=clusters,  # Add cluster data with counts
                          total_stocks=total_stocks,  # Add total stock count
                          cluster_colors=cluster_colors,
                          csrf_token=csrf_token)


@main_bp.route('/clusters')
def clusters():
    """Clustering analysis page - dedicated page for cluster analysis."""
    clusters_data = {}
    
    # All clusters and stocks
    for cluster in db.session.query(Cluster).all():
        cluster_stocks = db.session.query(Stock).filter_by(cluster_id=cluster.id).all()
        clusters_data[cluster.id] = [stock.code for stock in cluster_stocks]
    
    # Cluster colors and descriptions
    cluster_colors = {cluster.id: cluster.color for cluster in db.session.query(Cluster).all()}
    cluster_descriptions = {cluster.id: cluster for cluster in db.session.query(Cluster).all()}
    
    return render_template('clusters.html',
                          update_date=date.today().strftime('%d.%m.%Y'),
                          clusters_data=clusters_data,
                          cluster_colors=cluster_colors,
                          cluster_descriptions=cluster_descriptions)


@main_bp.route('/risk_profiling')
def risk_profiling():
    """Risk profiling page."""
    clusters_data = {}
    
    # All clusters and stocks
    for cluster in db.session.query(Cluster).all():
        cluster_stocks = db.session.query(Stock).filter_by(cluster_id=cluster.id).all()
        clusters_data[cluster.id] = [stock.code for stock in cluster_stocks]
    
    # Cluster colors and descriptions
    cluster_colors = {cluster.id: cluster.color for cluster in db.session.query(Cluster).all()}
    cluster_descriptions = {cluster.id: cluster for cluster in db.session.query(Cluster).all()}
    
    return render_template('risk_profiling.html',
                          update_date=date.today().strftime('%d.%m.%Y'),
                          clusters_data=clusters_data,
                          cluster_colors=cluster_colors,
                          cluster_descriptions=cluster_descriptions)


@main_bp.route('/stocks')
def stocks():
    """Stock details page."""
    # Filtering parameters
    search = request.args.get('search', '')
    cluster_id = request.args.get('cluster', '')
    min_volatility = request.args.get('volatility', '')
    min_beta = request.args.get('beta', '')
    
    # Build query
    query = db.session.query(Stock)
    
    # Apply filters
    if search:
        query = query.filter(Stock.code.ilike(f'%{search}%'))
    if cluster_id:
        query = query.filter(Stock.cluster_id == cluster_id)
    if min_volatility:
        query = query.filter(Stock.volatility >= float(min_volatility))
    if min_beta:
        query = query.filter(Stock.beta >= float(min_beta))
    
    # Get stocks
    all_stocks = query.all()
    
    # Get clusters
    clusters = db.session.query(Cluster).all()
    
    return render_template('stocks.html',
                          update_date=date.today().strftime('%d.%m.%Y'),
                          stocks=all_stocks,
                          clusters=clusters)


@main_bp.route('/stock/<stock_code>')
def stock_detail(stock_code):
    """Stock detail page."""
    # Find the stock
    stock = db.session.query(Stock).filter_by(code=stock_code).first_or_404()
    
    return render_template('stock_detail.html',
                          stock=stock,
                          update_date=date.today().strftime('%d.%m.%Y'))


# General route for pages under construction
@main_bp.route('/<page_name>')
def under_construction(page_name):
    """For pages under construction."""
    # Convert page name to human-readable format
    page_title = page_name.replace('_', ' ').title()
    
    return render_template('under_construction.html', 
                          title=page_title,
                          update_date=date.today().strftime('%d.%m.%Y'))


# Routes for special pages
@main_bp.route('/sector_analysis')
def sector_analysis():
    """Sector analysis page."""
    
    # Sample sector data
    sectors = [
        {
            "id": 1,
            "name": "Banking",
            "change": 2.4,
            "market_cap": 425.7,  # billion TL
            "pe_ratio": 6.2,
            "pb_ratio": 0.95,
            "dividend_yield": 2.2,
            "roe": 16.8,
            "stocks_count": 12,
            "performance": {
                "daily": 1.8,
                "weekly": 3.2,
                "monthly": 5.7,
                "yearly": 22.5
            }
        },
        {
            "id": 2,
            "name": "Holding",
            "change": 1.8,
            "market_cap": 380.3,  # billion TL
            "pe_ratio": 8.5,
            "pb_ratio": 1.2,
            "dividend_yield": 1.8,
            "roe": 14.2,
            "stocks_count": 18,
            "performance": {
                "daily": 1.2,
                "weekly": 2.5,
                "monthly": 4.8,
                "yearly": 18.6
            }
        },
        {
            "id": 3,
            "name": "Industrial",
            "change": 1.2,
            "market_cap": 310.6,  # billion TL
            "pe_ratio": 9.8,
            "pb_ratio": 1.4,
            "dividend_yield": 1.5,
            "roe": 12.5,
            "stocks_count": 26,
            "performance": {
                "daily": 0.9,
                "weekly": 1.8,
                "monthly": 3.5,
                "yearly": 15.4
            }
        },
        {
            "id": 4,
            "name": "Technology",
            "change": 0.9,
            "market_cap": 125.2,  # billion TL
            "pe_ratio": 15.4,
            "pb_ratio": 2.8,
            "dividend_yield": 0.8,
            "roe": 18.2,
            "stocks_count": 9,
            "performance": {
                "daily": 0.5,
                "weekly": 1.2,
                "monthly": 6.2,
                "yearly": 32.8
            }
        },
        {
            "id": 5,
            "name": "Food & Beverage",
            "change": 0.7,
            "market_cap": 190.5,  # billion TL
            "pe_ratio": 11.2,
            "pb_ratio": 1.6,
            "dividend_yield": 2.0,
            "roe": 11.8,
            "stocks_count": 14,
            "performance": {
                "daily": 0.6,
                "weekly": 1.4,
                "monthly": 2.8,
                "yearly": 12.5
            }
        },
        {
            "id": 6,
            "name": "Construction",
            "change": 0.4,
            "market_cap": 85.3,  # billion TL
            "pe_ratio": 7.8,
            "pb_ratio": 0.85,
            "dividend_yield": 1.2,
            "roe": 9.5,
            "stocks_count": 16,
            "performance": {
                "daily": 0.3,
                "weekly": 0.9,
                "monthly": 2.1,
                "yearly": 8.6
            }
        },
        {
            "id": 7,
            "name": "Cement",
            "change": 0.0,
            "market_cap": 76.1,  # billion TL
            "pe_ratio": 8.9,
            "pb_ratio": 1.1,
            "dividend_yield": 1.9,
            "roe": 10.2,
            "stocks_count": 11,
            "performance": {
                "daily": 0.0,
                "weekly": 0.5,
                "monthly": 1.8,
                "yearly": 6.5
            }
        },
        {
            "id": 8,
            "name": "Textile",
            "change": -0.3,
            "market_cap": 42.8,  # billion TL
            "pe_ratio": 6.5,
            "pb_ratio": 0.75,
            "dividend_yield": 1.1,
            "roe": 8.4,
            "stocks_count": 20,
            "performance": {
                "daily": -0.3,
                "weekly": -0.8,
                "monthly": -1.6,
                "yearly": 4.2
            }
        },
        {
            "id": 9,
            "name": "Tourism",
            "change": -0.8,
            "market_cap": 38.5,  # billion TL
            "pe_ratio": 9.2,
            "pb_ratio": 1.25,
            "dividend_yield": 0.9,
            "roe": 7.8,
            "stocks_count": 8,
            "performance": {
                "daily": -0.8,
                "weekly": -1.5,
                "monthly": -2.8,
                "yearly": 10.5
            }
        },
        {
            "id": 10,
            "name": "Energy",
            "change": -1.1,
            "market_cap": 130.4,  # billion TL
            "pe_ratio": 7.6,
            "pb_ratio": 1.05,
            "dividend_yield": 2.4,
            "roe": 11.6,
            "stocks_count": 15,
            "performance": {
                "daily": -1.1,
                "weekly": -2.2,
                "monthly": -3.5,
                "yearly": 5.8
            }
        },
    ]
    
    # Sector correlation matrix (sample)
    correlation_matrix = {
        "sectors": ["Banking", "Holding", "Industrial", "Technology", "Food"],
        "data": [
            [1.00, 0.85, 0.62, 0.48, 0.56],
            [0.85, 1.00, 0.70, 0.52, 0.60],
            [0.62, 0.70, 1.00, 0.65, 0.58],
            [0.48, 0.52, 0.65, 1.00, 0.42],
            [0.56, 0.60, 0.58, 0.42, 1.00]
        ]
    }
    
    # Sector rotation data (sample)
    sector_rotation = {
        "periods": ["Q1 2023", "Q2 2023", "Q3 2023", "Q4 2023", "Q1 2024"],
        "best_performing": ["Technology", "Banking", "Holding", "Industrial", "Banking"],
        "worst_performing": ["Tourism", "Textile", "Energy", "Construction", "Tourism"],
        "rotation_trends": [
            {"from": "Tourism", "to": "Technology", "period": "Q1 2023", "strength": "Strong"},
            {"from": "Energy", "to": "Banking", "period": "Q2 2023", "strength": "Medium"},
            {"from": "Textile", "to": "Holding", "period": "Q3 2023", "strength": "Weak"},
            {"from": "Cement", "to": "Industrial", "period": "Q4 2023", "strength": "Medium"},
            {"from": "Construction", "to": "Banking", "period": "Q1 2024", "strength": "Strong"}
        ]
    }
    
    # Sectoral clustering data (sample)
    sector_clusters = [
        {
            "id": 1,
            "name": "High Growth",
            "sectors": ["Technology", "Banking"],
            "avg_pe": 10.8,
            "avg_growth": 27.6,
            "volatility": "High"
        },
        {
            "id": 2,
            "name": "Balanced Growth",
            "sectors": ["Holding", "Industrial", "Food"],
            "avg_pe": 9.8,
            "avg_growth": 15.5,
            "volatility": "Medium"
        },
        {
            "id": 3,
            "name": "Value Sectors",
            "sectors": ["Construction", "Cement", "Energy"],
            "avg_pe": 8.1,
            "avg_growth": 7.0,
            "volatility": "Low"
        },
        {
            "id": 4,
            "name": "Cyclical Sectors",
            "sectors": ["Tourism", "Textile"],
            "avg_pe": 7.8,
            "avg_growth": 7.3,
            "volatility": "Very High"
        }
    ]
    
    return render_template('sector_analysis.html',
                          title="Sector Analysis",
                          update_date=date.today().strftime('%d.%m.%Y'),
                          sectors=sectors,
                          correlation_matrix=correlation_matrix,
                          sector_rotation=sector_rotation,
                          sector_clusters=sector_clusters)


@main_bp.route('/portfolio_builder')
def portfolio_builder():
    """Portfolio management page."""
    return render_template('portfolio_builder.html',
                          title="Portfolio Management",
                          update_date=date.today().strftime('%d.%m.%Y'))


@main_bp.route('/technical_analysis')
def technical_analysis():
    """Technical analysis page."""
    return render_template('technical_analysis.html',
                          title="Technical Analysis",
                          update_date=date.today().strftime('%d.%m.%Y'))


@main_bp.route('/fundamental_analysis')
def fundamental_analysis():
    """Fundamental analysis page."""
    
    # Sample stock data (in real application, this would come from database)
    sample_stocks = [
        {
            "code": "GARAN",
            "name": "Garanti Bank",
            "sector": "Banking",
            "price": 24.82,
            "change": 1.72,
            "pe_ratio": 6.8,
            "pb_ratio": 0.95,
            "market_cap": 104.2,  # billion TL
            "dividend_yield": 2.1,
            "roe": 18.5,  # %
            "roa": 1.8,  # %
            "net_profit_margin": 28.4  # %
        },
        {
            "code": "THYAO",
            "name": "Turkish Airlines",
            "sector": "Transportation",
            "price": 294.6,
            "change": 1.9,
            "pe_ratio": 4.2,
            "pb_ratio": 1.45,
            "market_cap": 406.5,  # billion TL
            "dividend_yield": 0.0,
            "roe": 34.6,  # %
            "roa": 12.2,  # %
            "net_profit_margin": 22.8  # %
        },
        {
            "code": "KCHOL",
            "name": "Koc Holding",
            "sector": "Holding",
            "price": 142.9,
            "change": 1.5,
            "pe_ratio": 8.4,
            "pb_ratio": 1.25,
            "market_cap": 362.3,  # billion TL
            "dividend_yield": 1.8,
            "roe": 15.2,  # %
            "roa": 5.6,  # %
            "net_profit_margin": 12.5  # %
        },
    ]
    
    # Sector averages
    sector_averages = {
        "Banking": {"pe_ratio": 5.6, "pb_ratio": 0.85, "roe": 16.8, "dividend_yield": 2.3},
        "Transportation": {"pe_ratio": 6.1, "pb_ratio": 1.42, "roe": 21.5, "dividend_yield": 0.8},
        "Holding": {"pe_ratio": 7.8, "pb_ratio": 1.15, "roe": 14.2, "dividend_yield": 1.5},
    }
    
    # Annual financial data (sample)
    historical_financials = {
        "years": ["2019", "2020", "2021", "2022", "2023"],
        "revenue": [45.2, 48.6, 62.8, 78.5, 96.2],  # billion TL
        "net_income": [6.2, 5.8, 8.4, 12.6, 18.5],  # billion TL
        "assets": [125.4, 138.2, 152.6, 180.4, 210.5],  # billion TL
        "equity": [32.5, 35.8, 42.1, 52.8, 65.4],  # billion TL
        "liabilities": [92.9, 102.4, 110.5, 127.6, 145.1],  # billion TL
    }
    
    # Financial ratios
    financial_ratios = {
        "liquidity_ratio": 1.42,
        "debt_to_equity": 2.22,
        "interest_coverage": 4.8,
        "asset_turnover": 0.45,
        "inventory_turnover": 12.6
    }
    
    return render_template('fundamental_analysis.html',
                          title="Fundamental Analysis",
                          update_date=date.today().strftime('%d.%m.%Y'),
                          stocks=sample_stocks,
                          sector_averages=sector_averages,
                          historical_financials=historical_financials,
                          financial_ratios=financial_ratios)


@main_bp.route('/market_observer')
def market_observer():
    """Market Observer page."""
    # Market data
    
    # BIST-100 daily change
    bist100_change = 1.45  # Sample data
    
    # Sectoral data - sample data
    sectors = [
        {"id": 1, "name": "Banking", "change": 2.4, "market_cap": 425.7, "pe_ratio": 6.2, "volume": 1850},
        {"id": 2, "name": "Holding", "change": 1.8, "market_cap": 380.3, "pe_ratio": 8.5, "volume": 1250},
        {"id": 3, "name": "Industrial", "change": 1.2, "market_cap": 310.6, "pe_ratio": 9.8, "volume": 980},
        {"id": 4, "name": "Technology", "change": 0.9, "market_cap": 125.2, "pe_ratio": 15.4, "volume": 450},
        {"id": 5, "name": "Food", "change": 0.7, "market_cap": 190.5, "pe_ratio": 11.2, "volume": 630},
        {"id": 6, "name": "Construction", "change": 0.4, "market_cap": 85.3, "pe_ratio": 7.8, "volume": 520},
        {"id": 7, "name": "Cement", "change": 0.0, "market_cap": 76.1, "pe_ratio": 8.9, "volume": 320},
        {"id": 8, "name": "Textile", "change": -0.3, "market_cap": 42.8, "pe_ratio": 6.5, "volume": 280},
        {"id": 9, "name": "Tourism", "change": -0.8, "market_cap": 38.5, "pe_ratio": 9.2, "volume": 190},
        {"id": 10, "name": "Energy", "change": -1.1, "market_cap": 130.4, "pe_ratio": 7.6, "volume": 580},
        {"id": 11, "name": "Mining", "change": -1.7, "market_cap": 55.2, "pe_ratio": 5.9, "volume": 420},
    ]
    
    # Macroeconomic indicators
    macro_indicators = [
        {"name": "CBRT Interest Rate", "value": "42.5%", "change": "-0.5%", "date": "10.05.2025"},
        {"name": "Inflation (CPI)", "value": "48.2%", "change": "+0.8%", "date": "05.05.2025"},
        {"name": "Inflation (PPI)", "value": "52.4%", "change": "+1.2%", "date": "05.05.2025"},
        {"name": "Unemployment Rate", "value": "9.8%", "change": "-0.3%", "date": "01.05.2025"},
        {"name": "Industrial Production", "value": "4.6%", "change": "+0.9%", "date": "01.05.2025"},
        {"name": "Current Account Deficit (billion $)", "value": "3.2", "change": "-0.5", "date": "28.04.2025"},
        {"name": "GDP Growth", "value": "3.1%", "change": "+0.4%", "date": "20.04.2025"},
    ]
    
    # Most traded stocks
    top_traded_stocks = [
        {"code": "GARAN", "name": "Garanti Bank", "volume": 450.2, "price": 102.5, "change": 2.1},
        {"code": "ASELS", "name": "Aselsan", "volume": 380.7, "price": 142.2, "change": 4.8},
        {"code": "THYAO", "name": "Turkish Airlines", "volume": 350.5, "price": 294.6, "change": 1.9},
        {"code": "KCHOL", "name": "Koc Holding", "volume": 320.3, "price": 142.9, "change": 1.5},
        {"code": "YKBNK", "name": "Yapi Kredi Bank", "volume": 310.1, "price": 23.9, "change": 0.8},
        {"code": "AKBNK", "name": "Akbank", "volume": 290.6, "price": 50.1, "change": 1.2},
        {"code": "SAHOL", "name": "Sabanci Holding", "volume": 270.4, "price": 75.0, "change": 0.9},
        {"code": "SISE", "name": "Sisecam", "volume": 250.2, "price": 34.7, "change": 1.6}
    ]
    
    # Liquidity metrics
    liquidity_metrics = {
        "daily_trading_volume": 28.5,  # billion TL
        "average_spread": 0.12,  # %
        "turnover_ratio": 0.35,  # %
        "market_depth": 86.4,  # million TL
        "volatility_index": 24.2  # VIX-like
    }
    
    # Foreign investor data
    foreign_investor_data = {
        "net_inflow_weekly": -125.4,  # million $
        "ownership_ratio": 32.8,  # %
        "largest_transactions": [
            {"stock": "SASA", "volume": 85.2, "type": "Sale"},
            {"stock": "BIMAS", "volume": 72.6, "type": "Purchase"},
            {"stock": "FROTO", "volume": 64.8, "type": "Purchase"}
        ]
    }
    
    return render_template('market_observer.html',
                          title="Market Observer",
                          update_date=date.today().strftime('%d.%m.%Y'),
                          bist100_change=bist100_change,
                          sectors=sectors,
                          macro_indicators=macro_indicators,
                          top_traded_stocks=top_traded_stocks,
                          liquidity_metrics=liquidity_metrics,
                          foreign_investor_data=foreign_investor_data)


@main_bp.route('/comparison_tool')
def comparison_tool():
    """Comparison tool page."""
    
    # Sample stock data
    sample_stocks = [
        {
            "code": "GARAN", 
            "name": "Garanti Bank",
            "sector": "Banking",
            "price": 24.82,
            "change": 1.72,
            "pe_ratio": 6.8,
            "pb_ratio": 0.95,
            "market_cap": 104.2,  # billion TL
            "dividend_yield": 2.1,
            "roe": 18.5,  # %
            "beta": 1.1,
            "volatility": 3.8,  # %
            "yearly_return": 42.3,  # %
            "risk_cluster": 2
        },
        {
            "code": "THYAO", 
            "name": "Turkish Airlines",
            "sector": "Transportation",
            "price": 294.6,
            "change": 1.9,
            "pe_ratio": 4.2,
            "pb_ratio": 1.45,
            "market_cap": 406.5,  # billion TL
            "dividend_yield": 0.0,
            "roe": 34.6,  # %
            "beta": 1.4,
            "volatility": 5.6,  # %
            "yearly_return": 67.5,  # %
            "risk_cluster": 1
        },
        {
            "code": "KCHOL", 
            "name": "Koc Holding",
            "sector": "Holding",
            "price": 142.9,
            "change": 1.5,
            "pe_ratio": 8.4,
            "pb_ratio": 1.25,
            "market_cap": 362.3,  # billion TL
            "dividend_yield": 1.8,
            "roe": 15.2,  # %
            "beta": 0.9,
            "volatility": 2.9,  # %
            "yearly_return": 29.8,  # %
            "risk_cluster": 2
        },
        {
            "code": "ASELS", 
            "name": "Aselsan",
            "sector": "Defense",
            "price": 142.2,
            "change": 4.8,
            "pe_ratio": 9.2,
            "pb_ratio": 2.1,
            "market_cap": 85.3,  # billion TL
            "dividend_yield": 0.7,
            "roe": 22.3,  # %
            "beta": 1.2,
            "volatility": 4.5,  # %
            "yearly_return": 56.2,  # %
            "risk_cluster": 1
        },
        {
            "code": "TUPRS", 
            "name": "Tupras",
            "sector": "Energy",
            "price": 196.5,
            "change": -0.8,
            "pe_ratio": 5.6,
            "pb_ratio": 1.15,
            "market_cap": 49.2,  # billion TL
            "dividend_yield": 3.2,
            "roe": 20.4,  # %
            "beta": 0.8,
            "volatility": 3.1,  # %
            "yearly_return": 18.5,  # %
            "risk_cluster": 3
        }
    ]
    
    # Cluster information
    risk_clusters = [
        {
            "id": 1,
            "name": "High Volatility, High Return",
            "avg_beta": 1.35,
            "avg_volatility": 5.2,
            "avg_return": 58.4,
            "risk_profile": "Aggressive"
        },
        {
            "id": 2,
            "name": "Medium Volatility, Balanced Return",
            "avg_beta": 1.05,
            "avg_volatility": 3.5,
            "avg_return": 35.6,
            "risk_profile": "Balanced"
        },
        {
            "id": 3,
            "name": "Low Volatility, Stable Return",
            "avg_beta": 0.75,
            "avg_volatility": 2.8,
            "avg_return": 22.2,
            "risk_profile": "Conservative"
        }
    ]
    
    # Sector information
    sectors = [
        {"name": "Banking", "stock_count": 12, "avg_pe": 5.6, "avg_roe": 16.8},
        {"name": "Holding", "stock_count": 18, "avg_pe": 8.5, "avg_roe": 14.2},
        {"name": "Transportation", "stock_count": 8, "avg_pe": 6.1, "avg_roe": 21.5},
        {"name": "Defense", "stock_count": 5, "avg_pe": 11.2, "avg_roe": 19.8},
        {"name": "Energy", "stock_count": 15, "avg_pe": 7.6, "avg_roe": 11.6},
        {"name": "Technology", "stock_count": 9, "avg_pe": 15.4, "avg_roe": 18.2},
        {"name": "Food", "stock_count": 14, "avg_pe": 11.2, "avg_roe": 11.8},
        {"name": "Industrial", "stock_count": 26, "avg_pe": 9.8, "avg_roe": 12.5},
    ]
    
    # Correlation data (inter-stock)
    correlation_data = {
        "labels": ["GARAN", "THYAO", "KCHOL", "ASELS", "TUPRS"],
        "matrix": [
            [1.00, 0.45, 0.72, 0.38, 0.52],
            [0.45, 1.00, 0.56, 0.64, 0.31],
            [0.72, 0.56, 1.00, 0.48, 0.62],
            [0.38, 0.64, 0.48, 1.00, 0.25],
            [0.52, 0.31, 0.62, 0.25, 1.00]
        ]
    }
    
    # Technical indicators comparison
    technical_indicators = {
        "stocks": ["GARAN", "THYAO", "KCHOL", "ASELS", "TUPRS"],
        "rsi": [58.2, 72.5, 54.8, 68.3, 42.6],
        "macd": [0.12, 0.75, 0.08, 0.65, -0.22],
        "stochastic": [68.5, 85.2, 62.4, 78.9, 32.5],
        "bollinger": ["Neutral", "Overbought", "Neutral", "Overbought", "Neutral"],
        "moving_avg": ["Above", "Above", "Above", "Above", "Below"]
    }
    
    return render_template('comparison_tool.html',
                          title="Comparison Tool",
                          update_date=date.today().strftime('%d.%m.%Y'),
                          stocks=sample_stocks,
                          risk_clusters=risk_clusters,
                          sectors=sectors,
                          correlation_data=correlation_data,
                          technical_indicators=technical_indicators)


@main_bp.route('/investor_profile')
def investor_profile():
    return under_construction('investor_profile')


@main_bp.route('/education_center')
def education_center():
    """Education center page."""
    
    # Machine learning education topics
    ml_topics = [
        {
            "id": 1,
            "title": "What is Clustering Analysis?",
            "summary": "Clustering analysis is an unsupervised learning technique that groups data points based on their similarities.",
            "level": "Beginner",
            "duration": "15 min",
            "category": "Machine Learning",
            "image_url": "img/education/clustering.jpg"
        },
        {
            "id": 2,
            "title": "K-Means Algorithm",
            "summary": "K-Means is a popular clustering algorithm used to divide data points into a specified number of clusters.",
            "level": "Intermediate",
            "duration": "20 min",
            "category": "Machine Learning",
            "image_url": "img/education/kmeans.jpg"
        },
        {
            "id": 3,
            "title": "Machine Learning Applications in Stock Market Data",
            "summary": "Discover how machine learning techniques can be applied to stock market data.",
            "level": "Advanced",
            "duration": "30 min",
            "category": "Machine Learning",
            "image_url": "img/education/ml_finance.jpg"
        }
    ]
    
    # Investment strategies education topics
    investment_topics = [
        {
            "id": 4,
            "title": "Portfolio Diversification Strategies",
            "summary": "Learn portfolio diversification techniques to reduce risk and optimize returns.",
            "level": "Beginner",
            "duration": "25 min",
            "category": "Investment Strategies",
            "image_url": "img/education/diversification.jpg"
        },
        {
            "id": 5,
            "title": "Value Investing vs. Growth Investing",
            "summary": "Comparison of two popular investment strategies and their applications in Turkish market.",
            "level": "Beginner",
            "duration": "20 min",
            "category": "Investment Strategies",
            "image_url": "img/education/value_growth.jpg"
        },
        {
            "id": 6,
            "title": "Momentum Investment Strategy",
            "summary": "Learn investment decision-making strategies using price and volume momentum.",
            "level": "Intermediate",
            "duration": "25 min",
            "category": "Investment Strategies",
            "image_url": "img/education/momentum.jpg"
        }
    ]
    
    # Risk management education topics
    risk_topics = [
        {
            "id": 7,
            "title": "Investment Psychology and Behavioral Finance",
            "summary": "Learn about investors' cognitive biases and their impact on investment decisions.",
            "level": "Beginner",
            "duration": "15 min",
            "category": "Risk Management",
            "image_url": "img/education/psychology.jpg"
        },
        {
            "id": 8,
            "title": "Stop-Loss and Take-Profit Strategies",
            "summary": "Basic risk management techniques used to limit losses and secure profits.",
            "level": "Beginner",
            "duration": "15 min",
            "category": "Risk Management",
            "image_url": "img/education/stop_loss.jpg"
        },
        {
            "id": 9,
            "title": "Risk and Return Optimization",
            "summary": "Learn to optimize risk and return balance using Modern Portfolio Theory.",
            "level": "Advanced",
            "duration": "30 min",
            "category": "Risk Management",
            "image_url": "img/education/risk_return.jpg"
        }
    ]
    
    # Video lessons
    video_lessons = [
        {
            "id": 10,
            "title": "Balance Sheet Reading Guide",
            "summary": "Learn how to read and interpret company balance sheets.",
            "duration": "45:32",
            "views": 12458,
            "instructor": "Prof. Dr. John Smith",
            "image_url": "img/education/videos/balance_sheet.jpg"
        },
        {
            "id": 11,
            "title": "Technical Analysis Fundamentals",
            "summary": "Learn support, resistance, trend lines and basic technical indicators.",
            "duration": "38:15",
            "views": 18765,
            "instructor": "Michael Johnson",
            "image_url": "img/education/videos/technical.jpg"
        },
        {
            "id": 12,
            "title": "Impact of Macroeconomic Factors on Stock Market",
            "summary": "Understand how inflation, interest rates and economic indicators affect the stock market.",
            "duration": "52:20",
            "views": 8542,
            "instructor": "Dr. Sarah Williams",
            "image_url": "img/education/videos/macro.jpg"
        }
    ]
    
    # Glossary terms
    glossary_terms = [
        {"term": "Beta", "definition": "A coefficient that measures a stock's sensitivity to market movements."},
        {"term": "P/E Ratio", "definition": "Price/Earnings ratio, calculated by dividing a stock's price by its earnings per share."},
        {"term": "EBITDA", "definition": "Earnings Before Interest, Tax, Depreciation and Amortization, a metric showing operational performance."},
        {"term": "P/B Ratio", "definition": "Price to Book Value ratio, obtained by dividing a stock's market value by its book value."},
        {"term": "Volatility", "definition": "A measure of price variability of a financial asset."},
        {"term": "ROE", "definition": "Return on Equity, calculated by dividing net profit by equity."},
        {"term": "Liquidity", "definition": "The ability of an asset to be converted to cash quickly without value loss."},
        {"term": "RSI", "definition": "Relative Strength Index, a technical analysis indicator."},
        {"term": "MACD", "definition": "Moving Average Convergence Divergence, a popular trend-following technical analysis indicator."},
        {"term": "IPO", "definition": "Initial Public Offering, the process of selling a company's shares to the public for the first time."}
    ]
    
    # Learning paths
    learning_paths = [
        {
            "id": 1,
            "title": "Stock Market for Beginners",
            "summary": "Basic concepts and strategies for those new to stock market investing.",
            "topics_count": 8,
            "duration": "3 hours",
            "level": "Beginner",
            "image_url": "img/education/paths/beginners.jpg"
        },
        {
            "id": 2,
            "title": "Technical Analysis Expert",
            "summary": "Learn all technical analysis tools and strategies in depth.",
            "topics_count": 12,
            "duration": "6 hours",
            "level": "Intermediate-Advanced",
            "image_url": "img/education/paths/technical.jpg"
        },
        {
            "id": 3,
            "title": "Fundamental Analysis Expert",
            "summary": "Learn to analyze company financials and perform valuations.",
            "topics_count": 10,
            "duration": "5 hours",
            "level": "Intermediate-Advanced",
            "image_url": "img/education/paths/fundamental.jpg"
        }
    ]
    
    return render_template('education_center.html',
                          title="Education Center",
                          update_date=date.today().strftime('%d.%m.%Y'),
                          ml_topics=ml_topics,
                          investment_topics=investment_topics,
                          risk_topics=risk_topics,
                          video_lessons=video_lessons,
                          glossary_terms=glossary_terms,
                          learning_paths=learning_paths)


@main_bp.route('/visualizations')
def visualizations():
    return under_construction('visualizations')


@main_bp.route('/user_profile')
def user_profile():
    """User profile page."""
    
    # Sample user information
    user = {
        "id": 1,
        "username": "investor_123",
        "email": "example@email.com",
        "full_name": "John Doe",
        "join_date": "12.04.2023",
        "subscription_type": "Premium",
        "subscription_expires": "12.04.2024",
        "profile_image": "img/avatars/user1.png"
    }
    
    # User's watchlist
    watchlist = [
        {
            "id": 1,
            "code": "GARAN",
            "name": "Garanti Bank",
            "price": 24.82,
            "change": 1.72,
            "added_date": "15.05.2023",
            "price_target": 28.50,
            "notes": "Technically, 25.20 resistance should be monitored."
        },
        {
            "id": 2,
            "code": "THYAO",
            "name": "Turkish Airlines",
            "price": 294.60,
            "change": 1.90,
            "added_date": "22.06.2023",
            "price_target": 320.00,
            "notes": "Aircraft orders and tourism season impact should be tracked."
        },
        {
            "id": 3,
            "code": "KCHOL",
            "name": "Koc Holding",
            "price": 142.90,
            "change": 1.50,
            "added_date": "03.07.2023",
            "price_target": 160.00,
            "notes": "Dividend date approaching, financials are strong."
        }
    ]
    
    # User's portfolio
    portfolio = [
        {
            "id": 1,
            "code": "GARAN",
            "name": "Garanti Bank",
            "quantity": 500,
            "buy_price": 22.40,
            "current_price": 24.82,
            "total_value": 12410.00,
            "profit_loss": 1210.00,
            "profit_loss_percent": 10.81,
            "weight": 32.5
        },
        {
            "id": 2,
            "code": "THYAO",
            "name": "Turkish Airlines",
            "quantity": 50,
            "buy_price": 275.00,
            "current_price": 294.60,
            "total_value": 14730.00,
            "profit_loss": 980.00,
            "profit_loss_percent": 7.13,
            "weight": 38.6
        },
        {
            "id": 3,
            "code": "KCHOL",
            "name": "Koc Holding",
            "quantity": 80,
            "buy_price": 135.50,
            "current_price": 142.90,
            "total_value": 11432.00,
            "profit_loss": 592.00,
            "profit_loss_percent": 5.46,
            "weight": 29.9
        }
    ]
    
    # User's notifications
    notifications = [
        {
            "id": 1,
            "type": "price_alert",
            "title": "Price Alert: GARAN",
            "message": "GARAN stock reached your target of 24.50 TL.",
            "date": "08.08.2023 09:45",
            "is_read": True
        },
        {
            "id": 2,
            "type": "news",
            "title": "Important News: THYAO",
            "message": "Turkish Airlines signed an agreement for new aircraft orders.",
            "date": "07.08.2023 14:30",
            "is_read": True
        },
        {
            "id": 3,
            "type": "analysis",
            "title": "New Analysis: Banking Sector",
            "message": "New sector analysis published for banking sector in your watchlist.",
            "date": "07.08.2023 10:15",
            "is_read": False
        },
        {
            "id": 4,
            "type": "price_alert",
            "title": "Price Alert: KCHOL",
            "message": "KCHOL stock reached your target of 140.00 TL.",
            "date": "06.08.2023 11:20",
            "is_read": False
        },
        {
            "id": 5,
            "type": "system",
            "title": "Account Update",
            "message": "Your account has been successfully upgraded to premium membership.",
            "date": "05.08.2023 16:45",
            "is_read": True
        }
    ]
    
    # User's settings
    settings = {
        "notification_preferences": {
            "email_alerts": True,
            "browser_notifications": True,
            "price_alerts": True,
            "news_alerts": True,
            "analysis_alerts": True
        },
        "display_preferences": {
            "dark_mode": False,
            "default_currency": "TRY",
            "default_view": "table",
            "show_portfolio_summary": True
        },
        "privacy_settings": {
            "profile_public": False,
            "share_portfolio": False,
            "show_real_returns": False
        }
    }
    
    # Risk profile survey
    risk_profile_questions = [
        {
            "id": 1,
            "question": "What is your priority when investing?",
            "options": [
                {"id": 1, "text": "Protect my capital and take minimum risk", "value": 1},
                {"id": 2, "text": "Take reasonable risk for balanced returns", "value": 2},
                {"id": 3, "text": "Ready to take high risk for high returns", "value": 3}
            ]
        },
        {
            "id": 2,
            "question": "Which of the following scenarios suits you better?",
            "options": [
                {"id": 1, "text": "5% return with almost no risk of loss", "value": 1},
                {"id": 2, "text": "10% return with 5% risk of loss", "value": 2},
                {"id": 3, "text": "20% return with 15% risk of loss", "value": 3}
            ]
        },
        {
            "id": 3,
            "question": "What do you think about investment horizon?",
            "options": [
                {"id": 1, "text": "Short term (0-1 year)", "value": 1},
                {"id": 2, "text": "Medium term (1-5 years)", "value": 2},
                {"id": 3, "text": "Long term (5+ years)", "value": 3}
            ]
        },
        {
            "id": 4,
            "question": "What would be your reaction if your portfolio value drops by 20%?",
            "options": [
                {"id": 1, "text": "Sell immediately and limit my losses", "value": 1},
                {"id": 2, "text": "Wait for a while and decide based on situation", "value": 2},
                {"id": 3, "text": "See it as an opportunity and buy more", "value": 3}
            ]
        },
        {
            "id": 5,
            "question": "What is your investment knowledge and experience?",
            "options": [
                {"id": 1, "text": "Just started, limited experience", "value": 1},
                {"id": 2, "text": "Intermediate level, familiar with basic investment instruments", "value": 2},
                {"id": 3, "text": "Advanced level, experienced with various investment instruments", "value": 3}
            ]
        }
    ]
    
    return render_template('user_profile.html',
                          title="My Account",
                          update_date=date.today().strftime('%d.%m.%Y'),
                          user=user,
                          watchlist=watchlist,
                          portfolio=portfolio,
                          notifications=notifications,
                          settings=settings,
                          risk_profile_questions=risk_profile_questions)


# This endpoint is no longer in use. Please refer to src/app/api.py module for API endpoints.
# Let's create a redirect to show that old endpoints are deprecated
@main_bp.route('/api/stock/<stock_code>')
def api_redirect(stock_code):
    """
    Redirects old API endpoint to new API endpoint
    """
    flash('This API endpoint is no longer in use. Please use /api/stocks/' + stock_code + ' endpoint.', 'warning')
    return redirect(url_for('api.get_stock', stock_code=stock_code))