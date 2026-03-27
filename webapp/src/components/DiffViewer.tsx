/**
 * DiffViewer — renders a unified diff for a specific file version.
 * Lines are colour-coded: green=added, red=removed, blue=hunk header, orange=file markers.
 */
import { useEffect, useState } from "react";
import { getVersionDiff } from "../api";

function DiffLine({ line }: { line: string }) {
    let color = "#eee";
    let bg = "transparent";

    if (line.startsWith("+") && !line.startsWith("+++")) {
        color = "#a6e22e";
        bg = "#1e2f1e";
    } else if (line.startsWith("-") && !line.startsWith("---")) {
        color = "#f92672";
        bg = "#2f1e1e";
    } else if (line.startsWith("@@")) {
        color = "#66d9ef";
        bg = "#1e1e2f";
    } else if (line.startsWith("+++") || line.startsWith("---")) {
        color = "#fd971f";
    }

    return (
        <div style={{ fontFamily: "monospace", whiteSpace: "pre-wrap", color, background: bg, padding: "2px 6px" }}>
            {line}
        </div>
    );
}

export default function DiffViewer({ path, version }: { path: string; version: number }) {
    const [diffLines, setDiffLines] = useState<string[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        setLoading(true);
        setError(null);
        getVersionDiff(path, version)
            .then((d) => {
                if (Array.isArray(d.diff)) {
                    setDiffLines(d.diff);
                } else {
                    setDiffLines(String(d.diff || "").split("\n"));
                }
            })
            .catch(() => setError("Failed to load diff"))
            .finally(() => setLoading(false));
    }, [path, version]);

    return (
        <div>
            <h3 style={{ margin: '0 0 8px 0' }}>Diff (v{version})</h3>
            {loading && <p style={{ fontSize: '12px', color: '#888' }}>Loading…</p>}
            {error && <p style={{ fontSize: '12px', color: '#d44' }}>{error}</p>}
            {!loading && !error && diffLines.length === 0 && (
                <p style={{ fontSize: '12px', color: '#aaa' }}>No diff available.</p>
            )}
            <div style={{ background: "#111", borderRadius: 6, padding: 8, maxHeight: 400, overflow: "auto" }}>
                {diffLines.map((line, i) => (
                    <DiffLine key={i} line={line} />
                ))}
            </div>
        </div>
    );
}
