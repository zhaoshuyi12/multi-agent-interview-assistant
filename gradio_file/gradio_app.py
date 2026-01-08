# gradio_app.py
import gradio as gr
import requests
import json

# 后端地址（确保 main.py 正在运行）
BASE_URL = "http://localhost:8000"


def submit_query(query: str, thread_id: str):
    """提交初始查询，触发多智能体流程（停在 integrate 前）"""
    if not query.strip():
        return ("", "", "", "", "", "请输入问题", thread_id)

    try:
        resp = requests.post(f"{BASE_URL}/query", json={
            "query": query,
            "thread_id": thread_id
        }, timeout=60)

        if resp.status_code == 200:
            data = resp.json()
            status = data.get("message", "已暂停，等待审批")

            research = _format_result(data.get("research_result", {}))
            analysis = _format_result(data.get("analysis_result", {}))
            web = _format_result(data.get("web_search_result", {}))

            return (
                research, analysis, web,
                "",  # final answer 留空
                status,
                data["thread_id"]
            )
        else:
            err = resp.json().get("detail", "未知错误")
            return ("", "", "", "", f"❌ 提交失败: {err}", thread_id)

    except Exception as e:
        return ("", "", "", "", f"❌ 请求异常: {str(e)}", thread_id)


def approve_and_get_answer(thread_id: str):
    """批准并继续执行到最终答案"""
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


def _format_result(result):
    if not result:
        return "无结果"
    if isinstance(result, dict):
        if "answer" in result:
            return result["answer"]
        else:
            return json.dumps(result, ensure_ascii=False, indent=2)
    return str(result)


# ===== Gradio UI =====
with gr.Blocks(title="多智能体协作系统") as demo:
    gr.Markdown("# 🤖 多智能体协作系统 (Research + Analysis + Web Search)")
    gr.Markdown("系统会根据问题自动调用不同智能体，并在整合前暂停，等待人工审核。")

    with gr.Row():
        with gr.Column():
            query_input = gr.Textbox(label="🔍 输入你的问题", lines=3,
                                     placeholder="例如：'分析特斯拉最近股价趋势，并查找相关新闻'")
            thread_id_input = gr.Textbox(label="🆔 Thread ID (可选)", value="default")
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

    # 事件绑定
    submit_btn.click(
        fn=submit_query,
        inputs=[query_input, thread_id_input],
        outputs=[research_output, analysis_output, web_output, final_output, status_output, thread_display]
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

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=6008)