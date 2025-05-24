import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import os
import sys

# Add main directory so we can access other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Data directory
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
# Data file
PRICE_DATA_FILE = os.path.join(DATA_DIR, "price_bist30_historical_data_13052025_7days.csv")
# Processed data file
PROCESSED_DATA_FILE = os.path.join(DATA_DIR, "processed_bist30_data.csv")

def load_data():
    """
    Loads data file and shows basic information
    """
    print("Loading data...")
    df = pd.read_csv(PRICE_DATA_FILE)
    print(f"Data loaded successfully. Total {len(df)} records available.\n")
    
    # Convert date column to datetime format
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Show basic data information
    print("First 5 rows of dataset:")
    print(df.head())
    print("\nGeneral information about dataset:")
    print(df.info())
    print("\nBasic statistics:")
    print(df.describe())
    
    # Check missing values
    missing_values = df.isnull().sum()
    print("\nMissing values:")
    print(missing_values[missing_values > 0])
    
    # Show unique stock codes and date count in dataset
    print(f"\nUnique stock count: {df['Stock_Code'].nunique()}")
    print(f"Unique date count: {df['Date'].nunique()}")
    print(f"Unique stock codes: {df['Stock_Code'].unique()}")
    print(f"Unique dates: {df['Date'].unique()}")
    
    return df

def clean_data(df):
    """
    Data cleaning operations
    """
    print("\nData cleaning operations starting...")
    
    # Save original data dimensions
    original_shape = df.shape
    
    # 1. Check and remove duplicated values
    duplicates = df.duplicated()
    if duplicates.sum() > 0:
        print(f"{duplicates.sum()} duplicate rows found and removed.")
        df = df.drop_duplicates()
    else:
        print("No duplicate rows found.")
    
    # 2. Mark 0.0 values in Weighted_Average and Volume_TL columns as NaN
    df.loc[df['Weighted_Average'] == 0.0, 'Weighted_Average'] = np.nan
    df.loc[df['Volume_TL'] == 0.0, 'Volume_TL'] = np.nan
    
    # 3. Fill missing values
    # If Weighted_Average is missing, fill with (High + Low) / 2
    df['Weighted_Average'] = df['Weighted_Average'].fillna((df['High'] + df['Low']) / 2)
    
    # If Volume_TL is missing and Volume_Lot exists, multiply by last price
    df['Volume_TL'] = df.apply(
        lambda row: row['Volume_Lot'] * row['Last_Price'] / 1000 if pd.isna(row['Volume_TL']) else row['Volume_TL'], 
        axis=1
    )
    
    # 4. Fix data types
    float_cols = ['Last_Price', 'Previous_Price', 'Change_Percent', 'High', 'Low', 
                 'Weighted_Average', 'Volume_Lot', 'Volume_TL']
    
    for col in float_cols:
        if df[col].dtype != 'float':
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # 5. Rename all columns correctly
    df = df.rename(columns={
        'Stock_Code': 'stock_code',
        'Last_Price': 'last_price',
        'Previous_Price': 'previous_price',
        'Change_Percent': 'change_percent',
        'High': 'high',
        'Low': 'low',
        'Weighted_Average': 'weighted_avg',
        'Volume_Lot': 'volume_lot',
        'Volume_TL': 'volume_tl',
        'Date': 'date'
    })
    
    # 6. Sort data by date and stock code
    df = df.sort_values(['date', 'stock_code'])
    
    # 7. Reset row numbers (index reset)
    df = df.reset_index(drop=True)
    
    # Report data dimensions after cleaning
    print(f"Data size before cleaning: {original_shape}")
    print(f"Data size after cleaning: {df.shape}")
    print("Data cleaning operations completed.")
    
    return df

def calculate_descriptive_statistics(df):
    """
    Calculate and show summary statistics
    """
    print("\nCalculating summary statistics...")
    
    # Summary statistics by stocks
    stock_stats = df.groupby('stock_code').agg({
        'last_price': ['mean', 'std', 'min', 'max'],
        'change_percent': ['mean', 'std', 'min', 'max'],
        'volume_lot': ['mean', 'sum']
    })
    
    print("\nSummary statistics by stocks:")
    print(stock_stats)
    
    # Volatility calculation (standard deviation / mean)
    volatility = (stock_stats[('last_price', 'std')] / stock_stats[('last_price', 'mean')]) * 100
    volatility = volatility.sort_values(ascending=False)
    
    print("\nStock volatility ranking (as %):")
    print(volatility)
    
    # Average daily change
    avg_change = stock_stats[('change_percent', 'mean')].sort_values(ascending=False)
    
    print("\nAverage daily change ranking (as %):")
    print(avg_change)
    
    # Trading volume ranking
    volume_ranking = stock_stats[('volume_lot', 'sum')].sort_values(ascending=False)
    
    print("\nTotal trading volume ranking (lot):")
    print(volume_ranking)
    
    return {
        'stock_stats': stock_stats,
        'volatility': volatility,
        'avg_change': avg_change,
        'volume_ranking': volume_ranking
    }

def explore_correlations(df):
    """
    Examine correlations between stock prices and changes
    """
    print("\nExamining stock correlations...")
    
    # Create pivot table: Rows are dates, columns are stocks, values are last_price
    price_pivot = df.pivot(index='date', columns='stock_code', values='last_price')
    
    # Price correlation
    price_corr = price_pivot.corr()
    
    # Calculate daily change rate
    returns_pivot = df.pivot(index='date', columns='stock_code', values='change_percent')
    
    # Change correlation
    returns_corr = returns_pivot.corr()
    
    print("\nStock price correlations:")
    print(price_corr.round(2))
    
    print("\nStock change correlations:")
    print(returns_corr.round(2))
    
    return {
        'price_corr': price_corr,
        'returns_corr': returns_corr
    }

def add_features(df):
    """
    Add new features for clustering analysis
    """
    print("\nAdding new features...")
    
    # Unique stocks and dates
    stocks = df['stock_code'].unique()
    dates = sorted(df['date'].unique())
    
    # Create new data frame
    feature_data = []
    
    for stock in stocks:
        stock_data = df[df['stock_code'] == stock].copy()
        
        if len(stock_data) == 0:
            print(f"Warning: No sufficient data for {stock}, skipping.")
            continue
        
        # Basic statistics
        avg_price = stock_data['last_price'].mean()
        price_volatility = stock_data['last_price'].std()
        avg_daily_change = stock_data['change_percent'].mean()
        change_volatility = stock_data['change_percent'].std()
        avg_volume = stock_data['volume_lot'].mean()
        max_gain = stock_data['change_percent'].max()
        max_loss = stock_data['change_percent'].min()
        
        # Add to feature data
        feature_data.append({
            'stock_code': stock,
            'avg_price': avg_price,
            'price_volatility': price_volatility,
            'avg_daily_change': avg_daily_change,
            'change_volatility': change_volatility,
            'avg_volume': avg_volume,
            'max_gain': max_gain,
            'max_loss': max_loss
        })
    
    # Convert to DataFrame
    feature_df = pd.DataFrame(feature_data)
    
    print("\nDataset with added new features:")
    print(feature_df.head())
    
    return feature_df

def preprocess_data(df):
    """
    Complete data preprocessing pipeline
    """
    print("\nStarting data preprocessing...")
    
    # 1. Clean data
    cleaned_df = clean_data(df)
    
    # 2. Calculate descriptive statistics
    stats = calculate_descriptive_statistics(cleaned_df)
    
    # 3. Examine correlations
    correlations = explore_correlations(cleaned_df)
    
    # 4. Add new features
    feature_df = add_features(cleaned_df)
    
    # 5. Save processed data
    feature_df.to_csv(PROCESSED_DATA_FILE, index=False)
    print(f"\nProcessed data saved to {PROCESSED_DATA_FILE}")
    
    return {
        'cleaned_data': cleaned_df,
        'feature_data': feature_df,
        'statistics': stats,
        'correlations': correlations
    }

def main():
    """
    Main function
    """
    print("========== BIST 30 Data Analysis and Preprocessing ==========")
    
    # 1. Load data
    df = load_data()
    
    # 2. Preprocess data
    results = preprocess_data(df)
    
    print("\n========== Data Analysis and Preprocessing Completed ==========")
    
    return results

if __name__ == "__main__":
    main() 