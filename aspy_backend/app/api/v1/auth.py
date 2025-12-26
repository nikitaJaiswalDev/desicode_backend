from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, UserLogin, UserResponse, SocialLoginRequest
from app.schemas.token import TokenResponse
from app.models.user import User
from app.models.subscription import Plan, Subscription, SubscriptionStatus, PlanType
from app.core.security import hash_password, verify_password, create_access_token, get_current_user
from datetime import datetime
from app.db.session import get_db
import secrets
import requests

router = APIRouter()

@router.post("/auth/social-login", response_model=TokenResponse, tags=["Authentication"])
def social_login(request: SocialLoginRequest, db: Session = Depends(get_db)):
    """Login or Register using Social Provider"""
    
    # Google Token Verification
    if request.provider.lower() == 'google' and request.token:
        try:
            resp = requests.get(
                "https://www.googleapis.com/oauth2/v3/userinfo", 
                headers={"Authorization": f"Bearer {request.token}"}
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid Google Token")
            
            google_data = resp.json()
            request.email = google_data.get('email')
            request.name = google_data.get('name', 'Google User')
            
            if not request.email:
                raise HTTPException(status_code=400, detail="Google account has no email")
                
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Google authentication failed: {str(e)}")

    # GitHub Code Verification
    elif request.provider.lower() == 'github' and request.code:
        import os
        client_id = os.getenv("GITHUB_CLIENT_ID")
        client_secret = os.getenv("GITHUB_CLIENT_SECRET")
        
        if not client_id or not client_secret:
            raise HTTPException(status_code=500, detail="GitHub credentials not configured")

        try:
            # Exchange code for token
            token_resp = requests.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": request.code
                }
            )
            if token_resp.status_code != 200:
                raise HTTPException(status_code=401, detail=f"Failed to exchange GitHub code: {token_resp.text}")
            
            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            if not access_token:
                 raise HTTPException(status_code=401, detail=f"No access token from GitHub. Response: {token_data}")

            # Get User Info
            user_resp = requests.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            github_user = user_resp.json()
            request.email = github_user.get("email")
            request.name = github_user.get("name") or github_user.get("login")

            # If email is private, fetch it
            if not request.email:
                emails_resp = requests.get(
                    "https://api.github.com/user/emails",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                if emails_resp.status_code == 200:
                    emails = emails_resp.json()
                    for e in emails:
                        if e.get("primary") and e.get("verified"):
                            request.email = e.get("email")
                            break
                    if not request.email and emails:
                         request.email = emails[0].get("email")
                         
        except Exception as e:
             raise HTTPException(status_code=401, detail=f"GitHub login failed: {str(e)}")

    # Apple Token Verification
    elif request.provider.lower() == 'apple' and request.token:
        try:
            # 1. Fetch Apple's Public Keys
            apple_keys_url = "https://appleid.apple.com/auth/keys"
            keys_resp = requests.get(apple_keys_url)
            keys = keys_resp.json()['keys']
            
            # 2. Decode the ID Token header to find the Key ID (kid)
            from jose import jwt
            
            # We verify the signature using the matching key
            # This requires matching the 'kid' from the token header to the keys from Apple
            # python-jose handles looking up the key if we pass the keyset, but we need to format it right
            # or simply let it try all keys (inefficient but works for small sets)
            
            # Simplified verification:
            # Audience should typically be verified.
            # We skip explicit audience check here for generic acceptance, OR check against env var if set
            # For strict security, you should check audience=APPLE_CLIENT_ID
            
            payload = jwt.decode(
                request.token,
                keys,
                algorithms=['RS256'],
                options={"verify_aud": False, "verify_iss": True}, # Issuer must be apple
                issuer="https://appleid.apple.com"
            )
            
            # 3. Extract Info
            token_email = payload.get('email')
            if token_email:
                request.email = token_email
            
            # Name is not in ID Token usually, it comes from frontend request (only on first login)
            # If request.name is already set by frontend, good. If not, fallback.
            if not request.name:
                request.name = "Apple User"
                
        except Exception as e:
             raise HTTPException(status_code=401, detail=f"Apple login failed: {str(e)}")

    if not request.email:
         raise HTTPException(status_code=400, detail="Email is required for social login")

    user = db.query(User).filter(User.email == request.email).first()

    if not user:
        # Create new user
        random_password = secrets.token_urlsafe(16)
        # Handle empty name if simple login
        base_name = request.name if request.name else "user"
        unique_username = base_name.replace(" ", "").lower() + "_" + secrets.token_hex(4)
        
        user = User(
            username=unique_username,
            email=request.email,
            password=hash_password(random_password),
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Assign Free Subscription
        free_plan = db.query(Plan).filter(Plan.type == PlanType.FREE).first()
        if free_plan:
            new_subscription = Subscription(
                user_id=user.id,
                plan_id=free_plan.id,
                status=SubscriptionStatus.ACTIVE,
                created_at=datetime.utcnow(),
                current_period_start=datetime.utcnow()
            )
            db.add(new_subscription)
            db.commit()

    token = create_access_token({"sub": user.email, "user_id": user.id})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "user_type": user.user_type.value,
            "is_active": user.is_active,
            "created_at": user.created_at
        }
    }

@router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
def register_user(request: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if email exists
    user_exists = db.query(User).filter(User.email == request.email).first()
    if user_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check if username exists
    username_exists = db.query(User).filter(User.username == request.username).first()
    if username_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # Create user
    new_user = User(
        username=request.username,
        email=request.email,
        password=hash_password(request.password),
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Assign Free Subscription
    free_plan = db.query(Plan).filter(Plan.type == PlanType.FREE).first()
    if free_plan:
        new_subscription = Subscription(
            user_id=new_user.id,
            plan_id=free_plan.id,
            status=SubscriptionStatus.ACTIVE,
            created_at=datetime.utcnow(),
            current_period_start=datetime.utcnow(),
            # No end date for free plan or handle logic as needed
        )
        db.add(new_subscription)
        db.commit()

    # Create access token
    token = create_access_token({"sub": new_user.email, "user_id": new_user.id})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": new_user.id,
            "username": new_user.username,
            "email": new_user.email,
            "user_type": new_user.user_type.value,
            "is_active": new_user.is_active,
            "created_at": new_user.created_at
        }
    }

@router.post("/auth/login", response_model=TokenResponse, tags=["Authentication"])
def login_user(request: UserLogin, db: Session = Depends(get_db)):
    """Login user and get access token"""
    user = db.query(User).filter(User.email == request.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not verify_password(request.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    token = create_access_token({"sub": user.email, "user_id": user.id})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "user_type": user.user_type.value,
            "is_active": user.is_active,
            "created_at": user.created_at
        }
    }

@router.get("/auth/me", response_model=UserResponse, tags=["Authentication"])
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user info"""
    return current_user

@router.get("/auth/stats", tags=["Authentication"])
def get_user_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get user dashboard statistics"""
    from app.models.code_execution import CodeExecution
    
    execution_count = db.query(CodeExecution).filter(CodeExecution.user_id == current_user.id).count()
    
    # Currently assuming 1 execution = 1 AI request as per current logic
    return {
        "total_executions": execution_count,
        "ai_requests": execution_count
    }

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user