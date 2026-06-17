# Taglish Disinformation Detection System

This repository contains the full source code for the Taglish Disinformation Detection System.

## 📂 Project Structure

- **`/admin-dashboard`**: The administrative control panel (React + Vite). Used to monitor predictions, model performance, and logs.
- **`/backend-api`**: The FastAPI server and AI engine. Handles text preprocessing, feature extraction, and disinformation prediction.
- **`/chrome-extension`**: The browser-side tool (React + Vite). Injects high-visibility scan buttons directly into social media posts.
- **`/docs`**: Project documentation, including the Software Design Document (SDD).

## 🚀 Getting Started

### 1. Start the Backend (The Brain)
Open a terminal in `/backend-api` and run:
```powershell
.\venv\Scripts\python.exe -m uvicorn src.app:app --port 8000
```

### 2. Start the Dashboard (The Control Panel)
Open a terminal in `/admin-dashboard` and run:
```powershell
npm run dev
```

### 3. Deploy the Extension (The Tool)
1. Build the extension: `cd chrome-extension; npm run build`
2. Open Chrome and go to `chrome://extensions/`
3. Click **"Load unpacked"** and select the `/chrome-extension/dist` folder.

## 🔑 Admin Credentials
- **Username:** `admin`
- **Password:** `admin123`
