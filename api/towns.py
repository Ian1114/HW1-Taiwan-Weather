"""Vercel entrypoint for township forecasts."""

from fastapi import FastAPI, Response

from api.index import towns

app = FastAPI()


@app.get("/")
@app.get("/api/towns")
def root(response: Response, county: str = "臺中市"):
    return towns(response, county)
