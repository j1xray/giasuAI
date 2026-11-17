from fastapi import FastAPI
from pydantic import BaseModel
import google.generativeai as genai
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()

# Cho phép Frontend (Next.js) gọi API từ domain khác
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cấu hình API Key
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-3.5-flash-lite')

class ChatRequest(BaseModel):
    prompt: str

@app.post("/api/chat")
async def chat(req: ChatRequest):
    try:
        response = model.generate_content(req.prompt)
        return {"answer": response.text}
    except Exception as e:
        return {"error": str(e)}

@app.get("/")
def health_check():
    return "AI Backend is running!"
