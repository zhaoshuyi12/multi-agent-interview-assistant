# gradio_app.py

import gradio as gr
import requests
import json
import os
BASE_URL = "http://localhost:8000"

def submit_query(query: str, thread_id: str):
    if not query.strip():
        return ("", "", "", "", "请输入问题", thread_id)
    try:
        resp = requests.post(f"{BASE_URL}/query", json={"query": query, "thread_id": thread_id}, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            status = data.get("message", "查询已完成")
            research = _format_result(data.get("research_result", {}))
            analysis = _format_result(data.get("analysis_result", {}))
            web = _format_result(data.get("web_search_result", {}))
            return (research, analysis, web, "", status, data["thread_id"])
        else:
            err = resp.json().get("detail", "未知错误")
            return ("", "", "", "", f"❌ 提交失败: {err}", thread_id)
    except Exception as e:
        return ("", "", "", "", f"❌ 请求异常: {str(e)}", thread_id)

def approve_and_get_answer(thread_id: str):
    if not thread_id.strip():
        return "", "请输入有效的 Thread ID"
    try:
        resp = requests.post(f"{BASE_URL}/approve/{thread_id}", timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("answer", "无回答"), "✅ 最终答案已生成！"
        else:
            err = resp.json().get("detail", "未知错误")
            return "", f"❌ 审批失败: {err}"
    except Exception as e:
        return "", f"❌ 请求异常: {str(e)}"

def get_kb_stats():
    """获取知识库统计信息"""
    try:
        resp = requests.get(f"{BASE_URL}/kb/stats", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            stats = data.get("stats", "无数据")
            if isinstance(stats, dict):
                return json.dumps(stats, ensure_ascii=False, indent=2)
            return str(stats)
        else:
            return f"❌ 获取失败: {resp.status_code}"
    except Exception as e:
        return f"❌ 请求异常: {str(e)}"
# ===== 结束新增 =====

def _format_result(result):
    if not result:
        return "无结果"
    if isinstance(result, dict):
        if "answer" in result:
            return result["answer"]
        elif "results" in result:
            return "\n".join(str(r) for r in result["results"])
        else:
            return json.dumps(result, ensure_ascii=False, indent=2)
    return str(result)
def handle_upload(file_obj, source_name: str):
    """处理文档上传到 /upload 接口"""
    if not file_obj:
        return "❌ 请先选择一个文件"
    try:
        with open(file_obj.name, "rb") as f:
            files = {"file": (os.path.basename(file_obj.name), f, "application/octet-stream")}
            data = {}
            if source_name:
                data["source_name"] = source_name

            resp = requests.post(
                f"{BASE_URL}/upload",
                files=files,
                data=data,
                timeout=120
            )

        if resp.status_code == 200:
            result = resp.json().get("message", "上传成功")
            return f"✅ 摄入成功！\n{result}"
        else:
            error_detail = resp.json().get("detail", resp.text)
            return f"❌ 上传失败 ({resp.status_code}): {error_detail}"
    except Exception as e:
        return f"❌ 请求异常: {str(e)}"
# ===== Gradio UI =====
with gr.Blocks(title="多智能体协作系统") as demo:
    gr.Markdown("# 🤖 多智能体协作系统 (Research + Analysis + Web Search)")
    gr.Markdown("系统会根据问题自动调用不同智能体，并在整合前暂停，等待人工审核。")

    # ===== ✅【新增】第 2 处：插入知识库状态面板 =====
    with gr.Accordion("📚 知识库状态", open=False):
        kb_stats_output = gr.Textbox(label="当前知识库统计", interactive=False, lines=4)
        refresh_kb_btn = gr.Button("🔄 刷新状态")
        refresh_kb_btn.click(fn=get_kb_stats, inputs=[], outputs=kb_stats_output)
    # ===== 结束新增 =====

    with gr.Row():
        with gr.Column():
            query_input = gr.Textbox(label="🔍 输入你的问题", lines=3, placeholder="例如：'分析特斯拉最近股价趋势，并查找相关新闻'")
            thread_id_input = gr.Textbox(label="🆔 Thread ID (可选)", value="")
            submit_btn = gr.Button("🚀 提交查询", variant="primary")
        with gr.Column():
            status_output = gr.Textbox(label="📌 状态", interactive=False)
            thread_display = gr.Textbox(label="🔖 当前 Thread ID", interactive=False)

    with gr.Tabs():
        with gr.Tab("📚 研究结果 (内部知识库)"):
            research_output = gr.Textbox(interactive=False, lines=8)
        with gr.Tab("📊 分析结果 (计算器/统计)"):
            analysis_output = gr.Textbox(interactive=False, lines=8)
        with gr.Tab("🌐 网络搜索结果"):
            web_output = gr.Textbox(interactive=False, lines=8)
        with gr.Tab("✅ 最终答案"):
            final_output = gr.Textbox(interactive=False, lines=10)
            approve_btn = gr.Button("✔️ 批准并生成最终答案")
            approve_status = gr.Textbox(label="审批状态", interactive=False)

    with gr.Accordion("📤 上传文档到知识库", open=False):
        gr.Markdown("""
        - 支持 PDF 和 DOCX 格式
        - 文档将被解析并加入研究知识库
        - 确保后端 MCP 服务中的知识库路径可写
        """)
        with gr.Row():
            upload_file = gr.File(
                label="选择文件（PDF/DOCX）",
                file_types=[".pdf", ".docx"]
            )
            source_name_input = gr.Textbox(
                label="来源名称（可选）",
                placeholder="例如：2024年报"
            )
            upload_btn = gr.Button("📥 上传并摄入")
        upload_status = gr.Textbox(label="上传结果", interactive=False, lines=3)

        upload_btn.click(
            fn=handle_upload,
            inputs=[upload_file, source_name_input],
            outputs=upload_status
        )

    # 事件绑定
    submit_btn.click(
        fn=submit_query,
        inputs=[query_input, thread_id_input],
        outputs=[
            research_output, analysis_output, web_output,
            final_output, status_output, thread_display
        ]
    )
    approve_btn.click(
        fn=approve_and_get_answer,
        inputs=[thread_display],
        outputs=[final_output, approve_status]
    )

    gr.Markdown("""
     --- 
    ### 工作流说明
    1. 提交问题后，系统会并行调用 **研究、分析、网络搜索** 智能体
    2. 执行到 **整合阶段前会自动暂停**
    3. 你可在此审查各智能体结果，确认无误后点击 **“批准并生成最终答案”**
    """)

    demo.load(fn=get_kb_stats, inputs=[], outputs=kb_stats_output)
    # ===== 结束新增 =====

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=6008)