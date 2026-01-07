#多智能体状态共享
from typing import TypedDict, Annotated, Literal, List, Any

from pydantic import Field

from config.llm_config import moon


class AgentState(TypedDict):
    messages: Annotated[List[str], Field(description="对话历史")]
    query: Annotated[str, Field(description="当前问题")]
    query_type: Literal["research", "analysis", "web_search", "general"]  # 查询类型
    research_result: dict
    analysis_result: dict
    web_search_result: dict
    final_answer: str
    current_agent:  str
#创建节点
def analysis_query(state: AgentState):
    prompt=f"""
    根据输入的内容判断属于以下哪个查询类型：
      - research: 需要研究/搜索信息的问题
        - analysis: 需要数据分析/计算的问题  
        - web_search: 需要查询互联网最新信息（如新闻、天气、股价等）
        - general: 一般性问题
        查询：{state['query']} 只返回查询类型
    """
    response=moon.invoke(prompt)
    query_type = response.content.strip().lower()
    return {"query_type": query_type, "current_agent": "analyzer"}

async def execute_research_agent(state: AgentState, research_agent):
    result=await research_agent.ainvoke({'messages':[{'role':'user','content':state['query']}]})
    return {"research_result": result["structured_response"],
            "current_agent": "researcher"}
async def execute_analysis_agent(state: AgentState, analysis_agent):
    result=await analysis_agent.ainvoke({'messages':[{'role':'user','content':state['query']}]})
    return {"analysis_result": result["structured_response"],
            "current_agent": "analyst"}
async def execute_web_search_agent(state: AgentState, web_search_agent):
    result=await web_search_agent.ainvoke({'messages':[{'role':'user','content':state['query']}]})
    structured=result["structured_response"]
    # ✅ 关键：将 AgentResponse 转为 dict
    if hasattr(structured, "model_dump"):  # Pydantic v2
        web_result = structured.model_dump()
    elif hasattr(structured, "__dict__"):  # dataclass 或普通对象
        web_result = structured.__dict__
    else:
        web_result = {"answer": str(structured)}  # 保底方案
    return {"web_search_result": web_result,
            "current_agent": "web_searcher"}

async def run_web_search_node(state: AgentState, agent: Any) -> dict:
    result = await execute_web_search_agent(state, agent)
    return result  # 必须是 dict！

async def run_research_node(state: AgentState, agent: Any) -> dict:
    result = await execute_research_agent(state, agent)
    return result

async def run_analysis_node(state: AgentState, agent: Any) -> dict:
    result = await execute_analysis_agent(state, agent)
    return result
def integrate_results(state: AgentState):
    all_results = []

    # 处理 research_result
    if state.get("research_result"):
        res = state["research_result"]
        if isinstance(res, dict) and "answer" in res:
            all_results.append(res["answer"])
        else:
            all_results.append(str(res))

    # 处理 analysis_result
    if state.get("analysis_result"):
        res = state["analysis_result"]
        if isinstance(res, dict) and "answer" in res:
            all_results.append(res["answer"])
        else:
            all_results.append(str(res))
    if state.get("web_search_result"):
        res = state["web_search_result"]
        if isinstance(res, dict) and "answer" in res:
            all_results.append(res["answer"])  # ← 字符串！
        else:
            all_results.append(str(res))

    # 现在 all_results 是 [str, str, ...]，可以安全 join
    integration_prompt = f"""基于以下智能体的分析，生成最终答案：

用户查询: {state['query']}

各智能体分析:
{chr(10).join(all_results)}

请提供全面、准确、专业的最终回答。"""

    response = moon.invoke(integration_prompt)

    return {
        "final_answer": response.content,
        "current_agent": "integrator"
    }