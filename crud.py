from sqlalchemy.orm import Session
from datetime import date, timedelta
from fastapi import HTTPException

from models import User, Task, History
from schemas import UserCreate, TaskCreate
import auth


def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user: UserCreate):
    hashed_password = auth.get_password_hash(user.password)
    db_user = User(name=user.name, email=str(user.email),
                   age=user.age, hashed_password=hashed_password)
    db.add(db_user)
    db.flush()
    return db_user

def create_task(db: Session, user: User, task: TaskCreate):
    due_date = task.due_date if task.due_date is not None else date.today()
    db_task = Task(title=task.title, user_id=user.id, due_date=due_date, create_date=date.today())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def get_tasks(db: Session, user: User):
    tasks = db.query(Task).filter(Task.user_id == user.id).all()
    for task in tasks:
        if not task.completed and task.due_date < date.today():
            task.due_date = date.today()
    db.commit()
    return tasks

def get_tasks_by_date(db: Session, user_id: int, day: date):
    return db.query(Task).filter(Task.user_id == user_id, Task.due_date == day).all()

def update_task_due_date(db: Session, task_id: int, user_id: int, completed: bool):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    if not completed:
        task.due_date = date.today() + timedelta(days=1)
    db.commit()
    db.refresh(task)
    return task

def log_action(db: Session, user: User, action: str):
    entry = History(user_id=user.id, action=action)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

def get_history(db: Session, user: User):
    return db.query(History).filter(History.user_id == user.id).order_by(History.timestamp.desc()).all()
