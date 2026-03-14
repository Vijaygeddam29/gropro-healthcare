# FastAPI main entrypoint
from fastapi import FastAPI

app = FastAPI()

@app.get('/')
def home():
    return {'message': 'GroPro MVP'}