## PDF Note Taker

A simple full-stack project for uploading PDFs and taking notes, built with a **Django REST API** backend and a **React + Vite** frontend.

---

### Project Structure

- `backend/`: Django REST API (authentication, file upload, AI-related endpoints, etc.)
- `frontend/`: React + Vite SPA that talks to the backend.

---

### How to run the backend (Django)

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

4. Make sure PostgreSQL is running and the database in `core/settings.py` / `.env` exists, then run migrations:

   ```bash
   python manage.py migrate
   ```

5. Start the Django development server:

   ```bash
   python manage.py runserver
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


