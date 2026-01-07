from typing import Optional, List, Dict

from langchain_classic.chains.history_aware_retriever import create_history_aware_retriever
from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_classic.retrievers.document_compressors import LLMChainExtractor
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from config.env_utils import ALi_API_KEY
from config.llm_config import qwen


class AdaptiveRetrieval:
    def __init__(self, vectorstore_path: str):
        self.embeddings=DashScopeEmbeddings(model="text-embedding-v4", dashscope_api_key=ALi_API_KEY)
        self.vectorstore = Chroma(persist_directory=vectorstore_path, embedding_function=self.embeddings)
        self.retriever=self.vectorstore.as_retriever(search_kwargs={"k": 5,"score_threshold":0.7})
        self.history_retriever=self.history_retriever()
        self.compress_retriever=ContextualCompressionRetriever(base_compressor=LLMChainExtractor.from_llm(qwen),
                                                               base_retriever=self.retriever)
    def history_retriever(self):
        prompt=ChatPromptTemplate.from_messages([('system','请你基于历史对话信息，重新组织生成一个独立的问题。'
                                                           '不要回答问题，只返回重新组织后的问题。'),
                                                 MessagesPlaceholder("chat_history"),('human','{input}')])
        return create_history_aware_retriever(llm=qwen,retriever=self.retriever,prompt=prompt)

    def assess_query_complexity(self, query: str) -> str:
        """评估查询复杂度"""
        # 简单启发式方法
        words = len(query.split())

        if words > 20 or any(word in query.lower() for word in ["analyze", "compare", "explain"]):
            return "high"
        elif words > 10:
            return "medium"
        else:
            return "low"

    async def adaptive_retrieve(
            self,query: str,chat_history: Optional[List] = None,strategy: str = "adaptive") -> List[Dict]:
        """自适应检索策略"""

        if strategy == "simple":
            # 简单检索
            docs = self.retriever.invoke(query)

        elif strategy == "history_aware" and chat_history:
            # 考虑历史
            docs = self.history_retriever.invoke({
                "input": query,
                "chat_history": chat_history
            })
        elif strategy=="compressed":
            docs=self.compress_retriever.invoke(query)
        else:
            complexity = self.assess_query_complexity(query)
            if complexity == "high" and chat_history:
                # 高度复杂查询
                docs = self.history_retriever.invoke({
                    "input": query,
                    "chat_history": chat_history
                })
            elif complexity == "medium":
                # 中等复杂查询
                docs = self.compress_retriever.invoke(query)
            else:
                # 简单查询
                docs = self.retriever.invoke(query)
        return [{"content": doc.page_content, "metadata": doc.metadata} for doc in docs]
    async  def add_to_knowlege(self,documents:List[str],metadata:Optional[Dict]=None):
        if metadata is None:
            metadata={}
        self.vectorstore.add_documents(documents=[Document(page_content=doc,metadata=metadata) for doc in documents])
        self.vectorstore.persist()
        return f"成功添加 {len(documents)} 个文档到知识库"
