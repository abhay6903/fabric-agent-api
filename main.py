# main.py → 100% WORKING VERSION (hard-coded credentials – for testing / demo)

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from azure.identity import ClientSecretCredential
import uuid
import time
import jwt

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ╔══════════════════════════════════════════════════════════╗
# ║                 YOUR HARD-CODED VALUES                   ║
# ╚══════════════════════════════════════════════════════════╝

TENANT_ID       = "b352ac0f-1307-4b50-8f5d-c9da98395387"
CLIENT_ID       = "60d900c9-1232-4a4a-8680-173c48ba5e11"
CLIENT_SECRET   = "g2p8Q~qSgrtBuuZFxMpjl_-GZpFa-gx9CwlBPaQ_"

# Your Fabric AI Skill endpoint (keep exactly this)
DATA_AGENT_URL = "https://api.fabric.microsoft.com/v1/workspaces/008fae24-7bf2-4a88-b2c9-900aeed5811a/aiskills/b3c3405b-feab-45b9-910d-db208419969d/aiassistant/openai"

# One conversation thread per user (optional but nice)
threads: dict = {}

def get_fabric_client() -> OpenAI:
    credential = ClientSecretCredential(
        tenant_id=TENANT_ID,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )
    token = credential.get_token("https://api.fabric.microsoft.com/.default")

    return OpenAI(
        api_key="anything",  # ignored
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
    if not message:
        raise HTTPException(400, "Missing message")

    # Optional: extract real user id from Power BI token (for per-user threads)
    user_id = "anonymous"
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        try:
            decoded = jwt.decode(token, options={"verify_signature": False})
            user_id = decoded.get("oid") or decoded.get("sub") or "anonymous"
        except:
            pass

    client = get_fabric_client()
    thread_id = threads.setdefault(user_id, client.beta.threads.create().id)

    # Send message
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=message
    )

    # Start run
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id="hardcoded-assistant"  # Fabric ignores this value anyway
    )

    # Poll until done
    while run.status in ["queued", "in_progress", "requires_action"]:
        time.sleep(1.1)
        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)

    if run.status == "failed":
        raise HTTPException(500, f"Fabric run failed: {run.last_error}")

    # Get latest assistant message
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    response = next(
        (m.content[0].text.value for m in messages.data if m.role == "assistant"),
        "No response from Fabric AI."
    )

    return {"response": response}

@app.get("/")
def root():
    return {"message": "Fabric AI Proxy is LIVE – POST to /chat with {'message': 'hello'}"}

@app.get("/health")
def health():
    return {"status": "ok", "version": "hardcoded-working-2025"}