import random
import time


def snowflake() -> int:
    return int(time.time() * 1000) * 1000 + random.randint(0, 999)