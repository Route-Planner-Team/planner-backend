import os
from dotenv import load_dotenv


class Config():
    load_dotenv()
    mongo_conn: str = os.getenv("MONGO", "")