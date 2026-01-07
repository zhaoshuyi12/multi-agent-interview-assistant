from typing import List

from langchain.agents import create_agent
from langchain_core.tools import BaseTool
from langchain.agents.middleware import SummarizationMiddleware, ToolRetryMiddleware, PIIMiddleware, AgentMiddleware
from pydantic import BaseModel, Field

from config.llm_config import moon

class AgentResponse(BaseModel):
    """结构化输出格式"""
    answer: str = Field(description="智能体的回答")
    reasoning: str = Field(description="推理过程")
    tools_used: List[str] = Field(description="使用的工具列表")
    citations: List[str] = Field(description="引用来源")


def create_specialist_agent(tools:List[BaseTool],name:str, role:str):
    system_prompt=f"""你是{name}，一位{role}。
        你的职责：{role}
        
        请按照以下步骤工作：
        1. 分析任务需求
        2. 必要时使用可用工具
        3. 提供详细且准确的回答
        4. 明确标注信息来源"""
    agent=create_agent(
        model=moon,tools=tools,
        system_prompt=system_prompt,
        middleware=[
            SummarizationMiddleware(
                model=moon,
                max_tokens_before_summary=4000,
                messages_to_keep=20,
            ),
            ToolRetryMiddleware(
                max_retries=3,
                backoff_factor=2.0,
                jitter=True
            ),
            PIIMiddleware("email", strategy="redact", apply_to_input=True)],
        response_format=AgentResponse
    )
    return  agent