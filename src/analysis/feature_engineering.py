import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler, MinMaxScaler
import sys

# Add main directory so we can access other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Data directory and file paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
PROCESSED_DATA_FILE = os.path.join(DATA_DIR, "processed_bist30_data.csv")
FEATURE_ENGINEERED_FILE = os.path.join(DATA_DIR, "feature_engineered_data.csv")
PRICE_DATA_FILE = os.path.join(DATA_DIR, "price_bist30_historical_data_13052025_7days.csv")

# Directory where graphs will be saved
IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "static", "images")

# Check graphics directory and create if necessary
if not os.path.exists(IMAGES_DIR):
    os.makedirs(IMAGES_DIR)

def save_figure(plt, filename):
    """
    Helper function for saving graphs
    Deletes existing file with the same name and saves again
    """
    filepath = os.path.join(IMAGES_DIR, filename)
    
    # Delete file if it exists
    if os.path.exists(filepath):
        os.remove(filepath)
    
    # Save graph
    plt.savefig(filepath, dpi=300)
    print(f"Graph saved: {filepath}")

def load_data():
    """
    Loads processed data and raw price data
    """
    print("Loading data...")
    # Load processed summary data
    processed_df = pd.read_csv(PROCESSED_DATA_FILE)
    
    # Load raw price data (for technical indicators)
    price_df = pd.read_csv(PRICE_DATA_FILE)
    price_df['Date'] = pd.to_datetime(price_df['Date'])
    
    print(f"Processed data size: {processed_df.shape}")
    print(f"Raw price data size: {price_df.shape}")
    
    return processed_df, price_df

def standardize_features(df):
    """
    Standardizes features (z-score normalization)
    """
    print("\nStandardizing features...")
    
    # Numerical columns to be standardized
    numeric_cols = ['avg_price', 'price_volatility', 'avg_daily_change', 
                    'change_volatility', 'avg_volume', 'max_gain', 'max_loss']
    
    # Create copy for standardization
    std_df = df.copy()
    
    # Z-score normalization using StandardScaler
    scaler = StandardScaler()
    std_df[numeric_cols] = scaler.fit_transform(df[numeric_cols])
    
    print("Standardization completed.")
    print("First 5 rows of standardized data:")
    print(std_df.head())
    
    return std_df, scaler

def normalize_features(df):
    """
    Normalizes features to 0-1 range
    """
    print("\nNormalizing features to 0-1 range...")
    
    # Numerical columns to be normalized
    numeric_cols = ['avg_price', 'price_volatility', 'avg_daily_change', 
                    'change_volatility', 'avg_volume', 'max_gain', 'max_loss']
    
    # Create copy for normalization
    norm_df = df.copy()
    
    # 0-1 normalization using MinMaxScaler
    scaler = MinMaxScaler()
    norm_df[numeric_cols] = scaler.fit_transform(df[numeric_cols])
    
    print("Normalization completed.")
    print("First 5 rows of normalized data:")
    print(norm_df.head())
    
    return norm_df, scaler

def calculate_risk_return_ratio(df):
    """
    Calculates risk-return ratio
    Risk: Volatility or standard deviation
    Return: Average daily change
    """
    print("\nCalculating risk-return ratios...")
    
    # Return / Risk ratio (Sharpe-like ratio)
    df['return_risk_ratio'] = df['avg_daily_change'] / df['price_volatility']
    
    # Visualize risk-return relationship
    plt.figure(figsize=(10, 6))
    sns.scatterplot(data=df, x='price_volatility', y='avg_daily_change', 
                    hue='return_risk_ratio', size='avg_volume', sizes=(50, 500),
                    palette='viridis')
    plt.title('Risk-Return Relationship')
    plt.xlabel('Risk (Price Volatility %)')
    plt.ylabel('Return (Average Daily Change %)')
    
    # Adjust graph to make text visible
    for i, row in df.iterrows():
        plt.text(row['price_volatility'], row['avg_daily_change'], 
                 row['stock_code'], fontsize=9)
    
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    # Save graph
    save_figure(plt, 'risk_return_plot.png')
    
    return df

def calculate_beta(price_df):
    """
    Calculates beta coefficient for each stock
    Beta: Measures a stock's sensitivity to the BIST-30 index
    """
    print("\nCalculating beta coefficients...")
    
    # BIST-30 index is calculated as the average of all stocks as a representative
    # In real application, actual BIST-30 index data should be used
    
    # Create pivot table for all stocks (rows: dates, columns: stocks)
    pivot_df = price_df.pivot(index='Date', columns='Stock_Code', values='Last_Price')
    
    # Daily percentage changes
    daily_returns = pivot_df.pct_change().dropna()
    
    # If daily change data is too little (less than 2 days), beta calculation cannot be done
    if len(daily_returns) < 2:
        print("Warning: Not enough data for beta calculation. Default value (1.0) will be used.")
        # Use 1.0 beta value for all stocks
        beta_values = {code: 1.0 for code in pivot_df.columns}
        beta_df = pd.DataFrame(list(beta_values.items()), columns=['stock_code', 'beta'])
        return beta_df
    
    # Market return (average of all stocks) - simplified approach
    market_returns = daily_returns.mean(axis=1)
    
    # Beta calculation
    beta_values = {}
    for column in daily_returns.columns:
        try:
            # Covariance / Variance
            covariance = daily_returns[column].cov(market_returns)
            variance = market_returns.var()
            
            # If variance is zero or NaN, beta cannot be calculated
            if variance == 0 or pd.isna(variance) or pd.isna(covariance):
                beta = 1.0  # Default value
            else:
                beta = covariance / variance
                
            # Clip extreme values
            if pd.isna(beta) or abs(beta) > 5:
                beta = 1.0  # Use default for extreme values
                
            beta_values[column] = round(beta, 3)
        except Exception as e:
            print(f"Beta calculation error ({column}): {e}")
            beta_values[column] = 1.0  # Default value in case of error
    
    # Convert beta values to DataFrame
    beta_df = pd.DataFrame(list(beta_values.items()), columns=['stock_code', 'beta'])
    
    print("Beta values calculated:")
    print(beta_df.sort_values('beta', ascending=False).head(10))
    
    return beta_df

def merge_all_features(processed_df, beta_df):
    """
    Merges all features
    """
    print("\nMerging all features...")
    
    # Merge existing features with beta values
    final_df = processed_df.merge(beta_df, on='stock_code', how='left')
    
    # Fill missing beta values with 1.0
    final_df['beta'] = final_df['beta'].fillna(1.0)
    
    print("Feature merging completed.")
    print("Final dataset with all features:")
    print(final_df.head())
    
    return final_df

def main():
    """
    Main function that runs the entire feature engineering pipeline
    """
    print("Starting BIST 30 Feature Engineering...")
    
    # 1. Load data
    processed_df, price_df = load_data()
    
    # 2. Calculate beta coefficients
    beta_df = calculate_beta(price_df)
    
    # 3. Merge all features
    final_df = merge_all_features(processed_df, beta_df)
    
    # 4. Calculate risk-return ratio
    final_df = calculate_risk_return_ratio(final_df)
    
    # 5. Save final dataset
    final_df.to_csv(FEATURE_ENGINEERED_FILE, index=False)
    print(f"Feature engineering completed. Results saved to {FEATURE_ENGINEERED_FILE}")
    
    return final_df

if __name__ == "__main__":
    main() 