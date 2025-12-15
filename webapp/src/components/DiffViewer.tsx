import { DiffEditor } from "@monaco-editor/react";

type Props = {
    original: string;
    modified: string;
};

export default function DiffViewer({ original, modified }: Props) {
    return (
        <div style={{ height: "100%", width: "100%" }}>
            <DiffEditor
                original={original}
                modified={modified}
                language="plaintext"
                theme="vs-dark"
                options={{
                    readOnly: true,
                    renderSideBySide: true,
                    minimap: { enabled: false },
                    automaticLayout: true, // 🔥 이거 중요
                }}
            />
        </div>
    );
}
