import os
import json
import traceback

import gradio as gr

from bioagent.agents import BioAgent
from bioagent.graph.engine import run_graph


def build_agent():
    # 从环境变量读取 LLM 配置；提供合理默认，不再硬编码密钥
    os.environ.setdefault("OPENAI_API_BASE", os.getenv("OPENAI_API_BASE", "https://api.ai190.com/v1"))
    model = os.getenv("OPENAI_MODEL_NAME", "gemini-2.5-pro")
    tools_model = os.getenv("TOOLS_MODEL_NAME", model)
    openai_key = os.getenv("OPENAI_API_KEY")

    api_keys = {
        "OPENAI_API_KEY": openai_key or "",
        "MCP_CONFIG": os.getenv("MCP_CONFIG", os.path.join(os.getcwd(), "mcp_config.yaml")),
    }
    return BioAgent(model=model, tools_model=tools_model, openai_api_key=openai_key, api_keys=api_keys)


agent = build_agent()


def chat_fn(message, history):
    try:
        formatted_history = [(h[0] or "", h[1] or "") for h in (history or [])]
        resp = agent.run(message, history=formatted_history)
        return resp
    except Exception as e:
        return f"Error: {e}\n{traceback.format_exc()}"


with gr.Blocks(title="BioAgent", theme=gr.themes.Soft()) as demo:
    gr.Markdown("**BioAgent** · 生物逆合成与知识图谱增强助手 (MCP + Biomni 工具)")

    # 状态：工具事件日志
    events_state = gr.State([])

    with gr.Tabs():
        with gr.TabItem("Chat"):
            chatbot = gr.Chatbot(height=500, type="messages")
            with gr.Row():
                msg = gr.Textbox(label="输入问题", scale=8, placeholder="提出你的问题，Agent 会规划→调用工具→反思…")
                send_btn = gr.Button("发送", variant="primary", scale=1)
            clear = gr.ClearButton([msg, chatbot])

        with gr.TabItem("Logs"):
            gr.Markdown("工具调用日志 / 时序（最新在下）")
            logs = gr.JSON(label="Step Logs", value={})

        with gr.TabItem("Plan"):
            plan_box = gr.Textbox(label="计划 / 反思（摘要）", lines=10)

    def respond(user_message, chat_history, events):
        use_graph = os.getenv("USE_LANGGRAPH", "0").lower() in ("1", "true", "yes")
        if use_graph:
            # 使用 LangGraph 引擎：计划→工具→反思→答案，并生成事件（同步调用）
            answer, evs, plan = run_graph(user_message)
            reply = answer
            events = (events or []) + (evs or [])
            plan_summary = "\n".join([f"- {p}" for p in (plan or [])]) or "(planner 未返回计划)"
        else:
            reply = chat_fn(user_message, chat_history)
            # 取回工具事件并追加至状态（旧链路）
            try:
                ev = agent.pop_tool_events()
                events = (events or []) + ev
            except Exception:
                pass
            plan_summary = "计划与结果见日志；若需更详细，请启用 USE_LANGGRAPH。"

        chat_history = chat_history + [[user_message, reply]]
        # 日志展示：显示为 {"events": [...]} 结构
        logs_value = {"events": events}
        return "", chat_history, events, logs_value, plan_summary

    send_btn.click(respond, [msg, chatbot, events_state], [msg, chatbot, events_state, logs, plan_box])
    msg.submit(respond, [msg, chatbot, events_state], [msg, chatbot, events_state, logs, plan_box])

if __name__ == "__main__":
    # 优先使用环境变量 PORT；未设置时让 Gradio 自动分配可用端口
    port_env = os.getenv("GRADIO_SERVER_PORT") or os.getenv("PORT")
    # 将 '0' 视为未指定端口
    try:
        server_port = int(port_env) if (port_env and str(port_env) != "0") else None
    except Exception:
        server_port = None

    demo.launch(
        server_name=os.getenv("GRADIO_SERVER_NAME", "127.0.0.1"),
        server_port=server_port,
        share=False,
    )


