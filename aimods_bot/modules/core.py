from dotenv import load_dotenv
import os

load_dotenv()


def return_bt():
    with open(os.getenv("COREPATH"), "r") as file:
        core = str(file.read()).strip()
    os.environ.pop("COREPATH")
    return core
