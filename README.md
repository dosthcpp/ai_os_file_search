AI_OS 프로젝트

1. config.json 위치 변경
2. python3 -m venv .venv
3. source .venv/bin/activate / .venv\Scripts\activate
4. pip install -r indexer/requirements.txt
5. cd webapp && yarn
6. uvicorn server.main:app --reload --port 8000 && python indexer.py
