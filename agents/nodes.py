#多智能体状态共享
from typing import TypedDict, Annotated, Literal, List, Any

from langchain_core.messages import AIMessage
from pydantic import Field

from RAG.adaptive_retrival import AdaptiveRetrieval
from config.llm_config import moon


class AgentState(TypedDict):
    messages: Annotated[List[str], Field(description="对话历史")]
    query: Annotated[str, Field(description="当前问题")]
    query_type: Literal["research", "analysis", "web_search"]  # 查询类型
    skip_tool: bool
    research_result: dict
    analysis_result: dict
    web_search_result: dict
    final_answer: str
    current_agent:  str
#创建节点
def analysis_query(state: AgentState):
    prompt=f"""
        你是一个智能路由器，请严格根据用户问题判断其所属类型，并仅输出以下三个词之一：
    - research：问题涉及事实、概念、定义、历史、原理、公司背景、技术细节等，需要从内部知识库检索信息。
    - analysis：问题包含数学计算、统计、公式推导、单位换算、数据分析等，需要调用计算器或分析工具。
    - web_search：问题涉及实时信息，如当前新闻、天气、股价、体育比分、最新政策、突发事件等，必须联网查询。
    
    用户问题：{state['query']}
    
    请只输出一个词：research / analysis / web_search
    """
    response=moon.invoke(prompt)
    query_type = response.content.strip().lower()
    print(query_type)
    return {"query_type": query_type,"skip_tools":False, "current_agent": "analyzer"}


async def execute_research_agent(state: AgentState, research_agent=None):
    query = state["query"]

    # 初始化 AdaptiveRetrieval（指向同一个 Chroma 库）
    retriever = AdaptiveRetrieval(vectorstore_path="/root/autodl-tmp/research_vectorstore")

    # 执行自适应检索（自动选择策略）
    retrieved_docs = await retriever.adaptive_retrieve(
        query=query,
        chat_history=[],
        strategy="history_aware"
    )
    print(retrieved_docs)
    # 构建回答
    if retrieved_docs:
        context = "\n\n".join([doc["content"] for doc in retrieved_docs])
        sources = [doc["metadata"].get("source", "未知") for doc in retrieved_docs]
        prompt = (
            f"你是一个专业研究员，请基于以下内部资料准确回答问题。\n\n"
            f"资料：\n{context}\n\n"
            f"问题：{query}\n\n"
            f"请直接给出答案，不要编造。如果资料不足，请说“根据现有资料无法确定”。"
        )
    else:
        prompt = f"问题：{query}\n根据内部知识库无法找到相关信息。"
        sources = []

    # 调用大模型生成最终回答
    response = moon.invoke(prompt)
    answer = response.content.strip()

    # 返回结构化结果
    structured_response = {
        "answer": answer,
        "sources": sources,
        "retrieved_count": len(retrieved_docs)
    }

    return {
        "research_result": structured_response,
        "current_agent": "researcher"
    }


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
    print('进入最后回答')
    skip = state.get("skip_tool", False)
    query = state["query"]

    if skip:
        # 直接用 LLM 回答通用问题
        prompt = f"你是一个智能助手，请回答：{query}"
        response =moon.invoke(prompt)
        return {"final_answer": [AIMessage(content=response.content)], "current_agent": "integrator"}

    # 否则整合工具结果
    research = state["research_result"].get("answer", "")
    analysis = state["analysis_result"].get("answer", "")
    web = state["web_search_result"].get("answer", "")
    combined = f"研究结果:\n{research}\n\n分析结果:\n{analysis}\n\n网络搜索:\n{web}"
    final_prompt = f"请整合以下信息，给出最终答案：\n\n{combined}"
    response = moon.invoke(final_prompt)
    print('----------------------------------')
    print( response,final_prompt)
    return {"final_answer": response.content, "current_agent": "integrator"}