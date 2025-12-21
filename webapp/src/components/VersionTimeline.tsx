import {useEffect, useState} from "react";
import {getVersion} from "../api.ts";

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

    useEffect(() => {
        getVersion(path)
            // .then((r) => r.json())
            .then(setVersions);
    }, [path]);

    return (
        <div style={{ marginBottom: 16 }}>
            <h3>Versions</h3>
            <ul>
                {versions.map((v) => (
                    <li
                        key={v.version}
                        style={{ cursor: "pointer" }}
                        onClick={() => onSelectVersion(v.version)}
                    >
                        v{v.version} · {v.summary}
                    </li>
                ))}
            </ul>
        </div>
    );
}
