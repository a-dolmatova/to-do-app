from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, date

from schemas import Token, UserResponse, UserCreate, UserDetail, TaskResponse, TaskCreate, HistoryResponse
from models import User, Task
from crud import (get_user_by_email, create_user, create_task, get_tasks, get_history, log_action,
                  get_tasks_by_date, update_task_due_date)
import auth
from database import engine, Base


Base.metadata.create_all(bind=engine)
app = FastAPI()


# Авторизация
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

# Регистрация
@app.post("/users/", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(auth.get_db)):
    if get_user_by_email(db, str(user.email)):
        raise HTTPException(status_code=400, detail="Введенный email уже зарегистрирован.")
    new_user = create_user(db, user)
    log_action(db, new_user, "Регистрация")
    return new_user

# Информация о текущем пользователе
@app.get("/users/me", response_model=UserDetail)
async def read_users_me(current_user: User = Depends(auth.get_current_user), db: Session = Depends(auth.get_db)):
    tasks = get_tasks(db, current_user)
    history = get_history(db, current_user)
    user_schema = UserResponse.model_validate(current_user)
    base = user_schema.model_dump()
    return {**base, "tasks": tasks, "history": history}

# CRUD-операции (Create, Read, Update и Delete)
@app.post("/tasks/", response_model=TaskResponse)
def create_task_for_user(task: TaskCreate,
                         current_user: User = Depends(auth.get_current_user),
                         db: Session = Depends(auth.get_db)):
    db_task = create_task(db, current_user, task)
    log_action(db, current_user, f"Создана задача: {db_task.title}")
    return db_task

@app.get("/tasks/", response_model=list[TaskResponse])
def read_tasks(current_user: User = Depends(auth.get_current_user),
               db: Session = Depends(auth.get_db)):
    return get_tasks(db, current_user)

@app.get("/tasks/{task_date}", response_model=list[TaskResponse])
def read_tasks_by_date(task_date: date,
                        current_user: User = Depends(auth.get_current_user),
                        db: Session = Depends(auth.get_db)):
    return get_tasks_by_date(db, current_user.id, task_date)

@app.patch("/tasks/{task_id}/complete", response_model=TaskResponse)
def update_task_complete(task_id: int,
                        completed: bool,
                        current_user: User = Depends(auth.get_current_user),
                        db: Session = Depends(auth.get_db)):
    db_task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    if not db_task:
        raise HTTPException(404, "Задача не найдена.")
    db_task.completed = completed
    db.commit()
    db.refresh(db_task)
    return db_task

@app.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task_day(task_id: int,
                completed: bool,
                current_user: User = Depends(auth.get_current_user),
                db: Session = Depends(auth.get_db)):
    return update_task_due_date(db, task_id, current_user.id, completed)

@app.get("/history/", response_model=list[HistoryResponse])
def get_user_history(current_user: User = Depends(auth.get_current_user),
                     db: Session = Depends(auth.get_db),):
    return get_history(db, current_user)

# Публичная ссылка на список задач на конкретный день
@app.get("/share/tasks/{user_id}/{task_date}", response_model=list[TaskResponse])
def shared_tasks(user_id: int, task_date: date, db: Session = Depends(auth.get_db)):
    return get_tasks_by_date(db, user_id=user_id, day=task_date)
