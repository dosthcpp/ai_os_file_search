import React, { useState, useEffect } from 'react';
import { Button, Layout, Typography, Space, Tooltip, Badge, Dropdown, theme, Progress } from 'antd';
import {
  FolderTree,
  Search,
  Settings,
  ShieldAlert,
  History,
  FileText,
  Monitor,
  LayoutGrid,
  FileSignature,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Link,
  Lock,
} from 'lucide-react';
import { useOSStore, WindowType } from '../store';
import { runSecurityAudit, signConsent, SecurityAuditResult, ConsentSignResult } from '../api';
import WindowFrame from './WindowFrame';
import FileTree from './FileTree';
import WatchPathSettings from './WatchPathSettings';
import FileContentViewer from './FileContentViewer';
import { VersionTimeline } from './VersionTimeline';
import SearchPanel from './SearchPanel';

const { Content, Footer } = Layout;
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
              <div style={{ display: 'flex', borderBottom: '1px solid #e8e8e8', background: '#fafafa', padding: '0 8px' }}>
                {[
                  { type: 'file-content', label: 'File Content', icon: <FileText size={13} /> },
                  { type: 'version-history', label: 'Version History', icon: <History size={13} /> },
                ].map(tab => (
                  <button
                    key={tab.type}
                    onClick={() => useOSStore.getState().openWindow(tab.type as any, win.title, win.params)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 5, height: 34, padding: '0 14px',
                      border: 'none', borderBottom: win.type === tab.type ? '2px solid #3b82f6' : '2px solid transparent',
                      background: 'transparent', cursor: 'pointer', fontSize: 12,
                      fontWeight: win.type === tab.type ? 600 : 400,
                      color: win.type === tab.type ? '#3b82f6' : '#666',
                      transition: 'color 0.15s',
                    }}
                  >
                    {tab.icon}{tab.label}
                  </button>
                ))}
              </div>
              <div style={{ flex: 1, overflow: 'auto' }}>
                {win.type === 'file-content' ? (
                  <FileContentViewer path={win.params.path} />
                ) : (
                  <div style={{ padding: 16 }}>
                    <VersionTimeline
                      path={win.params.path}
                      onSelectVersion={(_v) => {}}
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
        <div style={{ position: 'absolute', left: 16, top: 20, zIndex: 1, display: 'flex', flexDirection: 'column', gap: 8 }}>
          {[
            { icon: <FolderTree size={28} />, label: 'File Explorer', action: () => openWindow('file-tree', 'File Explorer') },
            { icon: <Search size={28} />, label: 'Search', action: () => openWindow('file-search', 'Search Files') },
            { icon: <ShieldAlert size={28} />, label: 'Security', action: () => openWindow('security-audit', 'Security Audit') },
            { icon: <FileSignature size={28} />, label: 'E-Consent', action: () => openWindow('consent', 'E-Consent') },
            { icon: <Settings size={28} />, label: 'Settings', action: () => openWindow('settings', 'Settings') },
          ].map(({ icon, label, action }) => (
            <button
              key={label}
              onClick={action}
              style={{
                display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.12)',
                borderRadius: 12, padding: '10px 8px', cursor: 'pointer', width: 72,
                color: 'white', backdropFilter: 'blur(8px)',
                transition: 'background 0.15s, transform 0.1s',
              }}
              onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = 'rgba(255,255,255,0.18)'; (e.currentTarget as HTMLButtonElement).style.transform = 'scale(1.05)'; }}
              onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'rgba(255,255,255,0.08)'; (e.currentTarget as HTMLButtonElement).style.transform = 'scale(1)'; }}
            >
              {icon}
              <span style={{ fontSize: 10, fontWeight: 500, textAlign: 'center', lineHeight: 1.2, textShadow: '0 1px 3px rgba(0,0,0,0.6)' }}>{label}</span>
            </button>
          ))}
        </div>

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

const THREAT_CONFIG: Record<string, { color: string; bg: string; border: string; icon: React.ReactNode }> = {
  CRITICAL: { color: '#cf1322', bg: '#fff1f0', border: '#ffa39e', icon: <XCircle size={14} color="#cf1322" /> },
  WARNING:  { color: '#ad6800', bg: '#fffbe6', border: '#ffe58f', icon: <AlertTriangle size={14} color="#ad6800" /> },
  SAFE:     { color: '#237804', bg: '#f6ffed', border: '#b7eb8f', icon: <CheckCircle size={14} color="#237804" /> },
};

const ThreatBadge: React.FC<{ level: string }> = ({ level }) => {
  const cfg = THREAT_CONFIG[level] ?? { color: '#555', bg: '#f0f0f0', border: '#ccc', icon: null };
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: '2px 10px', borderRadius: 20,
      background: cfg.bg, border: `1px solid ${cfg.border}`,
      color: cfg.color, fontWeight: 700, fontSize: 11, letterSpacing: 0.5,
    }}>
      {cfg.icon}{level}
    </span>
  );
};

const textareaStyle: React.CSSProperties = {
  width: '100%', fontFamily: 'monospace', fontSize: 11, boxSizing: 'border-box',
  border: '1px solid #d9d9d9', borderRadius: 6, padding: '6px 8px',
  resize: 'vertical', outline: 'none', background: '#fafafa', lineHeight: 1.5,
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
    const scoreColor = apk ? (apk.total_score >= 70 ? '#cf1322' : apk.total_score >= 40 ? '#faad14' : '#52c41a') : '#3b82f6';

    return (
        <div style={{ padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 12, height: '100%', overflow: 'auto' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <ShieldAlert size={18} color="#3b82f6" />
                    <Typography.Title level={5} style={{ margin: 0, fontSize: 14 }}>Security Audit</Typography.Title>
                </div>
                <Button
                    type="primary"
                    icon={<ShieldAlert size={13} />}
                    onClick={run}
                    loading={loading}
                    size="small"
                    style={{ borderRadius: 6, fontSize: 12 }}
                >
                    Run Audit
                </Button>
            </div>

            {/* Tabs */}
            <div style={{ display: 'flex', borderBottom: '1px solid #e8e8e8' }}>
                {([['apk', 'APK Analysis'], ['pi', 'PI Document Scan']] as const).map(([t, label]) => (
                    <button
                        key={t}
                        onClick={() => setActiveTab(t)}
                        style={{
                            height: 32, padding: '0 14px', border: 'none', background: 'transparent', cursor: 'pointer',
                            fontSize: 12, fontWeight: activeTab === t ? 600 : 400,
                            color: activeTab === t ? '#3b82f6' : '#666',
                            borderBottom: activeTab === t ? '2px solid #3b82f6' : '2px solid transparent',
                        }}
                    >
                        {label}
                    </button>
                ))}
            </div>

            {activeTab === 'apk' ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    <div>
                        <label style={{ fontSize: 11, color: '#888', fontWeight: 500, display: 'block', marginBottom: 4 }}>APK Manifest XML</label>
                        <textarea value={manifest} onChange={e => setManifest(e.target.value)} rows={5} style={textareaStyle} />
                    </div>
                    <div>
                        <label style={{ fontSize: 11, color: '#888', fontWeight: 500, display: 'block', marginBottom: 4 }}>String Resources XML</label>
                        <textarea value={strings} onChange={e => setStrings(e.target.value)} rows={4} style={textareaStyle} />
                    </div>
                    {apk && (
                        <div style={{ border: `1px solid ${THREAT_CONFIG[apk.threat_level]?.border ?? '#d9d9d9'}`, borderRadius: 8, overflow: 'hidden' }}>
                            {/* Score header */}
                            <div style={{ padding: '10px 14px', background: THREAT_CONFIG[apk.threat_level]?.bg ?? '#fff', borderBottom: '1px solid #f0f0f0', display: 'flex', alignItems: 'center', gap: 12 }}>
                                <ThreatBadge level={apk.threat_level} />
                                <div style={{ flex: 1 }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                                        <span style={{ fontSize: 11, color: '#666' }}>Threat Score</span>
                                        <span style={{ fontSize: 11, fontWeight: 700, color: scoreColor }}>{apk.total_score}/100</span>
                                    </div>
                                    <Progress percent={apk.total_score} showInfo={false} strokeColor={scoreColor} size="small" style={{ margin: 0 }} />
                                </div>
                            </div>
                            {/* Score breakdown */}
                            <div style={{ padding: '8px 14px', background: '#fff', display: 'flex', gap: 16, borderBottom: '1px solid #f5f5f5' }}>
                                <span style={{ fontSize: 11, color: '#555' }}>Permissions <b style={{ color: '#cf1322' }}>+{apk.score_breakdown.permission_score}</b></span>
                                <span style={{ fontSize: 11, color: '#555' }}>URLs <b style={{ color: '#ad6800' }}>+{apk.score_breakdown.url_score}</b></span>
                            </div>
                            <div style={{ padding: '6px 14px', background: '#fff', fontSize: 11, color: '#666' }}>{apk.summary}</div>
                            {/* Permission findings */}
                            {apk.permission_findings.length > 0 && (
                                <div style={{ padding: '8px 14px', background: '#fff5f5', borderTop: '1px solid #fff1f0' }}>
                                    <div style={{ fontSize: 11, fontWeight: 600, color: '#cf1322', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 4 }}>
                                        <Lock size={12} />DANGEROUS PERMISSIONS
                                    </div>
                                    {apk.permission_findings.map((f, i) => (
                                        <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 6, marginBottom: 4, fontSize: 11 }}>
                                            <span style={{ background: '#ff4d4f', color: 'white', borderRadius: 4, padding: '0 5px', fontSize: 10, fontWeight: 700, flexShrink: 0 }}>+{f.score}</span>
                                            <div>
                                                <code style={{ fontSize: 10, color: '#cf1322', background: '#fff0f0', padding: '0 4px', borderRadius: 3 }}>{f.permission}</code>
                                                <div style={{ color: '#888', marginTop: 2 }}>{f.reason}</div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                            {/* URL findings */}
                            {apk.url_findings.length > 0 && (
                                <div style={{ padding: '8px 14px', background: '#fffcf0', borderTop: '1px solid #fff7e6' }}>
                                    <div style={{ fontSize: 11, fontWeight: 600, color: '#ad6800', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 4 }}>
                                        <Link size={12} />SUSPICIOUS URLs
                                    </div>
                                    {apk.url_findings.map((f, i) => (
                                        <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 6, marginBottom: 4, fontSize: 11 }}>
                                            <span style={{ background: '#faad14', color: 'white', borderRadius: 4, padding: '0 5px', fontSize: 10, fontWeight: 700, flexShrink: 0 }}>+{f.score}</span>
                                            <code style={{ fontSize: 10, color: '#ad6800', background: '#fffbe6', padding: '0 4px', borderRadius: 3, wordBreak: 'break-all' }}>{f.url}</code>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    <div>
                        <label style={{ fontSize: 11, color: '#888', fontWeight: 500, display: 'block', marginBottom: 4 }}>Document Text</label>
                        <textarea value={docText} onChange={e => setDocText(e.target.value)} rows={5} style={{ ...textareaStyle, fontFamily: 'inherit', fontSize: 12 }} />
                    </div>
                    {pi && (
                        <div style={{ border: `1px solid ${THREAT_CONFIG[pi.risk]?.border ?? '#d9d9d9'}`, borderRadius: 8, overflow: 'hidden' }}>
                            <div style={{ padding: '10px 14px', background: THREAT_CONFIG[pi.risk]?.bg ?? '#fff', display: 'flex', alignItems: 'center', gap: 12 }}>
                                <ThreatBadge level={pi.risk} />
                                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12 }}>
                                    <Lock size={13} color="#3b82f6" />
                                    <span style={{ color: '#555' }}>Encryption:</span>
                                    <b style={{ color: '#1d4ed8' }}>{pi.encryption}</b>
                                </div>
                            </div>
                            {pi.details.length > 0 && (
                                <div style={{ padding: '8px 14px', background: '#fff' }}>
                                    {pi.details.map((d, i) => (
                                        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#cf1322', marginBottom: 4 }}>
                                            <AlertTriangle size={12} />{d}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

const FormInput: React.FC<{ label: string; value: string; onChange: (v: string) => void; placeholder?: string }> = ({ label, value, onChange, placeholder }) => (
    <div>
        <label style={{ fontSize: 11, color: '#888', fontWeight: 500, display: 'block', marginBottom: 4 }}>{label}</label>
        <input
            value={value}
            onChange={e => onChange(e.target.value)}
            placeholder={placeholder}
            style={{
                width: '100%', padding: '6px 10px', fontSize: 12, boxSizing: 'border-box',
                border: '1px solid #d9d9d9', borderRadius: 6, outline: 'none', background: '#fafafa',
                transition: 'border-color 0.15s',
            }}
            onFocus={e => { e.target.style.borderColor = '#3b82f6'; }}
            onBlur={e => { e.target.style.borderColor = '#d9d9d9'; }}
        />
    </div>
);

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

    const verified = result?.integrity === 'VERIFIED';

    return (
        <div style={{ padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 12, height: '100%', overflow: 'auto' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <FileSignature size={18} color="#3b82f6" />
                <Typography.Title level={5} style={{ margin: 0, fontSize: 14 }}>NFT E-Consent</Typography.Title>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <FormInput label="Teacher ID" value={form.teacher_id} onChange={v => setForm(f => ({ ...f, teacher_id: v }))} />
                <FormInput label="Parent ID" value={form.parent_id} onChange={v => setForm(f => ({ ...f, parent_id: v }))} />
                <div style={{ gridColumn: '1 / -1' }}>
                    <FormInput label="Form Title" value={form.title} onChange={v => setForm(f => ({ ...f, title: v }))} />
                </div>
                <div style={{ gridColumn: '1 / -1' }}>
                    <label style={{ fontSize: 11, color: '#888', fontWeight: 500, display: 'block', marginBottom: 4 }}>
                        Biometric Signature <span style={{ color: '#bbb' }}>(comma-separated floats, &gt;5 values = VERIFIED)</span>
                    </label>
                    <input
                        value={form.signature}
                        onChange={e => setForm(f => ({ ...f, signature: e.target.value }))}
                        style={{ width: '100%', padding: '6px 10px', fontSize: 12, boxSizing: 'border-box', border: '1px solid #d9d9d9', borderRadius: 6, outline: 'none', background: '#fafafa', fontFamily: 'monospace' }}
                    />
                </div>
            </div>

            <Button type="primary" onClick={submit} loading={loading} style={{ borderRadius: 6, alignSelf: 'flex-start' }}>
                Sign Consent
            </Button>

            {error && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 12px', background: '#fff1f0', border: '1px solid #ffa39e', borderRadius: 6, fontSize: 12, color: '#cf1322' }}>
                    <XCircle size={13} />{error}
                </div>
            )}

            {result && (
                <div style={{ border: `1px solid ${verified ? '#b7eb8f' : '#ffe58f'}`, borderRadius: 8, overflow: 'hidden' }}>
                    <div style={{ padding: '10px 14px', background: verified ? '#f6ffed' : '#fffbe6', display: 'flex', alignItems: 'center', gap: 10, borderBottom: '1px solid #f0f0f0' }}>
                        {verified ? <CheckCircle size={16} color="#52c41a" /> : <AlertTriangle size={16} color="#faad14" />}
                        <span style={{ fontWeight: 700, fontSize: 13, color: verified ? '#237804' : '#ad6800' }}>{result.integrity}</span>
                        <span style={{ fontSize: 11, color: '#888', marginLeft: 4 }}>NFT ID: <code style={{ fontSize: 10, background: '#f0f0f0', padding: '0 4px', borderRadius: 3 }}>{result.nft_id}</code></span>
                    </div>
                    <div style={{ padding: '10px 14px', background: '#fff', display: 'flex', flexDirection: 'column', gap: 4 }}>
                        <div style={{ fontSize: 12 }}><span style={{ color: '#888' }}>Status:</span> <b>{result.block.data.status}</b></div>
                        <div style={{ fontSize: 12 }}><span style={{ color: '#888' }}>Owner:</span> <b>{result.block.data.owner}</b></div>
                        <div style={{ marginTop: 6, fontFamily: 'monospace', fontSize: 10, color: '#aaa', wordBreak: 'break-all', background: '#fafafa', padding: '6px 8px', borderRadius: 4 }}>
                            {result.block.block_hash}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Desktop;
