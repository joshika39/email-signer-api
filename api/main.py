from pathlib import Path
from fastapi import FastAPI
import sys
import os

path_root = Path(__file__).parents[1]
sys.path.append(os.path.join(path_root))

from api import routes


app = FastAPI(
    title="Email Integrity Verification",
    description="This API is used to verify the integrity of an email address.",
    version="1.0.0"
)

app.include_router(routes.router)