"""
BIST data web scraping and update tool

This script fetches BIST data from Uzmanpara Milliyet website and updates CSV files.
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# Add main folder so we can access other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Import scraping module
from src.scraping.scrape_uzmanpara import main as scrape_main, get_date_range_backwards

# Import analysis and model modules
from src.analysis.data_analysis_preprocessing import preprocess_data
from src.analysis.feature_engineering import calculate_risk_return_ratio, calculate_beta, standardize_features
from src.models.clustering_model import apply_kmeans, find_optimal_k, prepare_features_for_clustering, perform_pca

# Data folder
DATA_DIR = os.path.dirname(__file__)

def scrape_latest_data(days=7, stock_list=None, separate_days=False):
    """
    Fetches latest data from web
    
    Parameters:
    -----------
    days : int
        How many days of data to fetch
    stock_list : list
        List of stock codes to fetch
    separate_days : bool
        Option to separate data into daily files
    """
    print("Starting latest data fetching from web...")
    
    # BIST 30 stocks (default)
    if stock_list is None:
        stock_list = [
            "AEFES", "AKBNK", "ASELS", "ASTOR", "BIMAS", "CIMSA", "EKGYO", "ENKAI", 
            "EREGL", "FROTO", "GARAN", "HEKTS", "ISCTR", "KCHOL", "KOZAL", "KRDMD", 
            "MGROS", "PETKM", "PGSUS", "SAHOL", "SASA", "SISE", "TAVHL", "TCELL", 
            "THYAO", "TOASO", "TTKOM", "TUPRS", "ULKER", "YKBNK"
        ]
    
    # Create output file name using computer's current date
    current_date = datetime.now()
    output_file = f"bist30_historical_data_{current_date.strftime('%d%m%Y')}_{days}days.csv"
    
    # Run scraping process
    scrape_main(output_file=output_file, stock_list=stock_list, days=days, separate_days=separate_days)
    
    # Created file paths
    price_file = os.path.join(DATA_DIR, "price_" + output_file)
    
    # Check if files were created
    if os.path.exists(price_file):
        print(f"Data fetching completed successfully. File: {price_file}")
        return True
    else:
        print("Data fetching failed.")
        return False

def update_processed_data(use_daily_files=False):
    """
    Processes raw data and updates processed_bist30_data.csv file
    
    Parameters:
    -----------
    use_daily_files : bool
        Option to use daily files
    """
    print("Starting data processing...")
    
    # If using daily files
    if use_daily_files:
        daily_dir = os.path.join(DATA_DIR, "daily")
        if not os.path.exists(daily_dir) or not os.listdir(daily_dir):
            print(f"Error: Daily data files not found. You must fetch data first.")
            return False
        
        # Read and combine all daily files
        all_data = []
        for filename in os.listdir(daily_dir):
            if filename.endswith('.csv'):
                file_path = os.path.join(daily_dir, filename)
                df = pd.read_csv(file_path)
                all_data.append(df)
                print(f"File read: {filename}")
        
        if not all_data:
            print("Error: No data found in daily data files.")
            return False
        
        # Combine all data
        df = pd.concat(all_data, ignore_index=True)
    else:
        # Raw data file path
        price_file = os.path.join(DATA_DIR, "price_bist30_historical_data_13052025_7days.csv")
        
        # Check if file exists
        if not os.path.exists(price_file):
            print(f"Error: {price_file} file not found.")
            return False
        
        # Read raw data
        df = pd.read_csv(price_file)
    
    try:
        # Check and convert date column
        if 'Tarih' in df.columns:
            df['Tarih'] = pd.to_datetime(df['Tarih'])
        
        # Preprocess data
        processed_df = preprocess_data(df)
        
        # Save processed data
        processed_output = os.path.join(DATA_DIR, "processed_bist30_data.csv")
        processed_df.to_csv(processed_output, index=False)
        
        print(f"Data processing completed. Result: {processed_output}")
        return True
    
    except Exception as e:
        print(f"Data processing error: {e}")
        return False

def update_feature_engineered_data(use_daily_files=False):
    """
    Applies feature engineering and updates feature_engineered_data.csv file
    
    Parameters:
    -----------
    use_daily_files : bool
        Option to use daily files
    """
    print("Starting feature engineering...")
    
    # Processed data file path
    processed_file = os.path.join(DATA_DIR, "processed_bist30_data.csv")
    
    # Check if file exists
    if not os.path.exists(processed_file):
        print(f"Error: Processed data file not found.")
        return False
    
    # Read raw price data (daily or combined)
    if use_daily_files:
        daily_dir = os.path.join(DATA_DIR, "daily")
        if not os.path.exists(daily_dir) or not os.listdir(daily_dir):
            print(f"Error: Daily data files not found.")
            return False
        
        # Read and combine all daily files
        all_data = []
        for filename in os.listdir(daily_dir):
            if filename.endswith('.csv'):
                file_path = os.path.join(daily_dir, filename)
                df = pd.read_csv(file_path)
                all_data.append(df)
        
        if not all_data:
            print("Error: No data found in daily data files.")
            return False
        
        # Combine all data
        price_df = pd.concat(all_data, ignore_index=True)
    else:
        price_file = os.path.join(DATA_DIR, "price_bist30_historical_data_13052025_7days.csv")
        if not os.path.exists(price_file):
            print(f"Error: Raw data file not found.")
            return False
        price_df = pd.read_csv(price_file)
    
    try:
        # Read processed data
        processed_df = pd.read_csv(processed_file)
        
        # Date conversion
        price_df['Tarih'] = pd.to_datetime(price_df['Tarih'])
        
        # Calculate risk-return ratio
        processed_df = calculate_risk_return_ratio(processed_df)
        
        # Calculate beta values
        beta_df = calculate_beta(price_df)
        
        # Combine all features
        final_df = pd.merge(processed_df, beta_df, on='stock_code', how='left')
        
        # Round numerical values
        for col in final_df.columns:
            if col != 'stock_code' and final_df[col].dtype in ['float64', 'float32']:
                final_df[col] = final_df[col].round(3)
        
        # Save result
        feature_output = os.path.join(DATA_DIR, "feature_engineered_data.csv")
        final_df.to_csv(feature_output, index=False)
        
        print(f"Feature engineering completed. Result: {feature_output}")
        return True
    
    except Exception as e:
        print(f"Feature engineering error: {e}")
        return False

def update_clustering_results():
    """Performs clustering analysis and updates clustering_results.csv file"""
    print("Starting clustering analysis...")
    
    # Feature engineered data file path
    feature_file = os.path.join(DATA_DIR, "feature_engineered_data.csv")
    
    # Check if file exists
    if not os.path.exists(feature_file):
        print(f"Error: {feature_file} file not found.")
        return False
    
    try:
        # Read data
        df = pd.read_csv(feature_file)
        
        # Prepare features for clustering
        X_scaled, stock_codes, features, feature_df = prepare_features_for_clustering(df)
        
        # Apply PCA
        X_pca, pca = perform_pca(X_scaled, stock_codes, features)
        
        # Find optimal number of clusters
        best_k = find_optimal_k(X_scaled)
        
        # Apply K-means clustering
        result = apply_kmeans(X_scaled, best_k, stock_codes, feature_df, X_pca)
        
        # Function returns a tuple (DataFrame, model)
        # Get only the DataFrame
        if isinstance(result, tuple) and len(result) > 0:
            result_df = result[0]  # Get first element (DataFrame)
        else:
            result_df = result
        
        # Save result
        clustering_output = os.path.join(DATA_DIR, "clustering_results.csv")
        result_df.to_csv(clustering_output, index=False)
        
        print(f"Clustering analysis completed. Result: {clustering_output}")
        return True
    
    except Exception as e:
        print(f"Clustering error: {e}")
        return False

def update_all_data(days=7, stock_list=None, separate_days=False, use_daily_files=False):
    """
    Runs entire data process: fetching, processing, feature engineering and clustering
    
    Parameters:
    -----------
    days : int
        How many days of data to fetch
    stock_list : list
        List of stock codes to fetch
    separate_days : bool
        Option to separate data into daily files
    use_daily_files : bool
        Option to use daily files in processing steps
    """
    print("\n=== Starting BIST Data Update Process ===\n")
    
    # 1. Fetch data from web
    if not scrape_latest_data(days, stock_list, separate_days):
        print("Data fetching failed. Process stopped.")
        return False
    
    # 2. Process raw data
    if not update_processed_data(use_daily_files):
        print("Data processing failed. Process stopped.")
        return False
    
    # 3. Apply feature engineering
    if not update_feature_engineered_data(use_daily_files):
        print("Feature engineering failed. Process stopped.")
        return False
    
    # 4. Perform clustering analysis
    if not update_clustering_results():
        print("Clustering analysis failed. Process stopped.")
        return False
    
    print("\n=== BIST Data Update Process Completed Successfully ===\n")
    return True

if __name__ == "__main__":
    # If run from command line
    import argparse
    
    parser = argparse.ArgumentParser(description='BIST data update tool')
    parser.add_argument('--days', type=int, default=7, help='How many days of data to fetch (default: 7)')
    parser.add_argument('--stocks', nargs='+', help='Which stocks to fetch (default: BIST 30)')
    parser.add_argument('--skip-scrape', action='store_true', help='Skip web scraping step')
    parser.add_argument('--separate-days', action='store_true', help='Save data to separate files by day')
    parser.add_argument('--use-daily-files', action='store_true', help='Use daily files in processing steps')
    
    args = parser.parse_args()
    
    if args.skip_scrape:
        print("Skipping web scraping step...")
        # Only do data processing and analysis
        update_processed_data(args.use_daily_files)
        update_feature_engineered_data(args.use_daily_files)
        update_clustering_results()
    else:
        # Full update process
        update_all_data(
            days=args.days, 
            stock_list=args.stocks, 
            separate_days=args.separate_days,
            use_daily_files=args.use_daily_files
        ) 