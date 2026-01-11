# app/orchestration/workflow.py
from functools import partial
from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END, START

from agents.nodes import AgentState, analysis_query,integrate_results, run_research_node, run_analysis_node, run_web_search_node
# 创建图
def build_agent_workflow(research_agent, analysis_agent, web_search_agent):
    """注册函数 → 构建图 → 返回编译对象"""
    builder = StateGraph(AgentState)

    # 1. 注册节点（**关键：把函数名传进去**）
    builder.add_node("analyze", analysis_query)  # ← 注册函数
    builder.add_node("research", partial(run_research_node, agent=research_agent))
    builder.add_node("analysis", partial(run_analysis_node, agent=analysis_agent))
    builder.add_node("web_search", partial(run_web_search_node, agent=web_search_agent))
    builder.add_node("integrate", integrate_results)
    builder.set_entry_point("analyze")
    # 2. 条件路由
    def route_by_type(state: AgentState) -> Literal["research", "analysis", "web_search", "integrate"]:
        return state["query_type"]

    def route_after_approval(state: AgentState):
        feedback = state.get("user_feedback", "").strip()
        count = state.get("loop_step", 0)
        if feedback == "同意" or count >= 3:
            return END  # ✅ 结束流程
        re_run_tools_keywords = ["搜", "查", "计算", "数据", "分析"]
        if any(kw in feedback for kw in re_run_tools_keywords):
            return "analyze"  # 回到开头，重新选工具
        else:
            return "integrate"  # 回到整合，仅重新润色
    builder.add_conditional_edges("analyze", route_by_type,
                                  {"research": "research", "analysis": "analysis", "web_search": "web_search",
                                   "integrate": "integrate"})
    builder.add_edge("research", "integrate")
    builder.add_edge("analysis", "integrate")
    builder.add_edge("web_search", "integrate")
    builder.add_conditional_edges(
        "integrate",
        route_after_approval,
        {END: END, "analyze": "analyze","integrate":"integrate"}
    )
    #设置入口

    # 添加持久化检查点[citation:1][citation:9]
    memory =MemorySaver()  # 生产环境用文件路径

    # 编译图
    graph = builder.compile(
        checkpointer=memory,
        interrupt_after=["integrate"]  # 在整合前可人工干预
    )
    graph.get_graph().draw_png("workflow.png")
    return graph