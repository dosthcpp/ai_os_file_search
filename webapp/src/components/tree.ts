export interface TreeNode {
    name: string;
    path: string;
    type: "file" | "directory";
    children?: TreeNode[];
}

interface FileChangeEvent {
    type: "file-changed";
    action: "created" | "modified" | "deleted";
    path: string;
    node?: TreeNode; // created일 때만
}

const splitPath = (path: string) =>
    path.replace(/^\/+/, "").split("/");

const cloneNode = (node: TreeNode): TreeNode => ({
    ...node,
    children: node.children ? [...node.children] : undefined,
});

function applyRecursively(
    nodes: TreeNode[],
    segments: string[],
    event: FileChangeEvent,
    depth: number
): TreeNode[] {
    return nodes.map((node) => {
        if (node.name !== segments[depth]) {
            return node;
        }

        const cloned = cloneNode(node);

        // 마지막 segment = 파일 자체
        if (depth === segments.length - 1) {
            if (event.action === "deleted") {
                return null as any; // 나중에 filter
            }

            if (event.action === "modified") {
                // 보통 트리 구조 변화 없음 → 그대로
                return cloned;
            }
        }

        // 중간 디렉토리
        if (cloned.children) {
            cloned.children = applyRecursively(
                cloned.children,
                segments,
                event,
                depth + 1
            ).filter(Boolean);
        }

        return cloned;
    })
        .filter(Boolean)
        .flatMap((node) => {
            // created 처리: 부모 디렉토리에서 추가
            if (
                event.action === "created" &&
                depth === segments.length - 2 &&
                node.name === segments[depth]
            ) {
                if (!node.children) node.children = [];

                const exists = node.children.some(
                    (c) => c.name === segments[segments.length - 1]
                );

                if (!exists && event.node) {
                    node.children.push(event.node);
                }
            }

            return [node];
        });
}


export function applyFileChange(
    tree: TreeNode[],
    event: FileChangeEvent
): TreeNode[] {
    const segments = splitPath(event.path);

    return applyRecursively(tree, segments, event, 0);
}
