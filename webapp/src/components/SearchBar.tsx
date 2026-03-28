import { useEffect, useRef, useState } from 'react';
import { searchFiles, SearchFilters, SearchResult } from '../api.ts';

const HISTORY_KEY = 'ai_os_search_history';
const MAX_HISTORY = 20;

function loadHistory(): string[] {
    try {
        return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
    } catch {
        return [];
    }
}

function saveHistory(history: string[]) {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
}

function addToHistory(query: string) {
    const history = loadHistory().filter(q => q !== query);
    history.unshift(query);
    saveHistory(history.slice(0, MAX_HISTORY));
}

type Props = {
    onSelectFile?: (path: string) => void;
};

export default function SearchBar({ onSelectFile }: Props) {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<SearchResult[]>([]);
    const [loading, setLoading] = useState(false);
    const [showFilters, setShowFilters] = useState(false);
    const [extFilter, setExtFilter] = useState('');
    const [prefixFilter, setPrefixFilter] = useState('');

    // History / autocomplete state
    const [history, setHistory] = useState<string[]>(() => loadHistory());
    const [showHistory, setShowHistory] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);

    const filteredHistory = history.filter(
        q => q.toLowerCase().includes(query.toLowerCase()) && q !== query
    );

    const onSearch = async (q = query) => {
        const trimmed = q.trim();
        if (!trimmed) return;
        setShowHistory(false);
        setLoading(true);
        const filters: SearchFilters = {};
        if (extFilter.trim()) filters.ext = extFilter.trim();
        if (prefixFilter.trim()) filters.path_prefix = prefixFilter.trim();
        try {
            const data = await searchFiles(trimmed, 10, filters);
            setResults(data);
            addToHistory(trimmed);
            setHistory(loadHistory());
        } catch {
            setResults([]);
        } finally {
            setLoading(false);
        }
    };

    const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter') onSearch();
        if (e.key === 'Escape') setShowHistory(false);
    };

    const onHistorySelect = (q: string) => {
        setQuery(q);
        onSearch(q);
    };

    const clearHistory = () => {
        saveHistory([]);
        setHistory([]);
    };

    // Close history dropdown when clicking outside
    useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (!inputRef.current?.closest('.search-wrapper')?.contains(e.target as Node)) {
                setShowHistory(false);
            }
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, []);

    return (
        <div style={{ marginBottom: 8 }}>
            {/* Search row */}
            <div className="search-wrapper" style={{ position: 'relative' }}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <input
                        ref={inputRef}
                        type="text"
                        placeholder="Search file contents..."
                        value={query}
                        onChange={e => setQuery(e.target.value)}
                        onKeyDown={onKeyDown}
                        onFocus={() => setShowHistory(true)}
                        style={{ flex: 1, minWidth: 0 }}
                    />
                    <button
                        onClick={() => setShowFilters(f => !f)}
                        title="Toggle filters"
                        style={{
                            padding: '2px 8px',
                            background: showFilters ? '#e0e7ff' : undefined,
                            border: '1px solid #ccc',
                            borderRadius: 4,
                            cursor: 'pointer',
                            fontSize: 12,
                        }}
                    >
                        Filters
                    </button>
                    <button onClick={() => onSearch()} disabled={loading}>
                        {loading ? 'Searching...' : 'Search'}
                    </button>
                </div>

                {/* History dropdown */}
                {showHistory && filteredHistory.length > 0 && (
                    <div style={{
                        position: 'absolute',
                        top: '100%',
                        left: 0,
                        right: 0,
                        zIndex: 100,
                        background: '#fff',
                        border: '1px solid #ddd',
                        borderRadius: 4,
                        boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
                        maxHeight: 200,
                        overflowY: 'auto',
                    }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 8px', borderBottom: '1px solid #eee', fontSize: 11, color: '#888' }}>
                            <span>Recent searches</span>
                            <span style={{ cursor: 'pointer', color: '#999' }} onClick={clearHistory}>Clear</span>
                        </div>
                        {filteredHistory.map((q, i) => (
                            <div
                                key={i}
                                onMouseDown={() => onHistorySelect(q)}
                                style={{
                                    padding: '5px 10px',
                                    cursor: 'pointer',
                                    fontSize: 13,
                                    borderBottom: '1px solid #f5f5f5',
                                }}
                                onMouseEnter={e => (e.currentTarget.style.background = '#f0f4ff')}
                                onMouseLeave={e => (e.currentTarget.style.background = '')}
                            >
                                {q}
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Filter panel */}
            {showFilters && (
                <div style={{ display: 'flex', gap: 8, marginTop: 6, alignItems: 'center' }}>
                    <label style={{ fontSize: 11, color: '#555', whiteSpace: 'nowrap' }}>Extension:</label>
                    <input
                        type="text"
                        placeholder=".py"
                        value={extFilter}
                        onChange={e => setExtFilter(e.target.value)}
                        style={{ width: 70, fontSize: 12 }}
                    />
                    <label style={{ fontSize: 11, color: '#555', whiteSpace: 'nowrap' }}>Path prefix:</label>
                    <input
                        type="text"
                        placeholder="/home/user/project"
                        value={prefixFilter}
                        onChange={e => setPrefixFilter(e.target.value)}
                        style={{ flex: 1, minWidth: 0, fontSize: 12 }}
                    />
                    <button
                        onClick={() => { setExtFilter(''); setPrefixFilter(''); }}
                        style={{ fontSize: 11, padding: '2px 6px' }}
                    >
                        Clear
                    </button>
                </div>
            )}

            {/* Results */}
            {results.length > 0 && (
                <ul style={{ margin: '6px 0 0', padding: 0, listStyle: 'none', maxHeight: 300, overflowY: 'auto' }}>
                    {results.map((r, i) => (
                        <li
                            key={i}
                            style={{
                                padding: '4px 6px',
                                cursor: r.path ? 'pointer' : 'default',
                                borderBottom: '1px solid #eee',
                            }}
                            onClick={() => r.path && onSelectFile?.(r.path)}
                        >
                            <div style={{ fontWeight: 'bold', fontSize: 12, color: '#555' }}>
                                {r.path ?? '(unknown)'}
                                {r.ext && (
                                    <span style={{ marginLeft: 4, fontSize: 10, color: '#fff', background: '#6366f1', borderRadius: 3, padding: '1px 4px' }}>
                                        {r.ext}
                                    </span>
                                )}
                                <span style={{ fontWeight: 'normal', color: '#aaa', marginLeft: 6 }}>
                                    score: {r.score.toFixed(3)}
                                </span>
                            </div>
                            <div style={{ fontFamily: 'monospace', fontSize: 11, color: '#333', whiteSpace: 'pre-wrap' }}>
                                {r.text.slice(0, 200)}
                            </div>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}
