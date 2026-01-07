# Multi-Agent Interview Assistant (MAIA)

## 功能
- 多智能体协同：Research / Analysis / WebSearch / General
- MCP 工具池：本地计算器、网络爬取、向量搜索
- RAG 历史记忆：Redis + Milvus 分层缓存
- 结构化输出：AgentResponse 零模拟

## 一键运行
```bash
pip install -r requirements.txt
docker compose up -d
curl http://localhost:8000/interview -d "{\"query\":\"3+4再乘2\"}"
```

## 技术栈
- LangGraph 1.0
- LangChain-MCP
- Redis + Milvus
- FastAPI + Uvicorn

## 许可证
MIT
