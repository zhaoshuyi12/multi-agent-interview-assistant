import datetime
import json
from pathlib import Path
from typing import Optional, List
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from fastmcp import FastMCP

from config.env_utils import ALi_API_KEY

mcp=FastMCP(name="research_server",instructions="检索查询mcp服务器")
embeddings=DashScopeEmbeddings(model="text-embedding-v4", dashscope_api_key=ALi_API_KEY,)
vectorstore_path = "/data/research_vectorstore"
#获取当前文件所在目录
file_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+ vectorstore_path
try:
        vectorstore = FAISS.load_local(file_path, embeddings,allow_dangerous_deserialization=True)
except:
        Path(file_path).mkdir(parents=True, exist_ok=True)
        #创建向量库，获取向量维度
        dummy_embeddings=embeddings.embed_query('初始化向量库')
        dimension=len(dummy_embeddings)
        from faiss import IndexFlatL2

        index = IndexFlatL2(dimension)
        vectorstore = FAISS(
            embedding_function=embeddings,
            index=index,
            index_to_docstore_id={},
            docstore={},
        )
        vectorstore.save_local(file_path)
        metadatas={"last_updated":datetime.datetime.now().isoformat()}
        with open(str(file_path) +"metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadatas, f, ensure_ascii=False, indent=2)
@mcp.tool(name="semantic_search", description="根据输入的查询内容，返回最相关的内容")
async def sentence_similarity(query: str,top_k: int = 5) -> list:
    try:
        docs = vectorstore.similarity_search(query, k=top_k)
        results = []
        for i, doc in enumerate(docs):
            metadata = doc.metadata
            source = metadata.get('source', '未知来源')
            date = metadata.get('date', '未知日期')

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
async  def add_content(content: str,metadata: dict=None) -> str:
    try:
        if metadata is None:
            metadata={}
        doc=Document(page_content=content, metadata=metadata)
        vectorstore.add_documents(documents=[doc])
        vectorstore.save_local(file_path)
        return "添加成功，当前总文档数"
    except:
        return "添加失败"


def load_vectorstore_and_metadata():
    """加载元数据"""
    # 加载元数据
    metadata_file = file_path / "metadata.json"
    if metadata_file.exists():
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    else:
        metadata = {"last_updated": "未知", "total_documents": 0}

    return  metadata
@mcp.tool(name="list_knowledge_base_stats",description="查看知识库统计信息")
def add_to_knowledge_base(
        text: str,
        source: str = "用户输入",
        category: str = "general",
        tags: Optional[List[str]] = None
) -> str:
    """
    添加文档到知识库

    Args:
        text: 文本内容
        source: 来源
        category: 分类
        tags: 标签列表

    Returns:
        操作结果
    """
    global vectorstore
    # 准备元数据
    metadata = {
        "source": source,
        "category": category,
        "tags": tags or [],
        "added_at": datetime.datetime.now().isoformat(),
        "text_length": len(text)
    }

    # 创建文档
    doc = Document(
        page_content=text,
        metadata=metadata
    )

    # 添加到向量存储
    vectorstore.add_documents([doc])
    vectorstore.save_local(file_path)

    return f"✅ 成功添加文档到知识库\n  来源: {source}\n  分类: {category}\n  长度: {len(text)} 字符"

if __name__ == "__main__":
    print("🚀 启动基于 Qwen Embedding 的研究服务器 (FastMCP)")
    print("💡 请确保已设置 DASHSCOPE_API_KEY 环境变量")
    mcp.run()