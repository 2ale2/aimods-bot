# raccoglie tutti i dati che servono al funzionamento del bot

import json
import os
from dotenv import load_dotenv

load_dotenv()


def return_env(env: str):
    return os.getenv(env)


def get_topics():
    with open("../misc/data.json", "r") as fp:
        topics = json.load(fp)
        return topics
