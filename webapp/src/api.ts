import axios from "axios";

const api = axios.create({
    baseURL: "http://localhost:8000",
});

export const fetchFileTree = async () => {
    const res = await api.get("/api/changed-files/tree");
    return res.data;
};

export const fetchDiff = async (path: string) => {
    const res = await api.get("/api/diff", { params: { path } });
    return res.data;
};

export async function getWatchPaths() {
    const res = await api.get('/api/watch-paths');
    return res.data as string[];
}

export async function addWatchPath(path: string) {
    const res = await api.post('/api/watch-path', { path });
    return res.data;
}

export async function getVersion(path: string) {
    const res = await api.get('/api/files/versions', { params: { path } });
    return res.data;
}

export async function getVersionDiff(path: string, version: number) {
    const res = await api.get('/api/files/version/diff', { params: { path, version } });
    return res.data;
}

export async function removeWatchPath(path: string) {
    const res = await api.delete('/api/watch-path', { data: { path } });
    return res.data;
}

export type SearchResult = {
    score: number;
    path: string | null;
    text: string;
    chunk_index: number | null;
    collection: string;
    ext?: string | null;
};

export type SearchFilters = {
    ext?: string;
    path_prefix?: string;
    collection?: string;
};

export async function searchFiles(query: string, n = 5, filters?: SearchFilters) {
    const params: Record<string, string | number> = { q: query, n };
    if (filters?.collection) params.collection = filters.collection;
    if (filters?.ext) params.ext = filters.ext;
    if (filters?.path_prefix) params.path_prefix = filters.path_prefix;
    const res = await api.get('/api/search', { params });
    return res.data as SearchResult[];
}

export async function getFileContent(path: string, maxBytes = 100_000) {
    const res = await api.get('/api/file-content', { params: { path, max_bytes: maxBytes } });
    return res.data as {
        ok: boolean;
        path?: string;
        size?: number;
        truncated?: boolean;
        content: string;
        error?: string;
    };
}

export type ThemePalette = { text: string; button: string; icon: string; bg: string };
export type ThemeExtractResult = {
  dominant_color: { r: number; g: number; b: number };
  luma: number;
  theme: 'dark_bg' | 'bright_bg';
  palette: ThemePalette;
};

export async function extractTheme(image_path: string, threshold = 50): Promise<ThemeExtractResult> {
  const res = await api.post('/api/theme/extract', { image_path, threshold });
  return res.data;
}

export type SecurityAuditResult = {
  apk_analysis: {
    threat_level: 'SAFE' | 'WARNING' | 'CRITICAL';
    total_score: number;
    score_breakdown: { permission_score: number; url_score: number };
    permission_findings: { permission: string; score: number; reason: string }[];
    url_findings: { url: string; score: number; reason: string }[];
    summary: string;
  };
  pi_analysis: {
    risk: 'SAFE' | 'CRITICAL';
    encryption: string;
    details: string[];
  };
};

export async function runSecurityAudit(manifest = '', strings = '', document_text = ''): Promise<SecurityAuditResult> {
  const res = await api.post('/api/security/audit', { manifest, strings, document_text });
  return res.data;
}

export type ConsentSignResult = {
  nft_id: string;
  integrity: 'VERIFIED' | 'FLAGGED';
  block: {
    data: { nft_id: string; owner: string; title: string; status: string; integrity: string };
    prev_hash: string;
    block_hash: string;
  };
};

export async function signConsent(teacher_id: string, title: string, parent_id: string, signature_pattern: number[]): Promise<ConsentSignResult> {
  const res = await api.post('/api/consent/sign', { teacher_id, title, parent_id, signature_pattern });
  return res.data;
}
