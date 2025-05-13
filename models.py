from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Date, Text
from sqlalchemy.orm import relationship
from datetime import datetime, date
from zoneinfo import ZoneInfo

from database import Base


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    age = Column(Integer)
    tasks = relationship('Task', back_populates='user')
    history = relationship('History', back_populates='user')

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    completed = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship('User', back_populates='tasks')
    due_date = Column(Date, default=date.today, index=True)
    create_date = Column(Date, default=date.today, index=True)

class History(Base):
    __tablename__ = 'history'
    id = Column(Integer, primary_key=True, index=True)
    action = Column(Text)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo("Asia/Novosibirsk")))
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship('User', back_populates='history')
