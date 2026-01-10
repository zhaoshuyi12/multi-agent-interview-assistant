# research_tools.py (修正版)

import json
from pathlib import Path
from typing import Optional, List
import sys
import os
from datetime import datetime
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from fastmcp import FastMCP
from config.env_utils import ALi_API_KEY

mcp = FastMCP(name="research_server", instructions="检索查询mcp服务器")

embeddings = DashScopeEmbeddings(model="text-embedding-v4", dashscope_api_key=ALi_API_KEY)

vectorstore_path = "/root/autodl-tmp/research_vectorstore"
os.makedirs(vectorstore_path, exist_ok=True)
METADATA_FILE = Path(vectorstore_path) / "knowledge_meta.json"

vectorstore = Chroma(persist_directory=vectorstore_path, embedding_function=embeddings)

# ===== 工具定义 =====
@mcp.tool(name="semantic_search", description="根据输入的查询内容，返回最相关的内容")
async def semantic_search(query: str, top_k: int = 5) -> list:
    try:
        docs = vectorstore.similarity_search(query, k=top_k)
        results = []
        for i, doc in enumerate(docs):
            metadata = doc.metadata
            source = metadata.get('source', '未知来源')
            date = metadata.get('date', metadata.get('added_at', '未知日期'))
            results.append(
                f"【结果 {i + 1}】\n"
                f"来源: {source} | 日期: {date}\n"
                f"内容: {doc.page_content[:300]}...\n"
                f"{'-' * 50}"
            )
        return "\n".join(results)
    except Exception as e:
        return [f"搜索失败: {str(e)}"]

@mcp.tool(name="add_to_knowledge_base", description="添加内容到语义搜索中")
def add_to_knowledge_base(
    text: str,
    source: str = "用户输入",
    category: str = "general",
    tags: Optional[List[str]] = None
) -> str:
    """
    添加内容到语义搜索中
    """
    global vectorstore
    try:
        metadata = {
            "source": source,
            "category": category,
            "tags": tags or [],
            "added_at": datetime.now().isoformat(),
            "text_length": len(text)
        }
        doc = Document(page_content=text, metadata=metadata)
        vectorstore.add_documents([doc])
        vectorstore.persist()

        # 更新元数据文件
        current_count = vectorstore._collection.count()
        meta_data = {
            "last_updated": datetime.now().isoformat(),
            "total_chunks": current_count
        }
        with open(METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, ensure_ascii=False, indent=2)

        return f"✅ 成功添加文档\n来源: {source}\n长度: {len(text)} 字符"
    except Exception as e:
        return f"❌ 添加失败: {str(e)}"

@mcp.tool(name="list_knowledge_base_stats", description="查看知识库统计信息")
def list_knowledge_base_stats() -> str:
    try:
        count = vectorstore._collection.count()
        last_updated = "未知"
        if METADATA_FILE.exists():
            with open(METADATA_FILE, "r", encoding="utf-8") as f:
                meta = json.load(f)
                last_updated = meta.get("last_updated", "未知")
        return (
            f"📊 知识库统计:\n"
            f"- 文档片段总数: {count}\n"
            f"- 最后更新时间: {last_updated}\n"
            f"- 存储路径: {vectorstore_path}"
        )
    except Exception as e:
        return f"❌ 获取统计失败: {str(e)}"

@mcp.tool(name="ingest_document", description="上传并解析 PDF 或 DOCX 文件，存入知识库")
async def ingest_document(file_path: str, source_name: str = None) -> str:
    try:
        file_path = Path(file_path).resolve()
        if not file_path.exists():
            return "❌ 文件不存在"
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            loader = PyPDFLoader(str(file_path))
        elif suffix == ".docx":
            loader = Docx2txtLoader(str(file_path))
        else:
            return "❌ 仅支持 .pdf 和 .docx 文件"

        docs = loader.load()
        if not docs:
            return "⚠️ 文档内容为空"

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500, chunk_overlap=50,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]
        )
        split_docs = splitter.split_documents(docs)

        metadata = {
            "source": source_name or file_path.name,
            "file_path": str(file_path),
            "ingested_at": datetime.now().isoformat(),
        }
        for doc in split_docs:
            doc.metadata.update(metadata)

        global vectorstore
        vectorstore.add_documents(split_docs)
        vectorstore.persist()

        # 更新元数据文件
        current_count = vectorstore._collection.count()
        meta_data = {
            "last_updated": datetime.now().isoformat(),
            "total_chunks": current_count
        }
        with open(METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, ensure_ascii=False, indent=2)

        return f"✅ 成功解析并添加 {len(split_docs)} 个文本片段（来源: {metadata['source']}）"
    except Exception as e:
        import traceback
        print(f"[ERROR] ingest_document failed: {e}")
        traceback.print_exc()
        return f"❌ 解析失败: {str(e)}"

if __name__ == "__main__":
    print("🚀 启动基于 Qwen Embedding 的研究服务器 (FastMCP)")
    print("💡 请确保已设置 DASHSCOPE_API_KEY 环境变量")
    mcp.run()