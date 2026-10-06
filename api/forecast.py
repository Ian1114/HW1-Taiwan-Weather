"""Vercel entrypoint for the forecast endpoint."""

from fastapi import FastAPI, Response

from api.index import forecast

app = FastAPI()


@app.get("/")
@app.get("/api/forecast")
def root(response: Response):
    return forecast(response)
