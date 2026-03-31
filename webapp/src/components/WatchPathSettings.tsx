import { useEffect, useState } from 'react';
import { getWatchPaths, addWatchPath, removeWatchPath, extractTheme, ThemeExtractResult } from '../api.ts';
import { useOSStore } from '../store';

export default function WatchPathSettings() {
    const [paths, setPaths] = useState<string[]>([]);
    const [tempPath, setTempPath] = useState<string>('');
    const [loading, setLoading] = useState(false);
    const [wallpaperPath, setWallpaperPath] = useState<string>('');
    const [themeLoading, setThemeLoading] = useState(false);
    const [themeResult, setThemeResult] = useState<ThemeExtractResult | null>(null);
    const [themeError, setThemeError] = useState<string | null>(null);
    const { setAdaptiveTheme } = useOSStore();

    const applyTheme = async () => {
        if (!wallpaperPath.trim()) return;
        setThemeLoading(true);
        setThemeError(null);
        try {
            const result = await extractTheme(wallpaperPath.trim());
            setThemeResult(result);
            setAdaptiveTheme({ palette: result.palette, dominantColor: result.dominant_color });
        } catch {
            setThemeError('Failed to extract theme — is the server running?');
        } finally {
            setThemeLoading(false);
        }
    };

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

            {/* ── Theme Engine ─────────────────────────────── */}
            <div style={{ marginTop: 16, borderTop: '1px solid #eee', paddingTop: 12 }}>
                <p style={{ fontWeight: 'bold', margin: '0 0 8px 0' }}>Adaptive Theme (v2-3)</p>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8 }}>
                    <input
                        type="text"
                        placeholder="/path/to/wallpaper.jpg"
                        value={wallpaperPath}
                        onChange={e => setWallpaperPath(e.target.value)}
                        style={{ flex: 1, padding: '4px 8px', fontSize: 12 }}
                    />
                    <button onClick={applyTheme} disabled={themeLoading || !wallpaperPath.trim()}>
                        {themeLoading ? 'Extracting...' : 'Apply'}
                    </button>
                </div>
                {themeResult && (
                    <div style={{ fontSize: 11 }}>
                        <div>Dominant: rgb({themeResult.dominant_color.r}, {themeResult.dominant_color.g}, {themeResult.dominant_color.b}) | Luma: {themeResult.luma} | Theme: <b>{themeResult.theme}</b></div>
                        <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
                            {Object.entries(themeResult.palette).map(([key, color]) => (
                                <div key={key} style={{ textAlign: 'center' }}>
                                    <div style={{ width: 28, height: 28, borderRadius: 6, background: color, border: '1px solid #ccc', margin: '0 auto' }} />
                                    <div style={{ fontSize: 10, color: '#888' }}>{key}</div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
                {themeError && <div style={{ color: '#d46', fontSize: 11 }}>{themeError}</div>}
            </div>
        </div>
    );
}
