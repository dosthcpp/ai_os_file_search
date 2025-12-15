import {Tree} from "antd";
import type {DataNode} from "antd/es/tree";
import {useEffect, useRef, useState} from "react";
import {applyFileChange} from "./tree.ts";

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

    // useEffect(() => {
    //     fetchFileTree().then((data) => {
    //         setTreeData(data.children.map(convertToTree));
    //     });
    // }, []);

    const wsRef = useRef<WebSocket | null>(null);

    useEffect(() => {
        if (wsRef.current) return; // StrictMode 2회 방지

        const ws = new WebSocket("ws://127.0.0.1:8000/ws/file-tree");
        wsRef.current = ws;

        ws.onopen = () => console.log("ws open");
        ws.onclose = () => console.log("ws close");
        ws.onerror = (e) => console.log("ws error", e);

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

        return () => {
            // StrictMode “가짜 언마운트”에서 close 되지 않게 하려면 아래 라인을 주석 처리해도 됨(개발중).
            ws.close();
            wsRef.current = null;
        };
    }, []);

    return (
        <Tree
            treeData={treeData}
            onSelect={(keys) => {
                if (keys.length > 0) {
                    onSelectFile(keys[0] as string);
                }
            }}
        />
    );
}
