import { useEffect, useState } from 'react';
import { getWatchPaths, addWatchPath } from '../api.ts';

export default function WatchPathSettings() {
    const [paths, setPaths] = useState<string[]>([]);
    const [tempPath, setTempPath] = useState<string>('');

    const load = async () => {
        const data = await getWatchPaths();
        setPaths(data);
    };

    const onChange = async (newPath: string) => {
        setTempPath(newPath);
    };

    const onAdd = async () => {
        if (!tempPath.trim()) return;
        if (paths.includes(tempPath)) {
            alert('이미 등록된 경로입니다');
            return;
        }

        const {ok} = await addWatchPath(tempPath.trim());
        if (ok) load().then();
        else alert('유효한 디렉토리가 아닙니다.');
    };

    // const handleSelectFolder = async () => {
    //     try {
    //         const dirHandle = await window.showSaveFilePicker();
    //         console.log(dirHandle);
    //         const path = dirHandle.name; // 폴더 이름만 가져옴
    //         // 또는 상대 경로 구성
    //         onAdd(path);
    //     } catch (err) {
    //         console.log('사용자가 취소함');
    //     }
    // };

    // const onRemove = async (path: string) => {
    //     if (!newPath.trim()) return;
    //     if (paths.includes(newPath)) {
    //         alert('이미 등록된 경로입니다');
    //         return;
    //     }
    //
    //     await addWatchPath(newPath.trim());
    //     setNewPath('');
    //     load().then();
    // };

    useEffect(() => {
        load().then();
    }, []);

    return (
        <div style={{
            marginBottom: '2px',
        }}>
            <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '16px'
            }}>
                <p style={{
                    fontWeight: 'bold',
                    margin: 0
                }}>감시 디렉토리 선택</p>
                <div>
                    <input
                        type="text"
                        placeholder="C:/test"
                        onChange={e => onChange(e.target.value)}
                    />
                    <button onClick={() => onAdd()}>폴더 선택</button>
                    {/*<button onClick={() => onRemove(p)}>삭제</button>*/}
                </div>
            </div>

            <ul style={{
                margin: 0
            }}>
                {paths.map(p => (
                    <li key={p}>{p}</li>
                ))}
            </ul>
        </div>
    );
}
