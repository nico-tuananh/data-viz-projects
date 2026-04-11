import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from typing import Any
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from preprocess import load_ml_ready_data

# --- Plotly defaults ---
PLOTLY_TEMPLATE = "plotly_white"
GRAPH_CONFIG = {
    "displaylogo": False,
    "responsive": True,
    "modeBarButtonsToRemove": [
        "lasso2d",
        "select2d",
    ],
}

FOREST_SAGE = [
    "#2f6f55",  # deep sage
    "#6aa084",  # soft sage
    "#9cc3a8",  # misty green
    "#1f4d3b",  # forest
    "#7a9d8f",  # gray sage
    "#b7d3c5",  # pale sage
]

# --- Color mapping (kept consistent across all charts) ---
SPECIES_COLOR_MAP = {
    "Adelie": "#60A5FA",     # lighter blue
    "Chinstrap": "#FBBF24",  # lighter ochre / amber
    "Gentoo": "#2DD4BF",     # lighter teal
}

SPECIES_ORDER = ["Adelie", "Chinstrap", "Gentoo"]

# Use the same 3-color palette across the whole dashboard for consistent storytelling
DASHBOARD_DISCRETE_SEQUENCE = [SPECIES_COLOR_MAP[s] for s in SPECIES_ORDER]
px.defaults.color_discrete_sequence = DASHBOARD_DISCRETE_SEQUENCE

# Keep clusters in the same palette (cycles when K > 3)
CLUSTER_COLOR_MAP = {
    f"Cluster {i}": DASHBOARD_DISCRETE_SEQUENCE[i % len(DASHBOARD_DISCRETE_SEQUENCE)]
    for i in range(5)
}


def capitalize_first_letter(text: str) -> str:
    value = str(text).strip()
    if not value:
        return value
    return value[:1].upper() + value[1:]


def format_selection(selected_values: list[str], all_values: list[str], noun: str) -> str:
    selected_values = [str(v) for v in (selected_values or []) if str(v).strip()]
    all_values = [str(v) for v in (all_values or []) if str(v).strip()]

    if not selected_values or set(selected_values) == set(all_values):
        return f"all {noun}"
    if len(selected_values) == 1:
        return selected_values[0]
    return ", ".join(selected_values)


def apply_fig_style(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        margin=dict(l=20, r=20, t=30, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="Geist, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif",
            color="#0F172A",
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        legend_title_text="",
        title=None,
        hoverlabel=dict(
            bgcolor="rgba(255, 255, 255, 0.96)",
            bordercolor="rgba(15, 23, 42, 0.20)",
            font=dict(
                family="Geist, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif",
                size=12,
                color="#0F172A",
            ),
            align="left",
        ),
    )
    fig.update_xaxes(gridcolor="rgba(15, 23, 42, 0.10)")
    fig.update_yaxes(gridcolor="rgba(15, 23, 42, 0.10)")
    return fig

# --- Data loading (runs once at server start) ---
df_full, X_scaled, feature_names = load_ml_ready_data()
df_full = df_full.reset_index(drop=True)

GLOBAL_AVG_BODY_MASS_KG = float(df_full["body_mass_kg"].mean())

_species_bill_means = (
    df_full.groupby("species")["bill_length_mm"].mean().sort_values().to_dict()
)
SPECIES_FACTS = (
    df_full.groupby("species")
    .agg(
        n=("species", "size"),
        avg_bill_length_mm=("bill_length_mm", "mean"),
        avg_bill_depth_mm=("bill_depth_mm", "mean"),
        avg_flipper_length_mm=("flipper_length_mm", "mean"),
        avg_body_mass_kg=("body_mass_kg", "mean"),
    )
    .to_dict("index")
)

species_options = sorted(df_full["species"].astype(str).unique().tolist())
island_options = sorted(df_full["island"].astype(str).unique().tolist())
sex_options = sorted(df_full["sex"].astype(str).unique().tolist())


# --- Callback helpers ---
def _empty_outputs(message: str) -> tuple[Any, ...]:
    alert = dbc.Alert(message, color="warning")
    empty = go.Figure()
    return alert, empty, empty, empty, empty, empty, empty, "", "", empty, empty


def _normalize_filters(
    selected_species: list[str] | None,
    selected_island: list[str] | None,
    selected_sex: list[str] | None,
) -> tuple[list[str], list[str], list[str]]:
    # Treat empty selection as "all" for each filter.
    return (
        selected_species or species_options,
        selected_island or island_options,
        selected_sex or sex_options,
    )


def _filter_df_and_indices(
    selected_species: list[str],
    selected_island: list[str],
    selected_sex: list[str],
):
    mask = (
        df_full["species"].isin(selected_species)
        & df_full["island"].isin(selected_island)
        & df_full["sex"].isin(selected_sex)
    )
    df = df_full.loc[mask]
    filtered_indices = df.index.to_numpy(dtype=int)
    return df, filtered_indices


def _build_summary_cards(df) -> dbc.Row:
    # KPI summary at the top.
    total_penguins = int(len(df))
    avg_mass = float(df["body_mass_kg"].mean())
    heaviest_penguin = df.loc[df["body_mass_kg"].idxmax()]

    heaviest_sex = str(heaviest_penguin.get("sex", "")).strip()
    if not heaviest_sex or heaviest_sex.lower() == "nan":
        heaviest_sex = "Unknown"
    else:
        heaviest_sex = heaviest_sex[:1].upper() + heaviest_sex[1:]

    return dbc.Row(
        [
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.Div("Penguins Observed", className="ag-caption"),
                            html.H2(f"{total_penguins}", className="mb-0 ag-data"),
                        ]
                    ),
                    className="shadow-sm h-100 w-100",
                ),
                md=4,
                className="d-flex",
            ),
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.Div("Average Body Mass (kg)", className="ag-caption"),
                            html.H2(f"{avg_mass:.2f}", className="mb-0 ag-data"),
                        ]
                    ),
                    className="shadow-sm h-100 w-100",
                ),
                md=4,
                className="d-flex",
            ),
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.Div("Heaviest Penguin", className="ag-caption"),
                            html.Div(
                                f"{heaviest_sex} {heaviest_penguin['species']} ({heaviest_penguin['island']})",
                                className="fw-semibold",
                            ),
                            html.Div(
                                f"{float(heaviest_penguin['body_mass_kg']):.2f} kg",
                                className="ag-caption ag-data",
                            ),
                        ]
                    ),
                    className="shadow-sm h-100 w-100",
                ),
                md=4,
                className="d-flex",
            ),
        ],
        className="g-3 mt-2 align-items-stretch",
    )


def _build_narrative(
    df,
    selected_species: list[str],
    selected_island: list[str],
    selected_sex: list[str],
) -> str:
    # Short, auto-generated insight text.
    n = int(len(df))
    selected_species_text = format_selection(selected_species, species_options, "species")
    selected_island_text = format_selection(selected_island, island_options, "islands")
    selected_sex_text = format_selection(
        [capitalize_first_letter(s) for s in selected_sex],
        [capitalize_first_letter(s) for s in sex_options],
        "sexes",
    )

    subset_avg_mass = float(df["body_mass_kg"].mean())
    pct_diff = 0.0
    if GLOBAL_AVG_BODY_MASS_KG != 0:
        pct_diff = (subset_avg_mass - GLOBAL_AVG_BODY_MASS_KG) / GLOBAL_AVG_BODY_MASS_KG * 100

    heavier_lighter = "heavier" if pct_diff >= 0 else "lighter"
    narrative_lines: list[str] = []

    if n < 10:
        narrative_lines.append("**Note:** Small sample size; trends may not be statistically significant.")

    narrative_lines.append(
        f"You are viewing **{n}** penguins from **{selected_species_text}** on **{selected_island_text}** (Sex: **{selected_sex_text}**)."
    )
    narrative_lines.append(
        f"These penguins are **{abs(pct_diff):.1f}%** {heavier_lighter} than the dataset average body mass."
    )

    species_share = df["species"].value_counts(normalize=True)
    if not species_share.empty and float(species_share.iloc[0]) >= 0.60:
        top_species = str(species_share.index[0])
        auto_insight = f"Most of this subset are **{top_species}** ({float(species_share.iloc[0]) * 100:.0f}%)."
    elif abs(pct_diff) >= 5:
        auto_insight = (
            f"Body mass differs noticeably from the global average (**{abs(pct_diff):.1f}%** {heavier_lighter})."
        )
    else:
        auto_insight = "Bill dimensions still show visible separation by species in many subsets."

    narrative_lines.append(f"The strongest pattern in this subset is: {auto_insight}")

    # Add one species-specific fact when the filter is focused.
    if selected_species and len(selected_species) == 1:
        sp = str(selected_species[0])
        facts = SPECIES_FACTS.get(sp)
        if facts:
            avg_bill = float(facts["avg_bill_length_mm"])
            bill_ranked = sorted(_species_bill_means.items(), key=lambda kv: kv[1])
            bill_trait = "moderate-length"
            if bill_ranked and sp == bill_ranked[0][0]:
                bill_trait = "shorter"
            elif bill_ranked and sp == bill_ranked[-1][0]:
                bill_trait = "longer"

            narrative_lines.append(
                f"**{sp}** penguins are recognized by their **{bill_trait} bills** (avg **{avg_bill:.1f} mm**)."
            )

    return "\n\n".join(narrative_lines)


def _compute_box_stats(source_df, value_col: str) -> dict[str, dict[str, float]]:
    # Precompute distribution stats for hover text.
    return (
        source_df.groupby("species")[value_col]
        .agg(
            n="size",
            min_val="min",
            q1=lambda s: float(s.quantile(0.25)),
            median="median",
            q3=lambda s: float(s.quantile(0.75)),
            max_val="max",
            mean="mean",
        )
        .to_dict("index")
    )


def _species_count_fig(df) -> go.Figure:
    counts = df.groupby("species").size().reset_index(name="count")
    fig = px.bar(
        counts,
        x="species",
        y="count",
        color="species",
        labels={"species": "Species", "count": "Count"},
        category_orders={"species": SPECIES_ORDER},
        color_discrete_map=SPECIES_COLOR_MAP,
    )
    fig = apply_fig_style(fig)
    fig.update_layout(showlegend=False)
    fig.update_traces(
        hovertemplate=(
            "Species: %{x}<br>"
            "Count: %{y}"
            "<extra></extra>"
        )
    )
    return fig


def _species_by_island_fig(df) -> go.Figure:
    grouped = df.groupby(["island", "species"]).size().reset_index(name="count")
    fig = px.bar(
        grouped,
        x="island",
        y="count",
        color="species",
        barmode="stack",
        labels={"island": "Island", "count": "Count", "species": "Species"},
        category_orders={"species": SPECIES_ORDER},
        color_discrete_map=SPECIES_COLOR_MAP,
    )
    fig = apply_fig_style(fig)
    fig.update_layout(legend_title_text="Species")
    fig.update_traces(
        hovertemplate=(
            "Island: %{x}<br>"
            "Species: %{fullData.name}<br>"
            "Count: %{y}"
            "<extra></extra>"
        )
    )
    return fig


def _mass_histogram_fig(df) -> go.Figure:
    fig = px.histogram(
        df,
        x="body_mass_kg",
        color="species",
        nbins=30,
        opacity=0.85,
        labels={"body_mass_kg": "Body Mass (kg)", "species": "Species"},
        category_orders={"species": SPECIES_ORDER},
        color_discrete_map=SPECIES_COLOR_MAP,
    )
    fig = apply_fig_style(fig)
    fig.update_layout(legend_title_text="Species")
    fig.update_traces(
        hovertemplate=(
            "Species: %{fullData.name}<br>"
            "Body Mass (kg): %{x:.2f}<br>"
            "Count: %{y}"
            "<extra></extra>"
        )
    )
    return fig


def _bill_scatter_fig(df) -> go.Figure:
    df_scatter = df.copy()
    df_scatter["sex_display"] = df_scatter["sex"].astype(str).str.strip().str.capitalize()

    fig = px.scatter(
        df_scatter,
        x="bill_length_mm",
        y="bill_depth_mm",
        color="species",
        size="body_mass_g",
        hover_name="species",
        custom_data=["island", "sex_display", "body_mass_g"],
        labels={
            "bill_length_mm": "Bill Length (mm)",
            "bill_depth_mm": "Bill Depth (mm)",
            "body_mass_g": "Body Mass (g)",
            "species": "Species",
            "island": "Island",
            "sex_display": "Sex",
        },
        category_orders={"species": SPECIES_ORDER},
        color_discrete_map=SPECIES_COLOR_MAP,
    )
    fig = apply_fig_style(fig)
    fig.update_layout(legend_title_text="Species")
    fig.update_traces(
        hovertemplate=(
            "<b>%{hovertext}</b><br>"
            "Bill Length: %{x:.1f} mm<br>"
            "Bill Depth: %{y:.1f} mm<br>"
            "Body Mass: %{customdata[2]:,.0f} g<br>"
            "Island: %{customdata[0]}<br>"
            "Sex: %{customdata[1]}"
            "<extra></extra>"
        )
    )

    # Highlight a notable extreme.
    max_bill_penguin = df.loc[df["bill_length_mm"].idxmax()]
    fig.add_annotation(
        x=max_bill_penguin["bill_length_mm"],
        y=max_bill_penguin["bill_depth_mm"],
        text=f"Longest Bill: {max_bill_penguin['bill_length_mm']}mm",
        showarrow=True,
        arrowhead=2,
        arrowsize=1.5,
        arrowcolor="red",
        font=dict(size=12, color="red"),
    )
    return fig


def _box_fig(df, value_col: str, y_label: str, value_format: str, unit: str) -> go.Figure:
    stats = _compute_box_stats(df, value_col)
    fig = px.box(
        df,
        x="species",
        y=value_col,
        color="species",
        labels={"species": "Species", value_col: y_label},
        category_orders={"species": SPECIES_ORDER},
        color_discrete_map=SPECIES_COLOR_MAP,
        points=False,
    )
    fig = apply_fig_style(fig)
    fig.update_layout(showlegend=False)
    fig.update_traces(hoveron="boxes")

    for trace in fig.data:
        sp = str(getattr(trace, "name", ""))
        st = stats.get(sp)
        if not st:
            continue
        trace.hovertext = (
            f"<b>{sp}</b><br>"
            f"n: {int(st['n'])}<br>"
            f"Median: {float(st['median']):{value_format}} {unit}<br>"
            f"IQR: {float(st['q1']):{value_format}}–{float(st['q3']):{value_format}} {unit}<br>"
            f"Min–Max: {float(st['min_val']):{value_format}}–{float(st['max_val']):{value_format}} {unit}"
        )
        trace.hovertemplate = "%{hovertext}<extra></extra>"

    return fig


def _ml_pca_figs(df, filtered_indices: np.ndarray, n_clusters: int, pca_mode: str):
    # Builds the "Actual" and "Cluster" PCA charts.
    fig_actual, fig_cluster = go.Figure(), go.Figure()
    pca_variance_text = ""

    X_subset = X_scaled[filtered_indices]
    n_components = 3 if str(pca_mode).lower() == "3d" else 2
    if X_subset.shape[0] < max(int(n_clusters), n_components):
        return fig_actual, fig_cluster, pca_variance_text

    kmeans = KMeans(n_clusters=int(n_clusters), random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X_subset)

    df_viz = df.copy()
    df_viz["Cluster"] = [f"Cluster {c}" for c in clusters]
    df_viz["sex_display"] = df_viz["sex"].astype(str).str.strip().str.capitalize()

    pca = PCA(n_components=n_components, random_state=42)
    X_pca = pca.fit_transform(X_subset)

    df_viz["PC1"] = X_pca[:, 0]
    df_viz["PC2"] = X_pca[:, 1]
    if n_components == 3:
        df_viz["PC3"] = X_pca[:, 2]

    retained = float(np.sum(pca.explained_variance_ratio_)) * 100
    pca_variance_text = (
        f"Using {n_components}D PCA, the projection retains {retained:.1f}% of the variance "
        f"from the 4 original measurements."
    )

    cluster_order = [f"Cluster {i}" for i in range(int(n_clusters))]

    if n_components == 2:
        fig_actual = px.scatter(
            df_viz,
            x="PC1",
            y="PC2",
            color="species",
            hover_name="species",
            custom_data=["island", "sex_display"],
            labels={
                "PC1": "Principal Component 1",
                "PC2": "Principal Component 2",
                "species": "Species",
                "island": "Island",
                "sex_display": "Sex",
            },
            category_orders={"species": SPECIES_ORDER},
            color_discrete_map=SPECIES_COLOR_MAP,
        )
        fig_actual = apply_fig_style(fig_actual)
        fig_actual.update_layout(legend_title_text="Species")
        fig_actual.update_traces(
            hovertemplate=(
                "<b>%{hovertext}</b><br>"
                "PC1: %{x:.2f}<br>"
                "PC2: %{y:.2f}<br>"
                "Island: %{customdata[0]}<br>"
                "Sex: %{customdata[1]}"
                "<extra></extra>"
            )
        )

        fig_cluster = px.scatter(
            df_viz,
            x="PC1",
            y="PC2",
            color="Cluster",
            hover_name="species",
            custom_data=["island", "sex_display"],
            labels={
                "PC1": "Principal Component 1",
                "PC2": "Principal Component 2",
                "Cluster": "Cluster",
                "island": "Island",
                "sex_display": "Sex",
            },
            category_orders={"Cluster": cluster_order},
            color_discrete_map=CLUSTER_COLOR_MAP,
        )
        fig_cluster = apply_fig_style(fig_cluster)
        fig_cluster.update_layout(legend_title_text="")
        fig_cluster.update_traces(
            hovertemplate=(
                "<b>%{hovertext}</b><br>"
                "Cluster: %{fullData.name}<br>"
                "PC1: %{x:.2f}<br>"
                "PC2: %{y:.2f}<br>"
                "Island: %{customdata[0]}<br>"
                "Sex: %{customdata[1]}"
                "<extra></extra>"
            )
        )
    else:
        fig_actual = px.scatter_3d(
            df_viz,
            x="PC1",
            y="PC2",
            z="PC3",
            color="species",
            hover_name="species",
            custom_data=["island", "sex_display"],
            labels={
                "PC1": "PC1",
                "PC2": "PC2",
                "PC3": "PC3",
                "species": "Species",
                "island": "Island",
                "sex_display": "Sex",
            },
            category_orders={"species": SPECIES_ORDER},
            color_discrete_map=SPECIES_COLOR_MAP,
        )
        fig_actual = apply_fig_style(fig_actual)
        fig_actual.update_traces(marker={"size": 5, "opacity": 0.8})
        fig_actual.update_layout(
            scene_camera={"eye": {"x": 1.8, "y": 1.8, "z": 0.8}},
            dragmode="orbit",
            legend_title_text="Species",
        )
        fig_actual.update_traces(
            hovertemplate=(
                "<b>%{hovertext}</b><br>"
                "PC1: %{x:.2f}<br>"
                "PC2: %{y:.2f}<br>"
                "PC3: %{z:.2f}<br>"
                "Island: %{customdata[0]}<br>"
                "Sex: %{customdata[1]}"
                "<extra></extra>"
            )
        )

        fig_cluster = px.scatter_3d(
            df_viz,
            x="PC1",
            y="PC2",
            z="PC3",
            color="Cluster",
            hover_name="species",
            custom_data=["island", "sex_display"],
            labels={
                "PC1": "PC1",
                "PC2": "PC2",
                "PC3": "PC3",
                "Cluster": "Cluster",
                "island": "Island",
                "sex_display": "Sex",
            },
            category_orders={"Cluster": cluster_order},
            color_discrete_map=CLUSTER_COLOR_MAP,
        )
        fig_cluster = apply_fig_style(fig_cluster)
        fig_cluster.update_traces(marker={"size": 5, "opacity": 0.8})
        fig_cluster.update_layout(
            scene_camera={"eye": {"x": 1.8, "y": 1.8, "z": 0.8}},
            dragmode="orbit",
            legend_title_text="",
        )
        fig_cluster.update_traces(
            hovertemplate=(
                "<b>%{hovertext}</b><br>"
                "Cluster: %{fullData.name}<br>"
                "PC1: %{x:.2f}<br>"
                "PC2: %{y:.2f}<br>"
                "PC3: %{z:.2f}<br>"
                "Island: %{customdata[0]}<br>"
                "Sex: %{customdata[1]}"
                "<extra></extra>"
            )
        )

    return fig_actual, fig_cluster, pca_variance_text

# Initialize Dash application with Bootstrap theme.
# The custom typography/palette is defined in assets/theme.css.
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Palmer Penguins Dashboard"

header = html.Div(
    dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Div(
                                [
                                    html.Img(
                                        src="/assets/penguin.svg",
                                        className="ag-logo",
                                        alt="Penguin illustration",
                                    ),
                                    html.Div(
                                        [
                                            html.H1("Palmer Penguins Dashboard", className="ag-title")
                                        ]
                                    ),
                                ],
                                className="ag-title-row",
                            ),
                            html.P(
                                "Explore penguin species, island habitats, and physical measurements through interactive storytelling.",
                                className="ag-caption mb-0",
                            ),
                        ],
                        lg=7,
                        md=7,
                        xs=12,
                    ),
                    dbc.Col(
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        html.Label("Species"),
                                        dcc.Dropdown(
                                            id="species-filter",
                                            options=[{"label": s, "value": s} for s in species_options],
                                            value=species_options,
                                            multi=True,
                                            placeholder="Select species...",
                                        ),
                                    ],
                                    xs=12,
                                    md=4,
                                ),
                                dbc.Col(
                                    [
                                        html.Label("Island"),
                                        dcc.Dropdown(
                                            id="island-filter",
                                            options=[{"label": i, "value": i} for i in island_options],
                                            value=island_options,
                                            multi=True,
                                            placeholder="Select islands...",
                                        ),
                                    ],
                                    xs=12,
                                    md=4,
                                ),
                                dbc.Col(
                                    [
                                        html.Label("Sex"),
                                        dcc.Dropdown(
                                            id="sex-filter",
                                            options=[
                                                {"label": capitalize_first_letter(s), "value": s}
                                                for s in sex_options
                                            ],
                                            value=sex_options,
                                            multi=True,
                                            placeholder="Select sex...",
                                        ),
                                    ],
                                    xs=12,
                                    md=4,
                                ),
                            ],
                            className="g-2",
                        ),
                        lg=5,
                        md=5,
                        xs=12,
                        className="ag-controls",
                    ),
                ],
                className="align-items-end gy-3",
            )
        ],
        fluid=True,
        className="py-4",
    ),
    className="ag-header",
)

# Main Content Layout
content = html.Div(
    [
        dcc.Loading(html.Div(id="summary-container", className="mb-4"), type="dot"),
        html.Hr(),
        html.H3("Who Lives Where?", className="mb-2"),
        html.P(
            "Species are not distributed uniformly across islands, suggesting that habitat is an important context for interpreting body measurements.",
            className="ag-caption mb-3",
        ),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Penguins by Species", className="text-center m-0")),
                    dbc.CardBody(dcc.Loading(dcc.Graph(id="species-count-chart", config=GRAPH_CONFIG, style={"height": "320px"}), type="circle"))
                ], className="ag-card mb-4")
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Species by Island", className="text-center m-0")),
                    dbc.CardBody(dcc.Loading(dcc.Graph(id="bar-chart", config=GRAPH_CONFIG, style={"height": "320px"}), type="circle"))
                ], className="ag-card mb-4")
            ], width=6)
        ], className="mb-0"),
        html.Hr(),
        html.H3("How Do Species Differ Physically?", className="mb-2"),
        html.P(
            "Physical measurements reveal strong separation among species, especially when comparing bill dimensions and body size.",
            className="ag-caption mb-3",
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    html.H5(
                                        "Bill Dimensions: Length vs Depth",
                                        className="text-center m-0",
                                    )
                                ),
                                dbc.CardBody(
                                    dcc.Loading(
                                        dcc.Graph(
                                            id="scatter-chart",
                                            config=GRAPH_CONFIG,
                                            style={"height": "420px"},
                                        ),
                                        type="circle",
                                    )
                                ),
                            ],
                            className="ag-card mb-4",
                        )
                    ],
                    width=8,
                ),
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H5("Drill-Down", className="mb-2"),
                                        dcc.Markdown(id="narrative-md", className="ag-caption"),
                                    ]
                                )
                            ],
                            className="ag-card mb-4",
                        ),
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H6("How to Read", className="mb-2"),
                                        html.Ul(
                                            [
                                                html.Li("Each point represents one penguin."),
                                                html.Li(
                                                    "Separation between clusters suggests distinct species-specific body profiles."
                                                ),
                                                html.Li(
                                                    "Use filters to focus on a subset; the drill-down text updates automatically."
                                                ),
                                            ],
                                            className="ag-caption mb-0",
                                        ),
                                    ]
                                )
                            ],
                            className="ag-card",
                        ),
                    ],
                    width=4,
                ),
            ],
            className="mb-2",
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    html.H5(
                                        "Body Mass (kg) by Species",
                                        className="text-center m-0",
                                    )
                                ),
                                dbc.CardBody(
                                    dcc.Loading(
                                        dcc.Graph(
                                            id="box-mass-chart",
                                            config=GRAPH_CONFIG,
                                            style={"height": "320px"},
                                        ),
                                        type="circle",
                                    )
                                ),
                            ],
                            className="ag-card mb-4",
                        )
                    ],
                    width=6,
                ),
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    html.H5(
                                        "Flipper Length (mm) by Species",
                                        className="text-center m-0",
                                    )
                                ),
                                dbc.CardBody(
                                    dcc.Loading(
                                        dcc.Graph(
                                            id="box-flipper-chart",
                                            config=GRAPH_CONFIG,
                                            style={"height": "320px"},
                                        ),
                                        type="circle",
                                    )
                                ),
                            ],
                            className="ag-card mb-4",
                        )
                    ],
                    width=6,
                ),
            ],
            className="mb-0",
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    html.H5(
                                        "Body Mass Distribution",
                                        className="text-center m-0",
                                    )
                                ),
                                dbc.CardBody(
                                    dcc.Loading(
                                        dcc.Graph(
                                            id="histogram-chart",
                                            config=GRAPH_CONFIG,
                                            style={"height": "320px"},
                                        ),
                                        type="circle",
                                    )
                                ),
                            ],
                            className="ag-card mb-4",
                        )
                    ],
                    width=12,
                )
            ]
        ),
        html.Hr(),
        html.H3("Machine Learning: K-Means Clustering", className="mb-3"),
        html.Div([
            html.Label("Select Number of Clusters (K)"),
            dcc.Slider(
                id="kmeans-slider",
                min=2, max=5, step=1, value=3,
                marks={i: str(i) for i in range(2, 6)}
            )
        ], className="mb-3"),
        html.Div(
            [
                html.Label("PCA Projection"),
                dcc.RadioItems(
                    id="pca-mode",
                    options=[
                        {"label": "2D", "value": "2d"},
                        {"label": "3D", "value": "3d"},
                    ],
                    value="2d",
                    inline=True,
                    inputStyle={"marginRight": "6px", "marginLeft": "10px"},
                ),
            ],
            className="mb-2",
        ),
        html.P(
            id="pca-variance-text",
            className="ag-caption text-center mb-4",
        ),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Actual Species Grouping", className="text-center m-0")),
                    dbc.CardBody(dcc.Loading(dcc.Graph(id="ml-actual-chart", config=GRAPH_CONFIG, style={"height": "350px"}), type="circle"))
                ], className="ag-card mb-4")
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("K-Means Clusters", className="text-center m-0")),
                    dbc.CardBody(dcc.Loading(dcc.Graph(id="ml-cluster-chart", config=GRAPH_CONFIG, style={"height": "350px"}), type="circle"))
                ], className="ag-card mb-4")
            ], width=6)
        ]),
        html.P(
            "Notice how the unsupervised clusters map back to the actual species groups based on their physical attributes.",
            className="ag-caption text-center mt-2",
        )
    ],
    className="p-4"
)

# Set app layout (no sidebar; filters live in header)
app.layout = html.Div([
    header,
    dbc.Container(content, fluid=True),
])

# Callbacks
@app.callback(
    [Output("summary-container", "children"),
     Output("species-count-chart", "figure"),
     Output("bar-chart", "figure"),
     Output("box-mass-chart", "figure"),
     Output("box-flipper-chart", "figure"),
     Output("histogram-chart", "figure"),
     Output("scatter-chart", "figure"),
     Output("narrative-md", "children"),
    Output("pca-variance-text", "children"),
     Output("ml-actual-chart", "figure"),
     Output("ml-cluster-chart", "figure")],
    [Input("species-filter", "value"),
     Input("island-filter", "value"),
     Input("sex-filter", "value"),
    Input("kmeans-slider", "value"),
    Input("pca-mode", "value")]
)
def update_dashboard(selected_species, selected_island, selected_sex, n_clusters, pca_mode):
    selected_species, selected_island, selected_sex = _normalize_filters(
        selected_species, selected_island, selected_sex
    )

    if not selected_species or not selected_island or not selected_sex:
        return _empty_outputs("Please select at least one option for each filter.")

    df, filtered_indices = _filter_df_and_indices(
        selected_species, selected_island, selected_sex
    )
    if df.empty:
        return _empty_outputs(
            "No data matches the selected filters. Please adjust your selection."
        )

    summary = _build_summary_cards(df)
    narrative_md = _build_narrative(df, selected_species, selected_island, selected_sex)

    # Charts
    fig_species = _species_count_fig(df)
    fig_bar = _species_by_island_fig(df)
    fig_hist = _mass_histogram_fig(df)
    fig_scatter = _bill_scatter_fig(df)
    fig_box_mass = _box_fig(df, "body_mass_kg", "Body Mass (kg)", ".2f", "kg")
    fig_box_flipper = _box_fig(
        df, "flipper_length_mm", "Flipper Length (mm)", ".0f", "mm"
    )

    # ML charts
    fig_actual, fig_cluster, pca_variance_text = _ml_pca_figs(
        df, filtered_indices, int(n_clusters), str(pca_mode)
    )
    return (
        summary,
        fig_species,
        fig_bar,
        fig_box_mass,
        fig_box_flipper,
        fig_hist,
        fig_scatter,
        narrative_md,
        pca_variance_text,
        fig_actual,
        fig_cluster,
    )

if __name__ == "__main__":
    app.run(debug=True)