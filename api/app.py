from fastapi import FastAPI

app = FastAPI()

#Invoke-RestMethod -Uri "http://localhost:8002" -Method GET (windows power shell)
@app.get("/")
def index():
    return {"Hello" : "World"}
