import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output
import plotly.express as px
import plotly.graph_objects as go
from sklearn.cluster import KMeans
from preprocess import load_ml_ready_data

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

# Fixed species colors for cross-chart consistency (storytelling requirement)
SPECIES_COLOR_MAP = {
    "Adelie": "#60A5FA",     # lighter blue
    "Chinstrap": "#FBBF24",  # lighter ochre / amber
    "Gentoo": "#2DD4BF",     # lighter teal
}

SPECIES_ORDER = ["Adelie", "Chinstrap", "Gentoo"]

# Separate palette for clustering (avoid reusing species identity colors)
CLUSTER_COLOR_MAP = {
    f"Cluster {i}": px.colors.qualitative.Set2[i] for i in range(5)
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

# Load data
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
                        md=6,
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
                                    md=4,
                                ),
                            ],
                            className="g-2",
                        ),
                        md=6,
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
        ], className="mb-4"),
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
     Output("ml-actual-chart", "figure"),
     Output("ml-cluster-chart", "figure")],
    [Input("species-filter", "value"),
     Input("island-filter", "value"),
     Input("sex-filter", "value"),
     Input("kmeans-slider", "value")]
)
def update_dashboard(selected_species, selected_island, selected_sex, n_clusters):
    selected_species = selected_species or species_options
    selected_island = selected_island or island_options
    selected_sex = selected_sex or sex_options

    if not selected_species or not selected_island or not selected_sex:
        empty_msg = dbc.Alert("Please select at least one option for each filter.", color="warning")
        empty = go.Figure()
        return empty_msg, empty, empty, empty, empty, empty, empty, "", empty, empty

    # Filter the dataframe
    mask = (df_full['species'].isin(selected_species)) & (df_full['island'].isin(selected_island)) & (df_full['sex'].isin(selected_sex))
    filtered_indices = df_full[mask].index
    df = df_full.loc[filtered_indices]

    if df.empty:
        empty_msg = dbc.Alert("No data matches the selected filters. Please adjust your selection.", color="warning")
        empty = go.Figure()
        return empty_msg, empty, empty, empty, empty, empty, empty, "", empty, empty

    # 1. Summary (KPI cards)
    total_penguins = int(len(df))
    avg_mass = float(df["body_mass_kg"].mean())
    heaviest_penguin = df.loc[df["body_mass_kg"].idxmax()]

    heaviest_sex = str(heaviest_penguin.get("sex", "")).strip()
    if not heaviest_sex or heaviest_sex.lower() == "nan":
        heaviest_sex = "Unknown"
    else:
        heaviest_sex = heaviest_sex[:1].upper() + heaviest_sex[1:]

    summary = dbc.Row(
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

    # Drill-down narrative (3 rules)
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
    narrative_lines = []
    if n < 10:
        narrative_lines.append(
            "**Note:** Small sample size; trends may not be statistically significant."
        )

    narrative_lines.append(
        f"You are viewing **{n}** penguins from **{selected_species_text}** on **{selected_island_text}** (Sex: **{selected_sex_text}**)."
    )
    narrative_lines.append(
        f"These penguins are **{abs(pct_diff):.1f}%** {heavier_lighter} than the dataset average body mass."
    )

    auto_insight = None
    species_share = df["species"].value_counts(normalize=True)
    if not species_share.empty and float(species_share.iloc[0]) >= 0.60:
        top_species = str(species_share.index[0])
        auto_insight = f"Most of this subset are **{top_species}** ({float(species_share.iloc[0]) * 100:.0f}%)."
    elif abs(pct_diff) >= 5:
        auto_insight = f"Body mass differs noticeably from the global average (**{abs(pct_diff):.1f}%** {heavier_lighter})."
    else:
        auto_insight = "Bill dimensions still show visible separation by species in many subsets."

    narrative_lines.append(f"The strongest pattern in this subset is: {auto_insight}")

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

    narrative_md = "\n\n".join(narrative_lines)

    # Who lives where?
    df_species_count = df.groupby("species").size().reset_index(name="count")
    fig_species = px.bar(
        df_species_count,
        x="species",
        y="count",
        color="species",
        labels={"species": "Species", "count": "Count"},
        category_orders={"species": SPECIES_ORDER},
        color_discrete_map=SPECIES_COLOR_MAP,
    )
    fig_species = apply_fig_style(fig_species)
    fig_species.update_layout(showlegend=False)
    fig_species.update_traces(
        hovertemplate=(
            "Species: %{x}<br>"
            "Count: %{y}"
            "<extra></extra>"
        )
    )

    # Species by Island (stacked)
    fig_bar = px.bar(
        df.groupby(['island', 'species']).size().reset_index(name='count'),     
        x="island", y="count", color="species", barmode="stack",
        labels={"island": "Island", "count": "Count", "species": "Species"},
        category_orders={"species": SPECIES_ORDER},
        color_discrete_map=SPECIES_COLOR_MAP,
    )
    fig_bar = apply_fig_style(fig_bar)
    fig_bar.update_layout(legend_title_text="Species")
    fig_bar.update_traces(
        hovertemplate=(
            "Island: %{x}<br>"
            "Species: %{fullData.name}<br>"
            "Count: %{y}"
            "<extra></extra>"
        )
    )

    # Body Mass Histogram
    fig_hist = px.histogram(
        df, x="body_mass_kg", color="species", nbins=30, opacity=0.85,
        labels={"body_mass_kg": "Body Mass (kg)", "species": "Species"},
        category_orders={"species": SPECIES_ORDER},
        color_discrete_map=SPECIES_COLOR_MAP,
    )
    fig_hist = apply_fig_style(fig_hist)
    fig_hist.update_layout(legend_title_text="Species")
    fig_hist.update_traces(
        hovertemplate=(
            "Species: %{fullData.name}<br>"
            "Body Mass (kg): %{x:.2f}<br>"
            "Count: %{y}"
            "<extra></extra>"
        )
    )

    # Scatter Plot (Bill dimensions)
    df_scatter = df.copy()
    df_scatter["sex_display"] = df_scatter["sex"].astype(str).str.strip().str.capitalize()

    fig_scatter = px.scatter(
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
    fig_scatter = apply_fig_style(fig_scatter)
    fig_scatter.update_layout(legend_title_text="Species")

    fig_scatter.update_traces(
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
    
    max_bill_penguin = df.loc[df['bill_length_mm'].idxmax()]
    fig_scatter.add_annotation(
        x=max_bill_penguin['bill_length_mm'], y=max_bill_penguin['bill_depth_mm'],
        text=f"Longest Bill: {max_bill_penguin['bill_length_mm']}mm",
        showarrow=True, arrowhead=2, arrowsize=1.5, arrowcolor="red",
        font=dict(size=12, color="red")
    )

    # Box plots
    def _box_stats(source_df, value_col: str) -> dict:
        agg = (
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
        return agg

    mass_stats = _box_stats(df, "body_mass_kg")
    flipper_stats = _box_stats(df, "flipper_length_mm")

    fig_box_mass = px.box(
        df,
        x="species",
        y="body_mass_kg",
        color="species",
        labels={"species": "Species", "body_mass_kg": "Body Mass (kg)"},
        category_orders={"species": SPECIES_ORDER},
        color_discrete_map=SPECIES_COLOR_MAP,
        points=False,
    )
    fig_box_mass = apply_fig_style(fig_box_mass)
    fig_box_mass.update_layout(showlegend=False)
    fig_box_mass.update_traces(hoveron="boxes")
    for trace in fig_box_mass.data:
        sp = str(getattr(trace, "name", ""))
        st = mass_stats.get(sp)
        if not st:
            continue
        trace.hovertext = (
            f"<b>{sp}</b><br>"
            f"n: {int(st['n'])}<br>"
            f"Median: {float(st['median']):.2f} kg<br>"
            f"IQR: {float(st['q1']):.2f}–{float(st['q3']):.2f} kg<br>"
            f"Min–Max: {float(st['min_val']):.2f}–{float(st['max_val']):.2f} kg"
        )
        trace.hovertemplate = "%{hovertext}<extra></extra>"

    fig_box_flipper = px.box(
        df,
        x="species",
        y="flipper_length_mm",
        color="species",
        labels={"species": "Species", "flipper_length_mm": "Flipper Length (mm)"},
        category_orders={"species": SPECIES_ORDER},
        color_discrete_map=SPECIES_COLOR_MAP,
        points=False,
    )
    fig_box_flipper = apply_fig_style(fig_box_flipper)
    fig_box_flipper.update_layout(showlegend=False)
    fig_box_flipper.update_traces(hoveron="boxes")
    for trace in fig_box_flipper.data:
        sp = str(getattr(trace, "name", ""))
        st = flipper_stats.get(sp)
        if not st:
            continue
        trace.hovertext = (
            f"<b>{sp}</b><br>"
            f"n: {int(st['n'])}<br>"
            f"Median: {float(st['median']):.0f} mm<br>"
            f"IQR: {float(st['q1']):.0f}–{float(st['q3']):.0f} mm<br>"
            f"Min–Max: {float(st['min_val']):.0f}–{float(st['max_val']):.0f} mm"
        )
        trace.hovertemplate = "%{hovertext}<extra></extra>"

    # 5. ML Clustering
    if len(df) > n_clusters:
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(X_scaled[filtered_indices])

        df_viz = df.copy()
        df_viz['Cluster'] = [f"Cluster {c}" for c in clusters]

        df_viz["sex_display"] = df_viz["sex"].astype(str).str.strip().str.capitalize()

        fig_actual = px.scatter(
            df_viz,
            x="flipper_length_mm",
            y="body_mass_g",
            color="species",
            hover_name="species",
            custom_data=["island", "sex_display"],
            labels={
                "flipper_length_mm": "Flipper Length (mm)",
                "body_mass_g": "Body Mass (g)",
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
                "Flipper Length: %{x:.0f} mm<br>"
                "Body Mass: %{y:,.0f} g<br>"
                "Island: %{customdata[0]}<br>"
                "Sex: %{customdata[1]}"
                "<extra></extra>"
            )
        )

        fig_cluster = px.scatter(
            df_viz,
            x="flipper_length_mm",
            y="body_mass_g",
            color="Cluster",
            hover_name="species",
            custom_data=["island", "sex_display"],
            labels={
                "flipper_length_mm": "Flipper Length (mm)",
                "body_mass_g": "Body Mass (g)",
                "Cluster": "Cluster",
                "island": "Island",
                "sex_display": "Sex",
            },
            category_orders={"Cluster": [f"Cluster {i}" for i in range(n_clusters)]},
            color_discrete_map=CLUSTER_COLOR_MAP,
        )
        fig_cluster = apply_fig_style(fig_cluster)
        fig_cluster.update_layout(legend_title_text="")
        fig_cluster.update_traces(
            hovertemplate=(
                "<b>%{hovertext}</b><br>"
                "Cluster: %{fullData.name}<br>"
                "Flipper Length: %{x:.0f} mm<br>"
                "Body Mass: %{y:,.0f} g<br>"
                "Island: %{customdata[0]}<br>"
                "Sex: %{customdata[1]}"
                "<extra></extra>"
            )
        )
    else:
        fig_actual, fig_cluster = go.Figure(), go.Figure()
    return (
        summary,
        fig_species,
        fig_bar,
        fig_box_mass,
        fig_box_flipper,
        fig_hist,
        fig_scatter,
        narrative_md,
        fig_actual,
        fig_cluster,
    )

if __name__ == "__main__":
    app.run(debug=True)