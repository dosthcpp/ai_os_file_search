/**
 * SearchPanel — semantic file search using the /api/search endpoint.
 * Renders a query input and a list of ranked results with score, path, and snippet.
 */
import { useState, useCallback } from 'react';
import { searchFiles, SearchResult } from '../api.ts';

type Props = {
    /** Called when the user clicks a result path, so the parent can select that file */
    onSelectFile?: (path: string) => void;
};

export default function SearchPanel({ onSelectFile }: Props) {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<SearchResult[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const runSearch = useCallback(async () => {
        const q = query.trim();
        if (!q) return;
        setLoading(true);
        setError(null);
        try {
            const data = await searchFiles(q);
            setResults(data);
            if (data.length === 0) setError('No results found.');
        } catch {
            setError('Search failed — is the server running?');
        } finally {
            setLoading(false);
        }
    }, [query]);

    const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter') runSearch();
    };

    return (
        <div style={{ padding: '8px 0' }}>
            {/* Search input row */}
            <div style={{ display: 'flex', gap: '4px', marginBottom: '6px' }}>
                <input
                    type="text"
                    placeholder="Search files…"
                    value={query}
                    onChange={e => setQuery(e.target.value)}
                    onKeyDown={onKeyDown}
                    disabled={loading}
                    style={{ flex: 1, fontSize: '12px' }}
                />
                <button onClick={runSearch} disabled={loading || !query.trim()}>
                    {loading ? '…' : 'Search'}
                </button>
            </div>

            {/* Error message */}
            {error && (
                <p style={{ color: '#d44', fontSize: '11px', margin: '0 0 4px 0' }}>{error}</p>
            )}

            {/* Result list */}
            {results.length > 0 && (
                <ul style={{ margin: 0, padding: 0, listStyle: 'none' }}>
                    {results.map((r, i) => (
                        <li
                            key={i}
                            onClick={() => onSelectFile?.(r.path)}
                            style={{
                                cursor: 'pointer',
                                padding: '6px',
                                marginBottom: '4px',
                                background: '#f5f5f5',
                                borderRadius: '4px',
                                borderLeft: '3px solid #4a9eff',
                            }}
                        >
                            {/* Score badge + path */}
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <span style={{ fontSize: '11px', fontWeight: 600, wordBreak: 'break-all' }}>
                                    {r.path}
                                </span>
                                <span style={{
                                    fontSize: '10px',
                                    background: '#4a9eff',
                                    color: '#fff',
                                    borderRadius: '3px',
                                    padding: '1px 5px',
                                    flexShrink: 0,
                                    marginLeft: '6px',
                                }}>
                                    {(r.score * 100).toFixed(0)}%
                                </span>
                            </div>
                            {/* Text snippet */}
                            <p style={{
                                margin: '3px 0 0 0',
                                fontSize: '11px',
                                color: '#555',
                                whiteSpace: 'pre-wrap',
                                wordBreak: 'break-word',
                            }}>
                                {r.text.slice(0, 200)}
                                {r.text.length > 200 ? '…' : ''}
                            </p>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}
