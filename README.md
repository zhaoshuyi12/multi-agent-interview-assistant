# Multi-Agent Assistant System

一个基于 LangChain 和 LangGraph 构建的多智能体助手系统，支持研究、数据分析、网络搜索等功能。

## 🌟 功能特性

- **多智能体协作**：研究智能体、分析智能体、网络搜索智能体协同工作
- **MCP 工具集成**：支持多种工具，包括计算器、科学研究、网络搜索等
- **自适应检索**：智能判断查询类型，选择合适的处理策略
- **RESTful API**：提供完整的 HTTP API 接口
- **持久化存储**：支持对话历史和知识库的持久化

## 🏗️ 系统架构

### 智能体类型
- **ResearchAgent**：内部知识研究员，负责语义搜索和知识库管理
- **AnalysisAgent**：数据分析师，执行数学计算、统计分析、单位转换
- **WebSearchAgent**：网络搜索专家，获取实时信息（新闻、天气、股价等）

### 核心组件
- **LangChain**：LLM 应用开发框架
- **LangGraph**：工作流编排引擎
- **FastMCP**：MCP 服务器实现
- **FastAPI**：Web 服务框架
- **Chroma/FAISS**：向量数据库
