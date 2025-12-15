import { useState } from "react";
import FileTree from "./components/FileTree";
import DiffViewer from "./components/DiffViewer";
import { fetchDiff } from "./api";

export default function App() {
    const [original, setOriginal] = useState("");
    const [modified, setModified] = useState("");

    const handleSelectFile = async (path: string) => {
        const res = await fetchDiff(path);

        setOriginal(res.old_text ?? "");
        setModified(res.new_text ?? "");
    };

    return (
        <div style={{ display: "flex", height: "100vh", width: "100vw" }}>
            <div style={{ width: "30%", borderRight: "1px solid #ddd" }}>
                <FileTree onSelectFile={handleSelectFile} />
            </div>

            <div style={{ flex: 1 }}>
                <DiffViewer original={original} modified={modified} />
            </div>
        </div>
    );

}
