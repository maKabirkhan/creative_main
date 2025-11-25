from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from routers import persona 

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],     
    allow_credentials=True,
    allow_methods=["*"],     
    allow_headers=["*"],       
)

@app.get("/")
async def home():
    return {"message": "welcome to FastAPI"}


app.include_router(persona.router, prefix="/persona", tags=["prsona"])

