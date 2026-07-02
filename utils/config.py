import os

from dotenv import load_dotenv
load_dotenv()
# 从环境变量中获取base_url
def get_base_url():
    return os.getenv("BASE_URL")