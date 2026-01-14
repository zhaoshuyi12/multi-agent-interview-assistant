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

def approve_and_get_answer(thread_id: str,feedback: str):
    if not thread_id.strip():
        return "", "请输入有效的 Thread ID"
    try:
        payload = {"feedback": feedback}
        resp = requests.post(f"{BASE_URL}/approve/{thread_id}",json=payload, timeout=60)
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
        resp = requests.get(f"{BASE_URL}/kb/stats")
        if resp.status_code == 200:
            data = resp.json()
            stats = data.get("stats", "无数据")
            if isinstance(stats, dict):
                return json.dumps(stats, ensure_ascii=False, indent=2)
            print(stats)
            return str(stats)
        else:
            import traceback
            traceback.print_exc()
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
with gr.Blocks(title="多智能体协作与决策系统") as demo:
    gr.Markdown("# 🤖 智能体协作与决策系统")
    gr.Markdown("""
        系统将根据您的问题调度多个智能体。在最终整合前，系统会**暂停并展示中间过程**。
        - **批准**：输入“同意”并提交，获取最终总结。
        - **重做**：输入具体意见并提交，智能体将根据反馈重新执行任务。
        """)

    # ===== ✅【新增】第 2 处：插入知识库状态面板 =====
    with gr.Accordion("📚 知识库状态", open=False):
        kb_stats_output = gr.Textbox(label="当前知识库统计", interactive=False, lines=4)
        print(kb_stats_output)
        refresh_kb_btn = gr.Button("🔄 刷新状态")
        refresh_kb_btn.click(fn=get_kb_stats, inputs=[], outputs=kb_stats_output)
    # ===== 结束新增 =====

    with gr.Row():
        with gr.Column():
            query_input = gr.Textbox(label="🔍 输入你的问题", lines=3, placeholder="例如：'分析特斯拉最近股价趋势，并查找相关新闻'")
            thread_id_input = gr.Textbox(label="🆔 Thread ID ", value="")
            submit_btn = gr.Button("🚀 提交查询", variant="primary")
        with gr.Column():
            status_output = gr.Textbox(label="📌 状态", interactive=False)
            thread_display = gr.Textbox(label="🔖 当前 Thread ID", interactive=False)

    with gr.Tabs():
        with gr.Tab("📚 研究结果 (内部知识库)"):
            research_output = gr.Textbox(interactive=False, lines=8)
            clear_research_btn = gr.Button("🗑️ 清空研究结果")
        with gr.Tab("📊 分析结果 (计算器/统计)"):
            analysis_output = gr.Textbox(interactive=False, lines=8)
        with gr.Tab("🌐 网络搜索结果"):
            web_output = gr.Textbox(interactive=False, lines=8)
        with gr.Tab("✅ 最终答案"):
            final_output = gr.Textbox(label="生成的答案内容", interactive=False, lines=10)

            with gr.Row():
                # 🚀 绿色大按钮，用于直接通过
                approve_btn = gr.Button("✅ 批准并生成 (同意)", variant="primary")

            # 使用折叠面板把反馈框藏起来，保持界面整洁
            with gr.Accordion("❌ 结果不满意？填写修改意见", open=False):
                feedback_input = gr.Textbox(
                    label="修改意见",
                    placeholder="例如：数据不够准确，请重新搜索...",
                    lines=3
                )
                retry_btn = gr.Button("🔄 提交意见并重新生成")

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
        fn=lambda :("⏳ 正在拼命运行中...", "", "", "", ""),
        outputs=[
            status_output, research_output, analysis_output, web_output, final_output]
    ).then(
        fn=submit_query,
        inputs=[query_input, thread_id_input],
        outputs=[
            research_output, analysis_output, web_output,
            final_output, status_output, thread_display
        ]
    )
    approve_btn.click(
        fn=approve_and_get_answer,
        inputs=[thread_display, feedback_input],
        outputs=[final_output, approve_status]
    )
    retry_btn.click(
        fn=approve_and_get_answer,
        inputs=[
            thread_display,  # 1. 告诉后端是哪个任务
            feedback_input  # 2. 告诉后端具体的修改意见
        ],
        outputs=[
            final_output,  # 刷新最终答案框（显示“处理中...”）
            approve_status  # 刷新状态提示
        ]
    )


    gr.Markdown("""
   --- 
### 🔄 工作流说明
1. **并行处理**：提交问题后，系统会同时派出 **研究 📚、分析 📊、网络搜索 🌐** 三个智能体。
2. **人工节点**：在生成最终答案前，系统会**自动暂停**，请你在上方标签页查看各智能体的初步结果。
3. **反馈与决策**：
   * ✅ **满意**：在意见框输入“同意”，点击提交，系统将整合出最终报告。
   * ❌ **不满意**：在意见框输入具体的修改建议（如“请更多参考网络搜索的结果”），系统将**重新运行**整个流程。
    """)

    demo.load(fn=get_kb_stats, inputs=[], outputs=kb_stats_output)
    # ===== 结束新增 =====

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=6008)