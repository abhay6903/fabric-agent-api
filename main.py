from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware  # For Power BI
from pydantic import BaseModel
from fabric_agent import FabricChat

app = FastAPI(title="Fabric Data Agent API")

# CORS for Power BI (allows requests from app.powerbi.com)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.powerbi.com", "https://*.powerbi.com", "*"],  # "*" for dev; restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent instance (singleton for thread persistence)
agent = FabricChat()

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    try:
        response = agent.ask(request.message)
        return {"response": response, "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)