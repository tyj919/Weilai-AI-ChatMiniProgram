import re
import os
import random
import requests
import gradio as gr
from flask import Flask, request, jsonify
import threading

# ====================  ====================
zhipu_key = os.getenv("ZHIPU_API_KEY", "cff7ee80e828486a88c75473f9f1ff2c.k3E9U6likrKQJTiD")
silicon_key = os.getenv("SILICON_API_KEY", "sk-wayxaltcgkfqpnlhskypwnizcdbdtasdffxbxxncslfsdtqr")

ZHIPU_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
SILICON_API_URL = "https://api.siliconflow.cn/v1/chat/completions"

# ==================== 全局对话历史 ====================
conversation_history = []

# ==================== 静态知识库 ====================
KNOWLEDGE_BASE = """
【蔚来全系车型简介】（续航均为CLTC综合工况，100kWh电池包为例）
- ET5：智能电动中型轿跑，续航最高710km，百公里加速4.3秒，标配NIO Pilot辅助驾驶。
- ET5T：ET5的猎装版，空间更大，兼具运动与实用，续航最高680km。
- ES6：智能电动全能SUV，续航最高625km，0-100km/h仅4.5秒，适合家庭出行。
- ET7：智能电动旗舰轿车，续航最高705km，0-100km/h仅3.8秒，搭载超感系统与超算平台。
- ES8：智能电动旗舰SUV，六座/七座布局，续航最高605km，空气悬架，豪华舒适。
- EC6：智能电动轿跑SUV，续航最高630km，溜背造型，运动风格。
- EC7：智能电动旗舰轿跑SUV，续航最高635km，极致优雅与性能。
（更多车型及电池包选择请咨询NIO顾问）

【质保政策】
- 首任车主（非营运）整车质保：6年或15万公里（以先到为准）。
- 三电系统（动力电池、驱动电机、电控系统）：首任车主享10年不限里程质保。
- 非首任车主或营运车辆，整车质保3年或12万公里，三电系统8年或15万公里。
- 定期在蔚来服务中心保养，确保质保有效性。

【换电服务】
- 蔚来全系支持换电，截至2024年中，全国已建成超2400座换电站，3分钟满电出发。
- 高速换电网络覆盖主要干线及城市核心区，长途出行更自由。
- 换电费用按度收费，电费+服务费，不同时段略有差异，也可使用换电权益券。

【BaaS电池租赁方案（2024年调整后）】
- 两种电池选择：75kWh标准续航电池、100kWh长续航电池。
- 选择BaaS购车，车价直减：75kWh电池减7万元，100kWh电池减12.8万元。
- 月租价格（2024年3月起）：75kWh电池728元/月，100kWh电池1128元/月。
- 支持灵活升级，按需切换，电池常新。

【售后与服务】
- NIO App一键预约保养，可免费上门取送车（部分城市覆盖）。
- 服务无忧套餐（可选，约13800元/年）包含免费维修、保养、保险、增强领航辅助等，详情咨询当地蔚来中心。
- 免费道路救援、车辆健康检查等全生命周期服务。
"""

# ==================== 工具函数 ====================
def book_maintain(car_model: str) -> str:
    """预约上门保养（目前支持所有量产车型）"""
    valid_models = ["ET5", "ET5T", "ES6", "ET7", "ES8", "EC6", "EC7"]
    if car_model.upper() in valid_models:
        return f"好的呢，已经帮您预约了{car_model.upper()}的上门保养服务哦～\n我们的服务专员会在24小时内给您打电话确认时间哒，请保持手机畅通哟～\n有任何问题随时找我呀！"
    else:
        return f"亲亲～您提到的{car_model}可能输入有误哦，目前支持ET5/ET5T/ES6/ET7/ES8/EC6/EC7预约保养～\n请核对一下车型名称，或联系您的专属顾问了解更多细节哟～"

def query_baas(batt_size: str) -> str:
    """查询电池月租价格（2024年3月起执行）"""
    if "75" in batt_size:
        return f"亲爱的～75度标准续航电池月租现在只要728元/月哦～\n选择BaaS购车，车价直减7万元，后期还能灵活升级，超划算哒！\n需要我帮您算算具体方案吗？"
    elif "100" in batt_size:
        return f"亲～100度长续航电池月租是1128元/月哟～\n车价能直减12.8万元，轻松享受长续航的快乐～\n您是在考虑换电方案吗？需要了解更多细节吗？"
    else:
        return f"亲爱的～BaaS电池租赁目前有75度和100度两种选择呢～\n您想了解哪一种呀？或者我给您介绍一下两种方案的区别？"

def query_free_electric() -> str:
    """查询当前免费换电权益（政策已调整）"""
    return (f"亲爱的～目前新购车用户的具体换电权益会根据市场活动调整，不再是固定的每月免费换电次数啦～\n"
            f"建议您联系NIO顾问或登录蔚来App查看最新购车礼遇哦，有时候会赠送换电体验券呢！\n"
            f"您是想了解某个车型的购车权益吗？我可以帮您简单介绍～")

# ==================== 追问模板 ====================
FOLLOW_UP_QUESTIONS = {
    "质保": ["您是已经提车了，还是在考虑购买呀？", "需要我帮您查一下具体车型的质保细节吗？"],
    "续航": ["您平时长途出行多吗？", "要不要了解一下换电网络覆盖情况呀？"],
    "换电": ["您所在的城市换电站多吗？", "需要我帮您查附近的换电站位置吗？"],
    "保养": ["您的爱车跑了多少公里啦？", "需要帮您预约保养时间吗？"],
    "车型": ["您更看重空间还是性能呢？", "预算大概在哪个范围呀？"],
    "BaaS": ["您平时充电方便吗？", "考虑过换电模式吗？"],
    "购买": ["您更喜欢轿车还是SUV呀？", "需要我帮您推荐一下车型吗？"],
    "售后": ["您遇到什么问题了吗？", "需要我帮您联系售后服务吗？"],
    "免费换电": ["购车权益现在变化很快呢，需要帮您转接专属顾问吗？"]
}

def generate_follow_up(user_input: str) -> str:
    """根据用户输入生成温柔的追问"""
    for topic, questions in FOLLOW_UP_QUESTIONS.items():
        if topic in user_input or topic in user_input.lower():
            return "\n" + random.choice(questions)
    return ""

# ==================== 工具调用解析 ====================
def extract_tool_call(text: str):
    """从模型输出中提取【函数名|参数】"""
    pattern = r"【(.*?)】"
    matches = re.findall(pattern, text)
    if not matches:
        return None, None
    inner = matches[0]
    if "|" in inner:
        func, arg = inner.split("|", 1)
    else:
        func, arg = inner, ""
    return func.strip(), arg.strip()

# ==================== 模型分流判断 ====================
def should_use_zhipu(user_input: str) -> bool:
    """根据用户输入关键词决定是否使用智谱模型（处理工具调用）"""
    keywords = ["预约", "保养", "电池月租", "月租", "baas", "免费换电", "换电套餐", "上门保养"]
    user_lower = user_input.lower()
    return any(k in user_lower for k in keywords)

# ==================== API调用封装 ====================
def call_zhipu(messages: list) -> str:
    if not zhipu_key or zhipu_key.startswith("your_"):
        return "【book_maintain|ET5】"  # 演示用，实际部署需真实密钥
    headers = {
        "Authorization": f"Bearer {zhipu_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "glm-4-flash",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1024
    }
    try:
        resp = requests.post(ZHIPU_API_URL, json=payload, headers=headers, timeout=30)
        if resp.status_code == 200:
            result = resp.json()
            if "choices" in result:
                return result["choices"][0]["message"]["content"]
            else:
                return f"API返回异常: {result}"
        else:
            return f"API请求失败，状态码: {resp.status_code}"
    except Exception as e:
        return f"网络出了点小问题: {str(e)}"

def call_silicon(messages: list) -> str:
    if not silicon_key or silicon_key.startswith("your_"):
        return "抱歉呀，硅基API密钥还没配置呢，暂时无法回答您的问题～"
    headers = {
        "Authorization": f"Bearer {silicon_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "Qwen/Qwen2.5-7B-Instruct",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1024
    }
    try:
        resp = requests.post(SILICON_API_URL, json=payload, headers=headers, timeout=30)
        if resp.status_code == 200:
            result = resp.json()
            if "choices" in result:
                return result["choices"][0]["message"]["content"]
            else:
                return f"API返回异常: {result}"
        else:
            return f"API请求失败，状态码: {resp.status_code}"
    except Exception as e:
        return f"网络有点小波动呢，请再问我一次吧～"

# ==================== 系统提示词  ====================
SYSTEM_SILICON = f"""你是蔚来NIO的官方暖心小管家，性格超级温柔、亲切可爱，说话就像贴心的好朋友一样～

你的任务是：
1. 用温暖、甜美的语气回答用户问题，多用"呀"、"呢"、"哟"、"哒"这些可爱的语气词
2. 回复要简短、口语化，像聊天一样自然，不要生硬地罗列条款
3. 可以适当用一些可爱的表情文字，但不要太多哦～

【知识库】
{KNOWLEDGE_BASE}

注意：如果用户提到预约保养、查电池月租、查免费换电等需要办理的业务，你不用处理，会有专门的业务助手来帮忙～
你只负责轻松聊天和知识解答，要保持甜甜的微笑哦～😊"""

SYSTEM_ZHIPU = f"""你是蔚来NIO的官方暖心小管家，既亲切又专业，说话温柔得像春风一样～

【知识库】
{KNOWLEDGE_BASE}

重要规则：
1. 如果用户想预约上门保养、查询电池月租、或者询问新车免费换电套餐，你绝对不能自己编造结果，必须用固定格式输出工具调用指令：【函数名|参数】。可用工具：
   - book_maintain：车型（ET5/ET5T/ES6/ET7/ES8/EC6/EC7），如【book_maintain|ET5】
   - query_baas：电池度数（75度/100度），如【query_baas|100度】
   - query_free_electric：无参数，如【query_free_electric|】
2. 输出工具指令时，只输出那一行格式，不要再加额外文字。
3. 其他普通问题（车型参数、质保政策、换电概念等）请根据知识库温柔解答，要用亲切的语气，多用"呀"、"呢"、"哟"、"哒"这些可爱的语气词，就像和好朋友聊天一样～
4. 回答完后可以适当追问一句，让对话更自然～"""

SYSTEM_REFINE = """你是蔚来NIO的官方暖心小管家，回复要超级温柔、亲切可爱，像和好朋友聊天一样～

请把下面的工具执行结果，用甜甜的语气润色一下，加上适当的语气词，让回复更温暖～
可以适当加一些可爱的表情，但不要太多哦～😊

工具结果：
{tool_result}

请用蔚来暖心客服的语气回复用户，要自然、亲切、简短～"""

# ==================== 对话处理核心 ====================
def agent_reply(user_input: str):
    """核心对话函数，给小程序调用"""
    global conversation_history
    
    if not user_input.strip():
        return "请输入内容哦～"
    
    use_zhipu = should_use_zhipu(user_input)
    system_prompt = SYSTEM_ZHIPU if use_zhipu else SYSTEM_SILICON
    
    messages = [{"role": "system", "content": system_prompt}]
    messages.append({"role": "user", "content": user_input})
    
    if use_zhipu:
        response = call_zhipu(messages)
    else:
        response = call_silicon(messages)
    
    func, arg = extract_tool_call(response)
    if func:
        if func == "book_maintain":
            tool_result = book_maintain(arg)
        elif func == "query_baas":
            tool_result = query_baas(arg)
        elif func == "query_free_electric":
            tool_result = query_free_electric()
        else:
            tool_result = "抱歉呀，这个功能我还没学会呢，请联系您的蔚来顾问哟～"
        
        # 密钥未配置时直接返回原始结果
        if not zhipu_key or zhipu_key.startswith("your_"):
            final_reply = tool_result
        else:
            refine_prompt = SYSTEM_REFINE.format(tool_result=tool_result)
            refine_messages = [{"role": "system", "content": refine_prompt}]
            final_reply = call_zhipu(refine_messages)
        return final_reply
    else:
        base_reply = response
        follow_up = generate_follow_up(user_input)
        return base_reply + follow_up

# ==================== Flask 小程序接口 ====================
app = Flask(__name__)

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.route("/chat", methods=["POST", "OPTIONS"])
def api_chat():
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json(silent=True) or {}
    msg = (data.get("question") or data.get("msg") or "").strip()
    ans = agent_reply(msg)
    return jsonify({"ans": ans, "answer": ans})

# ==================== Gradio 网页版 ====================
def respond_gradio(user_input: str, chat_history: list):
    if not user_input.strip():
        return chat_history, ""

    ans = agent_reply(user_input)
    chat_history = chat_history + [
        {"role": "user", "content": user_input},
        {"role": "assistant", "content": ans},
    ]
    return chat_history, ""


def clear_chat():
    return [], ""

# ==================== 启动 ====================
if __name__ == "__main__":
    # 启动接口（给小程序用）
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=5000, debug=False)).start()
    # 启动网页版
    with gr.Blocks(title="蔚来NIO智能客服") as demo:
        gr.Markdown("# 🚗 蔚来NIO智能客服")
        gr.Markdown("我是你的暖心小管家～关于车型、质保、换电、BaaS、保养预约都可以问我呀～😊")
        chatbot = gr.Chatbot(label="💬 对话窗口", height=500)
        user_input = gr.Textbox(label="✨ 输入你的问题", placeholder="比如：ET5续航多少呀？电池月租怎么算呢？预约保养ES6～")
        with gr.Row():
            send_btn = gr.Button("💝 发送", variant="primary")
            clear_btn = gr.Button("🧹 清空对话")
        send_btn.click(respond_gradio, inputs=[user_input, chatbot], outputs=[chatbot, user_input])
        user_input.submit(respond_gradio, inputs=[user_input, chatbot], outputs=[chatbot, user_input])
        clear_btn.click(clear_chat, outputs=[chatbot, user_input])
    demo.launch()