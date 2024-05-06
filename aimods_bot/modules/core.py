from dotenv import load_dotenv
import json
import os

load_dotenv()

TOPICS = {}


def return_env(env: str):
    return os.getenv(env)


def get_topics():
    global TOPICS

    with open("../misc/data.json", "r") as fp:
        TOPICS = json.load(fp)
