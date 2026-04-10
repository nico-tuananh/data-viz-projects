import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import plotly.express as px
import plotly.graph_objects as go

ML_FEATURES = [
    "bill_length_mm",
    "bill_depth_mm",
    "flipper_length_mm",
    "body_mass_g"
]


def prepare_ml_data(df):
    """Clean and scale data for ML."""
    df_ml = df.dropna(subset=ML_FEATURES).copy()
    X = df_ml[ML_FEATURES].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    return df_ml, X_scaled, scaler


def run_pca_and_kmeans(df, k=3):
    """Run 2D/3D PCA and K-Means clustering."""
    df_ml, X_scaled, scaler = prepare_ml_data(df)

    # 2-Component PCA
    pca2 = PCA(n_components=2, random_state=42)
    X_pca2 = pca2.fit_transform(X_scaled)

    # 3-Component PCA
    pca3 = PCA(n_components=3, random_state=42)
    X_pca3 = pca3.fit_transform(X_scaled)

    # K-Means
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    cluster_ids = kmeans.fit_predict(X_scaled)

    if len(np.unique(cluster_ids)) > 1:
        sil_score = silhouette_score(X_scaled, cluster_ids)
    else:
        sil_score = 0.0

    df_results = df_ml.copy()
    df_results["PC1"] = X_pca2[:, 0]
    df_results["PC2"] = X_pca2[:, 1]
    df_results["PC3"] = X_pca3[:, 2]
    df_results["cluster"] = [f"Cluster {i}" for i in cluster_ids]

    metrics = {
        "pc1_var": pca2.explained_variance_ratio_[0],
        "pc2_var": pca2.explained_variance_ratio_[1],
        "pc3_var": pca3.explained_variance_ratio_[2],
        "total_var_2d": pca2.explained_variance_ratio_.sum(),
        "total_var_3d": pca3.explained_variance_ratio_.sum(),
        "silhouette_score": sil_score,
        "k": k,
        "X_scaled": X_scaled  # Needed for fingerprints
    }

    return df_results, metrics


def create_pca_scatter(df_results, color_by="cluster"):
    """Create a 2D PCA scatter plot."""
    color_col = "species" if color_by == "species" else "cluster"
    fig = px.scatter(
        df_results, x='PC1', y='PC2', 
        color=color_col, 
        symbol='species',
        title=f'2D PCA Space: {color_col.capitalize()} vs Species',
        labels={'PC1': 'Principal Component 1', 'PC2': 'Principal Component 2'},
        width=800, height=600,
        template='plotly_white'
    )
    fig.update_layout(title_x=0.5)
    return fig


def create_3d_pca_scatter(df_results):
    """Create a 3D PCA scatter plot with optimized view."""
    fig = px.scatter_3d(
        df_results, x='PC1', y='PC2', z='PC3',
        color='cluster', 
        symbol='species',
        title='3D PCA Space: Exploring the Extra Dimension',
        labels={'PC1': 'PC1', 'PC2': 'PC2', 'PC3': 'PC3'},
        width=900, height=700,
        template='plotly_white'
    )
    fig.update_traces(marker={"size": 5, "opacity": 0.8, "line": {"width": 1, "color": "DarkSlateGrey"}})
    fig.update_layout(
        scene_camera={"eye": {"x": 1.8, "y": 1.8, "z": 0.8}},
        dragmode='orbit',
        title_x=0.5
    )
    return fig


def create_cluster_fingerprints_heatmap(df_results):
    """Create a heatmap of average feature values per cluster."""
    # Calculate means
    cluster_means = df_results.groupby('cluster')[ML_FEATURES].mean()
    # Normalize for visualization [0, 1]
    cluster_means_norm = (cluster_means - cluster_means.min()) / (cluster_means.max() - cluster_means.min())

    fig = px.imshow(
        cluster_means_norm.T,
        labels=dict(x='Cluster', y='Feature', color='Relative Value'),
        title='Cluster Fingerprints: Average Feature Values',
        color_continuous_scale='Blues',
        aspect='auto'
    )
    fig.update_layout(title_x=0.5, template='plotly_white')
    return fig


def generate_ml_summary_text(df_results, metrics):
    """Generate summary text of the ML results."""
    if df_results.empty:
        return "No data available."

    summary = (
        f"ML Summary\n"
        f"----------\n"
        f"Rows analyzed: {len(df_results)}\n"
        f"Variance Explained (2D): {metrics['total_var_2d']*100:.1f}%\n"
        f"Variance Explained (3D): {metrics['total_var_3d']*100:.1f}%\n"
        f"Silhouette Score: {metrics['silhouette_score']:.3f}\n"
    )
    return summary


if __name__ == "__main__":
    from preprocess import load_clean_data
    
    df = load_clean_data()
    df_results, metrics = run_pca_and_kmeans(df, k=3)
    
    print(generate_ml_summary_text(df_results, metrics))
    
    # Generate and show plots
    fig_2d = create_pca_scatter(df_results)
    fig_3d = create_3d_pca_scatter(df_results)
    fig_fingerprints = create_cluster_fingerprints_heatmap(df_results)
    
    fig_2d.show()
    fig_3d.show()
    fig_fingerprints.show()

    