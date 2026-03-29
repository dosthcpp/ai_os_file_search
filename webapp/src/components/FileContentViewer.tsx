import { useEffect, useState } from 'react';
import { getFileContent } from '../api.ts';

type Props = {
    path: string;
};

// Derive a language hint from file extension for basic header display
function langFromPath(path: string): string {
    const extension = path.includes('.') ? path.split('.').pop()?.toLowerCase() ?? '' : '';
    const map: Record<string, string> = {
        py: 'Python', js: 'JavaScript', ts: 'TypeScript',
        tsx: 'TypeScript/React', jsx: 'JavaScript/React',
        java: 'Java', go: 'Go', rs: 'Rust', rb: 'Ruby',
        cpp: 'C++', c: 'C', cs: 'C#', swift: 'Swift', kt: 'Kotlin',
        html: 'HTML', htm: 'HTML', json: 'JSON', yaml: 'YAML', yml: 'YAML',
        csv: 'CSV', md: 'Markdown', txt: 'Text', sh: 'Shell',
        pdf: 'PDF', docx: 'Word',
    };
    if (map[extension]) return map[extension];
    return extension ? extension.toUpperCase() : 'File';
}

export default function FileContentViewer({ path }: Props) {
    const [content, setContent] = useState<string | null>(null);
    const [truncated, setTruncated] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        let cancelled = false;
        setLoading(true);
        setContent(null);
        setError(null);
        setTruncated(false);

        getFileContent(path).then(res => {
            if (cancelled) return;
            if (res.ok) {
                setContent(res.content);
                setTruncated(res.truncated ?? false);
            } else {
                setError(res.error ?? 'Unknown error');
            }
        }).catch(e => {
            if (!cancelled) setError(String(e));
        }).finally(() => {
            if (!cancelled) setLoading(false);
        });

        return () => { cancelled = true; };
    }, [path]);

    const lang = langFromPath(path);
    const filename = path.split('/').pop() ?? path;

    return (
        <div style={{ marginTop: 12 }}>
            <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '6px 10px',
                background: '#f8f9fa',
                border: '1px solid #e2e8f0',
                borderBottom: 'none',
                borderRadius: '6px 6px 0 0',
            }}>
                <span style={{ fontWeight: 600, fontSize: 13 }}>{filename}</span>
                <span style={{
                    fontSize: 11, color: '#6366f1',
                    background: '#eef2ff', borderRadius: 4,
                    padding: '1px 6px',
                }}>
                    {lang}
                </span>
                {truncated && (
                    <span style={{ fontSize: 11, color: '#f59e0b', marginLeft: 'auto' }}>
                        ⚠ Showing first 100 KB
                    </span>
                )}
            </div>

            <div style={{
                border: '1px solid #e2e8f0',
                borderRadius: '0 0 6px 6px',
                overflow: 'hidden',
                maxHeight: 480,
                overflowY: 'auto',
            }}>
                {loading && (
                    <div style={{ padding: 16, color: '#888', fontSize: 13 }}>Loading…</div>
                )}
                {error && (
                    <div style={{ padding: 16, color: '#dc2626', fontSize: 13 }}>
                        Could not load file: {error}
                    </div>
                )}
                {content !== null && !loading && (
                    <pre style={{
                        margin: 0,
                        padding: '12px 16px',
                        fontFamily: '"Fira Code", "Cascadia Code", "Consolas", monospace',
                        fontSize: 12,
                        lineHeight: 1.6,
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-all',
                        background: '#fafafa',
                        color: '#1e293b',
                        overflowX: 'auto',
                    }}>
                        {content || <span style={{ color: '#aaa' }}>(empty file)</span>}
                    </pre>
                )}
            </div>
        </div>
    );
}
