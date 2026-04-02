import { useEffect, useState } from 'react';
import { Button, Input, Typography, Space, Tag, Divider, Alert } from 'antd';
import { FolderOpen, Trash2, Plus, Palette, CheckCircle2 } from 'lucide-react';
import { getWatchPaths, addWatchPath, removeWatchPath, extractTheme, ThemeExtractResult } from '../api.ts';
import { useOSStore } from '../store';

const { Text } = Typography;

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

    const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter') onAdd();
    };

    useEffect(() => {
        load();
    }, []);

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
            {/* Watch Directories Section */}
            <div style={{ marginBottom: 4 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 12 }}>
                    <FolderOpen size={15} color="#3b82f6" />
                    <Text strong style={{ fontSize: 13 }}>Watch Directories</Text>
                </div>

                <Space.Compact style={{ width: '100%', marginBottom: 12 }}>
                    <Input
                        placeholder="/path/to/watch"
                        value={tempPath}
                        onChange={e => setTempPath(e.target.value)}
                        onKeyDown={onKeyDown}
                        disabled={loading}
                        size="small"
                        style={{ fontSize: 12 }}
                    />
                    <Button
                        type="primary"
                        icon={<Plus size={13} />}
                        onClick={onAdd}
                        disabled={loading || !tempPath.trim()}
                        size="small"
                    >
                        Add
                    </Button>
                </Space.Compact>

                {paths.length === 0 ? (
                    <div style={{ padding: '10px 0', textAlign: 'center', color: '#bbb', fontSize: 12 }}>
                        No directories watched yet
                    </div>
                ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                        {paths.map(p => (
                            <div
                                key={p}
                                style={{
                                    display: 'flex', alignItems: 'center', gap: 8,
                                    padding: '6px 10px', background: '#f8faff',
                                    border: '1px solid #e0e8ff', borderRadius: 6,
                                }}
                            >
                                <FolderOpen size={13} color="#3b82f6" style={{ flexShrink: 0 }} />
                                <span style={{ flex: 1, fontSize: 12, wordBreak: 'break-all', color: '#374151', fontFamily: 'monospace' }}>{p}</span>
                                <Button
                                    type="text"
                                    size="small"
                                    danger
                                    icon={<Trash2 size={12} />}
                                    onClick={() => onRemove(p)}
                                    disabled={loading}
                                    style={{ flexShrink: 0, padding: '0 6px', height: 24 }}
                                />
                            </div>
                        ))}
                    </div>
                )}
            </div>

            <Divider style={{ margin: '14px 0' }} />

            {/* Adaptive Theme Section */}
            <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 12 }}>
                    <Palette size={15} color="#8b5cf6" />
                    <Text strong style={{ fontSize: 13 }}>Adaptive Theme</Text>
                    <Tag color="purple" style={{ fontSize: 10, marginLeft: 4 }}>v2-3</Tag>
                </div>

                <Space.Compact style={{ width: '100%', marginBottom: 10 }}>
                    <Input
                        placeholder="/path/to/wallpaper.jpg"
                        value={wallpaperPath}
                        onChange={e => setWallpaperPath(e.target.value)}
                        size="small"
                        style={{ fontSize: 12 }}
                    />
                    <Button
                        type="primary"
                        icon={<Palette size={13} />}
                        onClick={applyTheme}
                        disabled={themeLoading || !wallpaperPath.trim()}
                        loading={themeLoading}
                        size="small"
                        style={{ background: '#8b5cf6', borderColor: '#8b5cf6' }}
                    >
                        Apply
                    </Button>
                </Space.Compact>

                {themeError && (
                    <Alert type="error" message={themeError} style={{ fontSize: 11, padding: '4px 10px', marginBottom: 8 }} />
                )}

                {themeResult && (
                    <div style={{ background: '#faf5ff', border: '1px solid #e9d5ff', borderRadius: 8, padding: '10px 12px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                            <CheckCircle2 size={13} color="#7c3aed" />
                            <Text style={{ fontSize: 11, color: '#7c3aed', fontWeight: 600 }}>
                                Theme extracted — {themeResult.theme === 'dark_bg' ? 'Dark' : 'Light'} mode
                            </Text>
                        </div>
                        <div style={{ fontSize: 11, color: '#888', marginBottom: 8 }}>
                            Dominant: rgb({themeResult.dominant_color.r}, {themeResult.dominant_color.g}, {themeResult.dominant_color.b})
                            &nbsp;|&nbsp;Luma: {themeResult.luma}
                        </div>
                        <div style={{ display: 'flex', gap: 8 }}>
                            {Object.entries(themeResult.palette).map(([key, color]) => (
                                <div key={key} style={{ textAlign: 'center' }}>
                                    <div style={{
                                        width: 32, height: 32, borderRadius: 8, background: color,
                                        border: '2px solid rgba(0,0,0,0.08)', margin: '0 auto',
                                        boxShadow: '0 2px 6px rgba(0,0,0,0.12)',
                                    }} />
                                    <div style={{ fontSize: 10, color: '#888', marginTop: 4 }}>{key}</div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
