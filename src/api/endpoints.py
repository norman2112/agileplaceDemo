from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from src.services.user_service import update_user_profile
from src.models.user import UserProfile
from pydantic import BaseModel

app = FastAPI(
    title="Incident Auto-Resolution System",
    description="Automatically resolves high-confidence incidents with comprehensive auditing",
    version="1.0.0"
)

class UserLogin(BaseModel):
    email: str
    password: str

@app.post("/api/v1/auth/login", tags=["Auth"])
async def login(user_login: UserLogin):
    # Mock authentication, to be implemented
    if user_login.email == "test@example.com" and user_login.password == "password":
        return {"access_token": "dummy_token", "token_type": "bearer"}
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.put("/api/v1/user/profile", response_model=UserProfile, tags=["User"])
async def update_profile(user_id: str, profile: UserProfile, service=Depends(update_user_profile)):
    if user_id != profile.user_id:
        raise HTTPException(status_code=400, detail="User ID mismatch")
    return await service(user_id, profile)
