import os
from dotenv import load_dotenv


class Config():
    load_dotenv()
    MONGO: str = os.getenv("MONGO", "")
    JWTKEY: str = os.getenv("JWTKEY", "")

