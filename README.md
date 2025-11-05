# VisAI Assistant

An end-to-end assistant to extract structured data from travel documents, auto-fill visa forms, verify, and persist workflows.

## Stack
- Frontend: React + Tailwind (React Query, Axios)
- Backend: FastAPI (Pydantic, Uvicorn)
- OCR: pytesseract (optional: Google Vision)
- DB: PostgreSQL (SQLAlchemy planned)
- Infra: Docker / Docker Compose

## Quick start (backend)
```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --port 8000
```

## Docker Compose
```bash
docker compose up --build
```

## Environment
Create a `.env` file in the project root or export environment variables. See `backend/ENV.example.txt` for a ready-made list of keys.

## License
MIT


