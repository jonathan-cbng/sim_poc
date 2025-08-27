from fastapi import FastAPI

from src.ap_routes import ap_router

app = FastAPI()
app.include_router(ap_router)
