import React, { useState, useEffect } from 'react';
import { Card, Button, Layout, Menu, Typography, Space, Tooltip, Avatar, Badge, Dropdown, theme } from 'antd';
import {
  FolderTree,
  Search,
  Settings,
  ShieldAlert,
  Terminal,
  History,
  FileText,
  Monitor,
  LayoutGrid,
  FileSignature,
  Palette,
} from 'lucide-react';
import { useOSStore, WindowType } from '../store';
import { runSecurityAudit, signConsent, SecurityAuditResult, ConsentSignResult } from '../api';
import WindowFrame from './WindowFrame';
import FileTree from './FileTree';
import SearchBar from './SearchBar';
import WatchPathSettings from './WatchPathSettings';
import FileContentViewer from './FileContentViewer';
import { VersionTimeline } from './VersionTimeline';
import DiffViewer from './DiffViewer';
import SearchPanel from './SearchPanel';

const { Header, Content, Footer } = Layout;
const { Text } = Typography;

const Desktop: React.FC = () => {
  const { windows, activeWindowId, openWindow, restoreWindow, focusWindow, adaptiveTheme } = useOSStore();
  const { token } = theme.useToken();
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const renderWindowContent = (win: any) => {
    switch (win.type) {
      case 'file-tree':
        return <div style={{ padding: 16 }}><FileTree onSelectFile={(path) => openWindow('file-content', path.split('/').pop() || path, { path })} /></div>;
      case 'file-search':
        return <div style={{ padding: 16 }}><SearchPanel onSelectFile={(path) => openWindow('file-content', path.split('/').pop() || path, { path })} /></div>;
      case 'settings':
        return <div style={{ padding: 16 }}><WatchPathSettings /></div>;
        case 'file-content':
        case 'version-history':
          return (
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
              <div style={{ display: 'flex', borderBottom: '1px solid #d9d9d9', background: '#f5f5f5' }}>
                <Button 
                  type="text" 
                  size="small" 
                  style={{ borderRadius: 0, height: 32, padding: '0 16px', background: win.type === 'file-content' ? '#fff' : 'transparent', fontWeight: win.type === 'file-content' ? 600 : 400 }}
                  onClick={() => useOSStore.getState().openWindow('file-content', win.title, win.params)}
                >
                  File Content
                </Button>
                <Button 
                  type="text" 
                  size="small" 
                  style={{ borderRadius: 0, height: 32, padding: '0 16px', background: win.type === 'version-history' ? '#fff' : 'transparent', fontWeight: win.type === 'version-history' ? 600 : 400 }}
                  onClick={() => useOSStore.getState().openWindow('version-history', win.title, win.params)}
                >
                  Version History
                </Button>
              </div>
              <div style={{ flex: 1, overflow: 'auto' }}>
                {win.type === 'file-content' ? (
                  <FileContentViewer path={win.params.path} />
                ) : (
                  <div style={{ padding: 16 }}>
                    <VersionTimeline 
                      path={win.params.path} 
                      onSelectVersion={(v) => {
                         // We might want a separate state here for the selected version to show diff
                      }} 
                    />
                  </div>
                )}
              </div>
            </div>
          );
      case 'security-audit':
        return <SecurityAuditWindow />;
      case 'consent':
        return <ConsentWindow />;
      default:
        return <div>Unknown Window Type: {win.type}</div>;
    }
  };

  const startMenuItems = [
    { key: 'file-tree', icon: <FolderTree size={16} />, label: 'File Explorer', onClick: () => openWindow('file-tree', 'File Explorer') },
    { key: 'file-search', icon: <Search size={16} />, label: 'File Search', onClick: () => openWindow('file-search', 'Search Files') },
    { key: 'security-audit', icon: <ShieldAlert size={16} />, label: 'Security Audit', onClick: () => openWindow('security-audit', 'Security Audit') },
    { key: 'settings', icon: <Settings size={16} />, label: 'Settings', onClick: () => openWindow('settings', 'Settings') },
    { key: 'consent', icon: <FileSignature size={16} />, label: 'E-Consent', onClick: () => openWindow('consent', 'E-Consent') },
  ];

  return (
    <Layout style={{ height: '100vh', width: '100vw', background: '#1e293b', overflow: 'hidden', position: 'relative' }}>
      {/* Desktop Background */}
      <Content style={{ position: 'relative', height: '100%', width: '100%' }}>
        <div style={{ 
          position: 'absolute', 
          inset: 0, 
          background: adaptiveTheme ? adaptiveTheme.palette.bg : 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
          zIndex: 0 
        }} />
        
        {/* Desktop Icons */}
        <Space direction="vertical" style={{ position: 'absolute', left: 20, top: 20, zIndex: 1 }} size={20}>
          <Tooltip title="File Explorer" placement="right">
            <Button 
                type="text" 
                icon={<FolderTree size={32} color="white" />} 
                style={{ height: 60, width: 60, color: 'white' }}
                onClick={() => openWindow('file-tree', 'File Explorer')}
            />
          </Tooltip>
          <Tooltip title="Search" placement="right">
            <Button 
                type="text" 
                icon={<Search size={32} color="white" />} 
                style={{ height: 60, width: 60, color: 'white' }}
                onClick={() => openWindow('file-search', 'Search Files')}
            />
          </Tooltip>
           <Tooltip title="Security" placement="right">
            <Button
                type="text"
                icon={<ShieldAlert size={32} color="white" />}
                style={{ height: 60, width: 60, color: 'white' }}
                onClick={() => openWindow('security-audit', 'Security Audit')}
            />
          </Tooltip>
          <Tooltip title="E-Consent" placement="right">
            <Button
                type="text"
                icon={<FileSignature size={32} color="white" />}
                style={{ height: 60, width: 60, color: 'white' }}
                onClick={() => openWindow('consent', 'E-Consent')}
            />
          </Tooltip>
        </Space>

        {/* Windows Rendering */}
        {windows.map(win => (
          <WindowFrame key={win.id} window={win}>
            {renderWindowContent(win)}
          </WindowFrame>
        ))}
      </Content>

      {/* Taskbar */}
      <Footer style={{ 
        height: 48, 
        padding: '0 12px', 
        background: 'rgba(255, 255, 255, 0.1)', 
        backdropFilter: 'blur(10px)',
        borderTop: '1px solid rgba(255, 255, 255, 0.1)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        zIndex: 10000,
        color: 'white'
      }}>
        <Space size={12}>
          <Dropdown menu={{ items: startMenuItems }} placement="top" trigger={['click']}>
            <Button 
                type="primary" 
                shape="circle" 
                icon={<LayoutGrid size={20} />} 
                style={{ background: '#3b82f6', border: 'none' }}
            />
          </Dropdown>

          <div style={{ width: 1, height: 24, background: 'rgba(255,255,255,0.2)', margin: '0 4px' }} />

          {/* Taskbar Icons */}
          <Space size={4}>
            {windows.map(win => (
              <Tooltip key={win.id} title={win.title}>
                <Button
                  type={activeWindowId === win.id ? 'primary' : 'text'}
                  size="middle"
                  style={{ 
                    background: activeWindowId === win.id ? 'rgba(59, 130, 246, 0.5)' : win.isMinimized ? 'transparent' : 'rgba(255,255,255,0.1)',
                    color: 'white',
                    minWidth: 40,
                    maxWidth: 160,
                    padding: '0 12px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                  }}
                  onClick={() => {
                    if (win.isMinimized) {
                      restoreWindow(win.id);
                    } else if (activeWindowId === win.id) {
                      // Maybe minimize if clicking active? Puter style
                      // useOSStore.getState().minimizeWindow(win.id);
                    } else {
                      focusWindow(win.id);
                    }
                  }}
                >
                  <WindowIcon type={win.type} />
                  <span style={{ 
                    overflow: 'hidden', 
                    textOverflow: 'ellipsis', 
                    whiteSpace: 'nowrap',
                    fontSize: '12px',
                    fontWeight: activeWindowId === win.id ? 600 : 400,
                  }}>
                    {win.title}
                  </span>
                </Button>
              </Tooltip>
            ))}
          </Space>
        </Space>

        <Space size={16}>
          <Text style={{ color: 'white', fontSize: '13px', fontWeight: 500 }}>
            {currentTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </Text>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
             <Badge status="processing" color="#10b981" />
             <Text style={{ color: 'rgba(255,255,255,0.7)', fontSize: '12px' }}>System Ready</Text>
          </div>
        </Space>
      </Footer>
    </Layout>
  );
};

const WindowIcon: React.FC<{ type: WindowType }> = ({ type }) => {
    switch (type) {
        case 'file-tree': return <FolderTree size={16} />;
        case 'file-search': return <Search size={16} />;
        case 'settings': return <Settings size={16} />;
        case 'file-content': return <FileText size={16} />;
        case 'version-history': return <History size={16} />;
        case 'security-audit': return <ShieldAlert size={16} />;
        case 'consent': return <FileSignature size={16} />;
        default: return <Monitor size={16} />;
    }
};

const MOCK_MANIFEST = `<manifest package="com.suspicious.app">
    <uses-permission android:name="android.permission.READ_SMS"/>
    <uses-permission android:name="android.permission.INSTALL_PACKAGES"/>
    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>
</manifest>`;

const MOCK_STRINGS = `<resources>
    <string name="api_host">http://45.33.32.156/exfil</string>
    <string name="analytics">http://track.evil-domain.ru/collect</string>
</resources>`;

const MOCK_DOC = `Consent form for Tony Kim, RRN: 950101-1234567`;

const ThreatBadge: React.FC<{ level: string }> = ({ level }) => {
  const colors: Record<string, string> = { CRITICAL: '#ff4d4f', WARNING: '#faad14', SAFE: '#52c41a' };
  return <span style={{ padding: '2px 10px', borderRadius: 12, background: colors[level] || '#ccc', color: 'white', fontWeight: 700, fontSize: 12 }}>{level}</span>;
};

const SecurityAuditWindow: React.FC = () => {
    const [manifest, setManifest] = React.useState(MOCK_MANIFEST);
    const [strings, setStrings] = React.useState(MOCK_STRINGS);
    const [docText, setDocText] = React.useState(MOCK_DOC);
    const [auditData, setAuditData] = React.useState<SecurityAuditResult | null>(null);
    const [loading, setLoading] = React.useState(false);
    const [activeTab, setActiveTab] = React.useState<'apk' | 'pi'>('apk');

    const run = async () => {
        setLoading(true);
        try {
            const data = await runSecurityAudit(manifest, strings, docText);
            setAuditData(data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const apk = auditData?.apk_analysis;
    const pi = auditData?.pi_analysis;

    return (
        <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography.Title level={5} style={{ margin: 0 }}>Security Audit</Typography.Title>
                <Button type="primary" icon={<ShieldAlert size={14} />} onClick={run} loading={loading} size="small">
                    Run Audit
                </Button>
            </div>

            <div style={{ display: 'flex', gap: 8, borderBottom: '1px solid #f0f0f0', paddingBottom: 8 }}>
                {(['apk', 'pi'] as const).map(t => (
                    <Button key={t} size="small" type={activeTab === t ? 'primary' : 'default'} onClick={() => setActiveTab(t)}>
                        {t === 'apk' ? 'APK Analysis' : 'PI Document Scan'}
                    </Button>
                ))}
            </div>

            {activeTab === 'apk' ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    <div>
                        <Typography.Text type="secondary" style={{ fontSize: 11 }}>APK Manifest XML</Typography.Text>
                        <textarea value={manifest} onChange={e => setManifest(e.target.value)} rows={5} style={{ width: '100%', fontFamily: 'monospace', fontSize: 11, boxSizing: 'border-box' }} />
                    </div>
                    <div>
                        <Typography.Text type="secondary" style={{ fontSize: 11 }}>String Resources XML</Typography.Text>
                        <textarea value={strings} onChange={e => setStrings(e.target.value)} rows={4} style={{ width: '100%', fontFamily: 'monospace', fontSize: 11, boxSizing: 'border-box' }} />
                    </div>
                    {apk && (
                        <Card size="small">
                            <Space>
                                <ThreatBadge level={apk.threat_level} />
                                <Typography.Text>Score: <b>{apk.total_score}/100</b></Typography.Text>
                                <Typography.Text type="secondary" style={{ fontSize: 11 }}>Perms: {apk.score_breakdown.permission_score} | URLs: {apk.score_breakdown.url_score}</Typography.Text>
                            </Space>
                            <div style={{ marginTop: 8, fontSize: 12 }}>{apk.summary}</div>
                            {apk.permission_findings.length > 0 && (
                                <div style={{ marginTop: 8 }}>
                                    <b style={{ fontSize: 11 }}>Permissions</b>
                                    {apk.permission_findings.map((f, i) => (
                                        <div key={i} style={{ fontSize: 11, color: '#d46' }}>{f.permission} (+{f.score}): {f.reason}</div>
                                    ))}
                                </div>
                            )}
                            {apk.url_findings.length > 0 && (
                                <div style={{ marginTop: 8 }}>
                                    <b style={{ fontSize: 11 }}>URLs</b>
                                    {apk.url_findings.map((f, i) => (
                                        <div key={i} style={{ fontSize: 11, color: '#c60' }}>{f.url} (+{f.score})</div>
                                    ))}
                                </div>
                            )}
                        </Card>
                    )}
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    <div>
                        <Typography.Text type="secondary" style={{ fontSize: 11 }}>Document Text</Typography.Text>
                        <textarea value={docText} onChange={e => setDocText(e.target.value)} rows={4} style={{ width: '100%', fontSize: 12, boxSizing: 'border-box' }} />
                    </div>
                    {pi && (
                        <Card size="small">
                            <Space>
                                <ThreatBadge level={pi.risk} />
                                <Typography.Text>Encryption: <b>{pi.encryption}</b></Typography.Text>
                            </Space>
                            {pi.details.length > 0 && (
                                <div style={{ marginTop: 8 }}>
                                    {pi.details.map((d, i) => <div key={i} style={{ fontSize: 12, color: '#d46' }}>{d}</div>)}
                                </div>
                            )}
                        </Card>
                    )}
                </div>
            )}
        </div>
    );
};

const ConsentWindow: React.FC = () => {
    const [form, setForm] = React.useState({ teacher_id: 'Teacher01', title: 'Field Trip Consent', parent_id: 'Parent01', signature: '0.1,0.5,0.9,1.2,1.5,2.0' });
    const [result, setResult] = React.useState<ConsentSignResult | null>(null);
    const [loading, setLoading] = React.useState(false);
    const [error, setError] = React.useState<string | null>(null);

    const submit = async () => {
        setLoading(true);
        setError(null);
        try {
            const pattern = form.signature.split(',').map(s => parseFloat(s.trim())).filter(n => !isNaN(n));
            const data = await signConsent(form.teacher_id, form.title, form.parent_id, pattern);
            setResult(data);
        } catch (e) {
            setError('Failed to submit consent — is the server running?');
        } finally {
            setLoading(false);
        }
    };

    const inputStyle = { width: '100%', padding: '4px 8px', fontSize: 12, boxSizing: 'border-box' as const };

    return (
        <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 10 }}>
            <Typography.Title level={5} style={{ margin: 0 }}>NFT E-Consent</Typography.Title>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                {([['teacher_id', 'Teacher ID'], ['title', 'Form Title'], ['parent_id', 'Parent ID']] as const).map(([key, label]) => (
                    <div key={key} style={{ gridColumn: key === 'title' ? '1 / -1' : undefined }}>
                        <Typography.Text type="secondary" style={{ fontSize: 11 }}>{label}</Typography.Text>
                        <input value={form[key]} onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))} style={inputStyle} />
                    </div>
                ))}
                <div style={{ gridColumn: '1 / -1' }}>
                    <Typography.Text type="secondary" style={{ fontSize: 11 }}>Biometric Signature (comma-separated floats, &gt;5 values = VERIFIED)</Typography.Text>
                    <input value={form.signature} onChange={e => setForm(f => ({ ...f, signature: e.target.value }))} style={inputStyle} />
                </div>
            </div>
            <Button type="primary" onClick={submit} loading={loading} size="small">Sign Consent</Button>
            {error && <Typography.Text type="danger" style={{ fontSize: 12 }}>{error}</Typography.Text>}
            {result && (
                <Card size="small">
                    <Space wrap>
                        <Typography.Text><b>NFT ID:</b> {result.nft_id}</Typography.Text>
                        <span style={{ padding: '2px 10px', borderRadius: 12, background: result.integrity === 'VERIFIED' ? '#52c41a' : '#faad14', color: 'white', fontWeight: 700, fontSize: 12 }}>
                            {result.integrity}
                        </span>
                    </Space>
                    <div style={{ marginTop: 8, fontSize: 11 }}>
                        <div><b>Status:</b> {result.block.data.status}</div>
                        <div><b>Owner:</b> {result.block.data.owner}</div>
                        <div style={{ marginTop: 4, fontFamily: 'monospace', fontSize: 10, wordBreak: 'break-all', color: '#888' }}>
                            Block: {result.block.block_hash}
                        </div>
                    </div>
                </Card>
            )}
        </div>
    );
};

export default Desktop;
