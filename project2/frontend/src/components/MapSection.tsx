/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable react-hooks/set-state-in-effect */
import { useEffect, useState, useMemo } from 'react';
import { MapContainer, TileLayer, CircleMarker, Tooltip, useMap, GeoJSON } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { useFilters } from '../hooks/useFilters';
import { useTheme } from '../hooks/useTheme';
import { getEvents, getWeeklyGeo, getSourceMap } from '../api';

const GROUP_COLORS: Record<string, string> = {
  Western: '#2563EB',
  Chinese: '#EF4444',
  'Global/Other': '#71717A',
};

// Normalized mapping from GDELT FIPS codes to standard ISO-A2 codes
const FIPS_TO_ISO: Record<string, string> = {
  CH: 'CN', // China
  JA: 'JP', // Japan
  UK: 'GB', // United Kingdom
  GM: 'DE', // Germany
  AS: 'AU', // Australia (fallback proxy if AS appears)
};

type MapMode = 'markers' | 'choropleth' | 'source';

function MapBoundsReset({
  events,
  sourceMarkers,
  mode,
  geoData,
}: {
  events: { lat: number; lng: number }[];
  sourceMarkers: { lat: number; lng: number }[];
  mode: MapMode;
  geoData: any;
}) {
  const map = useMap();
  useEffect(() => {
    if (mode === 'markers' && events.length > 0) {
      const bounds = events.map((e) => [e.lat, e.lng] as [number, number]);
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 4 });
    } else if (mode === 'source' && sourceMarkers.length > 0) {
      const bounds = sourceMarkers.map((m) => [m.lat, m.lng] as [number, number]);
      map.fitBounds(bounds, { padding: [60, 60], maxZoom: 3 });
    } else if (mode === 'choropleth' && geoData) {
      map.setView([20, 0], 2);
    }
  }, [events, sourceMarkers, mode, geoData, map]);
  return null;
}

export default function MapSection() {
  const { filters, mediaParam, isSidebarCollapsed } = useFilters();
  const { theme } = useTheme();
  const [mode, setMode] = useState<MapMode>('markers');
  const [events, setEvents] = useState<any[]>([]);
  const [weeklyGeo, setWeeklyGeo] = useState<any[]>([]);
  const [sourceMap, setSourceMap] = useState<any[]>([]);
  const [geoJsonData, setGeoJsonData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [geoLoading, setGeoLoading] = useState(false);

  // Fetch world GeoJSON boundaries once
  useEffect(() => {
    setGeoLoading(true);
    fetch('https://raw.githubusercontent.com/datasets/geo-boundaries-world-110m/master/countries.geojson')
      .then((res) => res.json())
      .then((data) => setGeoJsonData(data))
      .catch((err) => console.error('Error loading world GeoJSON:', err))
      .finally(() => setGeoLoading(false));
  }, []);

  useEffect(() => {
    setLoading(true);
    const params = {
      start: filters.start,
      end: filters.end,
      media: mediaParam,
      direction: filters.direction,
    };
    // allSettled so a source-map failure never blocks events / weeklyGeo
    Promise.allSettled([
      getEvents({ ...params, limit: 2000 }),
      getWeeklyGeo(params),
      getSourceMap(params),
    ]).then(([evResult, geoResult, srcResult]) => {
      if (evResult.status === 'fulfilled')  setEvents(evResult.value.records);
      else console.error('Events fetch failed:', evResult.reason);

      if (geoResult.status === 'fulfilled') setWeeklyGeo(geoResult.value.records);
      else console.error('WeeklyGeo fetch failed:', geoResult.reason);

      if (srcResult.status === 'fulfilled') setSourceMap(srcResult.value.records);
      else console.warn('Source-map unavailable (Source Origin mode will be empty):', srcResult.reason);
    }).finally(() => setLoading(false));
  }, [filters.start, filters.end, mediaParam, filters.direction]);

  // ── Event-location markers (ActionGeo) ───────────────────────────────────
  const markers = useMemo(() => {
    return events
      .filter((e) => e.ActionGeo_Lat != null && e.ActionGeo_Long != null)
      .map((e) => ({
        lat: e.ActionGeo_Lat,
        lng: e.ActionGeo_Long,
        group: e.MediaGroup,
        tone: e.AvgTone,
        source: e.SourceDomain,
        eventType: e.EventTypeDesc,
        country: e.ActionGeo_CountryCode,
      }));
  }, [events]);

  // ── Source-origin markers ─────────────────────────────────────────────────
  const sourceMarkers = useMemo(() => {
    return sourceMap.map((s) => ({
      lat: s.source_lat,
      lng: s.source_lon,
      group: s.MediaGroup,
      country: s.source_country,
      totalEvents: s.TotalEvents,
      totalArticles: s.TotalArticles,
      avgTone: s.AvgTone,
      uniqueDomains: s.UniqueDomains,
    }));
  }, [sourceMap]);

  const maxSourceEvents = useMemo(
    () => Math.max(...sourceMarkers.map((m) => m.totalEvents), 1),
    [sourceMarkers],
  );

  // ── Choropleth ────────────────────────────────────────────────────────────
  const choroplethData = useMemo(() => {
    const dataMap: Record<string, { totalArticles: number; avgTone: number; totalEvents: number }> = {};
    weeklyGeo.forEach((row) => {
      const fips = row.ActionCountry || '';
      const iso = (FIPS_TO_ISO[fips] || fips).toUpperCase();
      const articles = Number(row.TotalArticles || 0);
      const tone = Number(row.AvgTone || 0);
      const eventsCount = Number(row.TotalEvents || 0);

      if (!dataMap[iso]) {
        dataMap[iso] = { totalArticles: 0, avgTone: 0, totalEvents: 0 };
      }

      const existing = dataMap[iso];
      const newArticles = existing.totalArticles + articles;
      const newAvgTone =
        newArticles > 0
          ? (existing.avgTone * existing.totalArticles + tone * articles) / newArticles
          : 0;

      existing.totalArticles = newArticles;
      existing.avgTone = newAvgTone;
      existing.totalEvents += eventsCount;
    });
    return dataMap;
  }, [weeklyGeo]);

  const maxArticles = useMemo(() => {
    const vals = Object.values(choroplethData).map((d) => d.totalArticles);
    return vals.length > 0 ? Math.max(...vals, 1) : 1;
  }, [choroplethData]);

  const getCountryStyle = (feature: any) => {
    const props = feature?.properties || {};
    const countryIso = (
      props.ISO_A2 || props.iso_a2 || props.ISO_2 || props.iso_2 || props.iso2 || ''
    ).toUpperCase();
    const data = choroplethData[countryIso];

    if (!data || data.totalArticles === 0) {
      return {
        fillColor: theme === 'dark' ? '#18181B' : '#FFFFFF',
        weight: 1,
        opacity: 0.4,
        color: theme === 'dark' ? '#27272A' : '#E4E4E7',
        fillOpacity: 0.15,
      };
    }

    const ratio = Math.log1p(data.totalArticles) / Math.log1p(maxArticles);
    const fillOpacity = 0.25 + ratio * 0.6;

    return {
      fillColor: '#84CC16',
      weight: 1.2,
      opacity: 0.8,
      color: theme === 'dark' ? '#3F3F46' : '#D4D4D8',
      fillOpacity,
    };
  };

  const onEachCountry = (feature: any, layer: any) => {
    const props = feature?.properties || {};
    const countryName = props.NAME || props.name || 'Unknown Country';
    const countryIso = (
      props.ISO_A2 || props.iso_a2 || props.ISO_2 || props.iso_2 || props.iso2 || ''
    ).toUpperCase();
    const data = choroplethData[countryIso];

    layer.on({
      mouseover: (e: any) => {
        const target = e.target;
        const currentStyle = getCountryStyle(feature);
        target.setStyle({
          weight: 2,
          color: theme === 'dark' ? '#FAFAFA' : '#09090B',
          fillColor: currentStyle.fillColor,
          fillOpacity: Math.min(0.95, (currentStyle.fillOpacity || 0) + 0.15),
        });
        if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) {
          target.bringToFront();
        }
      },
      mouseout: (e: any) => {
        const target = e.target;
        target.setStyle(getCountryStyle(feature));
      },
    });

    const borderStyleClass = theme === 'dark' ? 'border-[#27272A]' : 'border-[#E4E4E7]';
    const activeTextClass = theme === 'dark' ? 'text-[#FAFAFA]' : 'text-[#09090B]';
    const mutedTextClass = theme === 'dark' ? 'text-[#A1A1AA]' : 'text-[#71717A]';

    if (data && data.totalArticles > 0) {
      layer.bindTooltip(
        `<div class="custom-tooltip-content">
          <div class="font-mono font-bold text-sm ${activeTextClass} mb-1 border-b ${borderStyleClass} pb-1">${countryName} (${countryIso})</div>
          <div class="${mutedTextClass} text-xs">Articles: <span class="font-mono font-semibold ${activeTextClass}">${data.totalArticles.toLocaleString()}</span></div>
          <div class="${mutedTextClass} text-xs">Events: <span class="font-mono font-semibold ${activeTextClass}">${data.totalEvents.toLocaleString()}</span></div>
          <div class="${mutedTextClass} text-xs">Avg Tone: <span class="font-mono font-semibold ${data.avgTone >= 0 ? 'text-[#22C55E]' : 'text-[#EF4444]'}">${data.avgTone.toFixed(2)}</span></div>
        </div>`,
        { direction: 'top', sticky: true, opacity: 0.98, className: 'custom-map-tooltip' },
      );
    } else {
      layer.bindTooltip(
        `<div class="custom-tooltip-content">
          <div class="font-mono font-bold text-sm ${mutedTextClass} mb-1">${countryName} (${countryIso})</div>
          <div class="${mutedTextClass} text-xs">No media coverage recorded.</div>
        </div>`,
        { direction: 'top', sticky: true, opacity: 0.98, className: 'custom-map-tooltip' },
      );
    }
  };

  // ── Subtitle per mode ─────────────────────────────────────────────────────
  const subtitle =
    mode === 'markers'
      ? 'Bubble position = event geography (GDELT ActionGeo); color = media source group'
      : mode === 'source'
      ? 'Bubble position = approximate origin of publishing source; color = media source group'
      : 'Fill intensity = total article volume across all media groups';

  return (
    <div className="bg-surface border border-border rounded-lg overflow-hidden mb-6 transition-all duration-300 hover:shadow-glow-subtle hover:border-border-elevated">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border">
        <div>
          <h3 className="font-mono text-base font-bold tracking-wide">Geographic Narrative Spread</h3>
          <p className="text-xs text-text-muted mt-0.5">{subtitle}</p>
        </div>
        <div className="flex bg-bg rounded-lg p-1 border border-border">
          {(
            [
              { key: 'markers', label: 'Event Markers' },
              { key: 'source',  label: 'Source Origin' },
              { key: 'choropleth', label: 'Country View' },
            ] as { key: MapMode; label: string }[]
          ).map(({ key, label }) => (
            <button
              key={key}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all cursor-pointer ${
                mode === key
                  ? 'bg-primary text-white shadow-glow-subtle'
                  : 'text-text-muted hover:bg-surface-elevated hover:text-text-primary'
              }`}
              onClick={() => setMode(key)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Map */}
      <div className="relative" style={{ height: '500px' }}>
        {(loading || (mode === 'choropleth' && geoLoading)) && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-surface/80">
            <div className="text-text-muted text-sm font-mono flex items-center gap-2">
              <svg className="animate-spin h-4 w-4 text-primary" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              {geoLoading ? 'Loading World Map Borders...' : 'Filtering Map Data...'}
            </div>
          </div>
        )}

        {/* Color legend for marker-based modes */}
        {(mode === 'markers' || mode === 'source') && (
          <div
            className="absolute bottom-3 left-3 z-[1000] rounded-lg px-3 py-2 text-xs"
            style={{
              backgroundColor: theme === 'dark' ? 'rgba(24,24,27,0.92)' : 'rgba(255,255,255,0.92)',
              border: `1px solid ${theme === 'dark' ? '#27272A' : '#E4E4E7'}`,
            }}
          >
            <div className="font-mono font-bold mb-1.5 text-[10px] uppercase tracking-wider"
              style={{ color: theme === 'dark' ? '#A1A1AA' : '#71717A' }}>
              Media Group
            </div>
            {Object.entries(GROUP_COLORS).map(([group, color]) => (
              <div key={group} className="flex items-center gap-1.5 mb-1 last:mb-0">
                <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
                <span style={{ color: theme === 'dark' ? '#FAFAFA' : '#09090B' }}>{group}</span>
              </div>
            ))}
            {mode === 'source' && (
              <div className="mt-1.5 pt-1.5 text-[10px]"
                style={{ borderTop: `1px solid ${theme === 'dark' ? '#27272A' : '#E4E4E7'}`,
                         color: theme === 'dark' ? '#A1A1AA' : '#71717A' }}>
                Size = event volume
              </div>
            )}
          </div>
        )}

        <MapContainer
          key={`${theme}-${mode}-${isSidebarCollapsed}`}
          center={[20, 0]}
          zoom={2}
          scrollWheelZoom={true}
          style={{ height: '100%', width: '100%' }}
          className="z-0"
        >
          <TileLayer
            attribution='&copy; <a href="https://carto.com/">CARTO</a>'
            url={
              theme === 'dark'
                ? 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
                : 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png'
            }
          />
          <MapBoundsReset
            events={markers}
            sourceMarkers={sourceMarkers}
            mode={mode}
            geoData={geoJsonData}
          />

          {/* ── Event-location markers ── */}
          {mode === 'markers' &&
            markers.map((m, i) => (
              <CircleMarker
                key={i}
                center={[m.lat, m.lng]}
                radius={4 + Math.abs(m.tone) * 0.6}
                fillColor={GROUP_COLORS[m.group] || '#71717A'}
                color={GROUP_COLORS[m.group] || '#71717A'}
                fillOpacity={0.65}
                weight={1}
              >
                <Tooltip direction="top" offset={[0, -5]} opacity={0.98} className="custom-map-tooltip">
                  <div className="text-xs font-sans">
                    <div
                      className={`font-mono font-bold text-sm border-b pb-0.5 mb-1 ${
                        theme === 'dark' ? 'text-[#FAFAFA] border-[#27272A]' : 'text-[#09090B] border-[#E4E4E7]'
                      }`}
                    >
                      {m.source}
                    </div>
                    <div className={theme === 'dark' ? 'text-[#A1A1AA]' : 'text-[#71717A]'}>
                      Event location:{' '}
                      <span
                        className={`font-mono font-semibold ${
                          theme === 'dark' ? 'text-[#FAFAFA]' : 'text-[#09090B]'
                        }`}
                      >
                        {m.country}
                      </span>
                    </div>
                    <div className={theme === 'dark' ? 'text-[#A1A1AA]' : 'text-[#71717A]'}>
                      Media group:{' '}
                      <span
                        className={`font-mono font-semibold ${
                          theme === 'dark' ? 'text-[#FAFAFA]' : 'text-[#09090B]'
                        }`}
                      >
                        {m.group}
                      </span>
                    </div>
                    <div className={theme === 'dark' ? 'text-[#A1A1AA]' : 'text-[#71717A]'}>
                      Tone:{' '}
                      <span
                        className={`font-mono font-semibold ${
                          m.tone >= 0 ? 'text-[#22C55E]' : 'text-[#EF4444]'
                        }`}
                      >
                        {m.tone.toFixed(2)}
                      </span>
                    </div>
                    <div className="text-[#71717A] italic mt-1">{m.eventType}</div>
                  </div>
                </Tooltip>
              </CircleMarker>
            ))}

          {/* ── Source-origin markers ── */}
          {mode === 'source' &&
            sourceMarkers.map((m, i) => (
              <CircleMarker
                key={i}
                center={[m.lat, m.lng]}
                radius={6 + Math.sqrt(m.totalEvents / maxSourceEvents) * 28}
                fillColor={GROUP_COLORS[m.group] || '#71717A'}
                color={theme === 'dark' ? '#18181B' : '#FFFFFF'}
                fillOpacity={0.70}
                weight={1.5}
              >
                <Tooltip direction="top" offset={[0, -5]} opacity={0.98} className="custom-map-tooltip">
                  <div className="text-xs font-sans">
                    <div
                      className={`font-mono font-bold text-sm border-b pb-0.5 mb-1 ${
                        theme === 'dark' ? 'text-[#FAFAFA] border-[#27272A]' : 'text-[#09090B] border-[#E4E4E7]'
                      }`}
                    >
                      {m.country}
                    </div>
                    <div className={theme === 'dark' ? 'text-[#A1A1AA]' : 'text-[#71717A]'}>
                      Media group:{' '}
                      <span
                        className={`font-mono font-semibold ${
                          theme === 'dark' ? 'text-[#FAFAFA]' : 'text-[#09090B]'
                        }`}
                      >
                        {m.group}
                      </span>
                    </div>
                    <div className={theme === 'dark' ? 'text-[#A1A1AA]' : 'text-[#71717A]'}>
                      Events:{' '}
                      <span
                        className={`font-mono font-semibold ${
                          theme === 'dark' ? 'text-[#FAFAFA]' : 'text-[#09090B]'
                        }`}
                      >
                        {m.totalEvents.toLocaleString()}
                      </span>
                    </div>
                    <div className={theme === 'dark' ? 'text-[#A1A1AA]' : 'text-[#71717A]'}>
                      Articles:{' '}
                      <span
                        className={`font-mono font-semibold ${
                          theme === 'dark' ? 'text-[#FAFAFA]' : 'text-[#09090B]'
                        }`}
                      >
                        {m.totalArticles.toLocaleString()}
                      </span>
                    </div>
                    <div className={theme === 'dark' ? 'text-[#A1A1AA]' : 'text-[#71717A]'}>
                      Avg tone:{' '}
                      <span
                        className={`font-mono font-semibold ${
                          m.avgTone >= 0 ? 'text-[#22C55E]' : 'text-[#EF4444]'
                        }`}
                      >
                        {m.avgTone.toFixed(2)}
                      </span>
                    </div>
                    <div className={theme === 'dark' ? 'text-[#A1A1AA]' : 'text-[#71717A]'}>
                      Unique domains:{' '}
                      <span
                        className={`font-mono font-semibold ${
                          theme === 'dark' ? 'text-[#FAFAFA]' : 'text-[#09090B]'
                        }`}
                      >
                        {m.uniqueDomains}
                      </span>
                    </div>
                  </div>
                </Tooltip>
              </CircleMarker>
            ))}

          {/* ── Country choropleth ── */}
          {mode === 'choropleth' && geoJsonData && (
            <GeoJSON
              key={`${theme}-${weeklyGeo.length}`}
              data={geoJsonData}
              style={getCountryStyle}
              onEachFeature={onEachCountry}
            />
          )}
        </MapContainer>
      </div>

      {/* Disclaimer footer */}
      <div className="px-6 py-2 border-t border-border text-[11px] text-text-muted">
        {mode === 'markers' && (
          <>
            <span className="font-semibold">Event Markers:</span> bubble position = where GDELT
            detected the event geographically (ActionGeo). A Western outlet covering a Beijing story
            appears in China.
          </>
        )}
        {mode === 'source' && (
          <>
            <span className="font-semibold">Source Origin:</span> bubble position = approximate
            country/region of the publishing outlet, inferred from domain. Coordinates are
            estimated — not exact newsroom addresses. Bubble size = event volume.
          </>
        )}
        {mode === 'choropleth' && (
          <>
            <span className="font-semibold">Country View:</span> fill intensity = total article
            volume associated with each country across all media groups combined (ActionGeo).
          </>
        )}
      </div>
    </div>
  );
}
