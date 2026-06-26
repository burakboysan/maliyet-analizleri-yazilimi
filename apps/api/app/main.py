from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.settings import get_allowed_origin_regex, get_allowed_origins
from app.routers import admin, auth, fixed_costs, health, leave, materials, mobile_compat, modules, products, selection_wizard


app = FastAPI(
    title="Bomaksan Maliyet API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_origin_regex=get_allowed_origin_regex(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(mobile_compat.router)
app.include_router(modules.router)
app.include_router(leave.router)
app.include_router(materials.router)
app.include_router(products.router)
app.include_router(admin.router)
app.include_router(fixed_costs.router)
app.include_router(mobile_compat.tail_router)
app.include_router(selection_wizard.router)
