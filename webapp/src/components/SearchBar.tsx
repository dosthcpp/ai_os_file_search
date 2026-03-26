import { useState } from 'react';
import { searchFiles } from '../api.ts';

type SearchResult = {
    score: number;
    path: string | null;
    text: string;
    chunk_index: number | null;
    collection: string;
};

type Props = {
    onSelectFile?: (path: string) => void;
};

export default function SearchBar({ onSelectFile }: Props) {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<SearchResult[]>([]);
    const [loading, setLoading] = useState(false);

    const onSearch = async () => {
        if (!query.trim()) return;
        setLoading(true);
        try {
            const data = await searchFiles(query.trim(), 10);
            setResults(data);
        } catch {
            setResults([]);
        } finally {
            setLoading(false);
        }
    };

    const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter') onSearch();
    };

    return (
        <div style={{ marginBottom: 8 }}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <input
                    type="text"
                    placeholder="파일 내용 검색..."
                    value={query}
                    onChange={e => setQuery(e.target.value)}
                    onKeyDown={onKeyDown}
                    style={{ flex: 1, minWidth: 0 }}
                />
                <button onClick={onSearch} disabled={loading}>
                    {loading ? '검색 중...' : '검색'}
                </button>
            </div>

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
                                {r.path ?? '(unknown)'} &nbsp;
                                <span style={{ fontWeight: 'normal', color: '#aaa' }}>
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
