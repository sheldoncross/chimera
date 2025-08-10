from fastapi import FastAPI
from api import endpoints

app = FastAPI(title="Data Ingestion Service")

app.include_router(endpoints.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Data Ingestion Service is running"}