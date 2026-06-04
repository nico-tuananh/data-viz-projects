"""Shared visual constants for the Shiny dashboard."""

MEDIA_COLORS = {
    "Western": "#28a7ff",
    "Chinese": "#ff4d5e",
    "Global/Other": "#94a3b8",
    "ToneGap": "#f8b84e",
}

MODEL_COLORS = {
    "ActualDark": "#f8fafc",
    "ActualLight": "#0f172a",
    "ARIMA": "#28a7ff",
    "HoltWinters": "#ff4d5e",
    "Prophet": "#48d597",
    "TimesFM": "#f8b84e",
}

PLOT_FONT = "IBM Plex Sans, Arial, sans-serif"

THEME_STYLES = {
    "dark": {
        "font_color": "#dbeafe",
        "paper_bg": "rgba(0,0,0,0)",
        "plot_bg": "rgba(6,14,32,0.35)",
        "grid": "rgba(148,163,184,0.16)",
        "line": "rgba(148,163,184,0.28)",
        "hover_bg": "#0b1224",
        "hover_border": "#2c3e66",
        "annotation_bg": "rgba(15,23,42,0.82)",
        "annotation_border": "rgba(255,255,255,0.16)",
        "land": "#101b34",
        "ocean": "#07111f",
        "country": "rgba(148,163,184,0.45)",
        "coast": "rgba(148,163,184,0.28)",
        "actual_line": MODEL_COLORS["ActualDark"],
        "baseline": "rgba(226,232,240,0.68)",
        "subtle_positive": "rgba(248,184,78,0.10)",
        "subtle_negative": "rgba(255,77,94,0.08)",
    },
    "light": {
        "font_color": "#0f172a",
        "paper_bg": "rgba(255,255,255,0)",
        "plot_bg": "rgba(255,255,255,0.82)",
        "grid": "rgba(148,163,184,0.22)",
        "line": "rgba(100,116,139,0.40)",
        "hover_bg": "#ffffff",
        "hover_border": "#cbd5e1",
        "annotation_bg": "rgba(255,255,255,0.95)",
        "annotation_border": "rgba(15,23,42,0.18)",
        "land": "#eef3fb",
        "ocean": "#dce8f7",
        "country": "rgba(71,85,105,0.38)",
        "coast": "rgba(100,116,139,0.30)",
        "actual_line": MODEL_COLORS["ActualLight"],
        "baseline": "rgba(71,85,105,0.60)",
        "subtle_positive": "rgba(248,184,78,0.16)",
        "subtle_negative": "rgba(255,77,94,0.10)",
    },
}
