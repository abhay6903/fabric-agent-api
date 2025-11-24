import os
import time
import uuid
import warnings
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

warnings.filterwarnings("ignore", category=DeprecationWarning)

app = FastAPI(title="Fabric Data Agent API - Power BI Ready")

# Allow Power BI to call us
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.powerbi.com", "https://*.powerbi.com", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Only one env var needed on Render
DATA_AGENT_URL = os.getenv(
    "DATA_AGENT_URL",
    "https://api.fabric.microsoft.com/v1/workspaces/008fae24-7bf2-4a88-b2c9-900aeed5811a/aiskills/b3c3405b-feab-45b9-910d-db208419969d/aiassistant/openai"
)

class ChatRequest(BaseModel):
    userQuery: str
    context: str | None = None
    userId: str | None = None
    access_token: str

@app.post("/chat")
async def chat(request: ChatRequest):
    if not request.userQuery.strip():
        raise HTTPException(status_code=400, detail="Empty message")

    try:
        # Create OpenAI client using the user's token from Power BI
        client = OpenAI(
            api_key="dummy",
            base_url=DATA_AGENT_URL,
            default_query={"api-version": "2024-05-01-preview"},
            default_headers={
                "Authorization": f"Bearer {request.access_token}",
                "ActivityId": str(uuid.uuid4())
            }
        )

        # Optional: Use context from Power BI data role
        query = request.userQuery
        if request.context:
            query = f"Context: {request.context}\n\nQuestion: {query}"

        # Fresh thread per request
        thread = client.beta.threads.create()
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=query
        )

        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=client.beta.assistants.create(model="not used").id
        )

        print(f"User {request.userId or 'unknown'} asked: {query}")
        while run.status in ["queued", "in_progress"]:
            time.sleep(1.5)
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

        messages = client.beta.threads.messages.list(thread_id=thread.id)
        assistant_msg = next((m for m in messages.data if m.role == "assistant"), None)
        
        if not assistant_msg:
            raise ValueError("No response from agent")

        response_text = assistant_msg.content[0].text.value.strip()

        return {"response": response_text}

    except Exception as e:
        print("ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"status": "ok", "message": "Fabric Data Agent API is running"}