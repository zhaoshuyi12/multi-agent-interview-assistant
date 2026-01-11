# main.py
import asyncio
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, File, Form, UploadFile
from pydantic import BaseModel
from langchain_core.tools import BaseTool
from starlette.responses import JSONResponse

from agents.base_agent import create_specialist_agent
from agents.nodes import AgentState
from mcp_tools.mcp_integration import get_tools
from orchestration.workflow import build_agent_workflow

# 自定义模块


# 全局变量
WORKFLOW_GRAPH = None
ResearchTools = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    global WORKFLOW_GRAPH
    print("🚀 正在加载 MCP 工具...")

    try:
        # 获取所有 MCP 工具
        all_tools: List[BaseTool] = await get_tools()
        if not all_tools:
            raise RuntimeError("❌ 未加载到任何工具，请确保 MCP 服务已启动")

        # 分类工具
        research_tools = [t for t in all_tools if t.name in ("add_to_knowledge_base","semantic_search",
                                                             "list_knowledge_base_stats","ingest_document")]
        global ResearchTools
        ResearchTools=research_tools
        analysis_tools = [t for t in all_tools if t.name in (
            "basic_calculator", "scientific_calculator", "statistical_analysis", "unit_converter"
        )]
        web_search_tools = [t for t in all_tools if t.name == "zhiputool"]

        print(f"📚 研究工具: {[t.name for t in research_tools]}")
        print(f"📊 分析工具: {[t.name for t in analysis_tools]}")
        print(f"🌐 网络搜索工具: {[t.name for t in web_search_tools]}")

        # 创建智能体
        researcher = create_specialist_agent(research_tools, "ResearchAgent", "内部知识研究员")
        analyst = create_specialist_agent(analysis_tools, "AnalysisAgent", "数据分析师")
        web_searcher = create_specialist_agent(web_search_tools, "WebSearchAgent", "网络搜索专家")

        # 构建工作流
        global WORKFLOW_GRAPH
        WORKFLOW_GRAPH = build_agent_workflow(researcher, analyst, web_searcher)
        print("✅ 多智能体系统启动完成！")

        yield  # 启动完成，服务运行中

    except Exception as e:
        print(f"💥 启动失败: {e}")
        raise


# 创建 FastAPI 应用，传入 lifespan
app = FastAPI(
    title="Multi-Agent Assistant (LangChain 1.0 + LangGraph 1.0)",
    description="支持研究、分析、网络搜索的智能体系统",
    version="1.0",
    lifespan=lifespan  # ← 关键：使用 lifespan 替代 on_event
)

PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))
UPLOAD_DIR = PROJECT_ROOT / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
class QueryRequest(BaseModel):
    query: str
    thread_id: Optional[str] = "default"

class ApprovalResponse(BaseModel):
    thread_id: str
    query: str
    answer: str
    executed_by: str

class ApprovalRequest(BaseModel):
    feedback: str = "同意"  # 默认值为“同意”，如果用户不写意见则默认通过
@app.get("/health")
async def health_check():
    return {"status": "ok", "ready": WORKFLOW_GRAPH is not None}

@app.get("/kb/stats")
async def get_knowledge_base_stats():
    """获取知识库统计信息"""
    try:
        stats_tool = next((t for t in ResearchTools if t.name == "list_knowledge_base_stats"), None)
        if not stats_tool:
            return {"error": "未找到 list_knowledge_base_stats 工具"}
        result = await stats_tool.ainvoke({})
        return {"stats": result}
    except Exception as e:
        return {"error": str(e)}
@app.get("/tools")
async def list_tools():
    tools = await get_tools()
    return [{"name": t.name, "description": t.description} for t in tools]


@app.post("/query")
async def submit_query(request: QueryRequest):
    print('yes')
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="查询不能为空")

    config = {"configurable": {"thread_id": request.thread_id}}

    initial_state = AgentState(
        messages=[],
        query=request.query,
        query_type="general",
        research_result={},
        analysis_result={},
        web_search_result={},
        final_answer="",
        current_agent="user"
    )

    if WORKFLOW_GRAPH is None:
        raise HTTPException(status_code=503, detail="系统尚未初始化完成")

    try:

        current_state  = await WORKFLOW_GRAPH.ainvoke(initial_state, config=config)
        state_vals = current_state
        print(state_vals)
        return {
            "thread_id": request.thread_id,
            "status": "waiting_for_approval",
            "message": "流程已暂停。请审核各智能体的输出结果：若满意请提交‘同意’以生成最终答案；若不满意请提交具体的‘修改意见’，系统将根据反馈重新生成内容。",
            "query": state_vals.get("query"),
            "current_agent": state_vals.get("current_agent"),
            "web_search_result": state_vals.get("web_search_result", {}),
            "research_result": state_vals.get("research_result", {}),
            "analysis_result": state_vals.get("analysis_result", {})
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"执行失败: {str(e)}")


@app.post("/approve/{thread_id}", response_model=ApprovalResponse)
async def approve_and_continue(thread_id: str,request: ApprovalRequest):
    config = {"configurable": {"thread_id": thread_id}}

    # 获取当前工作流的状态快照
    current_state = await WORKFLOW_GRAPH.aget_state(config)
    print(current_state)
    if not current_state.next :
        # 可能已经执行完，或还没到中断点

        if current_state.values.get("final_answer"):
            return ApprovalResponse(
                thread_id=thread_id,
                query=current_state.values["query"],
                answer=current_state.values["final_answer"],
                executed_by=current_state.values.get("current_agent", "unknown")
            )

        else:
            raise HTTPException(
                status_code=400,
                detail="当前流程未处于待审批状态（可能尚未开始或已完成）"
            )
    WORKFLOW_GRAPH.update_state(config, {"user_feedback": request.feedback})
    # 👉 关键：传入 None 表示“无新输入，继续执行”
    final_state = await WORKFLOW_GRAPH.ainvoke(None, config)

    return ApprovalResponse(
        thread_id=thread_id,
        query=final_state["query"],
        answer=final_state.get("final_answer", "抱歉，重新生成答案时出现了问题。"),
        executed_by=final_state.get("current_agent", "unknown")
    )


@app.post("/upload")
async def upload_document(
        file: UploadFile = File(...),
        source_name: str = Form(None)
):
    """上传 PDF/DOCX 文件到研究知识库"""
    if not file.filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(status_code=400, detail="仅支持 .pdf 和 .docx 文件")

    # 保存文件
    file_path = UPLOAD_DIR / f"{uuid4()}{Path(file.filename).suffix}"
    with open(file_path, "wb") as f:
        f.write(await file.read())

    try:
        # 获取所有工具
        all_tools = await get_tools()
        ingest_tool = next((t for t in all_tools if t.name == "ingest_document"), None)

        if not ingest_tool:
            raise HTTPException(status_code=500, detail="未找到 ingest_document 工具")

        # 调用工具
        result = await ingest_tool.ainvoke({"file_path":file_path, "source_name":source_name})
        return {"message": result}

    finally:
        # 清理临时文件
        if file_path.exists():
            file_path.unlink()
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)