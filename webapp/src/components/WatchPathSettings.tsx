import { useEffect, useState } from 'react';
import { getWatchPaths, addWatchPath, removeWatchPath } from '../api.ts';

export default function WatchPathSettings() {
    const [paths, setPaths] = useState<string[]>([]);
    const [tempPath, setTempPath] = useState<string>('');
    const [loading, setLoading] = useState(false);

    const load = async () => {
        try {
            const data = await getWatchPaths();
            setPaths(data);
        } catch {
            console.error('Failed to load watch paths');
        }
    };

    const onAdd = async () => {
        if (!tempPath.trim()) return;
        if (paths.includes(tempPath.trim())) {
            alert('Path already registered');
            return;
        }
        setLoading(true);
        try {
            const { ok, error } = await addWatchPath(tempPath.trim());
            if (ok) {
                setTempPath('');
                await load();
            } else {
                alert(error ?? 'Invalid directory path');
            }
        } catch {
            alert('Failed to add path — is the server running?');
        } finally {
            setLoading(false);
        }
    };

    const onRemove = async (path: string) => {
        setLoading(true);
        try {
            await removeWatchPath(path);
            await load();
        } catch {
            alert('Failed to remove path');
        } finally {
            setLoading(false);
        }
    };

    // Allow adding with the Enter key
    const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter') onAdd();
    };

    useEffect(() => {
        load();
    }, []);

    return (
        <div style={{ marginBottom: '2px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <p style={{ fontWeight: 'bold', margin: 0 }}>Watch Directories</p>
                <div style={{ display: 'flex', gap: '4px' }}>
                    <input
                        type="text"
                        placeholder="/path/to/watch"
                        value={tempPath}
                        onChange={e => setTempPath(e.target.value)}
                        onKeyDown={onKeyDown}
                        disabled={loading}
                    />
                    <button onClick={onAdd} disabled={loading || !tempPath.trim()}>
                        Add
                    </button>
                </div>
            </div>

            <ul style={{ margin: '4px 0 0 0', padding: 0, listStyle: 'none' }}>
                {paths.map(p => (
                    <li key={p} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '2px 0' }}>
                        <span style={{ flex: 1, fontSize: '12px', wordBreak: 'break-all' }}>{p}</span>
                        <button
                            onClick={() => onRemove(p)}
                            disabled={loading}
                            style={{ fontSize: '11px', color: '#d44', cursor: 'pointer' }}
                        >
                            Remove
                        </button>
                    </li>
                ))}
            </ul>
        </div>
    );
}
