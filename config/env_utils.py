import os

import dotenv

dotenv.load_dotenv(override=True)
OPENAI_API_key = os.getenv("OPENAI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENAI_BASE_URL=os.getenv("OPENAI_BASE_URL")
DEEPSEEK_BASE_URL=os.getenv("DEEPSEEK_BASE_URL")
LOCAL_BASE_URL=os.getenv("LOCAL_BASE_URL")
zhipu_API_KEY = os.getenv("ZHIPU_API_KEY")
K2_API_KEY = os.getenv("MOONSHINE_API_KEY")
K2_BASE_URL=os.getenv("MOONSHINE_BASE_URL")
ALi_API_KEY=os.getenv("ALI_API_KEY")
ALi_BASE_URL=os.getenv("ALI_BASE_URL")
FIRECRAWL_API_KEY=os.getenv("FIRECRAWL_API_KEY")
FIRECRAWL_BASE_URL=os.getenv("FIRECRAWL_BASE_URL")