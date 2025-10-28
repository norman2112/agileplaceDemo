from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from src.services.user_service import update_user_profile
from src.models.user import UserProfile

app = FastAPI(
    title="Incident Auto-Resolution System",
    description="Automatically resolves high-confidence incidents with comprehensive auditing",
    version="1.0.0"
)

@app.put("/api/v1/user/profile", response_model=UserProfile, tags=["User"])
async def update_profile(user_id: str, profile: UserProfile, service=Depends(update_user_profile)):
    if user_id != profile.user_id:
        raise HTTPException(status_code=400, detail="User ID mismatch")
    return await service(user_id, profile)
