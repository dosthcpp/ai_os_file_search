import { useState } from "react";
import { Divider } from "antd";
import DiffViewer from "./DiffViewer.tsx";
import FileContentViewer from "./FileContentViewer.tsx";
import FileTree from "./FileTree.tsx";
import { VersionTimeline } from "./VersionTimeline.tsx";
import WatchPathSettings from "./WatchPathSettings.tsx";
import SearchBar from "./SearchBar.tsx";

type RightPanel = "content" | "diff";

export default function FileExplorer() {
    const [selectedPath, setSelectedPath] = useState<string | null>(null);
    const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
    const [rightPanel, setRightPanel] = useState<RightPanel>("content");

    const selectFile = (path: string) => {
        setSelectedPath(path);
        setSelectedVersion(null);
        setRightPanel("content");
    };

    return (
        <div style={{ display: "flex", height: "100vh" }}>
            {/* Left sidebar */}
            <div style={{
                width: '30vw',
                borderRight: "1px solid #ddd",
                padding: '8px 12px',
                overflowY: 'auto',
                display: 'flex',
                flexDirection: 'column',
                gap: 0,
            }}>
                <WatchPathSettings />
                <Divider style={{ margin: '8px 0' }} />
                <SearchBar onSelectFile={selectFile} />
                <Divider style={{ margin: '8px 0' }} />
                <FileTree onSelectFile={selectFile} />
            </div>

            {/* Right panel */}
            <div style={{ flex: 1, padding: 16, overflowY: 'auto' }}>
                {selectedPath ? (
                    <>
                        {/* Tab bar */}
                        <div style={{ display: 'flex', gap: 0, marginBottom: 12, borderBottom: '1px solid #e2e8f0' }}>
                            {(["content", "diff"] as RightPanel[]).map(tab => (
                                <button
                                    key={tab}
                                    onClick={() => setRightPanel(tab)}
                                    style={{
                                        padding: '6px 16px',
                                        border: 'none',
                                        borderBottom: rightPanel === tab ? '2px solid #6366f1' : '2px solid transparent',
                                        background: 'none',
                                        cursor: 'pointer',
                                        fontWeight: rightPanel === tab ? 600 : 400,
                                        color: rightPanel === tab ? '#6366f1' : '#555',
                                        fontSize: 13,
                                        textTransform: 'capitalize',
                                    }}
                                >
                                    {tab === "content" ? "File Content" : "Version History"}
                                </button>
                            ))}
                        </div>

                        {rightPanel === "content" && (
                            <FileContentViewer path={selectedPath} />
                        )}

                        {rightPanel === "diff" && (
                            <>
                                <VersionTimeline
                                    path={selectedPath}
                                    onSelectVersion={(v) => {
                                        setSelectedVersion(v);
                                    }}
                                />
                                {selectedVersion !== null && (
                                    <DiffViewer
                                        path={selectedPath}
                                        version={selectedVersion}
                                    />
                                )}
                            </>
                        )}
                    </>
                ) : (
                    <div style={{ color: '#aaa', marginTop: 48, textAlign: 'center', fontSize: 14 }}>
                        Select a file from the tree or search results to preview it.
                    </div>
                )}
            </div>
        </div>
    );
}
