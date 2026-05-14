# Confusion Network Translation Demo

This repository contains a local demo application for exploring translation confusion networks.  
It includes a FastAPI backend and a React + Vite frontend.

## Running the app locally

### 1. Clone the repository

```bash
git clone https://github.com/RobinHenrik/thesis-cn-app
cd thesis-cn-app
```

### 2. Start the backend

Open a terminal in the `backend` folder:

```bash
cd backend
```

Create and activate a Python virtual environment:
Python 3.9 is recommended, since the backend depends on Pynini and this version is known to work.
```bash
python3.9 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the backend:

```bash
uvicorn api:app --reload
```

The backend will run at:

```text
http://127.0.0.1:8000
```

### 3. Start the frontend

Open a second terminal in the `frontend` folder:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Create a `.env` file inside `frontend/` with:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Start the frontend:

```bash
npm run dev
```

Open the local Vite URL shown in the terminal, usually:

```text
http://localhost:5173
```

## Usage

1. Choose a source sentence.
2. Choose one of the candidate translations.
3. Click a word to inspect one-word and phrase alternatives.
4. Apply an alternative to update the translation.
5. Use the slider to highlight low-probability words.

## Notes

- If installing `pynini` fails, it may be easier to use a Conda/Miniforge environment instead of `venv`.
