_DIFF_STORE = {}  # path → html diff

def save_diff(path: str, html: str):
    _DIFF_STORE[path] = html

def get_diff(path: str):
    return _DIFF_STORE.get(path)