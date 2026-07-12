# AI-First CRM HCP Module

AI-first Healthcare Professional (HCP) CRM module focused on the **Log Interaction Screen** for field representatives. The screen supports both a structured form and a conversational chat workflow backed by a FastAPI service, LangGraph agent, Groq LLM integration, and SQL database persistence.

## What This Project Includes

- React UI with Redux Toolkit state management
- Structured interaction logging form
- Conversational chat interface for natural-language interaction logging
- Python FastAPI backend
- LangGraph agent using Groq `gemma2-9b-it`
- Six sales-focused LangGraph tools:
  - Log Interaction
  - Edit Interaction
  - Fetch HCP Profile
  - Suggest Next Best Action
  - Compliance Check
  - Schedule Follow-up
- SQLAlchemy database layer for PostgreSQL or MySQL
- Demo endpoint to show all tools working

## Project Structure

```text
.
├── backend
│   ├── app
│   │   ├── agent.py
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── settings.py
│   ├── .env.example
│   └── requirements.txt
├── frontend
│   ├── src
│   │   ├── App.jsx
│   │   ├── api.js
│   │   ├── main.jsx
│   │   ├── store.js
│   │   └── styles.css
│   ├── index.html
│   └── package.json
├── docker-compose.yml
└── README.md
```

## Backend Setup

1. Create a Groq API key from [Groq Console](https://console.groq.com/keys).
2. Start PostgreSQL:

```bash
docker compose up -d db
```

3. Create and activate a Python environment:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

4. Add your key in `backend/.env`:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=gemma2-9b-it
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/hcp_crm
```

5. Run FastAPI:

```bash
uvicorn app.main:app --reload --port 8000
```

Open API docs at `http://localhost:8000/docs`.

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## LangGraph Agent Role

The LangGraph agent acts as an AI orchestration layer for field representative workflows. It receives structured form submissions or conversational chat messages, identifies the representative intent, invokes the correct CRM tool, optionally uses the Groq LLM for summarization and entity extraction, validates compliance-sensitive text, and returns an auditable result to the UI.

In a real life sciences CRM, this agent would reduce manual data entry, improve field-note quality, standardize follow-up recommendations, and help representatives stay inside compliant promotional boundaries.

## LangGraph Tools

1. **Log Interaction**
   Captures HCP name, specialty, channel, products discussed, sentiment, outcome, next step, and free-text notes. The LLM summarizes the interaction and extracts useful entities such as product names, objections, and follow-up dates.

2. **Edit Interaction**
   Allows an existing logged interaction to be updated. The agent records edited values and refreshes the AI summary so the CRM keeps the latest representative notes.

3. **Fetch HCP Profile**
   Retrieves HCP context such as specialty, segment, affiliation, preferred channel, and recent interaction history.

4. **Suggest Next Best Action**
   Generates a sales-oriented recommendation based on HCP profile, interaction sentiment, product interest, and next-step intent.

5. **Compliance Check**
   Reviews notes for risk phrases such as off-label promotion, guaranteed outcomes, adverse-event mentions, or pricing claims.

6. **Schedule Follow-up**
   Creates a follow-up recommendation with date, channel, topic, and priority.




