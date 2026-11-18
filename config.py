import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY or SECRET_KEY in {"replace-with-a-long-random-secret"}:
        raise RuntimeError(
            "Set a strong, unique SECRET_KEY in your local .env file before starting the app."
        )

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///student_management.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
