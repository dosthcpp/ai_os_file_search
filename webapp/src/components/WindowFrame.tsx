import React, { useRef } from 'react';
import Draggable from 'react-draggable';
import { Card, Button, Space, Typography } from 'antd';
import { Minus, Square, X, Maximize2, Minimize2 } from 'lucide-react';
import { useOSStore, WindowInstance } from '../store';

const { Text } = Typography;

interface WindowProps {
  window: WindowInstance;
  children: React.ReactNode;
}

const WindowFrame: React.FC<WindowProps> = ({ window, children }) => {
  const nodeRef = useRef(null);
  const { closeWindow, minimizeWindow, maximizeWindow, focusWindow } = useOSStore();

  if (window.isMinimized) return null;

  const style: React.CSSProperties = {
    position: 'absolute',
    left: '50px',
    top: '50px',
    zIndex: window.zIndex,
    width: window.isMaximized ? '100vw' : '800px',
    height: window.isMaximized ? 'calc(100vh - 48px)' : '600px',
    maxWidth: '100vw',
    maxHeight: 'calc(100vh - 48px)',
    display: 'flex',
    flexDirection: 'column',
    boxShadow: '0 10px 25px rgba(0,0,0,0.2)',
    borderRadius: window.isMaximized ? 0 : '8px',
    overflow: 'hidden',
    transition: 'all 0.2s ease-out',
    ...(window.isMaximized ? { left: 0, top: 0 } : {}),
  };

  return (
    <Draggable
      nodeRef={nodeRef}
      handle=".window-header"
      disabled={window.isMaximized}
      onStart={() => focusWindow(window.id)}
    >
      <div ref={nodeRef} style={style} onClick={() => focusWindow(window.id)}>
        <Card
          size="small"
          styles={{
            header: {
              background: '#f0f2f5',
              borderBottom: '1px solid #d9d9d9',
              padding: '0 12px',
              cursor: window.isMaximized ? 'default' : 'move',
            },
            body: {
              padding: 0,
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
              background: '#fff',
            },
          }}
          className="window-header"
          title={
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Text strong style={{ fontSize: '13px' }}>{window.title}</Text>
            </div>
          }
          extra={
            <Space size={4}>
              <Button
                type="text"
                size="small"
                icon={<Minus size={14} />}
                onClick={(e) => {
                  e.stopPropagation();
                  minimizeWindow(window.id);
                }}
              />
              <Button
                type="text"
                size="small"
                icon={window.isMaximized ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
                onClick={(e) => {
                  e.stopPropagation();
                  maximizeWindow(window.id);
                }}
              />
              <Button
                type="text"
                size="small"
                danger
                icon={<X size={14} />}
                onClick={(e) => {
                  e.stopPropagation();
                  closeWindow(window.id);
                }}
              />
            </Space>
          }
          style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
        >
          <div style={{ flex: 1, overflow: 'auto', position: 'relative' }}>
            {children}
          </div>
        </Card>
      </div>
    </Draggable>
  );
};

export default WindowFrame;
