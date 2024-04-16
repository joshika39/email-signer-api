from pathlib import Path
from fastapi import FastAPI
import sys
import os
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from starlette.staticfiles import StaticFiles

path_root = Path(__file__).parents[1]
email_path = os.path.join(path_root, 'email')

sys.path.append(os.path.join(path_root))
sys.path.append(email_path)

from routes import router

description = """

This API is used to verify the integrity of an email address.

## How does it work?

The tool uses RSA encryption to sign the email message and then verify the signature. 
The sender's public key is used to verify the signature. The public key is sent to the recipient in the email message. 
The recipient can then use the public key to verify the signature.

When the sender first sends an email a private key is generated 
and used to sign every email that is sent by the given email address.
The public key can be retrieved by sending a GET request to the /key 
endpoint with the email address as a query parameter.

## Who is this for?

This tool was created for the [Ablaze](https://ablaze.one) team to be as professional as possible when sending emails.

## How to use

"""


app = FastAPI(
    title="Email Integrity Verification",
    description=description,
    version="1.0.0",
    docs_url=None
)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/docs", include_in_schema=False)
async def get_docs():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Documentation (Email Integrity Verification)",
        swagger_favicon_url="/static/favicon.ico"
    )

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    from fastapi import FastAPI
    uvicorn.run(app, host="0.0.0.0", port=1234)
