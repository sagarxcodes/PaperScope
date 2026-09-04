from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import random
import string

router = APIRouter(
    prefix="/api",
    tags=["Authentication"],
)

USERS = {}


class RegisterRequest(BaseModel):
    name: str
    email: str
    phone: str
    background: str
    learningGoal: str


class LoginRequest(BaseModel):
    email: str
    pin: str


def generate_pin():
    return ''.join(random.choices(string.digits, k=6))


@router.post("/register")
def register(request: RegisterRequest):
    email = request.email.lower().strip()

    pin = generate_pin()

    while any(user["pin"] == pin for user in USERS.values()):
        pin = generate_pin()

    user = {
        "name": request.name,
        "email": email,
        "phone": request.phone,
        "background": request.background,
        "learningGoal": request.learningGoal,
    }

    USERS[email] = {
        **user,
        "pin": pin,
    }

    return {
        "success": True,
        "message": "Learning profile created successfully.",
        "user": user,
        "pin": pin,
    }


@router.post("/login")
def login(request: LoginRequest):
    email = request.email.lower().strip()

    user = USERS.get(email)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="No learning profile found for this email.",
        )

    if user["pin"] != request.pin:
        raise HTTPException(
            status_code=401,
            detail="Invalid PIN.",
        )

    return {
        "success": True,
        "message": "Login successful.",
        "user": {
            "name": user["name"],
            "email": user["email"],
            "phone": user["phone"],
            "background": user["background"],
            "learningGoal": user["learningGoal"],
        },
    }
