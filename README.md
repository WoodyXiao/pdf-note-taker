## PDF Note Taker

A simple full-stack project for uploading PDFs and taking notes, built with a **Django REST API** backend and a **React + Vite** frontend.

---

### Project Structure

- `backend/`: Django REST API (authentication, file upload, AI-related endpoints, etc.)
- `frontend/`: React + Vite SPA that talks to the backend.

---

### How to run the backend (Django + Celery + Redis)

1. Go to the backend folder:

   ```bash
   cd backend
   ```

2. Create and activate a virtual environment (recommended):

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Make sure PostgreSQL is running (with the `vector` extension enabled for pgvector) and the database in `core/settings.py` / `.env` exists, then run migrations:

   ```bash
   python manage.py migrate
   ```

5. (Recommended) Create a `.env` file in `backend/` for local secrets:

   ```bash
   # backend/.env
   DJANGO_SECRET_KEY=change_me
   DJANGO_DEBUG=true

   POSTGRES_DB=pdf_note_taker
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=your_password
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432

   # Google Generative AI
   NEXT_PUBLIC_GEMINI_API_KEY=your_gemini_api_key
   GEMINI_CHAT_MODEL=gemini-flash-latest

   # Celery / Redis
   CELERY_BROKER_URL=redis://localhost:6379/0
   CELERY_RESULT_BACKEND=redis://localhost:6379/0
   ```

6. Start Redis (for Celery). On macOS with Homebrew:

   ```bash
   brew services start redis
   ```

7. Start a Celery worker (in a separate terminal, with the venv activated):

   ```bash
   cd backend
   source .venv/bin/activate
   celery -A core worker -l info
   ```

8. Start the Django development server (in another terminal, with the venv activated):

   ```bash
   python manage.py runserver 8000
   ```

The backend will be available at `http://127.0.0.1:8000/`.

---

### How to run the frontend (Vite + React)

1. Go to the frontend folder:

   ```bash
   cd frontend
   ```

2. Install Node dependencies:

   ```bash
   npm install
   ```

3. Start the dev server:

   ```bash
   npm run dev
   ```

Vite will show you a local URL (usually `http://localhost:5173`) where you can access the app.


