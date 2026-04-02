/**
 * SearchPanel — semantic file search using the /api/search endpoint.
 * Renders a query input and a list of ranked results with score, path, and snippet.
 */
import { useState, useCallback } from 'react';
import { Input, Button, Tag, Typography, Empty, Spin, Space } from 'antd';
import { Search, FileText } from 'lucide-react';
import { searchFiles, SearchResult } from '../api.ts';

const { Text } = Typography;

type Props = {
    onSelectFile?: (path: string) => void;
};

const scoreColor = (s: number) => s >= 0.8 ? '#10b981' : s >= 0.5 ? '#3b82f6' : '#94a3b8';

export default function SearchPanel({ onSelectFile }: Props) {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<SearchResult[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [searched, setSearched] = useState(false);

    const runSearch = useCallback(async () => {
        const q = query.trim();
        if (!q) return;
        setLoading(true);
        setError(null);
        setSearched(true);
        try {
            const data = await searchFiles(q);
            setResults(data);
        } catch {
            setError('Search failed — is the server running?');
            setResults([]);
        } finally {
            setLoading(false);
        }
    }, [query]);

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
                <Search size={14} color="#3b82f6" />
                <Typography.Title level={5} style={{ margin: 0, fontSize: 13, color: '#1e293b' }}>Semantic Search</Typography.Title>
            </div>

            {/* Search input */}
            <Space.Compact style={{ width: '100%' }}>
                <Input
                    size="small"
                    placeholder="Search files by content…"
                    value={query}
                    onChange={e => setQuery(e.target.value)}
                    onPressEnter={runSearch}
                    disabled={loading}
                    style={{ fontSize: 12 }}
                />
                <Button
                    size="small"
                    type="primary"
                    icon={<Search size={12} />}
                    onClick={runSearch}
                    loading={loading}
                    disabled={!query.trim()}
                    style={{ display: 'flex', alignItems: 'center' }}
                >
                    Search
                </Button>
            </Space.Compact>

            {/* Error */}
            {error && <Text type="danger" style={{ fontSize: 11 }}>{error}</Text>}

            {/* Loading */}
            {loading && (
                <div style={{ textAlign: 'center', padding: '16px 0' }}>
                    <Spin size="small" />
                </div>
            )}

            {/* Empty state */}
            {!loading && searched && results.length === 0 && !error && (
                <Empty description={<Text type="secondary" style={{ fontSize: 11 }}>No results found</Text>} imageStyle={{ height: 36 }} />
            )}

            {/* Results */}
            {!loading && results.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    <Text type="secondary" style={{ fontSize: 10 }}>{results.length} result{results.length !== 1 ? 's' : ''}</Text>
                    {results.map((r, i) => (
                        <div
                            key={i}
                            onClick={() => onSelectFile?.(r.path ?? '')}
                            style={{
                                cursor: 'pointer',
                                padding: '8px 10px',
                                background: '#f8faff',
                                border: '1px solid #e2e8f0',
                                borderLeft: `3px solid ${scoreColor(r.score)}`,
                                borderRadius: 6,
                                transition: 'background 0.12s',
                            }}
                            onMouseEnter={e => (e.currentTarget.style.background = '#eff6ff')}
                            onMouseLeave={e => (e.currentTarget.style.background = '#f8faff')}
                        >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 5, minWidth: 0 }}>
                                    <FileText size={11} color="#64748b" style={{ flexShrink: 0 }} />
                                    <Text style={{ fontSize: 11, fontWeight: 600, wordBreak: 'break-all', color: '#1e293b' }}>
                                        {r.path ?? '(unknown)'}
                                    </Text>
                                </div>
                                <Tag
                                    style={{ fontSize: 10, padding: '0 6px', borderRadius: 10, flexShrink: 0, marginLeft: 6, color: 'white', background: scoreColor(r.score), borderColor: scoreColor(r.score) }}
                                >
                                    {(r.score * 100).toFixed(0)}%
                                </Tag>
                            </div>
                            <Text type="secondary" style={{ fontSize: 10, lineHeight: 1.5, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                                {r.text.slice(0, 180)}{r.text.length > 180 ? '…' : ''}
                            </Text>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
