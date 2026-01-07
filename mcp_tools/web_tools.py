# mcp_servers/zhipu_search_mcp.py
import sys
import os

from fastmcp import FastMCP

from zai import ZhipuAiClient

# 添加项目根目录到路径（确保能导入 env_utils）
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


from config.env_utils import zhipu_API_KEY
# 初始化 FastMCP 服务
server = FastMCP(
    name="zsyMCP",
    instructions="提供基于智谱AI的网络搜索能力，支持实时信息查询（如天气、新闻等）"
)

# 使用官方 ZhipuAI SDK（更稳定）
client=ZhipuAiClient(api_key=zhipu_API_KEY)


@server.tool(name="zhiputool")
def my_search(query: str) -> str:
    """
    使用智谱AI高级搜索引擎（search_pro）查询最新网络信息。
    适用于：实时新闻、天气、股价、体育赛事、科技动态等。
    输入应为明确的搜索关键词或问题。
    """
    try:
        print(f"[MCP] 执行 zhiputool，查询: {query}")

        response = client.web_search.web_search(
            search_engine="search_pro",
            search_query=query
        )

        if hasattr(response, 'search_result') and response.search_result:
            contents = [d.content for d in response.search_result if d.content]
            if contents:
                return "\n\n".join(contents)

        return "未找到相关信息。"

    except Exception as e:
        print(f"[MCP ERROR] zhiputool 失败: {e}")
        return "搜索服务暂时不可用，请稍后再试。"


# 启动 MCP 服务（通过 stdio 通信）
if __name__ == "__main__":
    server.run()