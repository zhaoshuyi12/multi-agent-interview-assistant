import os
import sys

from langchain_mcp_adapters.client import MultiServerMCPClient

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
MCP_SERVER_CONFIGS = {
    "research_server": {
        "command": sys.executable,  # 使用当前Python解释器
        "args": [os.path.join(TOOLS_DIR, "research_tools.py")],
        "transport": "stdio",
    },
    "calculator_server": {
        "command": sys.executable,
        "args": [os.path.join(TOOLS_DIR, "calculator_server.py")],
        "transport": "stdio",
    },
    "web_tools_server": {
        "command": sys.executable,
        "args": [os.path.join(TOOLS_DIR, "web_tools.py")],
        "transport": "stdio",
    },
}
async def get_tools():
    """获取所有MCP工具"""
    try:
        # 1. 创建客户端
        client = MultiServerMCPClient(MCP_SERVER_CONFIGS)
        # 2. 获取所有工具
        tools = await client.get_tools()
        return tools

    except Exception as e:
        print(f"工具加载失败: {e}")
        return []  # 返回空列表，系统仍可运行
