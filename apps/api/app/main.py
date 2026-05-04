from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, health, leave, materials, modules, products, selection_wizard


app = FastAPI(
    title="Bomaksan Maliyet API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5180",
        "http://127.0.0.1:5180",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(modules.router)
app.include_router(leave.router)
app.include_router(materials.router)
app.include_router(products.router)
app.include_router(selection_wizard.router)
