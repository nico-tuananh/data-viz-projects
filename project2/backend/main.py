import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import summary, events, daily, weekly_geo, tone_gap, forecast, source_map, data_refresh, keywords, wordcloud

app = FastAPI(title="GDELT Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(summary.router)
app.include_router(events.router)
app.include_router(daily.router)
app.include_router(weekly_geo.router)
app.include_router(tone_gap.router)
app.include_router(forecast.router)
app.include_router(source_map.router)
app.include_router(data_refresh.router)
app.include_router(keywords.router)
app.include_router(wordcloud.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
