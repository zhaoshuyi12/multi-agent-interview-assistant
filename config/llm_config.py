from langchain_openai import ChatOpenAI
from config.env_utils import K2_API_KEY, K2_BASE_URL, OPENAI_BASE_URL, OPENAI_API_key,ALi_API_KEY,ALi_BASE_URL
#k2大模型调用
moon = ChatOpenAI(
    model='kimi-k2-0711-preview',
    temperature=0.6,
    api_key=K2_API_KEY,
    base_url=K2_BASE_URL,
    # extra_body={'enable_thinking': True},
)
#gpt4模型调用
gpt4 = ChatOpenAI(model="gpt-4.1",temperature=0.8,api_key=OPENAI_API_key,base_url=OPENAI_BASE_URL)
#claud大模型调用
claud=ChatOpenAI(model="claude-3-7-sonnet-20250219",temperature=0.8,api_key=OPENAI_API_key,
               base_url=OPENAI_BASE_URL)

#Qwen大模型调用
qwen = ChatOpenAI(model="qwen-max-2025-01-25",temperature=0.8,api_key=ALi_API_KEY,base_url=ALi_BASE_URL)
