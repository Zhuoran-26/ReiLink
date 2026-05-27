# ReiLink Backend

FastAPI local service for game detection, persona prompts, dialogue, local knowledge, mock voice, and JSONL conversation memory.

## Run

```bash
cd services/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Test

```bash
PYTHONPATH=services/backend pytest services/backend/tests
```

