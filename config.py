import os
from dotenv import load_dotenv


class Config():
    load_dotenv()
    MONGO: str = os.getenv("MONGO", "")
    JWTKEY: str = os.getenv("JWTKEY", "")
    FIREBASE_TYPE: str = os.getenv("FIREBASE_TYPE", "")
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "")
    FIREBASE_PRIVATE_KEY_ID: str = os.getenv("FIREBASE_PRIVATE_KEY_ID", "")
    FIREBASE_PRIVATE_KEY: str = os.getenv("FIREBASE_PRIVATE_KEY", "")
    FIREBASE_CLIENT_EMAIL: str = os.getenv("FIREBASE_CLIENT_EMAIL", "")
    FIREBASE_CLIENT_ID: str = os.getenv("FIREBASE_CLIENT_ID", "")
    FIREBASE_AUTH_URI: str = os.getenv("FIREBASE_AUTH_URI", "")
    FIREBASE_TOKEN_URI: str = os.getenv("FIREBASE_TOKEN_URI", "")
    FIREBASE_AUTH_PROVIDER_X509_CERT_URL: str = os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL", "")
    FIREBASE_CLIENT_X509_CERT_URL: str = os.getenv("FIREBASE_CLIENT_X509_CERT_URL", "")
    FIREBASE_API_KEY: str = os.getenv("FIREBASE_API_KEY", "")
