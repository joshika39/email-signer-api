from pathlib import Path
from fastapi import FastAPI
import sys
import os
import uvicorn  

path_root = Path(__file__).parents[1]
email_path = os.path.join(path_root, 'email')

sys.path.append(os.path.join(path_root))
sys.path.append(email_path)

from routes import router

app = FastAPI(
    title="Email Integrity Verification",
    description="This API is used to verify the integrity of an email address.",
    version="1.0.0"
)

app.include_router(router)

if __name__ == "__main__":
    from fastapi import FastAPI
    uvicorn.run(app, host="0.0.0.0", port=1234)
