# main.py  →  FINAL VERSION (real user identity + Microsoft login popup)

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from azure.identity import OnBehalfOfCredential
from openai import OpenAI
import uuid
import time
import os
import jwt

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Environment variables (set in Render dashboard)
TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("BACKEND_CLIENT_ID")
CLIENT_SECRET = os.getenv("BACKEND_CLIENT_SECRET")
DATA_AGENT_URL = "https://api.fabric.microsoft.com/v1/workspaces/008fae24-7bf2-4a88-b2c9-900aeed5811a/aiskills/b3c3405b-feab-45b9-910d-db208419969d/aiassistant/openai"
# Store one conversation thread per real user
threads: dict = {}

def get_fabric_client(user_token: str) -> OpenAI:
    cred = OnBehalfOfCredential(
        tenant_id=TENANT_ID,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        user_assertion=user_token
    )
    token = cred.get_token("https://api.fabric.microsoft.com/.default")
    return OpenAI(
        api_key="x",
        base_url=DATA_AGENT_URL,
        default_query={"api-version": "2024-05-01-preview"},
        default_headers={
            "Authorization": f"Bearer {token.token}",
            "ActivityId": str(uuid.uuid4())
        }
    )

@app.post("/chat")
async def chat(request: Request):
    body = await request.json()
    message = body.get("message", "").strip()
    auth_header = request.headers.get("Authorization", "")
    user_token = auth_header.replace("Bearer ", "").strip()

    if not message or not user_token:
        raise HTTPException(400, "Missing message or token")

    # Get user ID from Power BI token
    try:
        decoded = jwt.decode(user_token, options={"verify_signature": False})
        user_id = decoded.get("oid") or decoded.get("sub")
    except:
        raise HTTPException(401, "Invalid token")

    client = get_fabric_client(user_token)
    thread_id = threads.setdefault(user_id, client.beta.threads.create().id)

    # Send message & run
    client.beta.threads.messages.create(thread_id=thread_id, role="user", content=message)
    run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=str(uuid.uuid4()))

    while run.status in ["queued", "in_progress"]:
        time.sleep(1.2)
        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)

    messages = client.beta.threads.messages.list(thread_id=thread_id)
    response = next(
        (m.content[0].text.value for m in messages.data if m.role == "assistant"),
        "Sorry, no response."
    )

    return {"response": response}

@app.get("/")
async def root():
    return {"message": "Fabric AI Proxy is running – POST to /chat"}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "fabric-ai-proxy"}