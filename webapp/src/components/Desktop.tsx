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
} from 'lucide-react';
import { useOSStore, WindowType } from '../store';
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
  const { windows, activeWindowId, openWindow, restoreWindow, focusWindow } = useOSStore();
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
      default:
        return <div>Unknown Window Type: {win.type}</div>;
    }
  };

  const startMenuItems = [
    { key: 'file-tree', icon: <FolderTree size={16} />, label: 'File Explorer', onClick: () => openWindow('file-tree', 'File Explorer') },
    { key: 'file-search', icon: <Search size={16} />, label: 'File Search', onClick: () => openWindow('file-search', 'Search Files') },
    { key: 'security-audit', icon: <ShieldAlert size={16} />, label: 'Security Audit', onClick: () => openWindow('security-audit', 'Security Audit') },
    { key: 'settings', icon: <Settings size={16} />, label: 'Settings', onClick: () => openWindow('settings', 'Settings') },
  ];

  return (
    <Layout style={{ height: '100vh', width: '100vw', background: '#1e293b', overflow: 'hidden', position: 'relative' }}>
      {/* Desktop Background */}
      <Content style={{ position: 'relative', height: '100%', width: '100%' }}>
        <div style={{ 
          position: 'absolute', 
          inset: 0, 
          background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
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
        default: return <Monitor size={16} />;
    }
};

const SecurityAuditWindow: React.FC = () => {
    const [auditData, setAuditData] = useState<any>(null);
    const [loading, setLoading] = useState(false);

    const runAudit = async () => {
        setLoading(true);
        try {
            const res = await fetch('/api/security/audit');
            const data = await res.json();
            setAuditData(data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{ padding: 20 }}>
            <div style={{ marginBottom: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography.Title level={4} style={{ margin: 0 }}>System Security Audit</Typography.Title>
                <Button type="primary" icon={<ShieldAlert size={16} />} onClick={runAudit} loading={loading}>
                    Run Full Audit
                </Button>
            </div>
            {auditData ? (
                <Card size="small" title="Audit Results">
                    <pre style={{ maxHeight: 400, overflow: 'auto' }}>
                        {JSON.stringify(auditData, null, 2)}
                    </pre>
                </Card>
            ) : (
                <div style={{ textAlign: 'center', padding: '40px 0', color: '#888' }}>
                    <ShieldAlert size={48} style={{ opacity: 0.2, marginBottom: 16 }} />
                    <p>Click "Run Full Audit" to scan the system for security issues.</p>
                </div>
            )}
        </div>
    );
};

export default Desktop;
