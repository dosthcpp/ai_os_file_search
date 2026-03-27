import DiffViewer from "./DiffViewer.tsx";
import FileTree from "./FileTree.tsx";
import { useState } from "react";
import { VersionTimeline } from "./VersionTimeline.tsx";
import WatchPathSettings from "./WatchPathSettings.tsx";
import SearchPanel from "./SearchPanel.tsx";
import { Divider } from "antd";

export default function FileExplorer() {
    const [selectedPath, setSelectedPath] = useState<string | null>(null);
    const [selectedVersion, setSelectedVersion] = useState<number | null>(null);

    return (
        <div style={{ display: "flex", height: "100vh" }}>
            {/* Left panel: settings, search, and file tree */}
            <div style={{ width: '30vw', borderRight: "1px solid #ddd", padding: '8px', overflowY: 'auto' }}>
                <WatchPathSettings />
                <Divider style={{ margin: '8px 0' }} />
                <SearchPanel onSelectFile={(path) => {
                    setSelectedPath(path);
                    setSelectedVersion(null);
                }} />
                <Divider style={{ margin: '8px 0' }} />
                <FileTree
                    onSelectFile={(path) => {
                        setSelectedPath(path);
                        setSelectedVersion(null); // reset version when file changes
                    }}
                />
            </div>

            {/* Right panel: version timeline and diff viewer */}
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
