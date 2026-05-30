/* eslint-disable @typescript-eslint/no-explicit-any */
import { useCallback, useEffect, useState, useMemo, useRef } from 'react';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { useFilters } from '../hooks/useFilters';
import { useTheme } from '../hooks/useTheme';
import { getEvents, getWeeklyGeo, getSourceMap } from '../api';
import { Map, MapClusterLayer, MapControls, useMap } from './ui/map';

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

type MapMode = 'markers' | 'source' | 'choropleth';

const getChoroplethColor = (avgTone: number) => {
  if (avgTone > 1.5) return '#059669'; // Emerald 600
  if (avgTone > 0.5) return '#10B981'; // Emerald 500
  if (avgTone > 0.1) return '#34D399'; // Emerald 400
  if (avgTone > -0.1) return '#9CA3AF'; // Gray 400 (Neutral)
  if (avgTone > -0.5) return '#F87171'; // Red 400
  if (avgTone > -1.5) return '#EF4444'; // Red 500
  return '#DC2626'; // Red 600
};

// ── Choropleth 3D Extrusion Layer Component ──
function ChoroplethLayer({
  geoJsonData,
  choroplethData,
  maxArticles,
  theme,
  mode,
  onCountryClick,
}: {
  geoJsonData: any;
  choroplethData: any;
  maxArticles: number;
  theme: string;
  mode: MapMode;
  onCountryClick: (countryIso: string, countryName: string) => void;
}) {
  const { map, isLoaded } = useMap();

  const geojson = useMemo(() => {
    if (!geoJsonData || !geoJsonData.features) {
      return { type: 'FeatureCollection' as const, features: [] };
    }
    const features = geoJsonData.features.map((feature: any) => {
      const props = feature.properties || {};
      const countryName = props.name || props.NAME || 'Unknown';
      const countryIso = (
        props.iso_a2 || props.ISO_A2 || props.iso_2 || props.ISO_2 || props.iso2 || ''
      ).toUpperCase();

      const data = choroplethData[countryIso];

      let height = 0;
      let color = theme === 'dark' ? '#1c1c24' : '#E4E4E7';
      let totalArticles = 0;
      let totalEvents = 0;
      let avgTone = 0;

      if (data && data.totalArticles > 0) {
        totalArticles = data.totalArticles;
        totalEvents = data.totalEvents;
        avgTone = data.avgTone;

        const ratio = Math.log1p(totalArticles) / Math.log1p(maxArticles);
        // Max extrusion height of 600,000 meters (600km) on the globe
        height = ratio * 600000;
        color = getChoroplethColor(avgTone);
      }

      return {
        ...feature,
        properties: {
          ...props,
          name: countryName,
          isoCode: countryIso,
          height,
          color,
          totalArticles,
          totalEvents,
          avgTone,
        },
      };
    });

    return { type: 'FeatureCollection' as const, features };
  }, [geoJsonData, choroplethData, maxArticles, theme]);

  useEffect(() => {
    if (!isLoaded || !map) return;

    if (!map.getSource('3d-choropleth-source')) {
      map.addSource('3d-choropleth-source', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      });
    }

    if (!map.getLayer('3d-choropleth-layer')) {
      // 3D extrusion layer for visual height
      map.addLayer({
        id: '3d-choropleth-layer',
        type: 'fill-extrusion',
        source: '3d-choropleth-source',
        paint: {
          'fill-extrusion-height': ['get', 'height'],
          'fill-extrusion-base': 0,
          'fill-extrusion-color': ['get', 'color'],
          'fill-extrusion-opacity': 0.7,
        },
      });

      // Flat 2D layer for click and hover interaction (always matches globe shape perfectly)
      map.addLayer({
        id: '3d-choropleth-interactive-layer',
        type: 'fill',
        source: '3d-choropleth-source',
        paint: {
          'fill-color': 'rgba(0, 0, 0, 0)',
        },
      });

      const popup = new maplibregl.Popup({
        closeButton: false,
        closeOnClick: false,
        className: 'custom-map-popup',
      });

      map.on('mousemove', '3d-choropleth-interactive-layer', (e) => {
        map.getCanvas().style.cursor = 'pointer';
        const features = e.features;
        if (!features || !features[0]) return;
        const f = features[0];
        const props = f.properties;

        const html = props.totalArticles > 0
          ? `
            <div class="custom-tooltip-content">
              <div class="font-mono font-bold text-sm border-b pb-1 mb-1 border-border-elevated">${props.name} (${props.isoCode})</div>
              <div class="text-xs">Articles: <span class="font-mono font-semibold">${props.totalArticles.toLocaleString()}</span></div>
              <div class="text-xs">Events: <span class="font-mono font-semibold">${props.totalEvents.toLocaleString()}</span></div>
              <div class="text-xs mt-0.5">Avg Tone: <span class="font-mono font-semibold ${props.avgTone >= 0 ? 'text-[#22C55E]' : 'text-[#EF4444]'}">${Number(props.avgTone).toFixed(2)}</span></div>
              <div class="text-text-muted mt-1 italic text-[10px]">Click country to view event list</div>
            </div>
          `
          : `
            <div class="custom-tooltip-content">
              <div class="font-mono font-bold text-sm border-b pb-1 mb-1 border-border-elevated">${props.name} (${props.isoCode})</div>
              <div class="text-xs text-text-muted">No media coverage recorded.</div>
            </div>
          `;
        popup.setLngLat(e.lngLat).setHTML(html).addTo(map);
      });

      map.on('mouseleave', '3d-choropleth-interactive-layer', () => {
        map.getCanvas().style.cursor = '';
        popup.remove();
      });

      map.on('click', '3d-choropleth-interactive-layer', (e) => {
        const features = e.features;
        if (!features || !features[0]) return;
        const f = features[0];
        const props = f.properties;
        onCountryClick(props.isoCode, props.name);
      });
    }
  }, [isLoaded, map, onCountryClick]);

  useEffect(() => {
    if (!isLoaded || !map) return;

    const source = map.getSource('3d-choropleth-source') as maplibregl.GeoJSONSource;
    if (source) {
      if (mode === 'choropleth') {
        source.setData(geojson);
        map.setLayoutProperty('3d-choropleth-layer', 'visibility', 'visible');
        map.setLayoutProperty('3d-choropleth-interactive-layer', 'visibility', 'visible');
      } else {
        source.setData({ type: 'FeatureCollection' as const, features: [] });
        map.setLayoutProperty('3d-choropleth-layer', 'visibility', 'none');
        map.setLayoutProperty('3d-choropleth-interactive-layer', 'visibility', 'none');
      }
    }
  }, [isLoaded, map, geojson, mode]);

  return null;
}

// ── Dynamic tooltips for cluster/unclustered points ──
function MapTooltips({ mode }: { mode: MapMode }) {
  const { map, isLoaded } = useMap();

  useEffect(() => {
    if (!isLoaded || !map) return;

    const popup = new maplibregl.Popup({
      closeButton: false,
      closeOnClick: false,
      className: 'custom-map-popup',
    });

    const handleMouseMoveEventsPoint = (e: any) => {
      if (!e.features?.length) return;
      const props = e.features[0].properties;
      map.getCanvas().style.cursor = 'pointer';

      const html = `
        <div class="custom-tooltip-content">
          <div class="font-mono font-bold text-sm border-b pb-1 mb-1 border-border-elevated">Single Event</div>
          <div class="text-xs">Source: <span class="font-mono font-semibold">${props.source || 'Unknown'}</span></div>
          <div class="text-xs">Location: <span class="font-mono font-semibold">${props.country || '—'}</span></div>
          <div class="text-xs">Group: <span class="font-mono font-semibold">${props.group}</span></div>
          <div class="text-xs mt-0.5">Tone: <span class="font-mono font-semibold ${props.tone >= 0 ? 'text-[#22C55E]' : 'text-[#EF4444]'}">${Number(props.tone).toFixed(2)}</span></div>
          ${props.eventType ? `<div class="text-[10px] text-text-muted italic mt-1 truncate">${props.eventType}</div>` : ''}
        </div>
      `;
      popup.setLngLat(e.lngLat).setHTML(html).addTo(map);
    };

    const handleMouseMoveEventsCluster = (e: any) => {
      if (!e.features?.length) return;
      const props = e.features[0].properties;
      map.getCanvas().style.cursor = 'pointer';

      const html = `
        <div class="custom-tooltip-content">
          <div class="font-mono font-bold text-sm border-b pb-1 mb-1 border-border-elevated">${props.point_count} Clustered Events</div>
          <div class="text-text-muted mt-1 italic text-[10px]">Click to expand & view list</div>
        </div>
      `;
      popup.setLngLat(e.lngLat).setHTML(html).addTo(map);
    };

    const handleMouseMoveSourcesPoint = (e: any) => {
      if (!e.features?.length) return;
      const props = e.features[0].properties;
      map.getCanvas().style.cursor = 'pointer';

      const html = `
        <div class="custom-tooltip-content">
          <div class="font-mono font-bold text-sm border-b pb-1 mb-1 border-border-elevated">${props.country || 'Unknown'}</div>
          <div class="text-xs">Media group: <span class="font-mono font-semibold">${props.group}</span></div>
          <div class="text-xs">Events: <span class="font-mono font-semibold">${Number(props.totalEvents).toLocaleString()}</span></div>
          <div class="text-xs">Articles: <span class="font-mono font-semibold">${Number(props.totalArticles).toLocaleString()}</span></div>
          <div class="text-xs mt-0.5">Avg tone: <span class="font-mono font-semibold ${props.avgTone >= 0 ? 'text-[#22C55E]' : 'text-[#EF4444]'}">${Number(props.avgTone).toFixed(2)}</span></div>
          <div class="text-xs">Unique domains: <span class="font-mono font-semibold">${props.uniqueDomains}</span></div>
        </div>
      `;
      popup.setLngLat(e.lngLat).setHTML(html).addTo(map);
    };

    const handleMouseMoveSourcesCluster = (e: any) => {
      if (!e.features?.length) return;
      const props = e.features[0].properties;
      map.getCanvas().style.cursor = 'pointer';

      const html = `
        <div class="custom-tooltip-content">
          <div class="font-mono font-bold text-sm border-b pb-1 mb-1 border-border-elevated">${props.point_count} Clustered Sources</div>
          <div class="text-text-muted mt-1 italic text-[10px]">Click to expand & view list</div>
        </div>
      `;
      popup.setLngLat(e.lngLat).setHTML(html).addTo(map);
    };

    const handleMouseLeave = () => {
      map.getCanvas().style.cursor = '';
      popup.remove();
    };

    if (mode === 'markers') {
      map.on('mousemove', 'unclustered-point-events', handleMouseMoveEventsPoint);
      map.on('mouseleave', 'unclustered-point-events', handleMouseLeave);
      map.on('mousemove', 'clusters-events', handleMouseMoveEventsCluster);
      map.on('mouseleave', 'clusters-events', handleMouseLeave);
    } else if (mode === 'source') {
      map.on('mousemove', 'unclustered-point-sources', handleMouseMoveSourcesPoint);
      map.on('mouseleave', 'unclustered-point-sources', handleMouseLeave);
      map.on('mousemove', 'clusters-sources', handleMouseMoveSourcesCluster);
      map.on('mouseleave', 'clusters-sources', handleMouseLeave);
    }

    return () => {
      popup.remove();
      if (map.getLayer('unclustered-point-events')) {
        map.off('mousemove', 'unclustered-point-events', handleMouseMoveEventsPoint);
        map.off('mouseleave', 'unclustered-point-events', handleMouseLeave);
      }
      if (map.getLayer('clusters-events')) {
        map.off('mousemove', 'clusters-events', handleMouseMoveEventsCluster);
        map.off('mouseleave', 'clusters-events', handleMouseLeave);
      }
      if (map.getLayer('unclustered-point-sources')) {
        map.off('mousemove', 'unclustered-point-sources', handleMouseMoveSourcesPoint);
        map.off('mouseleave', 'unclustered-point-sources', handleMouseLeave);
      }
      if (map.getLayer('clusters-sources')) {
        map.off('mousemove', 'clusters-sources', handleMouseMoveSourcesCluster);
        map.off('mouseleave', 'clusters-sources', handleMouseLeave);
      }
    };
  }, [isLoaded, map, mode]);

  return null;
}

// ── Bounding camera fit component ──
function MapFitBounds({
  mode,
  markers,
  sourceMarkers,
}: {
  mode: MapMode;
  markers: any[];
  sourceMarkers: any[];
}) {
  const { map, isLoaded } = useMap();

  useEffect(() => {
    if (!isLoaded || !map) return;

    const performFit = () => {
      if (mode === 'markers' && markers.length > 0) {
        const lats = markers.map((m) => m.lat);
        const lngs = markers.map((m) => m.lng);
        const minLat = Math.min(...lats);
        const maxLat = Math.max(...lats);
        const minLng = Math.min(...lngs);
        const maxLng = Math.max(...lngs);

        if (minLat === maxLat && minLng === maxLng) {
          map.easeTo({ center: [minLng, minLat], zoom: 4, duration: 1000 });
        } else {
          map.fitBounds([
            [minLng, minLat],
            [maxLng, maxLat],
          ], { padding: 40, maxZoom: 4, duration: 1000 });
        }
      } else if (mode === 'source' && sourceMarkers.length > 0) {
        const lats = sourceMarkers.map((m) => m.lat);
        const lngs = sourceMarkers.map((m) => m.lng);
        const minLat = Math.min(...lats);
        const maxLat = Math.max(...lats);
        const minLng = Math.min(...lngs);
        const maxLng = Math.max(...lngs);

        if (minLat === maxLat && minLng === maxLng) {
          map.easeTo({ center: [minLng, minLat], zoom: 3, duration: 1000 });
        } else {
          map.fitBounds([
            [minLng, minLat],
            [maxLng, maxLat],
          ], { padding: 50, maxZoom: 3, duration: 1000 });
        }
      } else if (mode === 'choropleth') {
        map.easeTo({ center: [12, 18], zoom: 2.0, pitch: 30, duration: 1000 });
      }
    };

    performFit();
  }, [isLoaded, map, mode, markers, sourceMarkers]);

  return null;
}

export default function MapSection() {
  const { filters, mediaParam } = useFilters();
  const { theme } = useTheme();
  const [mode, setMode] = useState<MapMode>('markers');
  const [events, setEvents] = useState<any[]>([]);
  const [weeklyGeo, setWeeklyGeo] = useState<any[]>([]);
  const [sourceMap, setSourceMap] = useState<any[]>([]);
  const [geoJsonData, setGeoJsonData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [geoLoading, setGeoLoading] = useState(true);
  const [selectedEvents, setSelectedEvents] = useState<any[] | null>(null);

  const mapRef = useRef<maplibregl.Map | null>(null);

  const clusterProperties = useMemo(() => ({
    western: ['+', ['case', ['==', ['get', 'group'], 'Western'], 1, 0]],
    chinese: ['+', ['case', ['==', ['get', 'group'], 'Chinese'], 1, 0]],
    global: ['+', ['case', ['==', ['get', 'group'], 'Global/Other'], 1, 0]],
  }), []);

  const clusterColorExpression = useMemo(() => [
    'case',
    // If Western is dominant
    [
      'all',
      ['>', ['number', ['get', 'western'], 0], ['number', ['get', 'chinese'], 0]],
      ['>', ['number', ['get', 'western'], 0], ['number', ['get', 'global'], 0]],
    ],
    '#2563EB', // Western Blue
    // If Chinese is dominant
    [
      'all',
      ['>', ['number', ['get', 'chinese'], 0], ['number', ['get', 'western'], 0]],
      ['>', ['number', ['get', 'chinese'], 0], ['number', ['get', 'global'], 0]],
    ],
    '#EF4444', // Chinese Red
    // If Global/Other is dominant
    [
      'all',
      ['>', ['number', ['get', 'global'], 0], ['number', ['get', 'western'], 0]],
      ['>', ['number', ['get', 'global'], 0], ['number', ['get', 'chinese'], 0]],
    ],
    '#71717A', // Global/Other Gray
    // Tie breaker or default
    '#D97706', // Amber for mixed clusters
  ], []);

  const pointColorExpression = useMemo(() => [
    'case',
    ['==', ['get', 'group'], 'Western'], '#2563EB',
    ['==', ['get', 'group'], 'Chinese'], '#EF4444',
    '#71717A', // Fallback
  ], []);

  // Fetch world GeoJSON boundaries once
  useEffect(() => {
    fetch('https://raw.githubusercontent.com/datasets/geo-boundaries-world-110m/master/countries.geojson')
      .then((res) => res.json())
      .then((data) => setGeoJsonData(data))
      .catch((err) => console.error('Error loading world GeoJSON:', err))
      .finally(() => setGeoLoading(false));
  }, []);

  useEffect(() => {
    let active = true;
    Promise.resolve().then(() => {
      if (active) setLoading(true);
    });

    const params = {
      start: filters.start,
      end: filters.end,
      media: mediaParam,
      direction: filters.direction,
    };
    Promise.allSettled([
      getEvents({ ...params, limit: 2000 }),
      getWeeklyGeo(params),
      getSourceMap(params),
    ]).then(([evResult, geoResult, srcResult]) => {
      if (!active) return;
      if (evResult.status === 'fulfilled') setEvents(evResult.value.records);
      else console.error('Events fetch failed:', evResult.reason);

      if (geoResult.status === 'fulfilled') setWeeklyGeo(geoResult.value.records);
      else console.error('WeeklyGeo fetch failed:', geoResult.reason);

      if (srcResult.status === 'fulfilled') setSourceMap(srcResult.value.records);
      else console.warn('Source-map unavailable (Source Origin mode will be empty):', srcResult.reason);
    }).finally(() => {
      if (active) setLoading(false);
    });

    return () => {
      active = false;
    };
  }, [filters.start, filters.end, mediaParam, filters.direction]);

  // ── Event-location markers (ActionGeo) ───────────────────────────────────
  const markers = useMemo(() => {
    return events
      .filter((e) => {
        const lat = e.ActionGeo_Lat;
        const lng = e.ActionGeo_Long;
        return lat != null && !Number.isNaN(lat) && lng != null && !Number.isNaN(lng);
      })
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
      topDomains: s.TopDomains,
    }));
  }, [sourceMap]);

  // ── Choropleth data grouping ──────────────────────────────────────────────
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

  // Transform markers/sources to GeoJSON point FeatureCollections for MapClusterLayer
  const eventGeoJSON = useMemo(() => {
    return {
      type: 'FeatureCollection' as const,
      features: markers.map((m, i) => ({
        type: 'Feature' as const,
        id: i,
        geometry: {
          type: 'Point' as const,
          coordinates: [m.lng, m.lat],
        },
        properties: {
          index: i,
          group: m.group,
          tone: m.tone,
          source: m.source,
          eventType: m.eventType,
          country: m.country,
        },
      })),
    };
  }, [markers]);

  const sourceGeoJSON = useMemo(() => {
    return {
      type: 'FeatureCollection' as const,
      features: sourceMarkers.map((s, i) => ({
        type: 'Feature' as const,
        id: i,
        geometry: {
          type: 'Point' as const,
          coordinates: [s.lng, s.lat],
        },
        properties: {
          index: i,
          group: s.group,
          country: s.country,
          tone: s.avgTone, // Map avgTone to 'tone' for detail panel compatibility
          source: `Outlets in ${s.country || 'Unknown'}`, // Map to 'source' for detail panel compatibility
          totalEvents: s.totalEvents,
          totalArticles: s.totalArticles,
          uniqueDomains: s.uniqueDomains,
          topDomains: s.topDomains,
        },
      })),
    };
  }, [sourceMarkers]);

  // Click handler for unclustered points
  const handlePointClick = useCallback((feature: any) => {
    setSelectedEvents([feature.properties]);
  }, []);

  // Click handler for clusters - fetches leaves and displays them in the side panel
  const handleClusterClick = useCallback((clusterId: number, coordinates: [number, number]) => {
    const map = mapRef.current;
    if (!map) return;

    // Zoom into cluster
    map.easeTo({
      center: coordinates,
      zoom: map.getZoom() + 1.2,
    });

    const source = map.getSource('cluster-source-events') as maplibregl.GeoJSONSource;
    if (source) {
      source.getClusterLeaves(clusterId, 100, 0)
        .then((features) => {
          if (!features) return;
          const pts = features.map((f: any) => f.properties);
          setSelectedEvents(pts);
        })
        .catch((err) => console.error(err));
    }
  }, []);

  const handleSourcePointClick = useCallback((feature: any) => {
    setSelectedEvents([feature.properties]);
  }, []);

  const handleSourceClusterClick = useCallback((clusterId: number, coordinates: [number, number]) => {
    const map = mapRef.current;
    if (!map) return;

    map.easeTo({
      center: coordinates,
      zoom: map.getZoom() + 1.2,
    });

    const source = map.getSource('cluster-source-sources') as maplibregl.GeoJSONSource;
    if (source) {
      source.getClusterLeaves(clusterId, 100, 0)
        .then((features) => {
          if (!features) return;
          const pts = features.map((f: any) => f.properties);
          setSelectedEvents(pts);
        })
        .catch((err) => console.error(err));
    }
  }, []);

  // Click handler for country view (Choropleth)
  const handleCountryClick = useCallback((countryIso: string, countryName: string) => {
    // Find all events that occurred in this country
    const countryEvents = events.filter((e) => {
      const fips = e.ActionGeo_CountryCode || '';
      const iso = (FIPS_TO_ISO[fips] || fips).toUpperCase();
      return iso === countryIso;
    });

    // Map to detail panel format
    const pts = countryEvents.map((e, idx) => ({
      index: idx,
      group: e.MediaGroup,
      tone: e.AvgTone,
      source: e.SourceDomain,
      eventType: e.EventTypeDesc,
      country: e.ActionGeo_CountryCode,
      countryName: countryName,
    }));

    setSelectedEvents(pts.length > 0 ? pts : [{
      index: 0,
      group: 'Global/Other',
      tone: null,
      source: 'No recorded events',
      eventType: '',
      country: countryIso,
      countryName: countryName,
    }]);
  }, [events]);

  const subtitle =
    mode === 'markers'
      ? '3D Globe Projection + Map Clusters = narratives mapped geographically; hover to count; click to inspect.'
      : mode === 'source'
      ? '3D Globe Projection + Map Clusters = outlets publishing country-wise; click to list domains.'
      : '3D Country Extrusion = height shows publication volume; color shows narrative sentiment tone.';

  return (
    <div className="bg-surface border border-border rounded-lg overflow-hidden mb-6 transition-all duration-300 hover:shadow-glow-subtle hover:border-border-elevated">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border">
        <div>
          <h3 className="font-mono text-base font-bold tracking-wide">Geographic Narrative Spread (3D Globe)</h3>
          <p className="text-xs text-text-muted mt-0.5">{subtitle}</p>
        </div>
        <div className="flex bg-bg rounded-lg p-1 border border-border">
          {(
            [
              { key: 'markers', label: '3D Event Markers' },
              { key: 'source', label: '3D Source Origin' },
              { key: 'choropleth', label: '3D Country View' },
            ] as { key: MapMode; label: string }[]
          ).map(({ key, label }) => (
            <button
               key={key}
               className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all cursor-pointer ${
                 mode === key
                   ? 'bg-primary text-white shadow-glow-subtle'
                   : 'text-text-muted hover:bg-surface-elevated hover:text-text-primary'
               }`}
               onClick={() => {
                 setMode(key);
                 setSelectedEvents(null);
               }}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Map + Detail Panel */}
      <div className="relative flex" style={{ height: 'clamp(480px, 56vh, 680px)' }}>
        {/* Map Container */}
        <div className="relative flex-1 min-w-0 h-full">
          <Map
            ref={mapRef}
            projection={{ type: 'globe' }}
            theme={theme === 'dark' ? 'dark' : 'light'}
            center={[30, 20]}
            zoom={2.3}
            pitch={20}
            bearing={0}
            minZoom={2.0}
            className="w-full h-full"
          >
            {mode === 'markers' && (
              <MapClusterLayer
                id="events"
                data={eventGeoJSON}
                clusterProperties={clusterProperties}
                clusterColor={clusterColorExpression}
                pointColor={pointColorExpression}
                renderAsPie={true}
                onPointClick={handlePointClick}
                onClusterClick={handleClusterClick}
              />
            )}
            {mode === 'source' && (
              <MapClusterLayer
                id="sources"
                data={sourceGeoJSON}
                clusterProperties={clusterProperties}
                clusterColor={clusterColorExpression}
                pointColor={pointColorExpression}
                renderAsPie={true}
                onPointClick={handleSourcePointClick}
                onClusterClick={handleSourceClusterClick}
              />
            )}
            <ChoroplethLayer
              geoJsonData={geoJsonData}
              choroplethData={choroplethData}
              maxArticles={maxArticles}
              theme={theme}
              mode={mode}
              onCountryClick={handleCountryClick}
            />
            <MapTooltips mode={mode} />
            <MapFitBounds mode={mode} markers={markers} sourceMarkers={sourceMarkers} />
            <MapControls showZoom showCompass showFullscreen />
          </Map>

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
                {geoLoading ? 'Loading 3D World Borders...' : 'Structuring 3D Globe Elements...'}
              </div>
            </div>
          )}

          {/* Color legend for marker-based modes */}
          {(mode === 'markers' || mode === 'source') && (
            <div
              className="absolute bottom-3 left-3 z-10 rounded-lg px-3 py-2 text-xs"
              style={{
                backgroundColor: theme === 'dark' ? 'rgba(24,24,27,0.92)' : 'rgba(255,255,255,0.92)',
                border: `1px solid ${theme === 'dark' ? '#27272A' : '#E4E4E7'}`,
              }}
            >
              <div className="font-mono font-bold mb-1.5 text-[10px] uppercase tracking-wider text-text-muted">
                Media Group
              </div>
              <div className="flex flex-col gap-1.5">
                {Object.entries(GROUP_COLORS).map(([group, color]) => (
                  <div key={group} className="flex items-center gap-1.5">
                    <div className="w-3.5 h-3.5 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
                    <span className="text-text-primary">{group}</span>
                  </div>
                ))}
              </div>
              <div className="mt-1.5 pt-1.5 text-[10px] border-t border-border text-text-muted">
                Dominant group colors clusters
              </div>
            </div>
          )}

          {/* Color legend for 3D choropleth mode */}
          {mode === 'choropleth' && (
            <div
              className="absolute bottom-3 left-3 z-10 rounded-lg px-3 py-2 text-xs"
              style={{
                backgroundColor: theme === 'dark' ? 'rgba(24,24,27,0.92)' : 'rgba(255,255,255,0.92)',
                border: `1px solid ${theme === 'dark' ? '#27272A' : '#E4E4E7'}`,
              }}
            >
              <div className="font-mono font-bold mb-1.5 text-[10px] uppercase tracking-wider text-text-muted">
                Average Sentiment
              </div>
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded-full flex-shrink-0 bg-[#10B981]" />
                  <span className="text-text-primary">Positive (Tone &gt; 0.1)</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded-full flex-shrink-0 bg-[#9CA3AF]" />
                  <span className="text-text-primary">Neutral</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded-full flex-shrink-0 bg-[#EF4444]" />
                  <span className="text-text-primary">Negative (Tone &lt; -0.1)</span>
                </div>
              </div>
              <div className="mt-1.5 pt-1.5 text-[10px] border-t border-border text-text-muted">
                3D extrusion height = article volume
              </div>
            </div>
          )}
        </div>

        {/* ── Event Detail Side Panel (always visible) ── */}
        <div
          className="w-80 flex-shrink-0 border-l border-border overflow-y-auto flex flex-col"
          style={{ backgroundColor: theme === 'dark' ? 'rgba(22,24,32,0.96)' : 'rgba(255,255,255,0.96)' }}
        >
          {selectedEvents ? (
            <>
              <div className="sticky top-0 z-10 flex items-center justify-between px-4 py-3 border-b border-border"
                style={{ backgroundColor: theme === 'dark' ? 'rgba(22,24,32,0.98)' : 'rgba(255,255,255,0.98)' }}>
                <div>
                  <h4 className="font-mono text-sm font-bold tracking-wide">
                    {mode === 'source'
                      ? `${selectedEvents.length} Source Group${selectedEvents.length !== 1 ? 's' : ''}`
                      : `${selectedEvents.length} Event${selectedEvents.length !== 1 ? 's' : ''}`
                    }
                  </h4>
                  <p className="text-[10px] text-text-muted mt-0.5">
                    {selectedEvents[0]?.countryName
                      ? `${selectedEvents[0].countryName} (${selectedEvents[0].country})`
                      : (selectedEvents[0]?.country || 'Unknown')
                    } · {selectedEvents[0]?.group || ''}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedEvents(null)}
                  className="p-1 rounded hover:bg-surface-elevated transition-colors cursor-pointer text-text-muted hover:text-text-primary"
                  title="Close"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <div className="divide-y divide-border">
                {selectedEvents.map((ev, i) => (
                  <div key={i} className="px-4 py-3 hover:bg-surface-elevated/50 transition-colors">
                    <div className="flex items-center gap-2 mb-1">
                      <div
                        className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                        style={{ backgroundColor: GROUP_COLORS[ev.group] || '#71717A' }}
                      />
                      <span className="font-mono text-xs font-semibold truncate text-text-primary">
                        {ev.source || 'Unknown'}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]">
                      <div className="text-text-muted">
                        Location: <span className="font-mono text-text-primary">{ev.country || '—'}</span>
                      </div>
                      <div className="text-text-muted">
                        Group: <span className="font-mono text-text-primary">{ev.group || '—'}</span>
                      </div>
                      {ev.tone !== null && (
                        <div className="text-text-muted">
                          Tone: <span className={`font-mono font-semibold ${ev.tone >= 0 ? 'text-[#22C55E]' : 'text-[#EF4444]'}`}>
                            {Number(ev.tone).toFixed(2)}
                          </span>
                        </div>
                      )}
                      {ev.totalEvents !== undefined && (
                        <div className="text-text-muted">
                          Events: <span className="font-mono text-text-primary">{ev.totalEvents.toLocaleString()}</span>
                        </div>
                      )}
                      {ev.totalArticles !== undefined && (
                        <div className="text-text-muted">
                          Articles: <span className="font-mono text-text-primary">{ev.totalArticles.toLocaleString()}</span>
                        </div>
                      )}
                      {ev.uniqueDomains !== undefined && (
                        <div className="text-text-muted">
                          Domains: <span className="font-mono text-text-primary">{ev.uniqueDomains}</span>
                        </div>
                      )}
                    </div>
                    {ev.topDomains && (
                      <div className="text-text-muted mt-1.5 pt-1 border-t border-border/30">
                        <span className="font-semibold block text-[10px] uppercase text-text-muted">Top Outlets:</span>
                        <span className="font-mono text-text-primary text-[10px] leading-tight block mt-0.5 break-words">
                          {ev.topDomains}
                        </span>
                      </div>
                    )}
                    {ev.eventType && (
                      <div className="text-[10px] text-text-muted italic mt-1 truncate">{ev.eventType}</div>
                    )}
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center px-6 text-center">
              <svg className="w-10 h-10 text-text-muted mb-3 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <p className="font-mono text-xs text-text-muted leading-relaxed">
                Click a point or cluster on the 3D globe to list narrative events at that location
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Disclaimer footer */}
      <div className="px-6 py-2 border-t border-border text-[11px] text-text-muted">
        {mode === 'markers' && (
          <>
            <span className="font-semibold">Event Clusters:</span> MapLibre 3D Globe clustering. Click a cluster or point to inspect the source list in the right-hand panel. Right-click and drag the globe to rotate and pitch in 3D.
          </>
        )}
        {mode === 'source' && (
          <>
            <span className="font-semibold">Source Clusters:</span> publisher origin locations clustered geographically on the 3D globe.
          </>
        )}
        {mode === 'choropleth' && (
          <>
            <span className="font-semibold">3D Country View:</span> extruded country height = total article volume. Fill color represents sentiment (emerald is positive tone, red is negative tone).
          </>
        )}
      </div>
    </div>
  );
}
