# AegisAI — FAQ & Troubleshooting

Common issues and their fixes for setting up and running AegisAI.

---

## 1. Backend fails to start immediately after cloning

**Problem:** Running `uvicorn app.main:app --reload` crashes on startup.

**Cause:** Missing or incomplete `.env` file in the `backend/` directory.

**Fix:**
```bash
cd backend
cp .env.example .env
```
Then open `.env` and set at minimum:
- `SECRET_KEY` — any random 32-character string
- `LLM_API_KEY` — your OpenAI key, or `ollama` if using Ollama

---

## 2. `LLM_API_KEY` error when using Ollama (free, no key)

**Problem:** RAG queries fail with an authentication error even though
you are using Ollama locally.

**Cause:** `LLM_API_KEY` is not set to the special Ollama value.

**Fix:** In `backend/.env`, set:
LLM_API_KEY=ollama LLM_BASE_URL=http://localhost:11434/v1LLM_MODEL=llama3.2

Make sure Ollama is running and the model is pulled:
```bash
ollama pull llama3.2
```

---

## 3. PostgreSQL connection refused on startup

**Problem:** Backend logs show `connection refused` for the database.

**Cause:** PostgreSQL is not running, or Docker Compose was not started.

**Fix (Docker users):**
```bash
docker compose up -d
```
**Fix (manual setup):** Start your local PostgreSQL service and ensure
`DATABASE_URL` in `backend/.env` matches your local credentials.

---

## 4. Frontend shows a blank page or API errors in the browser

**Problem:** Visiting `http://localhost:5173` shows a blank screen or
every API call fails.

**Cause:** The backend is not running, or `VITE_API_URL` is not set.

**Fix:**
1. Make sure the backend is running on port `8000`.
2. In `frontend/`, check that `VITE_API_URL=http://localhost:8000` is set
   (create a `.env` file in `frontend/` if it doesn't exist).

---

## 5. `pip install` fails with a Python version error

**Problem:** Installing `requirements.txt` throws compatibility errors.

**Cause:** AegisAI requires **Python 3.11 or higher**. Earlier versions
are not supported.

**Fix:** Check your Python version:
```bash
python --version
```
If below 3.11, download Python 3.11+ from https://python.org and
recreate your virtual environment.

---

## 6. Docker Compose port conflict on startup

**Problem:** `docker compose up -d` fails with "port is already in use."

**Cause:** Another service is already using port `5173`, `8000`, or `5432`.

**Fix:** Either stop the conflicting service, or override the ports in
`docker-compose.override.yml`:
```yaml
services:
  frontend:
    ports:
      - "5174:5173"
  backend:
    ports:
      - "8001:8000"
```

---

> Still stuck? Open a [Discussion](https://github.com/SdSarthak/AegisAI/discussions)
> or search existing [Issues](https://github.com/SdSarthak/AegisAI/issues).
