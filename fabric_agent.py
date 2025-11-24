import uuid
import time
import warnings
from azure.identity import InteractiveBrowserCredential
from openai import OpenAI

warnings.filterwarnings("ignore", category=DeprecationWarning)

TENANT_ID = "b352ac0f-1307-4b50-8f5d-c9da98395387"
DATA_AGENT_URL = "https://api.fabric.microsoft.com/v1/workspaces/008fae24-7bf2-4a88-b2c9-900aeed5811a/aiskills/b3c3405b-feab-45b9-910d-db208419969d/aiassistant/openai"

class FabricChat:
    def __init__(self):
        print("Authenticating...")  # Log for backend
        self.cred = InteractiveBrowserCredential(tenant_id=TENANT_ID)
        token = self.cred.get_token("https://api.fabric.microsoft.com/.default")
        
        self.client = OpenAI(
            api_key="x",
            base_url=DATA_AGENT_URL,
            default_query={"api-version": "2024-05-01-preview"},
            default_headers={
                "Authorization": f"Bearer {token.token}",
                "ActivityId": str(uuid.uuid4())
            }
        )
        # Persistent thread for conversation context
        self.thread = self.client.beta.threads.create()

    def ask(self, question: str) -> str:
        self.client.beta.threads.messages.create(
            thread_id=self.thread.id, role="user", content=question
        )
        run = self.client.beta.threads.runs.create(
            thread_id=self.thread.id,
            assistant_id=self.client.beta.assistants.create(model="not used").id
        )
        print("Thinking", end="")  # Log
        while run.status in ["queued", "in_progress"]:
            time.sleep(1.5)
            print(".", end="")
            run = self.client.beta.threads.runs.retrieve(thread_id=self.thread.id, run_id=run.id)
        print()
        
        messages = self.client.beta.threads.messages.list(thread_id=self.thread.id)
        assistant_msg = next((m for m in messages.data if m.role == "assistant"), None)
        return assistant_msg.content[0].text.value.strip() if assistant_msg else "No response."