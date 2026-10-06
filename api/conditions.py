"""Vercel entrypoint for weather and environmental conditions."""

from fastapi import FastAPI, Response

from api.index import conditions

app = FastAPI()


@app.get("/")
@app.get("/api/conditions")
def root(response: Response, kind: str = "rain", county: str = "臺中市"):
    return conditions(response, kind, county)
