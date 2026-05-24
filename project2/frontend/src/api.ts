import axios from 'axios';

const getApiBase = () => {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  // Dynamically target the server's IP/hostname instead of hardcoding localhost
  if (typeof window !== 'undefined' && window.location) {
    const hostname = window.location.hostname;
    // Keep http or https protocol aligned with the page
    const protocol = window.location.protocol;
    return `${protocol}//${hostname}:8002`;
  }
  return 'http://localhost:8002';
};

const API_BASE = getApiBase();

const api = axios.create({
  baseURL: `${API_BASE}/api`,
  timeout: 30000,
});

export interface FilterParams {
  start: string;
  end: string;
  media: string;
  direction: string;
}

export interface SummaryResponse {
  totalEvents: number;
  uniqueSources: number;
  avgToneWestern: number | null;
  avgToneChinese: number | null;
  mediaBreakdown: { MediaGroup: string; Events: number; Sources: number }[];
}

export interface EventsResponse {
  count: number;
  records: Array<{
    GLOBALEVENTID: number;
    Date: string;
    MediaGroup: string;
    EventDirection: string;
    ActionGeo_Lat: number;
    ActionGeo_Long: number;
    ActionGeo_CountryCode: string;
    SourceDomain: string;
    AvgTone: number;
    GoldsteinScale: number;
    NumArticles: number;
    EventTypeDesc: string;
    QuadClassDesc: string;
  }>;
}

export interface DailyResponse {
  count: number;
  records: Array<{
    Date: string;
    MediaGroup: string;
    TotalEvents: number;
    TotalArticles: number;
    AvgTone: number;
    AvgGoldstein: number;
  }>;
}

export interface WeeklyGeoResponse {
  count: number;
  records: Array<{
    ActionCountry: string;
    MediaGroup: string;
    TotalEvents: number;
    TotalArticles: number;
    AvgTone: number;
    AvgGoldstein: number;
  }>;
}

export interface ToneGapResponse {
  count: number;
  records: Array<{
    Date: string;
    WesternTone: number | null;
    ChineseTone: number | null;
    ToneGap: number | null;
  }>;
}

export function buildParams(filters: FilterParams) {
  return {
    start: filters.start,
    end: filters.end,
    media: filters.media,
    direction: filters.direction,
  };
}

export async function getSummary(params: FilterParams) {
  const res = await api.get<SummaryResponse>('/summary', { params: buildParams(params) });
  return res.data;
}

export async function getEvents(params: FilterParams & { limit?: number }) {
  const res = await api.get<EventsResponse>('/events', { params: { ...buildParams(params), limit: params.limit || 5000 } });
  return res.data;
}

export async function getDaily(params: FilterParams) {
  const res = await api.get<DailyResponse>('/daily', { params: buildParams(params) });
  return res.data;
}

export async function getWeeklyGeo(params: FilterParams) {
  const res = await api.get<WeeklyGeoResponse>('/weekly_geo', { params: buildParams(params) });
  return res.data;
}

export async function getToneGap(params: FilterParams) {
  const res = await api.get<ToneGapResponse>('/tone_gap', { params: buildParams(params) });
  return res.data;
}

export default api;
