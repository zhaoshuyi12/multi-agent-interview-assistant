# Multi-Agent RAG System with LangGraph & MCP 🤖🔍

这是一个基于 **LangGraph** 构建的高度模块化多智能体系统。它集成了 **RAG (检索增强生成)**、**实时网络搜索**、以及 **MCP (Model Context Protocol)** 扩展工具。系统不仅能自主选择工具解决问题，还引入了“人工确认与迭代反馈”机制，确保输出结果的准确性与可控性。

## 🌟 技术亮点

- **有状态图流 (LangGraph)**：使用 `StateGraph` 管理复杂任务流，支持条件路由、循环迭代及状态持久化。
- **MCP 协议集成**：通过 `FastMCP` 实现了计算器、研究检索、网络搜索等独立微服务工具，具备极强的扩展性。
- **自适应 RAG 策略**：基于 `ChromaDB` 和 `DashScope` 嵌入，支持历史感知的检索压缩，有效提升知识库问答精度。
- **Human-in-the-Loop**：设计了反馈循环节点，用户可以对 AI 生成的初步结果进行评价、修正，并触发系统重新分析执行。
- **异步 FastAPI 后端**：采用异步并发处理工具调用，结合 `Gradio` 提供直观的多智能体协作过程展示。

## 🏗️ 系统架构图


*(建议在此处放置由代码生成的 Mermaid 图或逻辑流程图)*

1. **Analyzer (调度专家)**：解析意图，决定流向 `research`、`analysis` 或 `web_search`。
2. **Specialist Agents (专家集群)**：
   - `Research Agent`: 深入本地知识库进行语义检索。
   - `Analysis Agent`: 处理复杂的逻辑计算。
   - `Web Search Agent`: 获取互联网实时信息。
3. **Integrator (整合器)**：多源信息汇聚、去重、逻辑校验并生成最终回答。
4. **Approval Loop (反馈环)**：用户介入，决定直接完成任务或要求 AI 修正。

