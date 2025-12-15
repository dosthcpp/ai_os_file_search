import axios from "axios";

const api = axios.create({
    baseURL: "http://localhost:8000", // server 주소
});

export const fetchFileTree = async () => {
    const res = await api.get("/api/changed-files/tree");
    return res.data;
};

export const fetchDiff = async (path: string) => {
    const res = await api.get("/api/diff", {
        params: { path },
    });
    return res.data;
};
