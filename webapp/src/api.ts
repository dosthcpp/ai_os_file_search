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
