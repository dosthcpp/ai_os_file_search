import DiffViewer from "./DiffViewer.tsx";
import FileTree from "./FileTree.tsx";
import {useState} from "react";
import {VersionTimeline} from "./VersionTimeline.tsx";
import WatchPathSettings from "./WatchPathSettings.tsx";
import SearchBar from "./SearchBar.tsx";
import {Divider} from "antd";

export default function FileExplorer() {
    const [selectedPath, setSelectedPath] = useState<string | null>(null);
    const [selectedVersion, setSelectedVersion] = useState<number | null>(null);

    return (
        <div style={{ display: "flex", height: "100vh" }}>
            {/* 좌측 트리 */}
            <div style={{ width: '30vw', borderRight: "1px solid #ddd", padding: '8px 12px', overflowY: 'auto' }}>
                <WatchPathSettings />
                <Divider />
                <SearchBar onSelectFile={(path) => {
                    setSelectedPath(path);
                    setSelectedVersion(null);
                }} />
                <Divider />
                <FileTree
                    onSelectFile={(path) => {
                        setSelectedPath(path);
                        setSelectedVersion(null);
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
