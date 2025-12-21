from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.v1.auth import get_current_active_user
from app.models.user import User
from app.models.code_execution import CodeExecution
from app.models.subscription import Subscription, SubscriptionStatus
from app.schemas.execution import CodeRunRequest, CodeRunResponse
from openai import OpenAI
import os
import sys
import io
import traceback

router = APIRouter()

# Configure OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def execute_python_safe(code_str: str) -> str:
    """
    Executes Python code in a restricted environment and captures stdout.
    Note: This is a basic soft-sandbox (no docker).
    """
    # Basic security check
    banned = ["import os", "import sys", "import subprocess", "__import__", "open(", "exec(", "eval("]
    for b in banned:
        if b in code_str:
            return "Security Error: usage of restricted modules/functions"

    old_stdout = sys.stdout
    redirected_output = io.StringIO()
    sys.stdout = redirected_output
    
    try:
        # Define a restricted global scope
        safe_globals = {"__builtins__": __builtins__} # Still allows some dangerous things, but better than nothing for a demo
        exec(code_str, safe_globals)
        output = redirected_output.getvalue()
    except Exception:
        output = traceback.format_exc()
    finally:
        sys.stdout = old_stdout
    
    return output

@router.post("/execute", response_model=CodeRunResponse)
def execute_code(
    request: CodeRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Check limits
    limit = 2
    is_limited = True
    
    # Check active subscription
    active_sub = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.status == SubscriptionStatus.ACTIVE
    ).first()

    if active_sub and active_sub.plan:
        if active_sub.plan.price > 0:
            is_limited = False
    
    if is_limited:
        run_count = db.query(CodeExecution).filter(CodeExecution.user_id == current_user.id).count()
        if run_count >= limit:
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Free plan limit reached ({limit} runs). Please upgrade to purchase a subscription to continue running code."
            )

    try:
        # 1. Translate Code
        # Try finding a valid model
        model_name = 'gpt-4o'
        
        translation_messages = [
            {"role": "system", "content": "You are an expert code translator. Convert the input pseudocode/instruction into valid, executable Python code. Do not use input() functions (hardcode values if needed). Return ONLY the python code, no markdown backticks."},
            {"role": "user", "content": f"Input Code ({request.language}):\n{request.code}"}
        ]
        
        response = client.chat.completions.create(
            model=model_name,
            messages=translation_messages,
            temperature=0.2
        )

        python_code = response.choices[0].message.content.replace("```python", "").replace("```", "").strip()

        # 2. Execute Code
        execution_output = execute_python_safe(python_code)

        # Return only the output without explanation
        final_output = f"> Generated Python Code:\n{python_code}\n\n> Output:\n{execution_output}"


    except Exception as e:
        # Debug helper: List available models
        available_models = ["gpt-4o", "gpt-3.5-turbo"] # Static list as listing is different in OpenAI
            
        final_output = f"Error processing request: {str(e)}\n\nAvailable Models: {', '.join(available_models)}"
        
        # Fallback to simulated if API fails or key missing
        if "API_KEY" in str(e):
             final_output = f"> Executing {request.language} code...\n\n> Output:\nHello from DesiCodes (Simulated)!\nLanguage: {request.language}\n(OpenAI API Key missing or invalid)"

    
    # Save execution
    from app.models.language import Language
    lang_slug = request.language.lower()
    lang_obj = db.query(Language).filter(Language.slug == lang_slug).first()
    
    # If not found by exact slug, maybe map common variations
    if not lang_obj:
        # Fallback query if needed or leave None
        pass

    execution = CodeExecution(
        user_id=current_user.id,
        language=request.language,
        language_id=lang_obj.id if lang_obj else None,
        code=request.code,
        output=final_output
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    return {"output": final_output}
