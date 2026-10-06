"""Vercel entrypoint for supported counties."""

from fastapi import FastAPI

from api.index import counties

app = FastAPI()


@app.get("/")
@app.get("/api/counties")
def root():
    return counties()
