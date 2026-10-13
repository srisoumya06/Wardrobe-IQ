# Wardrobe IQ 👗

> **Your Closet, Smarter Everyday**

Wardrobe IQ is a smart wardrobe-management and fashion-assistance web application built with Python Flask. It helps users organize clothing items digitally, plan outfits from their own wardrobe, track clothing availability, and explore personalized styling and wardrobe insights.

**Project status:** Under development. Feature availability depends on the current implementation and the configuration of any external APIs.

## ✨ Features

- **Dashboard:** View wardrobe summaries, item counts, usage information, and wardrobe insights based on recorded data.
- **Digital Closet:** Add and organize clothing items with details such as category, colour, brand, size, price, and images.
- **Laundry & Availability:** Track whether items are available, worn, or in the laundry, where supported by the current implementation.
- **Smart Outfit Studio:** Explore outfit combinations using items in your wardrobe, with outfit selection and favourites where implemented.
- **Calendar & Outfit Memories:** Review recorded outfit history, where the relevant features are implemented.
- **AI Fashion Lab:** Fashion-analysis and styling suggestions when the required AI integration is configured.
- **AI Fashion Assistant:** A conversational fashion helper when the configured AI service is available.
- **Shopping Companion:** Explore potential wardrobe gaps and shopping suggestions, subject to the available product data/integrations.
- **Live Fashion Trends:** Browse trend information when a reliable source or API is configured.
- **Pack Your Bags:** Create trip-oriented packing suggestions from wardrobe items, where implemented.
- **Fashion Points:** Track supported activities and progress, where implemented.

**Note:** The list describes the project's intended capabilities. Check the running application and configuration to confirm which features are currently available.

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend** | Python, Flask |
| **Frontend** | HTML, CSS, JavaScript, Jinja2 templates |
| **Database** | SQLite and SQLAlchemy (according to the project configuration) |
| **Authentication** | Flask-Login (if enabled in the current configuration) |
| **Charts** | Chart.js (where used) |
| **Image Handling** | Pillow (where used) |
| **AI Integration** | Gemini API, if configured and used by the application |
| **Deployment Target** | Render |

## 📁 Project Structure

The exact structure may change as development continues. The repository currently follows a Flask application layout similar to:

```text
WardrobeIQ/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── models.py
│   ├── routes/
│   ├── services/
│   ├── templates/
│   └── static/
├── tests/
├── requirements.txt
├── run.py
├── seed_demo.py
├── .env.example
├── .gitignore
└── README.md
```

## 🚀 Run Locally

### 1. Prerequisites

Install:
- **Python 3.11** or another version supported by the project's dependencies
- **Git** (optional, for cloning the repository)

### 2. Clone the Repository

```bash
git clone https://github.com/srisoumya06/Wardrobe-IQ.git
cd Wardrobe-IQ
```

### 3. Create and Activate a Virtual Environment

**Windows (PowerShell):**

```bash
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use **Command Prompt**:

```bash
.venv\Scripts\activate.bat
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Install Dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Create a local `.env` file based on `.env.example` if the project uses `python-dotenv` or another environment loader.

Example variable names (use only the ones your application actually reads):

```env
SECRET_KEY=replace-with-a-long-random-secret
GEMINI_API_KEY=your-gemini-api-key
```

Add any other required variables documented by the application's configuration.

**Important:** Never commit `.env` or paste API keys into GitHub, screenshots, or public messages. Keep `.env` excluded in `.gitignore`. Do not copy real secrets into this README.

### 6. Start the Application

```bash
python run.py
```

Open the local URL printed in the terminal (often [http://127.0.0.1:5000](http://127.0.0.1:5000)).

**Important:** If the application fails to start, review the terminal error and verify that the environment variables, database configuration, and dependencies are correct.

## 🌐 Deployment (Render)

Wardrobe IQ can be deployed as a Web Service on Render.

Typical settings for this repository are:

| Setting | Value |
| :--- | :--- |
| **Repository** | [https://github.com/srisoumya06/Wardrobe-IQ](https://github.com/srisoumya06/Wardrobe-IQ) |
| **Root Directory** | Leave blank if `requirements.txt` and `run.py` are in the repository root. |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn run:app` — use this only if `run.py` exposes the Flask application as `app` and `gunicorn` is included in `requirements.txt`. |

Configure required environment variables in Render's Environment settings. Do not commit or publish secrets.

### Database and Uploaded Files

**Important:** SQLite databases and files saved on a hosting instance may not persist across restarts or redeployments unless persistent storage is configured. Before using the hosted app with important data, configure an appropriate persistent disk/database and upload-storage strategy. A hosted persistent disk may require a paid plan; check the hosting provider's current limits and pricing.

## 🔐 Security and Privacy

- Never commit `.env`, API tokens, passwords, or other credentials.
- Use a strong, randomly generated `SECRET_KEY`.
- If a secret was exposed, revoke or rotate it with the provider and update the deployment environment.
- Do not commit personal photos or private user uploads to a public repository.
- Validate uploaded file types and sizes and enforce user-level access controls.
- Use production-safe settings for deployment; do not expose Flask debug mode publicly.

## 🧪 Tests

If tests are included in the repository, run them from the project root:

```bash
python -m pytest
```

If `pytest` is not installed or the project uses a different test runner, follow the project's test configuration.

## 🔧 Troubleshooting

- **ModuleNotFoundError:** Activate the correct virtual environment and install `requirements.txt`.
- **Application fails to start on Render:** Check the build and runtime logs, the start command, and whether all required packages are listed in `requirements.txt`.
- **AI feature unavailable:** Confirm that the application reads the correct environment-variable name and that the API key is valid and has the required access.
- **Database or upload data disappears:** Check the database path and configure persistent storage for the deployed service.
- **Images do not appear:** Check upload paths, static-file URLs, permissions, and whether uploaded files are stored in persistent storage.

## 🎯 Project Goal

Wardrobe IQ aims to make everyday dressing more organized and practical by connecting a digital closet with outfit suggestions, clothing availability, wardrobe insights, and trip packing assistance.

## 👩‍💻 Repository

- [Wardrobe IQ on GitHub](https://github.com/srisoumya06/Wardrobe-IQ)
