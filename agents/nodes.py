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
    user_feedback: str
#创建节点
def analysis_query(state: AgentState):
    query = state["query"]
    feedback = state.get("user_feedback", "").strip()

    # 💡 无论是否是迭代，都使用结构化的指令来约束模型
    role_instruction = """
    你是一个任务调度专家。你的任务是分析用户问题，并从以下工具中选择最合适的一个。
    严禁输出任何关于问题的回答、建议或攻略。

    可选工具：
    1. research: 适合深入的研究、学术定义、百科知识。
    2. analysis: 适合逻辑推理、数学计算、单位转换。
    3. web_search: 适合实时信息、天气、最新新闻、具体地点推荐。
    4. integrate: 仅在不需要任何工具、直接整合现有信息时使用。
    """

    if not feedback or feedback == "同意":
        prompt_content = f"{role_instruction}\n\n用户原始问题：{query}\n\n请只输出工具名称（例如：web_search）。"
    else:
        prompt_content = f"""
        {role_instruction}

        ### 任务上下文 📋
        用户原始问题：{query}
        用户的修改意见：{feedback}

        ### 输出要求 🧠
        请结合反馈，严格按照以下格式回复：
        TOOL: [工具名称]
        REASON: [简短理由]
        """

    response = moon.invoke(prompt_content)
    raw_output = response.content.strip().lower()
    print(f"LLM 原始输出: {raw_output}")

    # 防御性清洗逻辑保持不变
    if "web_search" in raw_output or "web" in raw_output:
        query_type = "web_search"
    elif "research" in raw_output:
        query_type = "research"
    elif "analysis" in raw_output:
        query_type = "analysis"
    else:
        query_type = "integrate"

    print(f"校准后的路由目标: {query_type}")
    return {"query_type": query_type, "skip_tools": False, "current_agent": "analyzer"}

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
    print('进入最后回答整合阶段')

    # 获取原始素材
    research = state.get("research_result", {}).get("answer", "")
    analysis = state.get("analysis_result", {}).get("answer", "")
    web = state.get("web_search_result", {}).get("answer", "")

    # 获取用户反馈
    feedback = state.get("user_feedback", "").strip()

    # 💡 核心优化：构建带有指令优先级的上下文
    context = f"研究数据：{research}\n分析数据：{analysis}\n实时信息：{web}"

    # 如果有反馈且不是“同意”，则构建反馈指令
    instruction = "请整合以上信息，给出专业且详尽的回答。"
    if feedback and feedback != "同意":
        instruction = f"⚠️ 用户对上一次回答不满意，提出了以下修改意见：【{feedback}】。请严格根据此意见，结合背景数据重新撰写回答。"

    final_prompt = f"""
    你是一个全能型报告整合专家。

    [背景素材]
    {context}

    [任务指令]
    {instruction}

    注意：如果背景素材中缺少用户反馈所需的信息，请诚实说明，不要虚构数据。
    """

    response = moon.invoke(final_prompt)
    return {"final_answer": response.content, "current_agent": "integrator"}