"""
BIST data loading module

This module loads scraped data and analysis results into the database.
"""

import pandas as pd
import os
import sys
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

# Add main directory so we can access other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Import database models
from src.app import db
from src.app.models import Stock, Cluster, PriceHistory

# Data file paths
DATA_DIR = os.path.dirname(__file__)
PRICE_DATA_FILE = os.path.join(DATA_DIR, "price_bist30_historical_data_13052025_7days.csv")
CLUSTERING_RESULTS_FILE = os.path.join(DATA_DIR, "clustering_results.csv")
FEATURE_ENGINEERED_FILE = os.path.join(DATA_DIR, "feature_engineered_data.csv")
PROCESSED_DATA_FILE = os.path.join(DATA_DIR, "processed_bist30_data.csv")

def load_clusters_from_csv():
    """Loads cluster information from CSV file"""
    print("Loading cluster data...")
    
    try:
        # Read cluster data from CSV
        clusters_df = pd.read_csv(CLUSTERING_RESULTS_FILE)
        
        # Get unique cluster IDs
        unique_clusters = clusters_df['cluster'].unique()
        
        # Cluster colors - Compatible with pastel colors
        cluster_colors = {
            0: "rgba(59, 130, 246, 0.6)",   # Pastel Blue - Balanced Volatility
            1: "rgba(34, 197, 94, 0.6)",    # Pastel Green - Low Volatility  
            2: "rgba(245, 158, 11, 0.6)",   # Pastel Orange - High Volatility
            3: "rgba(239, 68, 68, 0.6)",    # Pastel Red - Positive Return
        }
        
        # Cluster descriptions
        cluster_descriptions = {
            0: {
                "name": "Balanced Volatility, Moderate Risk",
                "summary": "Stocks in this cluster show a stable profile with balanced volatility and moderate risk level.",
                "investor_profile": "Balanced"
            },
            1: {
                "name": "Low Volatility, Stable",
                "summary": "Stocks in this cluster show low volatility and stable performance. Suitable for conservative investors.",
                "investor_profile": "Conservative"
            },
            2: {
                "name": "High Volatility, High Risk",
                "summary": "Stocks in this cluster show an aggressive profile with high volatility and high risk level.",
                "investor_profile": "Aggressive"
            },
            3: {
                "name": "Positive Return, Moderate Volatility",
                "summary": "Stocks in this cluster show a growth-oriented profile with positive returns and moderate volatility.",
                "investor_profile": "Growth Oriented"
            }
        }
        
        # For each unique cluster
        for cluster_id in unique_clusters:
            # Cluster data
            cluster_stocks = clusters_df[clusters_df['cluster'] == cluster_id]
            
            # Calculate cluster statistics
            avg_volatility = cluster_stocks['price_volatility'].mean()
            avg_change = cluster_stocks['avg_daily_change'].mean()
            avg_beta = cluster_stocks['beta'].mean()
            risk_return_ratio = cluster_stocks['return_risk_ratio'].mean()
            
            # Cluster description and color
            cluster_info = cluster_descriptions.get(cluster_id, {"name": f"Cluster {cluster_id}", "summary": "Auto-generated cluster", "investor_profile": "General"})
            cluster_color = cluster_colors.get(cluster_id, "#000000")  # Default black
            
            # Add cluster to database
            cluster = Cluster(
                id=int(cluster_id),
                name=cluster_info["name"],
                color=cluster_color,
                avg_volatility=round(float(avg_volatility), 2),
                avg_change=round(float(avg_change), 2),
                avg_beta=round(float(avg_beta), 2),
                risk_return_ratio=round(float(risk_return_ratio), 2),
                summary=cluster_info["summary"],
                investor_profile=cluster_info["investor_profile"]
            )
            
            db.session.add(cluster)
        
        # Save changes
        db.session.commit()
        print(f"{len(unique_clusters)} clusters loaded successfully.")
        return True
    
    except Exception as e:
        db.session.rollback()
        print(f"Cluster loading error: {e}")
        return False

def load_stocks_from_csv():
    """Loads stock information from CSV file"""
    print("Loading stock data...")
    
    try:
        # Read feature-engineered data
        stocks_df = pd.read_csv(FEATURE_ENGINEERED_FILE)
        
        # Read clustering results
        cluster_df = pd.read_csv(CLUSTERING_RESULTS_FILE)
        
        # Merge two datasets
        merged_df = pd.merge(stocks_df, cluster_df[['stock_code', 'cluster']], on='stock_code', how='left')
        
        # For each stock
        for _, row in merged_df.iterrows():
            # Create stock model
            stock = Stock(
                code=row['stock_code'],
                avg_price=float(row['avg_price']),
                volatility=float(row['price_volatility']),
                avg_change=float(row['avg_daily_change']),
                beta=float(row['beta']),
                risk_return_ratio=float(row['return_risk_ratio']),
                max_gain=float(row['max_gain']),
                max_loss=float(row['max_loss']),
                cluster_id=int(row['cluster'])
            )
            
            db.session.add(stock)
        
        # Save changes
        db.session.commit()
        print(f"{len(merged_df)} stocks loaded successfully.")
        return True
    
    except Exception as e:
        db.session.rollback()
        print(f"Stock loading error: {e}")
        return False

def load_price_history_from_csv():
    """Loads stock price history data from daily CSV files"""
    print("Loading price history data...")
    
    try:
        # Get stock IDs
        stock_id_map = {}
        for stock in db.session.query(Stock).all():
            stock_id_map[stock.code] = stock.id
        
        count = 0
        
        # Daily dosyalar klasörü
        daily_dir = os.path.join(DATA_DIR, 'daily')
        
        # Daily klasöründeki tüm CSV dosyalarını oku
        if os.path.exists(daily_dir):
            for filename in os.listdir(daily_dir):
                if filename.endswith('.csv'):
                    file_path = os.path.join(daily_dir, filename)
                    
                    try:
                        # Her daily dosyayı oku
                        daily_df = pd.read_csv(file_path)
                        
                        # For each price data in the file
                        for _, row in daily_df.iterrows():
                            stock_code = row['Stock_Code']
                            
                            # Find stock ID
                            stock_id = stock_id_map.get(stock_code)
                            if not stock_id:
                                continue
                            
                            # Get date from 'Tarih' column
                            try:
                                price_date = datetime.strptime(row['Tarih'], '%Y-%m-%d').date()
                            except ValueError:
                                try:
                                    price_date = datetime.strptime(row['Tarih'], '%d.%m.%Y').date()
                                except ValueError:
                                    print(f"Invalid date format: {row['Tarih']}")
                                    continue
                            
                            # Check if this price history already exists
                            existing = db.session.query(PriceHistory).filter_by(
                                stock_id=stock_id, 
                                date=price_date
                            ).first()
                            
                            if existing:
                                continue  # Skip if already exists
                            
                            # Create price history model
                            price_history = PriceHistory(
                                stock_id=stock_id,
                                date=price_date,
                                open_price=float(row['Previous_Price']) if pd.notna(row['Previous_Price']) else float(row['Last_Price']),
                                high_price=float(row['High']),
                                low_price=float(row['Low']),
                                close_price=float(row['Last_Price']),
                                volume=int(row['Volume_Lot']) if pd.notna(row['Volume_Lot']) else 0
                            )
                            
                            db.session.add(price_history)
                            count += 1
                            
                            # Commit every 100 records
                            if count % 100 == 0:
                                db.session.commit()
                        
                        print(f"Processed {filename}")
                        
                    except Exception as file_error:
                        print(f"Error processing {filename}: {file_error}")
                        continue
        
        # Final commit
        db.session.commit()
        print(f"{count} price history records loaded successfully.")
        return True
    
    except Exception as e:
        db.session.rollback()
        print(f"Price history loading error: {e}")
        return False

def load_all_real_data():
    """Loads all real data into database"""
    print("Starting to load all real data...")
    
    try:
        # 1. Load clusters
        if not load_clusters_from_csv():
            print("Cluster loading failed.")
            return False
        
        # 2. Load stocks
        if not load_stocks_from_csv():
            print("Stock loading failed.")
            return False
        
        # 3. Load price history
        if not load_price_history_from_csv():
            print("Price history loading failed.")
            return False
        
        print("All data loaded successfully!")
        return True
    
    except SQLAlchemyError as e:
        print(f"Database error: {e}")
        return False
    
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("BIST data loading tool - use from Flask application instead of running this file directly.") 