import { useEffect, useState } from 'react';
import { Button, Input, Tag, Typography, Space, Divider, Spin } from 'antd';
import { FolderOpen, Palette, X, Plus } from 'lucide-react';
import { getWatchPaths, addWatchPath, removeWatchPath, extractTheme, ThemeExtractResult } from '../api.ts';
import { useOSStore } from '../store';

const { Text, Title } = Typography;

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
        if (paths.includes(tempPath.trim())) return;
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

    useEffect(() => { load(); }, []);

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
            {/* Watch Directories Section */}
            <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10 }}>
                    <FolderOpen size={14} color="#3b82f6" />
                    <Title level={5} style={{ margin: 0, fontSize: 13, color: '#1e293b' }}>Watch Directories</Title>
                </div>

                <Space.Compact style={{ width: '100%', marginBottom: 10 }}>
                    <Input
                        size="small"
                        placeholder="/path/to/directory"
                        value={tempPath}
                        onChange={e => setTempPath(e.target.value)}
                        onPressEnter={onAdd}
                        disabled={loading}
                        style={{ fontSize: 12 }}
                    />
                    <Button
                        size="small"
                        type="primary"
                        icon={<Plus size={12} />}
                        onClick={onAdd}
                        disabled={loading || !tempPath.trim()}
                        style={{ display: 'flex', alignItems: 'center' }}
                    >
                        Add
                    </Button>
                </Space.Compact>

                {loading && <Spin size="small" style={{ display: 'block', marginBottom: 6 }} />}

                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {paths.length === 0 && !loading && (
                        <Text type="secondary" style={{ fontSize: 11 }}>No directories watched yet.</Text>
                    )}
                    {paths.map(p => (
                        <Tag
                            key={p}
                            closable
                            onClose={() => onRemove(p)}
                            closeIcon={<X size={10} />}
                            style={{ fontSize: 11, maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', gap: 4, padding: '2px 8px', borderRadius: 6 }}
                            color="blue"
                        >
                            {p}
                        </Tag>
                    ))}
                </div>
            </div>

            <Divider style={{ margin: '14px 0' }} />

            {/* Adaptive Theme Section */}
            <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10 }}>
                    <Palette size={14} color="#8b5cf6" />
                    <Title level={5} style={{ margin: 0, fontSize: 13, color: '#1e293b' }}>Adaptive Theme</Title>
                    <Tag style={{ fontSize: 10, padding: '0 6px', borderRadius: 10 }} color="purple">v2-3</Tag>
                </div>

                <Space.Compact style={{ width: '100%', marginBottom: 8 }}>
                    <Input
                        size="small"
                        placeholder="/path/to/wallpaper.jpg"
                        value={wallpaperPath}
                        onChange={e => setWallpaperPath(e.target.value)}
                        onPressEnter={applyTheme}
                        style={{ fontSize: 12 }}
                    />
                    <Button
                        size="small"
                        type="primary"
                        onClick={applyTheme}
                        loading={themeLoading}
                        disabled={!wallpaperPath.trim()}
                        style={{ background: '#8b5cf6', borderColor: '#8b5cf6' }}
                    >
                        Apply
                    </Button>
                </Space.Compact>

                {themeResult && (
                    <div style={{ fontSize: 11, background: '#fafafa', border: '1px solid #e2e8f0', borderRadius: 6, padding: '8px 10px' }}>
                        <Text type="secondary" style={{ fontSize: 10, display: 'block', marginBottom: 6 }}>
                            Dominant: rgb({themeResult.dominant_color.r}, {themeResult.dominant_color.g}, {themeResult.dominant_color.b})
                            {' '}· Luma: {themeResult.luma}
                            {' '}· Mode: <b>{themeResult.theme}</b>
                        </Text>
                        <div style={{ display: 'flex', gap: 6 }}>
                            {Object.entries(themeResult.palette).map(([key, color]) => (
                                <div key={key} style={{ textAlign: 'center' }}>
                                    <div style={{ width: 24, height: 24, borderRadius: 5, background: color, border: '1px solid rgba(0,0,0,0.1)', margin: '0 auto' }} />
                                    <div style={{ fontSize: 9, color: '#888', marginTop: 2 }}>{key}</div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
                {themeError && <Text type="danger" style={{ fontSize: 11 }}>{themeError}</Text>}
            </div>
        </div>
    );
}
