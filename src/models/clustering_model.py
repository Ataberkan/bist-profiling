import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans, DBSCAN
from sklearn.metrics import silhouette_score
from sklearn.metrics.pairwise import euclidean_distances
import matplotlib.cm as cm
import sys

# Add main directory so we can access other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Data directory and file paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
PRICE_DATA_FILE = os.path.join(DATA_DIR, "price_bist30_historical_data_13052025_7days.csv")
FEATURE_ENGINEERED_FILE = os.path.join(DATA_DIR, "feature_engineered_data.csv")
CLUSTERING_RESULTS_FILE = os.path.join(DATA_DIR, "clustering_results.csv")
PROCESSED_DATA_FILE = os.path.join(DATA_DIR, "processed_bist30_data.csv")

# Directory where graphs will be saved
IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "static", "images")

# Check graphics directory and create if necessary
if not os.path.exists(IMAGES_DIR):
    os.makedirs(IMAGES_DIR)

def save_figure(plt, filename):
    """
    Helper function for saving figures
    Deletes existing file with the same name and saves the figure
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
    Loads feature-engineered data
    """
    print("Loading data...")
    # Load feature-engineered data
    df = pd.read_csv(FEATURE_ENGINEERED_FILE)
    
    print(f"Data size: {df.shape}")
    print("First 5 rows of data:")
    print(df.head())
    
    return df

def prepare_features_for_clustering(df):
    """
    Prepares features for clustering
    """
    print("\nPreparing features for clustering...")
    
    # Keep stock codes separately
    stock_codes = df['stock_code'].values
    
    # Features to be used for clustering
    # Important features like Beta, risk-return ratio, volatility, average daily change
    features = ['price_volatility', 'avg_daily_change', 'change_volatility', 
                'beta', 'return_risk_ratio']
    
    # Data cleaning - check NaN, infinite values and extremely large values
    X = df[features].copy()
    
    # Replace NaN and infinite values with more reasonable values
    for col in features:
        # Detect NaN and infinite values
        mask_nan = pd.isna(X[col])
        mask_inf = np.isinf(X[col])
        
        if mask_nan.any() or mask_inf.any():
            print(f"Warning: {mask_nan.sum()} NaN and {mask_inf.sum()} infinite values found in '{col}' column.")
            
            # Replace NaN and infinite values with column mean
            # If all values are NaN/inf, use 0
            col_mean = X.loc[~(mask_nan | mask_inf), col].mean() if (~(mask_nan | mask_inf)).any() else 0
            X.loc[mask_nan | mask_inf, col] = col_mean
            
        # Check extremely large values (e.g. greater than 1000)
        mask_extreme = np.abs(X[col]) > 1000
        if mask_extreme.any():
            print(f"Warning: {mask_extreme.sum()} extremely large values found in '{col}' column.")
            # Limit with a reasonable value while preserving sign
            X.loc[mask_extreme, col] = np.sign(X.loc[mask_extreme, col]) * 1000
    
    # Get X matrix from selected features (cleaned version)
    X_values = X.values
    
    # Standardize selected features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_values)
    
    print(f"Selected features for clustering: {features}")
    print(f"Standardized data dimensions: {X_scaled.shape}")
    
    return X_scaled, stock_codes, features, df

def perform_pca(X, stock_codes, feature_names):
    """
    Applies PCA (Principal Component Analysis) for dimensionality reduction
    """
    print("\nApplying PCA...")
    
    # For 2D PCA
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X)
    
    # Print variance ratios
    explained_variance = pca.explained_variance_ratio_
    print(f"Variance ratios explained by first 2 components: {explained_variance}")
    print(f"Total explained variance: {sum(explained_variance):.2f}")
    
    # Visualize contributions of features to PCA components
    plt.figure(figsize=(10, 6))
    components = pd.DataFrame(pca.components_, columns=feature_names)
    sns.heatmap(components, cmap='coolwarm', annot=True, fmt='.2f')
    plt.title('PCA Components and Feature Contributions')
    plt.xlabel('Features')
    plt.ylabel('PCA Components')
    plt.tight_layout()
    save_figure(plt, 'pca_components.png')
    
    # Visualize PCA results
    plt.figure(figsize=(12, 8))
    plt.scatter(X_pca[:, 0], X_pca[:, 1], alpha=0.8, s=100)
    
    # Place stock codes on the graph
    for i, txt in enumerate(stock_codes):
        plt.annotate(txt, (X_pca[i, 0], X_pca[i, 1]), fontsize=9)
    
    plt.title('Data Visualization Reduced to 2D with PCA')
    plt.xlabel(f'First Principal Component ({explained_variance[0]:.2f})')
    plt.ylabel(f'Second Principal Component ({explained_variance[1]:.2f})')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    save_figure(plt, 'pca_visualization.png')
    
    return X_pca, pca

def find_optimal_k(X):
    """
    Determines optimal number of clusters (Elbow method and Silhouette score)
    """
    print("\nDetermining optimal number of clusters...")
    
    # For Elbow method
    distortions = []
    silhouette_scores = []
    K_range = range(2, 10)  # Evaluate cluster numbers from 2 to 9
    
    for k in K_range:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(X)
        distortions.append(kmeans.inertia_)
        
        # Silhouette score (for k>=2)
        if k >= 2:
            labels = kmeans.labels_
            silhouette_avg = silhouette_score(X, labels)
            silhouette_scores.append(silhouette_avg)
            print(f"Silhouette Score for k={k}: {silhouette_avg:.3f}")
    
    # Elbow method graph
    plt.figure(figsize=(12, 5))
    plt.subplot(1, 2, 1)
    plt.plot(K_range, distortions, 'bx-')
    plt.xlabel('k (Number of Clusters)')
    plt.ylabel('Distortion (Inertia)')
    plt.title('Elbow Method')
    plt.grid(True)
    
    # Silhouette score graph
    plt.subplot(1, 2, 2)
    plt.plot(K_range, silhouette_scores, 'rx-')
    plt.xlabel('k (Number of Clusters)')
    plt.ylabel('Silhouette Score')
    plt.title('Silhouette Score Analysis')
    plt.grid(True)
    
    plt.tight_layout()
    save_figure(plt, 'optimal_k.png')
    
    # Suggest k value with highest silhouette score
    best_k = K_range[np.argmax(silhouette_scores)]
    print(f"Optimal number of clusters according to highest Silhouette score: {best_k}")
    
    return best_k

def apply_kmeans(X, best_k, stock_codes, df, X_pca):
    """
    K-means clustering algorithm
    """
    print(f"\nK-means clustering algorithm (k={best_k})...")
    
    # Create and apply K-means model
    kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(X)
    
    # Get cluster centers
    centers = kmeans.cluster_centers_
    
    # Calculate silhouette score
    silhouette_avg = silhouette_score(X, cluster_labels)
    print(f"Silhouette Score: {silhouette_avg:.3f}")
    
    # Add results to DataFrame
    results_df = df.copy()
    results_df['cluster'] = cluster_labels
    
    # Visualize clusters (after PCA)
    plt.figure(figsize=(12, 8))
    
    # Different colors for different clusters
    colors = cm.rainbow(np.linspace(0, 1, best_k))
    
    for i, color in enumerate(colors):
        # Select points in the cluster
        cluster_points = X_pca[cluster_labels == i]
        cluster_stocks = stock_codes[cluster_labels == i]
        
        # Plot points
        plt.scatter(cluster_points[:, 0], cluster_points[:, 1], 
                    s=100, c=color.reshape(1,-1), alpha=0.6, label=f'Cluster {i}')
        
        # Add stock codes
        for j, stock in enumerate(cluster_stocks):
            plt.annotate(stock, (cluster_points[j, 0], cluster_points[j, 1]), fontsize=9)
    
    # Convert cluster centers to PCA space
    centers_pca = PCA(n_components=2).fit(X).transform(centers) if len(X[0]) > 2 else centers
    
    # Plot cluster centers
    plt.scatter(centers_pca[:, 0], centers_pca[:, 1], 
                marker='X', s=200, c='black', alpha=0.8, label='Center')
    
    plt.title(f'K-means Clustering Results (k={best_k})')
    plt.xlabel('First Principal Component')
    plt.ylabel('Second Principal Component')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    save_figure(plt, 'kmeans_clusters.png')
    
    # Analyze cluster profiles (excluding stock_code column)
    numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
    cluster_profiles = results_df.groupby('cluster')[numeric_cols].mean()
    print("\nCluster Profiles (Average Values):")
    print(cluster_profiles)
    
    # List stock codes for each cluster
    for i in range(best_k):
        cluster_stocks = results_df[results_df['cluster'] == i]['stock_code'].tolist()
        print(f"\nCluster {i} Stocks:")
        print(", ".join(cluster_stocks))
    
    # Cluster profile graph
    plt.figure(figsize=(14, 6))
    
    # Selected features
    profile_features = ['price_volatility', 'avg_daily_change', 'beta', 'return_risk_ratio']
    
    for i in range(best_k):
        plt.subplot(1, best_k, i+1)
        cluster_profile = cluster_profiles.loc[i, profile_features]
        cluster_profile.plot(kind='bar')
        plt.title(f'Cluster {i} Profile')
        plt.xticks(rotation=45)
        plt.tight_layout()
    
    save_figure(plt, 'cluster_profiles.png')
    
    # Save results to file
    results_df.to_csv(CLUSTERING_RESULTS_FILE, index=False)
    print(f"Clustering results saved to {CLUSTERING_RESULTS_FILE}")
    
    return results_df, kmeans

def apply_dbscan(X, stock_codes, df, X_pca):
    """
    DBSCAN clustering algorithm
    """
    print("\nApplying DBSCAN clustering...")
    
    # Calculate distance matrix
    distances = euclidean_distances(X)
    
    # Calculate average distance and suggest epsilon
    eps = np.mean(distances) * 0.5
    min_samples = max(5, int(len(X) * 0.1))  # Minimum sample count
    
    print(f"Suggested epsilon: {eps:.3f}")
    print(f"Suggested min_samples: {min_samples}")
    
    # Apply DBSCAN
    dbscan = DBSCAN(eps=eps, min_samples=min_samples)
    cluster_labels = dbscan.fit_predict(X)
    
    # Determine cluster count (excluding noise)
    n_clusters = len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)
    n_noise = list(cluster_labels).count(-1)
    
    print(f"Cluster count determined by DBSCAN: {n_clusters}")
    print(f"Sample count marked as noise: {n_noise}")
    
    # Calculate silhouette score (for at least 2 clusters and noise-free cases)
    if n_clusters >= 2 and n_noise < len(X):
        # Select noise-free samples
        X_valid = X[cluster_labels != -1]
        labels_valid = cluster_labels[cluster_labels != -1]
        if len(set(labels_valid)) >= 2:  # At least 2 different clusters exist
            silhouette_avg = silhouette_score(X_valid, labels_valid)
            print(f"Silhouette Score without noise: {silhouette_avg:.3f}")
    
    # Add results to DataFrame
    results_df = df.copy()
    results_df['dbscan_cluster'] = cluster_labels
    
    # Calculate cluster profiles (if at least one cluster exists)
    if n_clusters > 0:
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
        cluster_profiles = results_df.groupby('dbscan_cluster')[numeric_cols].mean()
        print("\nDBSCAN Cluster Profiles (Average Values):")
        print(cluster_profiles)
    
    # Visualize clusters (after PCA)
    plt.figure(figsize=(12, 8))
    
    # Black for noise, different colors for clusters
    unique_clusters = set(cluster_labels)
    colors = cm.rainbow(np.linspace(0, 1, len(unique_clusters) - (1 if -1 in unique_clusters else 0)))
    color_map = {}
    color_idx = 0
    
    for cluster in unique_clusters:
        if cluster == -1:
            color_map[cluster] = [0, 0, 0, 1]  # Black
        else:
            color_map[cluster] = colors[color_idx]
            color_idx += 1
    
    for cluster in unique_clusters:
        # Select points in the cluster
        cluster_points = X_pca[cluster_labels == cluster]
        cluster_stocks = stock_codes[cluster_labels == cluster]
        
        # Create label
        if cluster == -1:
            label = 'Noise'
        else:
            label = f'Cluster {cluster}'
        
        # Plot points
        plt.scatter(cluster_points[:, 0], cluster_points[:, 1], 
                    s=100, c=np.array(color_map[cluster]).reshape(1,-1), 
                    alpha=0.6, label=label)
        
        # Add stock codes
        for j, stock in enumerate(cluster_stocks):
            plt.annotate(stock, (cluster_points[j, 0], cluster_points[j, 1]), fontsize=9)
    
    plt.title('DBSCAN Clustering Results')
    plt.xlabel('First Principal Component')
    plt.ylabel('Second Principal Component')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    save_figure(plt, 'dbscan_clusters.png')
    
    # List stock codes for clusters defined by DBSCAN
    for cluster in sorted(unique_clusters):
        if cluster == -1:
            cluster_name = "Noise"
        else:
            cluster_name = f"Cluster {cluster}"
        
        cluster_stocks = results_df[results_df['dbscan_cluster'] == cluster]['stock_code'].tolist()
        print(f"\n{cluster_name} Stocks:")
        print(", ".join(cluster_stocks))
    
    return results_df, dbscan

def run_clustering_model(feature_data_path, n_clusters=4, output_path=None):
    """
    Performs clustering analysis
    """
    print("\nStarting clustering analysis...")
    
    # Load data
    try:
        df = pd.read_csv(feature_data_path)
    except FileNotFoundError:
        print(f"Error: File not found: {feature_data_path}")
        return None
    
    # Prepare data for clustering
    X_scaled, stock_codes, features, df = prepare_features_for_clustering(df)
    
    if X_scaled is None or len(X_scaled) == 0:
        print("Error: No data suitable for clustering found.")
        return None
    
    # Apply PCA
    X_pca, pca = perform_pca(X_scaled, stock_codes, features)
    
    # Find optimal number of clusters
    best_k = find_optimal_k(X_scaled)
    
    # If the user has not specified a number of clusters, use the found optimal value
    if n_clusters is None:
        n_clusters = best_k
    
    # Apply K-means clustering
    results_df, kmeans = apply_kmeans(X_scaled, n_clusters, stock_codes, df, X_pca)
    
    # Also apply DBSCAN for comparison
    dbscan_df, dbscan = apply_dbscan(X_scaled, stock_codes, df, X_pca)
    
    # Save results
    if output_path:
        results_df.to_csv(output_path, index=False)
        print(f"Results saved to: {output_path}")
    
    return {
        'results_df': results_df,
        'dbscan_df': dbscan_df,
        'kmeans_model': kmeans,
        'dbscan_model': dbscan,
        'pca_model': pca,
        'features': features,
        'stock_codes': stock_codes,
        'n_clusters': n_clusters
    }

def save_cluster_summary_to_db():
    """
    Calculates cluster summary statistics and saves to database
    """
    try:
        # Read clustering results
        if not os.path.exists(CLUSTERING_RESULTS_FILE):
            print("Error: Clustering results file not found. Run clustering analysis first.")
            return False
        
        results_df = pd.read_csv(CLUSTERING_RESULTS_FILE)
        
        # Calculate cluster summaries
        from src.app import create_app, db
        from src.app.models import Cluster
        
        app = create_app()
        
        with app.app_context():
            # Clear existing cluster data
            db.session.query(Cluster).delete()
            
            # Calculate summary for each cluster
            cluster_summaries = []
            for cluster_id in results_df['cluster'].unique():
                cluster_data = results_df[results_df['cluster'] == cluster_id]
                
                # Calculate statistics
                avg_volatility = cluster_data['price_volatility'].mean()
                avg_change = cluster_data['avg_daily_change'].mean()
                avg_beta = cluster_data['beta'].mean()
                avg_risk_return = cluster_data['return_risk_ratio'].mean()
                
                # Determine cluster characteristics
                if avg_volatility < 2.0 and avg_beta < 1.0:
                    name = "Low Volatility, Stable"
                    summary = "Stocks in this cluster show low volatility and stable performance."
                    investor_profile = "Conservative"
                    color = "#22c55e"  # Green
                elif avg_volatility > 3.0 and avg_beta > 1.5:
                    name = "High Volatility, High Risk"
                    summary = "Stocks in this cluster show an aggressive profile with high volatility and high risk level."
                    investor_profile = "Aggressive"
                    color = "#f59e0b"  # Orange
                elif avg_change > 0 and avg_risk_return > 0:
                    name = "Positive Return, Moderate Volatility"
                    summary = "Stocks in this cluster show a growth-oriented profile with positive returns and moderate volatility."
                    investor_profile = "Growth Oriented"
                    color = "#ef4444"  # Red
                else:
                    name = "Balanced Volatility, Moderate Risk"
                    summary = "Stocks in this cluster show a stable profile with balanced volatility and moderate risk level."
                    investor_profile = "Balanced"
                    color = "#3b82f6"  # Blue
                
                # Create cluster object
                cluster_obj = Cluster(
                    id=int(cluster_id),
                    name=name,
                    color=color,
                    avg_volatility=round(avg_volatility, 2),
                    avg_change=round(avg_change, 2),
                    avg_beta=round(avg_beta, 2),
                    risk_return_ratio=round(avg_risk_return, 2),
                    summary=summary,
                    investor_profile=investor_profile
                )
                
                cluster_summaries.append(cluster_obj)
                db.session.add(cluster_obj)
            
            # Save to database
            db.session.commit()
            print(f"Cluster summaries saved to database. {len(cluster_summaries)} clusters processed.")
            
            return True
            
    except Exception as e:
        print(f"Error saving cluster summaries: {e}")
        return False

def main():
    """
    Main function that runs the entire clustering analysis pipeline
    """
    print("Starting BIST 30 Clustering Analysis...")
    
    # Check if feature-engineered data exists
    if not os.path.exists(FEATURE_ENGINEERED_FILE):
        print("Error: Feature-engineered data not found.")
        print("Please run the feature engineering module first.")
        return
    
    # Run clustering analysis
    results = run_clustering_model(FEATURE_ENGINEERED_FILE, n_clusters=4)
    
    if results is None:
        print("Error: Clustering analysis failed.")
        return
    
    # Save cluster summaries to database
    save_cluster_summary_to_db()
    
    print("\nClustering analysis completed successfully!")
    print(f"Results saved to: {CLUSTERING_RESULTS_FILE}")
    print(f"Graphs saved to: {IMAGES_DIR}")
    
    return results

if __name__ == "__main__":
    main() 