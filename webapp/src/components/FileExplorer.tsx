import DiffViewer from "./DiffViewer.tsx";
import FileTree from "./FileTree.tsx";
import {useState} from "react";
import {VersionTimeline} from "./VersionTimeline.tsx";
import WatchPathSettings from "./WatchPathSettings.tsx";
import {Divider} from "antd";

export default function FileExplorer() {
    const [selectedPath, setSelectedPath] = useState<string | null>(null);
    const [selectedVersion, setSelectedVersion] = useState<number | null>(null);

    return (
        <div style={{ display: "flex", height: "100vh" }}>
            {/* 좌측 트리 */}
            <div style={{ width: '30vw', borderRight: "1px solid #ddd" }}>
                <WatchPathSettings />
                <Divider />
                <FileTree
                    onSelectFile={(path) => {
                        setSelectedPath(path);
                        setSelectedVersion(null); // 파일 바뀌면 버전 초기화
                    }}
                />
            </div>

            {/* 우측 패널 */}
            <div style={{ flex: 1, padding: 16 }}>
                {selectedPath && (
                    <>
                        <VersionTimeline
                            path={selectedPath}
                            onSelectVersion={setSelectedVersion}
                        />

                        {selectedVersion !== null && (
                            <DiffViewer
                                path={selectedPath}
                                version={selectedVersion}
                            />
                        )}
                    </>
                )}
            </div>
        </div>
    );
}
