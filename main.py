from fastapi import FastAPI, Request, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, date

from schemas import Token, UserCreate, TaskCreate
from models import User, Task
from crud import get_user_by_email, create_user, create_task, get_tasks, get_history, log_action, get_tasks_by_date
import auth
from database import engine, Base


Base.metadata.create_all(bind=engine)
app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


# Токен
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(auth.get_db)):
    user = get_user_by_email(db, form_data.username)
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Неверный логин или пароль.",
                            headers={"WWW-Authenticate": "Bearer"})
    access_token = auth.create_access_token(data={"sub": str(user.id)},
                                            expires_delta=timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": access_token, "token_type": "bearer"}


# Регистрация пользователя
@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
def register_action(request: Request,
                    name: str = Form(...),
                    email: str = Form(...),
                    age: int = Form(...),
                    password: str = Form(...),
                    db: Session = Depends(auth.get_db)):
    if get_user_by_email(db, email):
        return templates.TemplateResponse("register.html", {"request": request, "error": "Email уже зарегистрирован"})
    try:
        user = create_user(db, UserCreate(name=name, email=email, age=age, password=password))
        log_action(db, user, "Регистрация.")
        db.commit()
    except Exception:
        db.rollback()
        return templates.TemplateResponse("register.html", {"request": request, "error": "Ошибка при регистрации."})
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)


# Вход и выход в аккаунт
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login_action(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(auth.get_db)
):
    user = get_user_by_email(db, email)
    if not user or not auth.verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Неверные учетные данные"}
        )
    token = auth.create_access_token({"sub": str(user.id)})
    response = RedirectResponse(url="/tasks", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="Authorization",
        value=f"Bearer {token}",
        path="/",
        httponly=True,
    )
    return response
@app.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("Authorization")
    return response


# Задачи
@app.get("/tasks", response_class=HTMLResponse)
def show_tasks(request: Request,
               current_user: User = Depends(auth.get_current_user),
               db: Session = Depends(auth.get_db)):
    tasks = get_tasks(db, current_user)
    history = get_history(db, current_user)
    return templates.TemplateResponse("tasks.html",
                                      {"request": request,
                                       "tasks": tasks,
                                       "history": history})

@app.post("/tasks")
def add_task(request: Request,
             title: str = Form(...),
             due_date: date = Form(None),
             current_user: User = Depends(auth.get_current_user),
             db: Session = Depends(auth.get_db)):
    create_task(db, current_user, TaskCreate(title=title, due_date=due_date))
    log_action(db, current_user, f"Создана задача: {title}.")
    return RedirectResponse(url="/tasks", status_code=status.HTTP_302_FOUND)

@app.post("/tasks/{task_id}/complete")
def complete_task(task_id: int,
                  completed: bool = Form(...),
                  current_user: User = Depends(auth.get_current_user),
                  db: Session = Depends(auth.get_db)):
    task = db.query(Task).get(task_id)
    if not task or task.user_id != current_user.id:
        raise HTTPException(404, "Задача не найдена")
    task.completed = completed
    db.commit()
    db.refresh(task)
    action = f"Задача '{task.title}' " + ("отмечена выполненной" if completed else "отмечена невыполненной")
    log_action(db, current_user, action)
    return RedirectResponse(url="/tasks", status_code=status.HTTP_302_FOUND)


# Ссылка на список задач на конкретный день
@app.get("/share/{user_id}/{task_date}", response_class=HTMLResponse)
def share(request: Request,
          user_id: int,
          task_date: date,
          db: Session = Depends(auth.get_db)):
    tasks = get_tasks_by_date(db, user_id, task_date)
    return templates.TemplateResponse("share.html",
                                      {"request": request,
                                       "tasks": tasks,
                                       "date": task_date})
