/**
 * VersionTimeline — lists all recorded versions for a file.
 * Clicking a version triggers onSelectVersion so the parent can show the diff.
 */
import { useEffect, useState } from "react";
import { getVersion } from "../api.ts";

type Version = {
    version: number;
    timestamp: number;
    summary: string;
    change_type: string;
};

export function VersionTimeline({
    path,
    onSelectVersion,
}: {
    path: string;
    onSelectVersion: (v: number) => void;
}) {
    const [versions, setVersions] = useState<Version[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        setLoading(true);
        setError(null);
        getVersion(path)
            .then(setVersions)
            .catch(() => setError("Failed to load versions"))
            .finally(() => setLoading(false));
    }, [path]);

    return (
        <div style={{ marginBottom: 16 }}>
            <h3 style={{ margin: '0 0 8px 0' }}>Versions</h3>
            {loading && <p style={{ fontSize: '12px', color: '#888' }}>Loading…</p>}
            {error && <p style={{ fontSize: '12px', color: '#d44' }}>{error}</p>}
            {!loading && !error && versions.length === 0 && (
                <p style={{ fontSize: '12px', color: '#aaa' }}>No versions recorded yet.</p>
            )}
            <ul style={{ margin: 0, paddingLeft: '16px' }}>
                {versions.map((v) => (
                    <li
                        key={v.version}
                        style={{ cursor: "pointer", fontSize: '13px', marginBottom: '4px' }}
                        onClick={() => onSelectVersion(v.version)}
                    >
                        <strong>v{v.version}</strong>
                        {' · '}
                        <span style={{ color: '#555' }}>{v.summary}</span>
                        {' · '}
                        <span style={{ fontSize: '11px', color: '#888' }}>
                            {new Date(v.timestamp * 1000).toLocaleTimeString()}
                        </span>
                    </li>
                ))}
            </ul>
        </div>
    );
}
