/**
 * FileTree — displays a live file tree via WebSocket.
 * Automatically reconnects with exponential back-off when the connection drops.
 */
import { Tree } from "antd";
import type { DataNode } from "antd/es/tree";
import { useEffect, useRef, useState, useCallback } from "react";
import { applyFileChange } from "./tree.ts";

const WS_URL = "ws://127.0.0.1:8000/ws/file-tree";
const RECONNECT_BASE_MS = 1_000;   // initial reconnect delay
const RECONNECT_MAX_MS = 30_000;   // cap reconnect delay

type Props = {
    onSelectFile: (path: string) => void;
};

function convertToTree(node: any): DataNode {
    if (node.type === "file") {
        return {
            title: `${node.name} (${node.status})`,
            key: node.path,
            isLeaf: true,
        };
    }
    return {
        title: node.name,
        key: node.name,
        children: node.children?.map(convertToTree),
    };
}

export default function FileTree({ onSelectFile }: Props) {
    const [treeData, setTreeData] = useState<DataNode[]>([]);
    const [connected, setConnected] = useState(false);

    const wsRef = useRef<WebSocket | null>(null);
    const retryDelayRef = useRef(RECONNECT_BASE_MS);
    const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const unmountedRef = useRef(false);

    const connect = useCallback(() => {
        if (unmountedRef.current) return;

        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
            console.log("[ws] connected");
            setConnected(true);
            retryDelayRef.current = RECONNECT_BASE_MS; // reset back-off on success
        };

        ws.onclose = () => {
            console.log("[ws] closed — reconnecting in", retryDelayRef.current, "ms");
            setConnected(false);
            wsRef.current = null;
            if (!unmountedRef.current) {
                // Exponential back-off with a cap
                retryTimerRef.current = setTimeout(() => {
                    retryDelayRef.current = Math.min(retryDelayRef.current * 2, RECONNECT_MAX_MS);
                    connect();
                }, retryDelayRef.current);
            }
        };

        ws.onerror = (e) => console.warn("[ws] error", e);

        ws.onmessage = (e) => {
            const data = JSON.parse(e.data);
            if (data.type === "ping") return;
            if (data.type === "file-changed") {
                setTreeData((prev) => applyFileChange(prev, data));
            }
            if (data.type === "tree") {
                setTreeData(data.tree.children.map(convertToTree));
            }
        };
    }, []);

    useEffect(() => {
        unmountedRef.current = false;
        connect();
        return () => {
            unmountedRef.current = true;
            if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
            wsRef.current?.close();
            wsRef.current = null;
        };
    }, [connect]);

    return (
        <div>
            {!connected && (
                <p style={{ fontSize: '10px', color: '#aaa', margin: '0 0 4px 0' }}>
                    Connecting…
                </p>
            )}
            <Tree
                treeData={treeData}
                onSelect={(keys) => {
                    if (keys.length > 0) onSelectFile(keys[0] as string);
                }}
            />
        </div>
    );
}
