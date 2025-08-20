# -*- coding: utf-8 -*-
"""
Opentrons协议生成器 - LangGraph
======================================

用于自动生成Opentrons机器人协议。
主要功能包括：
1. 根据用户目标生成标准操作程序(SOP)
2. 将SOP转换为可执行的Python代码
3. 自动验证和修复代码错误
4. 提供流式生成和迭代优化

作者: Gaoyuan

"""

import os
import requests
import re # 用于正则表达式匹配，提取错误信息
import ast # 用于快速Python语法检查
import json # 用于处理Planner返回的JSON格式修改计划
from typing import Optional, Callable, Dict, Any, TypedDict, Annotated, Literal
from datetime import datetime  # 用于给流式事件添加时间戳
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain.chains import LLMChain
from langgraph.graph import StateGraph, END, START
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.graph.message import add_messages

# Use absolute imports from project root
from backend.config import (
    api_key, base_url, model_name,
    DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_INTENT_MODEL, # Import new config
    LABWARE_FOR_OT2, LABWARE_FOR_FLEX,
    INSTRUMENTS_FOR_OT2, INSTRUMENTS_FOR_FLEX,
    MODULES_FOR_OT2, MODULES_FOR_FLEX,
    CODE_EXAMPLES, COMMON_PITFALLS_OT2
)
from backend.diff_utils import apply_diff
from backend.opentrons_utils import run_opentrons_simulation, SimulateToolInput
from backend.prompts import (
    SOP_GENERATION_PROMPT_TEMPLATE, 
    CODE_GENERATION_PROMPT_TEMPLATE_FLEX,
    CODE_GENERATION_PROMPT_TEMPLATE_OT2,
    CODE_CORRECTION_DIFF_TEMPLATE_FLEX,
    CODE_CORRECTION_DIFF_TEMPLATE_OT2,
    CODE_PLANNER_PROMPT_TEMPLATE, # 新增：Planner模板
    CODE_DIFFER_PROMPT_TEMPLATE, # 新增：Differ模板  
    CODE_DIFFER_FIX_PROMPT_TEMPLATE, # 新增：Differ修复模板
    # English Prompts
    ENG_SOP_GENERATION_PROMPT_TEMPLATE,
    ENG_CODE_GENERATION_PROMPT_TEMPLATE_FLEX,
    ENG_CODE_GENERATION_PROMPT_TEMPLATE_OT2,
    ENG_CODE_CORRECTION_DIFF_TEMPLATE_FLEX,
    ENG_CODE_CORRECTION_DIFF_TEMPLATE_OT2,
    ENG_CODE_PLANNER_PROMPT_TEMPLATE,
    ENG_CODE_DIFFER_PROMPT_TEMPLATE,
    ENG_SOP_CONVERSATION_CLASSIFIER_PROMPT_TEMPLATE,
    ENG_CODE_CONVERSATION_CLASSIFIER_PROMPT_TEMPLATE,
    ENG_GENERAL_CODE_CHAT_PROMPT_TEMPLATE,
)

# ============================================================================
# 数据结构定义部分
# ============================================================================

class CodeGenerationState(TypedDict):
    """
    LangGraph状态管理类
    
    这个类定义了代码生成过程中需要跟踪的所有状态信息。
    LangGraph使用这个状态在不同的处理节点之间传递数据。
    
    属性说明:
        original_sop (str): 原始的标准操作程序文本，在整个流程中不会改变
        hardware_context (str): 硬件配置信息，包括机器人型号、移液器等
        python_code (Optional[str]): 当前版本的Python代码，会通过diff进行迭代更新
        llm_diff_output (Optional[str]): LLM生成的原始diff文本，用于日志和调试
        simulation_result (Optional[dict]): 模拟运行的结果，包含成功/失败信息
        feedback_for_llm (Dict[str, str]): 给大语言模型的结构化反馈信息，用于错误修正
        attempts (int): 当前尝试次数，用于控制重试逻辑
        max_attempts (int): 最大尝试次数，避免无限循环
        iteration_reporter (Optional[Callable]): 回调函数，用于向前端报告进度
    """
    # 输入数据 - 在运行过程中不会改变
    original_sop: str
    hardware_context: str
    
    # 会被更新的数据
    python_code: Optional[str]
    llm_diff_output: Optional[str]
    simulation_result: Optional[dict]
    feedback_for_llm: Dict[str, str]
    
    # 控制流程的变量
    attempts: int
    max_attempts: int
    
    # 用于报告进度的回调函数
    iteration_reporter: Optional[Callable[[Dict[str, Any]], None]]

# ============================================================================
# SOP生成功能部分
# ============================================================================

def generate_sop_with_langchain(user_goal_with_hardware_context: str) -> str:
    """
    使用本地LangChain生成标准操作程序(SOP)
    
    这个函数接收用户的实验目标和硬件配置，然后使用大语言模型
    生成详细的、可执行的标准操作程序。
    
    参数:
        user_goal_with_hardware_context (str): 组合输入，包含硬件配置和用户目标，
                                              用"---"分隔
    
    返回:
        str: 生成的SOP markdown文本，或者错误信息
    
    工作流程:
        1. 解析输入，分离硬件配置和用户目标
        2. 调用SOP生成链(sop_generation_chain)
        3. 格式化输出结果
        4. 处理可能出现的异常
    """
    try:
        # 步骤1: 分割输入以提取硬件配置和用户目标
        if "---" in user_goal_with_hardware_context:
            parts = user_goal_with_hardware_context.split("---", 1)
            hardware_context = parts[0].strip()
            user_goal = parts[1].strip()
        else:
            # 如果没有找到分隔符，假设整个输入都是用户目标
            hardware_context = "No specific hardware configuration provided."
            user_goal = user_goal_with_hardware_context.strip()
        
        # 打印调试信息，帮助开发者了解处理过程
        print(f"Debug - [generate_sop_with_langchain] 原始输入长度: {len(user_goal_with_hardware_context)}")
        print(f"Debug - [generate_sop_with_langchain] 硬件配置长度: {len(hardware_context)}")
        print(f"Debug - [generate_sop_with_langchain] 硬件配置内容:\n{hardware_context}")
        print(f"Debug - [generate_sop_with_langchain] 用户目标: {user_goal}")
        
        # 步骤2: 使用本地LangChain生成SOP
        print(f"Debug - [generate_sop_with_langchain] 开始使用本地LangChain生成SOP")
        
        # 调用预先配置的SOP生成链
        sop_result = sop_generation_chain.run({
            "hardware_context": hardware_context,
            "user_goal": user_goal
        })
        
        print(f"Debug - [generate_sop_with_langchain] SOP生成完成，长度: {len(sop_result)} 字符")
        
        # 步骤3: 确保返回格式一致
        # 如果生成的SOP没有标准标题，自动添加
        if not sop_result.startswith("## Generated Standard Operating Procedure"):
            sop_result = f"## Generated Standard Operating Procedure (SOP)\n\n{sop_result}"
        
        return sop_result
        
    except Exception as e:
        # 步骤4: 错误处理 - 捕获并记录所有异常
        print(f"Debug - [generate_sop_with_langchain] SOP生成异常: {e}")
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Debug - [generate_sop_with_langchain] 完整错误堆栈: {error_traceback}")
        # 返回标准化的错误字符串，而不是抛出原始异常
        return f"Error: An unexpected error occurred during SOP generation. Details: {str(e)}\nTraceback:\n{error_traceback}"

# ============================================================================
# 大语言模型配置部分
# ============================================================================

# LLM for complex generation tasks (SOPs)
llm = ChatOpenAI(
    model_name=model_name,
    openai_api_base=base_url,
    openai_api_key=api_key,
    temperature=0.0,
    streaming=True, 
    max_retries=2,
    request_timeout=60
)

# LLM for faster code generation and correction tasks
code_gen_llm = ChatOpenAI(
    model_name=DEEPSEEK_INTENT_MODEL, # Re-using the intent model name, "DeepSeek-V3-Fast"
    openai_api_base=DEEPSEEK_BASE_URL,
    openai_api_key=DEEPSEEK_API_KEY,
    temperature=0.0,
    streaming=False, # Code generation should not be streaming token by token in the backend
    max_retries=2,
    request_timeout=120 # Give more time for code generation
)

# ============================================================================
# 提示词模板对象创建
# ============================================================================

# 创建SOP生成的提示词模板对象
SOP_GENERATION_PROMPT = PromptTemplate(
    input_variables=["hardware_context", "user_goal"],  # 输入变量名
    template=ENG_SOP_GENERATION_PROMPT_TEMPLATE             # 模板内容
)

# 为Flex创建代码生成的提示词模板对象
CODE_GEN_PROMPT_FLEX = PromptTemplate(
    input_variables=["hardware_context", "sop_text", "feedback_for_llm",
                     "valid_labware_list_str", "valid_instrument_list_str", 
                     "valid_module_list_str", "code_examples_str", "previous_code",
                     "apiLevel"],
    template=ENG_CODE_GENERATION_PROMPT_TEMPLATE_FLEX
)

# 为OT-2创建代码生成的提示词模板对象
CODE_GEN_PROMPT_OT2 = PromptTemplate(
    input_variables=["hardware_context", "sop_text", "feedback_for_llm",
                     "valid_labware_list_str", "valid_instrument_list_str", 
                     "valid_module_list_str", "code_examples_str", "previous_code",
                     "apiLevel", "common_pitfalls_str"],
    template=ENG_CODE_GENERATION_PROMPT_TEMPLATE_OT2
)

# 创建用于生成代码修正Diff的提示词模板对象
CODE_CORRECTION_PROMPT_FLEX = PromptTemplate(
    input_variables=[
        "analysis_of_failure", "recommended_action", "full_error_log", "previous_code",
        "valid_labware_list_str", "valid_instrument_list_str", "valid_module_list_str"
    ],
    template=ENG_CODE_CORRECTION_DIFF_TEMPLATE_FLEX
)

# 为OT-2创建代码修正Diff的提示词模板对象
CODE_CORRECTION_PROMPT_OT2 = PromptTemplate(
    input_variables=[
        "analysis_of_failure", "recommended_action", "full_error_log", "previous_code",
        "valid_labware_list_str", "valid_instrument_list_str", "valid_module_list_str"
    ],
    template=ENG_CODE_CORRECTION_DIFF_TEMPLATE_OT2
)

# ============================================================================
# LangChain链式处理配置部分
# ============================================================================

# 初始化SOP生成链 (uses powerful 'llm' instance)
sop_generation_chain = LLMChain(llm=llm, prompt=SOP_GENERATION_PROMPT)

# 初始化代码生成链 (为Flex和OT-2分别创建)
code_gen_chain_flex = LLMChain(llm=code_gen_llm, prompt=CODE_GEN_PROMPT_FLEX)
code_gen_chain_ot2 = LLMChain(llm=code_gen_llm, prompt=CODE_GEN_PROMPT_OT2)

# 初始化代码修正链 (为Flex和OT-2分别创建)
code_correction_chain_flex = LLMChain(llm=code_gen_llm, prompt=CODE_CORRECTION_PROMPT_FLEX)
code_correction_chain_ot2 = LLMChain(llm=code_gen_llm, prompt=CODE_CORRECTION_PROMPT_OT2)

# ============================================================================
# 流式生成功能部分
# ============================================================================

async def generate_sop_with_langchain_stream(hardware_context: str, user_goal: str):
    """
    使用LangChain以流式方式异步生成SOP
    
    这个函数实现了真正的流式输出，能够实时显示LLM生成的每个token，
    而不是等待完整结果。这大大改善了用户体验，特别是对于长文本生成。
    
    参数:
        hardware_context (str): 硬件配置信息
        user_goal (str): 用户的实验目标
    
    生成器返回:
        str: 每次yield一个token字符串
    
    技术细节:
        - 使用async/await实现异步处理
        - 直接调用llm.astream()绕过LLMChain的缓冲
        - 每个token立即yield给调用者
    """
    print("Debug - [generate_sop_with_langchain_stream] 开始使用LLM astream 实时生成SOP")
    
    try:
        # 准备链的输入参数
        chain_input = {"hardware_context": hardware_context, "user_goal": user_goal}
        
        # 为了实现真正的token级流式输出，我们绕过LLMChain，直接调用llm.astream
        # 步骤1: 手动格式化提示词
        formatted_prompt = SOP_GENERATION_PROMPT.format(**chain_input)
        
        print(f"Debug - [stream] Prompt已格式化，准备直接调用llm.astream")
        
        # 步骤2: 直接调用llm.astream，它返回一个包含AIMessageChunk的异步迭代器
        token_count = 0
        async for chunk in llm.astream(formatted_prompt):
            # AIMessageChunk有一个.content属性，包含实际的token字符串
            if chunk and hasattr(chunk, 'content') and chunk.content:
                token_count += 1
                # print(f"Debug - [stream] Yielding token #{token_count}")
                yield chunk.content  # 立即yield每个token
        
        print(f"Debug - [generate_sop_with_langchain_stream] 流式生成完成，总共产出 {token_count} 个token")
        
    except Exception as e:
        print(f"Error - [generate_sop_with_langchain_stream] 流式生成失败: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        # 错误时提供一个回退信息
        yield f"Error: Streaming failed. Details: {str(e)}"

# ============================================================================
# 错误分析功能部分
# ============================================================================

def extract_error_from_simulation(simulation_output: str) -> str:
    """
    从模拟输出中智能提取相关错误信息
    
    当Opentrons模拟运行失败时，输出通常包含大量信息。这个函数
    使用多种策略来提取最有用的错误信息，帮助后续的错误修正。
    
    参数:
        simulation_output (str): 模拟运行的完整输出字符串
    
    返回:
        str: 提取的关键错误信息
    
    工作策略:
        1. 优先查找"Cleaned STDERR"部分（最干净的错误信息）
        2. 其次，查找并返回最后一个Traceback的完整内容
        3. 如果没有，搜索标准错误关键词
        4. 如果仍然没有，查找警告信息
        5. 最后提供通用的失败信息
    """
    # 策略1: 首先，尝试查找Cleaned STDERR部分
    cleaned_stderr_match = re.search(r"--- Cleaned STDERR ---\n(.*?)(?:\n---|\Z)", simulation_output, re.DOTALL)
    if cleaned_stderr_match and cleaned_stderr_match.group(1).strip():
        # 如果有非空的cleaned stderr，优先使用它
        # 但我们仍然要检查里面是否有Traceback
        cleaned_stderr = cleaned_stderr_match.group(1).strip()
        traceback_header = "Traceback (most recent call last):"
        if traceback_header in cleaned_stderr:
             # 返回包含Traceback的部分
             return cleaned_stderr[cleaned_stderr.rfind(traceback_header):]
        # 如果没有traceback，但有内容，也返回它
        return cleaned_stderr

    # 策略2 (改进): 查找最后一个Traceback
    traceback_header = "Traceback (most recent call last):"
    if traceback_header in simulation_output:
        # 直接返回从最后一个Traceback开始到字符串末尾的所有内容
        return simulation_output[simulation_output.rfind(traceback_header):]

    # 策略3: 原始的关键词搜索作为后备
    error_lines = []
    in_traceback = False
    error_keywords = ["Error", "Exception", "Traceback (most recent call last)", "FAILED"]
    
    for line in simulation_output.splitlines():
        if any(keyword in line for keyword in error_keywords):
            in_traceback = True
        if in_traceback:
            error_lines.append(line)
            if len(error_lines) > 20 and not line.startswith(" "):
                break 
    
    if error_lines:
        return "\n".join(error_lines)

    # 策略4: 检查警告
    warning_lines = [line for line in simulation_output.splitlines() if "warning" in line.lower() or "caution" in line.lower()]
    if warning_lines:
        return "Warnings found:\n" + "\n".join(warning_lines[:10])
            
    # 策略5: 通用失败
    if "FAIL" in simulation_output.upper():
         return "\n".join(simulation_output.splitlines()[-15:])
         
    return "No specific error details extracted, but simulation did not succeed."

# ============================================================================
# LangGraph节点函数部分
# ============================================================================

def generate_code_node(state: CodeGenerationState):
    """
    代码生成节点函数
    - 首次尝试: 生成完整的Python协议代码
    - 后续尝试: 生成一个diff补丁并应用它来修正代码
    """
    attempt_num = state['attempts'] + 1
    print(f"--- Graph: Generating Code (Attempt {attempt_num}) ---")
    reporter = state.get('iteration_reporter')
    final_code = None
    llm_diff_output = None

    # 优化点: 根据硬件配置动态选择正确的硬件列表和提示词
    hardware_context = state["hardware_context"]
    is_flex = "flex" in hardware_context.lower()
    
    # 根据机器人类型选择正确的配置
    if is_flex:
        print("Debug - Detected 'Flex' robot. Using Flex-specific hardware lists and prompt.")
        valid_labware = LABWARE_FOR_FLEX
        valid_instruments = INSTRUMENTS_FOR_FLEX
        valid_modules = MODULES_FOR_FLEX
        code_gen_chain = code_gen_chain_flex
        code_correction_chain = code_correction_chain_flex
        common_pitfalls_str = "" # Not used for Flex
    else:
        print("Debug - Detected 'OT-2' robot (or default). Using OT-2-specific hardware lists and prompt.")
        valid_labware = LABWARE_FOR_OT2
        valid_instruments = INSTRUMENTS_FOR_OT2
        valid_modules = MODULES_FOR_OT2
        code_gen_chain = code_gen_chain_ot2
        code_correction_chain = code_correction_chain_ot2
        common_pitfalls_str = "\n".join(f"- {pitfall}" for pitfall in COMMON_PITFALLS_OT2)

    api_version_match = re.search(r"API Version:\s*([\d.]+)", hardware_context)
    api_version = api_version_match.group(1) if api_version_match else "2.19"

    valid_labware_str = "\n".join(f"- {name}" for name in valid_labware)
    valid_instruments_str = "\n".join(f"- {name}" for name in valid_instruments)
    valid_modules_str = "\n".join(f"- {name}" for name in valid_modules)

    if state['attempts'] == 0:
        # 首次尝试: 从SOP生成完整代码
        if reporter:
            reporter({
                "event_type": "code_attempt", "attempt_num": attempt_num,
                "message": f"Generating full code from SOP (Attempt {attempt_num})"
            })
        
        # 动态构建chain_input，只包含当前prompt需要的变量
        chain_input = {
            "hardware_context": state["hardware_context"],
            "sop_text": state['original_sop'],
            "feedback_for_llm": "", 
            "previous_code": "N/A",
            "valid_labware_list_str": valid_labware_str,
            "valid_instrument_list_str": valid_instruments_str,
            "valid_module_list_str": valid_modules_str,
            "code_examples_str": CODE_EXAMPLES,
            "apiLevel": api_version,
        }
        if not is_flex:
            chain_input["common_pitfalls_str"] = common_pitfalls_str

        raw_generated_code = code_gen_chain.run(chain_input)
        
        # 增加后处理步骤来清洗输出
        if "</think>" in raw_generated_code:
            raw_generated_code = raw_generated_code.split("</think>", 1)[-1]

        # 清理Markdown代码块标记
        if raw_generated_code.strip().startswith("```python"):
            raw_generated_code = raw_generated_code.strip()[9:]
            if raw_generated_code.strip().endswith("```"):
                raw_generated_code = raw_generated_code.strip()[:-3]
        final_code = raw_generated_code.strip()

    else:
        # 后续尝试: 使用增量修复策略 (diff_edit)
        if reporter:
            reporter({
                "event_type": "diff_generation_start", "attempt_num": attempt_num,
                "message": f"Generating diff patch (Attempt {attempt_num})"
            })
        
        previous_code = state["python_code"]
        feedback = state["feedback_for_llm"]

        chain_input = {
            "analysis_of_failure": feedback.get("analysis", "N/A"),
            "recommended_action": feedback.get("action", "N/A"),
            "full_error_log": feedback.get("error_log", "N/A"),
            "previous_code": previous_code,
            "valid_labware_list_str": valid_labware_str,
            "valid_instrument_list_str": valid_instruments_str,
            "valid_module_list_str": valid_modules_str,
        }
        
        generated_diff = code_correction_chain.run(chain_input)
        llm_diff_output = generated_diff

        if reporter:
            reporter({
                "event_type": "diff_generated", "attempt_num": attempt_num,
                "diff_output": generated_diff, "message": "Diff patch generated, now applying..."
            })
            
        try:
            final_code = apply_diff(previous_code, generated_diff)
            if reporter:
                reporter({"event_type": "diff_applied", "attempt_num": attempt_num, "message": "Diff patch applied successfully."})
        except ValueError as e:
            print(f"CRITICAL: Failed to apply diff on attempt {attempt_num}: {e}")
            final_code = previous_code
            if reporter:
                reporter({
                    "event_type": "diff_failed", "attempt_num": attempt_num,
                    "error_details": str(e),
                    "message": "Error: Failed to apply AI-generated diff patch. This usually means the SEARCH block did not match."
                })

    if reporter:
        reporter({
            "event_type": "code_generated", "attempt_num": attempt_num,
            "generated_code": final_code, "message": f"Code generation complete. Length: {len(final_code)} chars"
        })
    
    return {
        "python_code": final_code,
        "llm_diff_output": llm_diff_output,
        "attempts": state["attempts"] + 1
    }

def simulate_code_node(state: CodeGenerationState):
    """
    代码模拟节点函数
    运行Opentrons模拟器来验证生成的代码
    """
    print("--- Graph: Simulating Code ---")
    
    # 向前端报告模拟开始
    if state.get('iteration_reporter'):
        state['iteration_reporter']({
            "event_type": "simulation_start",
            "attempt_num": state['attempts'],
            "message": f"Starting simulation for attempt #{state['attempts']}"
        })
    
    # 获取要模拟的代码
    code_to_simulate = state["python_code"]
    if not code_to_simulate:
        # 如果代码为空，直接返回错误
        result = {"success": False, "error_details": "Code generation resulted in empty script."}
    else:
        # 运行Opentrons模拟器
        result = run_opentrons_simulation(code_to_simulate, return_structured=True)
    
    # 向前端报告模拟结果
    if state.get('iteration_reporter'):
        state['iteration_reporter']({
            "event_type": "simulation_log_raw",
            "attempt_num": state['attempts'],
            "raw_output": result.get("raw_output", ""),
            "structured_result": result,
            "message": f"Simulation complete. Status: {result.get('final_status', 'Unknown')}"
        })
    
    # 返回包含模拟结果的状态更新
    return {"simulation_result": result}

def prepare_feedback_node(state: CodeGenerationState):
    """
    分析模拟失败并为LLM准备结构化的、可操作的反馈。
    """
    print("--- Graph: Preparing Intelligent Feedback for LLM ---")
    
    simulation_result = state["simulation_result"]
    raw_error_output = simulation_result.get("raw_output", "")
    error_details = extract_error_from_simulation(raw_error_output)
    
    # 新增：检查是否因相同错误陷入循环
    previous_feedback = state.get("feedback_for_llm", {})
    previous_error = previous_feedback.get("error_log", "")
    # 如果错误信息完全相同，并且已经尝试超过1次，则认为是卡住了
    is_stuck = error_details == previous_error and state["attempts"] > 1

    if is_stuck:
        print("🔥🔥🔥 LOOP DETECTED! The previous fix failed. Escalating feedback to LLM. 🔥🔥🔥")
        # 提供一个更强烈的指令来打破循环
        analysis = (
            "The previous attempt to fix the code was unsuccessful and resulted in the exact same error. "
            "This indicates the initial analysis or the proposed fix was incorrect. A different approach is required."
        )
        action = (
            "Action: **STOP** and re-evaluate the problem from the beginning. "
            "Do not repeat the previous failed attempt. "
            "1. **Re-read the SOP and the code from scratch.** Look for fundamental logical errors. "
            "2. **Ignore your previous analysis.** It was wrong. "
            "3. **Propose a completely new and different solution.** If you changed a labware name before, maybe the problem is the deck slot. If you changed a parameter, maybe the entire function call is wrong. Be creative and think of an alternative fix."
        )
    else:
        # --- Start of intelligent feedback generation ---
        analysis = "An unknown error occurred."
        action = "Please re-read the SOP and your generated code carefully. Check for any logical inconsistencies or deviations from the examples provided."
        
        # 1. Labware/Instrument/Module Loading & Configuration Errors
        if "LabwareLoadError" in error_details or "cannot find a definition for labware" in error_details:
            analysis = "The simulation failed with a `LabwareLoadError`. This almost always means a labware `load_name` in your script does not exactly match a name from the `VALID LABWARE NAMES` list, or it is not compatible with the robot type."
            action = "Action: Carefully check every `protocol.load_labware()` call. Compare the `load_name` string against the provided list and correct any misspelling or inconsistency. Ensure you are using labware compatible with the specified robot."
        elif "InstrumentLoadError" in error_details or "cannot find a definition for instrument" in error_details:
            analysis = "The simulation failed with an `InstrumentLoadError`. This means a pipette `instrument_name` in your script is incorrect."
            action = "Action: Check your `protocol.load_instrument()` call. The `instrument_name` must be an exact match from the `VALID INSTRUMENT NAMES` list for the specified robot."
        elif "ModuleLoadError" in error_details:
            analysis = "The simulation failed with a `ModuleLoadError`. This means a module `load_name` in your script is incorrect."
            action = "Action: Check your `protocol.load_module()` call. The `load_name` must be an exact match from the `VALID MODULE NAMES` list."
        elif "DeckConflictError" in error_details:
            analysis = "The simulation failed with a `DeckConflictError`. This means the protocol tried to load two different items (labware or modules) into the same deck slot."
            action = "Action: Review all `protocol.load_labware()` and `protocol.load_module()` calls. Ensure that each item is assigned a unique and valid deck slot number or address."
        elif "KeyError" in error_details and re.search(r"\'[A-D][1-9][0-9]*\'", error_details):
            analysis = "The simulation failed with a `KeyError` on an alphanumeric key (e.g., 'D2', 'C3'). This is a classic OT-2 error. OT-2 protocols require deck slots to be numeric strings like '1', '2', '10'."
            action = "Action: This is an OT-2 protocol. You must change all deck slot locations from the alphanumeric format (like 'D2') to the correct numeric string format (like '2'). Review all `protocol.load_labware()` and `protocol.load_module()` calls and fix the slot names."
        elif "valid deck slot must be a string" in error_details: # Fallback for more verbose errors
            analysis = "The simulation failed because an invalid deck slot format was used. For OT-2, deck slots must be strings of numbers (e.g., '1', '2', '10'), not 'A1', 'B2', etc."
            action = "Action: Review all `protocol.load_labware()` and `protocol.load_module()` calls. Change all deck slot locations to the correct OT-2 number format (e.g., change 'A1' to '1')."
        elif "InvalidSpecificationForRobotTypeError" in error_details:
            analysis = "The simulation failed with `InvalidSpecificationForRobotTypeError`. This is a critical error indicating a mismatch between the robot type and the hardware or API version used in the script."
            action = "Action: The `requirements` or `metadata` in your script must match the `Hardware Configuration`. If the hardware says 'Flex', your script MUST use `requirements = {'robotType': 'Flex', ...}`. If it says 'OT-2', it MUST use `metadata = {'apiLevel': '...'}`. Also, ensure all loaded labware and pipettes are compatible with that robot."

        # 2. Python语法和属性错误
        elif "SyntaxError" in error_details:
            analysis = "The script failed with a Python `SyntaxError`. This is a basic code structure error."
            action = "Action: Review the line indicated in the error for mistakes like missing commas, incorrect indentation, or unclosed parentheses. Fix the Python syntax."
        elif "AttributeError" in error_details:
            analysis = f"The script failed with an `AttributeError`. This often means you are trying to use a method or property that doesn't exist for an object (like a pipette or labware) in the specified API version. The error was: `{error_details}`"
            action = "Action: Review the Opentrons API documentation for the correct methods and parameters for liquid handling and module control. Pay close attention to the provided `DETAILED CODE EXAMPLES` which show valid patterns."
        elif "NameError" in error_details:
            analysis = f"The script failed with a `NameError`, meaning a variable or function was used before it was defined. Error: `{error_details}`"
            action = "Action: Ensure all variables (for labware, pipettes, etc.) are defined with `protocol.load_*` before you use them in commands."
            
        # 3. 协议逻辑与状态错误
        elif "NoTrashDefinedError" in error_details:
            analysis = "The simulation failed with a `NoTrashDefinedError`. This typically happens in Flex protocols when an action requires a trash container (like dropping a tip), but one has not been defined."
            action = "Action: For Flex protocols, you must explicitly load a trash bin. Add a line like `trash = protocol.load_trash_bin('A3')` to your labware loading section. For OT-2 protocols, use `protocol.fixed_trash['A1']` instead of loading a separate trash bin."
        elif "TipAttachedError" in error_details:
            analysis = "The simulation failed with a `TipAttachedError`. This means the protocol attempted to pick up a new tip when a tip was already attached to the pipette."
            action = "Action: Ensure every `pipette.pick_up_tip()` call is preceded by a `pipette.drop_tip()` or `pipette.return_tip()` call from the previous liquid handling step. Do not call `pick_up_tip()` twice in a row."
        elif "missing tip" in error_details.lower():
            analysis = "The protocol tried to perform a liquid handling action without a tip."
            action = "Action: Ensure you call `pipette.pick_up_tip()` before any `aspirate` or `dispense` commands. Also, make sure you don't drop a tip (`pipette.drop_tip()`) and then try to use the pipette again without picking up a new one."
        elif "Cannot aspirate when module is engaged" in error_details:
            analysis = "The simulation failed because the protocol tried to aspirate liquid while the Magnetic Module was engaged. This is not allowed as it would aspirate magnetic beads."
            action = "Action: Before the aspirate command that caused the error, you must call `magnetic_module.disengage()`. This moves the magnets away from the plate, allowing the pipette to safely aspirate the supernatant."
        elif "volume" in error_details.lower() and ("out of range" in error_details.lower() or "not a valid" in error_details.lower()):
            analysis = "The protocol tried to use a volume that is outside the valid range for the specified pipette."
            action = "Action: Check all `aspirate`, `dispense`, and `mix` commands. Ensure the volumes are within the minimum and maximum capacity of the pipette being used."
        elif "Cannot perform action" in error_details and "while module is" in error_details:
            analysis = "The protocol attempted an action on a module that is currently busy or in an incompatible state (e.g., trying to open a Heater-Shaker latch while it is shaking)."
            action = "Action: Ensure you stop the module's current action before proceeding. For example, call `heater_shaker.deactivate_shaker()` before trying `heater_shaker.open_labware_latch()`."
        
        else:
            # 改进通用后备方案
            analysis = "The simulation failed with an error that was not automatically categorized. This could be a complex logical error in the protocol steps."
            action = "Action: Please carefully review the [Full Error Log] and the [Previous Failed Code] below. Analyze the script's logic against the SOP to identify the root cause and generate a corrected version."

        # --- End of intelligent feedback generation ---

    if state.get('iteration_reporter'):
        state['iteration_reporter']({
            "event_type": "iteration_result",
            "attempt_num": state['attempts'],
            "status": "FAILED",
            "error_details": error_details,
            "message": f"Attempt #{state['attempts']} failed."
        })
    
    feedback_dict = {
        "analysis": analysis,
        "action": action,
        "error_log": error_details,
    }
    
    return {"feedback_for_llm": feedback_dict}

def should_continue(state: CodeGenerationState):
    """
    LangGraph条件边函数：核心决策引擎
    =====================================
    这是LangGraph工作流的关键决策点，根据模拟结果和尝试次数决定下一步行动：
    - 如果模拟成功 → 结束流程，返回最终代码
    - 如果模拟失败但未达到最大尝试次数 → 继续循环，进入反馈准备阶段
    - 如果达到最大尝试次数 → 强制结束，返回失败状态
    
    决策逻辑遵循"开发-测试-调试"的迭代模式，模拟真实的编程工作流。
    """
    print("=== [LangGraph Decision Engine] 分析当前状态 ===")
    
    # 获取关键状态信息
    simulation_result = state.get("simulation_result")
    current_attempt = state.get("attempts", 0)
    max_attempts = state.get("max_attempts", 5)
    
    print(f"[Decision Engine] 当前尝试: {current_attempt}/{max_attempts}")
    
    if not simulation_result:
        print("[Decision Engine] ⚠️  缺少模拟结果，继续下一轮生成")
        return "continue"
    
    # 检查成功状态和警告
    success = simulation_result.get("success", False)
    has_warnings = simulation_result.get("has_warnings", False)
    error_details = simulation_result.get("error_details", "")
    
    print(f"[Decision Engine] 模拟结果: 成功={success}, 有警告={has_warnings}")
    
    if success and not has_warnings:
        # ✅ 理想情况：代码完美运行，无任何问题
        print("[Decision Engine] ✅ 模拟完全成功！流程结束")
        if state.get('iteration_reporter'):
            state['iteration_reporter']({
                "event_type": "iteration_result",
                "attempt_num": current_attempt,
                "status": "SUCCESS",
                "final_code": state.get("python_code", ""),
                "message": f"第 {current_attempt} 次尝试成功！模拟通过，无警告。"
            })
        return "end"
    elif success and has_warnings:
        # ⚠️  可接受情况：代码能运行，但有警告（如弃用提醒等）
        print("[Decision Engine] ⚠️  模拟成功但有警告，仍视为完成")
        if state.get('iteration_reporter'):
            state['iteration_reporter']({
                "event_type": "iteration_result",
                "attempt_num": current_attempt,
                "status": "SUCCESS_WITH_WARNINGS",
                "warning_details": error_details,
                "message": f"第 {current_attempt} 次尝试成功，但存在警告。"
            })
        return "end"
    elif current_attempt >= max_attempts:
        # 💀 失败情况：已达到最大尝试次数，必须停止避免无限循环
        print(f"[Decision Engine] 💀 已达到最大尝试次数 ({max_attempts})，强制结束")
        if state.get('iteration_reporter'):
            state['iteration_reporter']({
                "event_type": "iteration_result",
                "attempt_num": current_attempt,
                "status": "FINAL_FAILED",
                "error_details": error_details,
                "final_code": state.get("python_code", ""),
                "message": f"最终失败：{max_attempts} 次尝试后仍无法通过模拟。"
            })
        return "end"
    else:
        # 🔄 继续情况：模拟失败，但还有重试机会，进入调试修复流程
        print(f"[Decision Engine] 🔄 模拟失败，准备第 {current_attempt + 1} 次尝试")
        print(f"[Decision Engine] 错误信息: {error_details[:100]}..." if error_details else "无具体错误详情")
        return "continue"

# ============================================================================
# LangGraph工作流构建和编译
# ============================================================================

# 创建和编译LangGraph工作流
workflow = StateGraph(CodeGenerationState)

# 向图中添加节点
workflow.add_node("generator", generate_code_node)           # 代码生成器节点
workflow.add_node("simulator", simulate_code_node)           # 代码模拟器节点
workflow.add_node("feedback_preparer", prepare_feedback_node) # 反馈准备器节点

# 定义图的流程
workflow.add_edge(START, "generator")                        # 从开始节点到代码生成器
workflow.add_edge("generator", "simulator")                  # 从代码生成器到模拟器
workflow.add_conditional_edges(                              # 条件边：根据模拟结果决定下一步
    "simulator",
    should_continue,
    {
        "continue": "feedback_preparer",  # 如果需要继续，去反馈准备器
        "end": END                        # 如果完成，结束流程
    }
)
workflow.add_edge("feedback_preparer", "generator")          # 循环回到代码生成器

# 将图编译为可运行的应用程序
code_generation_graph = workflow.compile()

def run_code_generation_graph(
    tool_input: str, 
    max_iterations: int,
    iteration_reporter: Optional[Callable[[Dict[str, Any]], None]] = None
) -> str:
    """
    基于LangGraph的新代码生成函数，替代旧的迭代循环
    
    参数:
        tool_input: 包含SOP和硬件配置的输入字符串，用特定分隔符分隔
        max_iterations: 覆盖默认的最大尝试次数
        iteration_reporter: 可选的回调函数，用于报告进度信息
    
    返回:
        str: 生成的协议代码或错误信息
    """
    try:
        print(f"Debug - [langchain_agent.py] Entering LangGraph-based code generation")

        # 为命令行兼容性定义默认报告器
        def default_reporter(event_data: Dict[str, Any]):
            if event_data["event_type"] == "iteration_log":
                print(f"[ProtocolCodeGenerator] {event_data['message']}")
            elif event_data["event_type"] == "code_attempt":
                print(f"[ProtocolCodeGenerator] 生成代码尝试 {event_data['attempt_num']}")
            elif event_data["event_type"] == "simulation_start":
                print(f"[ProtocolCodeGenerator] 开始模拟验证第 {event_data['attempt_num']} 次尝试...")
            elif event_data["event_type"] == "simulation_log_raw":
                print(f"[ProtocolCodeGenerator] 模拟结果: {event_data.get('message', '')}")
            elif event_data["event_type"] == "iteration_result":
                print(f"[ProtocolCodeGenerator] 第 {event_data['attempt_num']} 次尝试结果: {event_data['status']}")

        reporter = iteration_reporter or default_reporter

        # 解析工具输入
        separator = "\n---CONFIG_SEPARATOR---\n"
        if separator not in tool_input:
            error_msg = "Error: Input for ProtocolCodeGenerator must contain SOP and hardware context separated by '\n---CONFIG_SEPARATOR---\n'."
            reporter({
                "event_type": "iteration_log",
                "message": error_msg,
                "attempt_num": 0,
                "max_attempts": 5
            })
            return error_msg
        
        # 分离SOP和硬件配置
        original_sop, hardware_context = tool_input.split(separator, 1)
        original_sop = original_sop.strip()
        hardware_context = hardware_context.strip()

        # 从硬件配置中提取API版本
        api_version_match = re.search(r"API Version:\s*([\d.]+)", hardware_context)
        api_version_for_prompt = api_version_match.group(1) if api_version_match else "2.19"
        
        # 设置初始状态，使用覆盖值
        initial_state = CodeGenerationState(
            original_sop=original_sop,
            hardware_context=hardware_context,
            python_code=None,
            llm_diff_output=None,
            simulation_result=None,
            feedback_for_llm={},
            attempts=0,
            max_attempts=max_iterations,
            iteration_reporter=reporter
        )
        
        # 每次尝试涉及3个节点（generator -> simulator -> feedback_preparer）
        # 所以9次尝试 × 3个节点 =27次总节点访问
        config = {"recursion_limit": 50}
        final_state = code_generation_graph.invoke(initial_state, config=config)
        
        # 格式化并返回最终结果
        simulation_result = final_state.get("simulation_result", {})
        success = simulation_result.get("success", False)
        has_warnings = simulation_result.get("has_warnings", False)
        
        if success and not has_warnings:
            # 成功且无警告，直接返回代码
            return final_state.get("python_code", "")
        elif success and has_warnings:
            # 成功但有警告，返回警告信息和代码
            warning_details = simulation_result.get("error_details", "")
            final_result = f"Warning: Protocol simulation succeeded with warnings. Please review these warnings before using:\n{warning_details}\n\nGenerated Code:\n```python\n{final_state.get('python_code', '')}\n```"
            return final_result
        else:
            # 失败，返回结构化的错误信息
            error_details = simulation_result.get('error_details', 'Unknown failure')
            last_code = final_state.get('python_code', '')
            
            # 构建用户友好的错误报告
            final_error = f"""**协议生成失败报告**

**总体状态**: 经过 {final_state['attempts']} 次尝试后失败

**最后一次错误详情**:
{error_details}

**最后生成的代码** (可参考修改):
```python
{last_code}
```

**原始SOP**:
{original_sop}

**建议**:
- 检查SOP中是否包含不兼容的硬件要求
- 确认试剂体积和移液器容量匹配
- 验证deck layout是否正确配置
- 如果错误持续，请考虑简化实验步骤"""
            return final_error

    except Exception as e:
        # 异常处理
        print(f"Debug - [langchain_agent.py] Exception in LangGraph code generation: {e}")
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Debug - 完整错误堆栈: {error_traceback}")
        return f"Error: An unexpected error occurred during protocol generation. Details: {str(e)}\nTraceback:\n{error_traceback}"

# ============================================================================
# NOTE: Removed deprecated wrapper function run_automated_protocol_generation_with_iteration
# Use run_code_generation_graph or run_code_generation_graph_stream directly instead
# ============================================================================

# ============================================================================
# 新增：异步流式代码生成函数
# ============================================================================

async def run_code_generation_graph_stream(
    tool_input: str, 
    max_iterations: int
):
    """
    基于LangGraph的异步流式代码生成函数
    
    此函数使用 LangGraph 的 astream() 方法来实现真正的异步流式响应。
    它会在图执行的每个关键步骤后 yield 一个JSON对象，允许前端实时显示进度。
    
    参数:
        tool_input: 包含SOP和硬件配置的输入字符串，用特定分隔符分隔
        max_iterations: 最大迭代次数
    
    生成器返回:
        Dict[str, Any]: 每次yield一个包含事件类型和相关数据的JSON对象
    
    事件类型说明:
        - "start": 开始执行
        - "node_start": 节点开始执行
        - "node_complete": 节点执行完成
        - "attempt_result": 尝试结果（成功/失败）
        - "final_result": 最终结果
        - "error": 执行错误
    """
    try:
        print(f"Debug - [run_code_generation_graph_stream] 开始异步流式代码生成")
        
        # 发送开始事件
        yield {
            "event_type": "start",
            "message": "开始协议代码生成流程...",
            "timestamp": datetime.now().isoformat()
        }

        # 解析工具输入
        separator = "\n---CONFIG_SEPARATOR---\n"
        if separator not in tool_input:
            error_msg = "Error: Input for ProtocolCodeGenerator must contain SOP and hardware context separated by '\n---CONFIG_SEPARATOR---\n'."
            yield {
                "event_type": "error",
                "message": error_msg,
                "timestamp": datetime.now().isoformat()
            }
            return
        
        # 分离SOP和硬件配置
        original_sop, hardware_context = tool_input.split(separator, 1)
        original_sop = original_sop.strip()
        hardware_context = hardware_context.strip()

        # 从硬件配置中提取API版本
        api_version_match = re.search(r"API Version:\s*([\d.]+)", hardware_context)
        api_version_for_prompt = api_version_match.group(1) if api_version_match else "2.19"
        
        # 设置初始状态
        initial_state = CodeGenerationState(
            original_sop=original_sop,
            hardware_context=hardware_context,
            python_code=None,
            llm_diff_output=None,
            simulation_result=None,
            feedback_for_llm={},
            attempts=0,
            max_attempts=max_iterations,
            iteration_reporter=None  # 不需要在流式版本中使用回调
        )
        
        yield {
            "event_type": "initialization",
            "message": f"初始化完成，最大尝试次数: {max_iterations}",
            "max_attempts": max_iterations,
            "timestamp": datetime.now().isoformat()
        }
        
        # 使用 astream 异步执行图
        config = {"recursion_limit": 50}
        
        # 跟踪当前状态
        current_state = initial_state
        current_attempt = 0
        
        async for chunk in code_generation_graph.astream(initial_state, config=config):
            # chunk 是一个字典，键是节点名，值是该节点的输出
            for node_name, node_output in chunk.items():
                print(f"Debug - [stream] Node '{node_name}' completed with output keys: {list(node_output.keys())}")
                
                # 更新当前状态
                current_state.update(node_output)
                
                if node_name == "generator":
                    # 代码生成节点完成
                    current_attempt = current_state.get("attempts", 0)
                    yield {
                        "event_type": "node_complete",
                        "node_name": "generator",
                        "message": f"第 {current_attempt} 次代码生成完成",
                        "attempt_num": current_attempt,
                        "has_code": bool(current_state.get("python_code")),
                        "timestamp": datetime.now().isoformat()
                    }
                    
                elif node_name == "simulator":
                    # 模拟器节点完成
                    sim_result = current_state.get("simulation_result", {})
                    success = sim_result.get("success", False)
                    has_warnings = sim_result.get("has_warnings", False)
                    
                    yield {
                        "event_type": "node_complete",
                        "node_name": "simulator",
                        "message": f"第 {current_attempt} 次模拟验证完成",
                        "attempt_num": current_attempt,
                        "simulation_success": success,
                        "has_warnings": has_warnings,
                        "error_details": sim_result.get("error_details", "") if not success else "",
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # 如果模拟成功，这可能是最终结果
                    if success:
                        yield {
                            "event_type": "attempt_result", 
                            "status": "SUCCESS_WITH_WARNINGS" if has_warnings else "SUCCESS",
                            "attempt_num": current_attempt,
                            "message": f"第 {current_attempt} 次尝试成功！" + (" (有警告)" if has_warnings else ""),
                            "final_code": current_state.get("python_code", ""),
                            "warning_details": sim_result.get("error_details", "") if has_warnings else "",
                            "timestamp": datetime.now().isoformat()
                        }
                    
                elif node_name == "feedback_preparer":
                    # 反馈准备器节点完成
                    feedback = current_state.get("feedback_for_llm", {})
                    yield {
                        "event_type": "node_complete",
                        "node_name": "feedback_preparer",
                        "message": f"第 {current_attempt} 次错误分析完成，准备下一轮修正",
                        "attempt_num": current_attempt,
                        "has_feedback": bool(feedback),
                        "error_analysis": feedback.get("analysis", ""),
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # 检查是否达到最大尝试次数
                    if current_attempt >= max_iterations:
                        yield {
                            "event_type": "attempt_result",
                            "status": "FINAL_FAILED",
                            "attempt_num": current_attempt,
                            "message": f"达到最大尝试次数 ({max_iterations})，代码生成失败",
                            "final_code": current_state.get("python_code", ""),
                            "error_details": sim_result.get("error_details", ""),
                            "timestamp": datetime.now().isoformat()
                        }
        
        # 发送最终结果
        final_simulation = current_state.get("simulation_result", {})
        final_success = final_simulation.get("success", False)
        final_warnings = final_simulation.get("has_warnings", False)
        final_code = current_state.get("python_code", "")
        
        if final_success:
            yield {
                "event_type": "final_result",
                "status": "success",
                "message": "协议代码生成成功完成！",
                "generated_code": final_code,
                "has_warnings": final_warnings,
                "warning_details": final_simulation.get("error_details", "") if final_warnings else "",
                "total_attempts": current_attempt,
                "timestamp": datetime.now().isoformat()
            }
        else:
            # 构建失败报告
            error_details = final_simulation.get('error_details', 'Unknown failure')
            final_error = f"""**协议生成失败报告**

**总体状态**: 经过 {current_attempt} 次尝试后失败

**最后一次错误详情**:
{error_details}

**最后生成的代码** (可参考修改):
```python
{final_code}
```

**原始SOP**:
{original_sop}

**建议**:
- 检查SOP中是否包含不兼容的硬件要求
- 确认试剂体积和移液器容量匹配
- 验证deck layout是否正确配置
- 如果错误持续，请考虑简化实验步骤"""

            yield {
                "event_type": "final_result",
                "status": "failure",
                "message": "协议代码生成失败",
                "error_report": final_error,
                "generated_code": final_code,
                "error_details": error_details,
                "total_attempts": current_attempt,
                "timestamp": datetime.now().isoformat()
            }

    except Exception as e:
        # 异常处理
        print(f"Debug - [run_code_generation_graph_stream] Exception: {e}")
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Debug - 完整错误堆栈: {error_traceback}")
        
        yield {
            "event_type": "error",
            "message": f"协议生成过程中发生异常: {str(e)}",
            "error_traceback": error_traceback,
            "timestamp": datetime.now().isoformat()
        }

# ============================================================================
# 协议代码生成的简化接口函数
# ============================================================================

def generate_protocol_code(sop_markdown: str, hardware_config: str, max_iterations: int = 5) -> str:
    """
    生成协议代码的简化接口函数
    这个函数提供了一个更简单的API来生成协议代码，直接返回结果
    
    参数:
        sop_markdown: SOP的markdown格式文本
        hardware_config: 硬件配置字符串
        max_iterations: 最大迭代次数
    
    返回:
        str: 生成的协议代码或错误信息
    """
    print(f"Debug - [generate_protocol_code] 开始协议代码生成 (max_iterations={max_iterations})")
    
    try:
        # 格式化输入参数，使用特定分隔符连接SOP和硬件配置
        tool_input = f"{sop_markdown}\n---CONFIG_SEPARATOR---\n{hardware_config}"
        
        # 调用LangGraph工作流生成代码
        result = run_code_generation_graph(tool_input, max_iterations=max_iterations)
        
        print(f"Debug - [generate_protocol_code] 代码生成完成，长度: {len(result)} 字符")
        return result
        
    except Exception as e:
        # 捕获异常并返回错误信息
        print(f"Error - [generate_protocol_code] 代码生成失败: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return f"Error: 协议代码生成失败: {str(e)}"

# ============================================================================
# 主函数 - 用于测试
# ============================================================================

if __name__ == '__main__':
    print("Langchain agent setup complete with LangGraph-based iterative protocol generator.")
    
    # 测试新的LangGraph实现
    # 这里定义了一个简单的测试用例
    test_sop = "1. Add 50ul of water from Trough A1 to wells A1-A3 of a 96-well plate.\n2. Add 50ul of reagent X from Tube B1 to wells A1-A3 of the 96-well plate."
    test_hw = "Robot Model: Opentrons Flex\nAPI Version: 2.19\nLeft Pipette: flex_1channel_1000\nRight Pipette: None\nDeck Layout:\n  A1: opentrons_96_tiprack_1000ul\n  B1: opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap \n  C1: corning_96_wellplate_360ul_flat"
    
    # 格式化测试输入并运行测试
    test_tool_input = f"{test_sop}\n---CONFIG_SEPARATOR---\n{test_hw}"
    # 测试代码生成（使用唯一的增量修复策略）
    print("\n--- Testing code generation with diff_edit strategy ---")
    result = run_code_generation_graph(test_tool_input, max_iterations=5)
    print("\n--- LangGraph Code Generation Test Result ---")
    print(result)

# ############################################################################
# # 第一阶段：定义 Agent 的核心工具 (自主代码编辑)
# ############################################################################

from langchain_core.tools import tool
from langchain.tools import BaseTool
from langgraph.types import Command

def _extract_diff_content(diff_response: str) -> str:
    """
    (内部函数) 从 LLM 生成的完整响应中提取 diff 内容。
    
    LLM 的响应可能包含思考过程或 Markdown 代码块。这个函数
    负责提取出可供 `apply_diff` 使用的纯粹的 diff 文本。
    
    Args:
        diff_response: LLM 返回的原始字符串
        
    Returns:
        提取出的 diff 文本
    """
    # 查找被 ` ```diff ` 和 ` ``` ` 包围的代码块
    diff_match = re.search(r'```diff\s*(.*?)\s*```', diff_response, re.DOTALL)
    if diff_match:
        # 如果找到，返回代码块的内容
        return diff_match.group(1).strip()
    
    # 作为后备方案，如果找不到 `diff` 标记，但内容看起来像一个 diff
    # （包含 SEARCH/REPLACE 块），则直接返回原始文本
    if "------- SEARCH" in diff_response and "------- REPLACE" in diff_response:
        return diff_response.strip()
        
    # 如果都找不到，可能 LLM 返回了非 diff 内容，这是一种错误情况
    # 但为了稳健，我们返回原始响应，让 apply_diff 来处理
    return diff_response.strip()

@tool
def modify_code_tool(original_code: str, user_instruction: str) -> str:
    """
    修改代码工具：专注于根据用户指令修改代码，返回修改后的完整代码。
    
    此工具会调用 LLM 生成 diff 补丁，然后应用到原始代码上。
    它不关心代码是否能通过模拟，只负责修改。
    
    Args:
        original_code: 原始代码字符串
        user_instruction: 用户修改指令
        
    Returns:
        修改后的完整代码字符串
        
    Raises:
        Exception: 如果修改失败
    """
    try:
        print(f"Debug - [modify_code_tool] 开始代码修改")
        
        # 使用简化的 Planner-Differ 架构
        planner_prompt = CODE_PLANNER_PROMPT_TEMPLATE.format(
            user_instruction=user_instruction,
            original_code=original_code,
            hardware_context="No specific hardware context - inferred from code",
            valid_labware_list_str="N/A - Context will be inferred from code",
            valid_instrument_list_str="N/A - Context will be inferred from code", 
            valid_module_list_str="N/A - Context will be inferred from code",
            common_pitfalls_str="- Check API compatibility (OT-2 vs Flex)\n- OT-2 uses numeric deck slots\n- Flex uses alphanumeric deck slots"
        )
        
        # 步骤1：生成修改计划
        planner_response = llm.invoke(planner_prompt).content.strip()
        
        # 提取JSON格式的修改计划
        try:
            json_match = re.search(r'```json\s*(.*?)\s*```', planner_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = planner_response
            
            modification_plan = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise Exception(f"修改计划生成格式错误: {e}")
        
        # 步骤2：生成 diff
        differ_prompt = CODE_DIFFER_PROMPT_TEMPLATE.format(
            modification_plan=json.dumps(modification_plan, indent=2, ensure_ascii=False),
            original_code=original_code
        )
        
        diff_response = code_gen_llm.invoke(differ_prompt).content.strip()
        
        # 步骤3：应用 diff (增加重试逻辑)
        diff_content = _extract_diff_content(diff_response)
        
        try:
            modified_code = apply_diff(original_code, diff_content)
        except ValueError as e:
            print(f"Warning - [modify_code_tool] Diff应用失败，尝试自动修复: {e}")
            
            # 尝试修复 diff
            fixer_prompt = CODE_DIFFER_FIX_PROMPT_TEMPLATE.format(
                original_code=original_code,
                user_instruction=user_instruction,
                failed_diff=diff_content,
                error_message=str(e)
            )
            
            fixed_diff_response = code_gen_llm.invoke(fixer_prompt).content.strip()
            fixed_diff_content = _extract_diff_content(fixed_diff_response)
            
            # 再次尝试应用修复后的 diff
            modified_code = apply_diff(original_code, fixed_diff_content) # 如果再次失败，会自然抛出异常
        
        # 步骤4：快速语法验证
        syntax_valid, syntax_error = _validate_python_syntax(modified_code)
        if not syntax_valid:
            raise Exception(f"生成的代码语法错误: {syntax_error}")
        
        print(f"Debug - [modify_code_tool] 代码修改成功")
        return modified_code
        
    except Exception as e:
        print(f"Error - [modify_code_tool] 代码修改失败: {e}")
        raise Exception(f"代码修改失败: {str(e)}")


@tool
def simulate_protocol_tool(code_to_simulate: str) -> str:
    """
    模拟协议工具：专注于验证代码，运行 Opentrons 模拟器并返回结果。
    
    此工具接收代码并返回模拟器输出的字符串（成功或失败日志）。
    
    Args:
        code_to_simulate: 要模拟的代码字符串
        
    Returns:
        模拟结果的字符串描述
    """
    try:
        print(f"Debug - [simulate_protocol_tool] 开始协议模拟")
        
        # 运行 Opentrons 模拟器
        simulation_result = run_opentrons_simulation(code_to_simulate, return_structured=True)
        
        if simulation_result["success"]:
            if simulation_result.get("has_warnings", False):
                result_msg = f"✅ 模拟成功，但有警告:\n{simulation_result.get('warning_details', '')}"
            else:
                result_msg = "✅ 模拟成功，代码验证通过"
        else:
            error_details = simulation_result.get("error_details", "未知错误")
            result_msg = f"❌ 模拟失败:\n{error_details}"
            
            # 添加错误建议
            recommendations = simulation_result.get("recommendations", [])
            if recommendations:
                result_msg += f"\n\n建议:\n" + "\n".join(f"- {rec}" for rec in recommendations)
        
        print(f"Debug - [simulate_protocol_tool] 模拟完成")
        return result_msg
        
    except Exception as e:
        print(f"Error - [simulate_protocol_tool] 模拟失败: {e}")
        return f"❌ 模拟过程中发生错误: {str(e)}"


# ############################################################################
# # 第二阶段：构建 LangGraph Agent 工作流
# ############################################################################

class CodeAgentState(TypedDict):
    """
    代码编辑 Agent 的状态管理类
    
    此状态类用于追踪 Agent 工作流中的所有关键信息。
    LangGraph 使用这个状态在不同的节点之间传递数据。
    """
    # 消息历史：追踪完整的对话历史，这是 Agent 做决策的上下文
    messages: Annotated[list, add_messages]
    
    # 当前代码：保存当前最新版本的代码，会在修改工具成功执行后被更新
    current_code: str


def agent_node(state: CodeAgentState):
    """
    Agent 节点：负责决策的大脑
    
    此节点会接收整个状态，调用绑定了工具的 LLM。
    LLM 的输出将决定是直接回复用户，还是调用一个或多个工具。
    
    Args:
        state: 当前的 Agent 状态
        
    Returns:
        包含 LLM 响应消息的状态更新
    """
    print("Debug - [agent_node] Agent is thinking...")
    
    # 为 Agent 添加系统提示
    system_message = HumanMessage(content="""You are an expert Opentrons protocol programming assistant. Your primary goal is to help users modify and validate their protocols. You have two powerful tools at your disposal:

1.  **`modify_code_tool`**: Use this tool for any code modification request (e.g., change, add, remove, fix, update).
2.  **`simulate_protocol_tool`**: Use this tool to verify code correctness.

**Your workflow is critical for success. Follow it strictly:**
1.  When the user asks for a code modification, your **first and only** action should be to call `modify_code_tool`.
2.  After `modify_code_tool` succeeds, the system will confirm the change. Your **next and only** action should be to call `simulate_protocol_tool` to validate the new code.
3.  After simulation, report the results to the user. If the simulation fails, analyze the error and decide whether to call `modify_code_tool` again to fix it.
4.  If the user is just asking a question, answer it directly without using tools.
5.  If a tool call fails unexpectedly, inform the user about the failure and ask for clarification or a different approach. Do not retry the same failed tool call repeatedly.

Always proceed one step at a time. Do not chain multiple tool calls in a single response.""")
    
    # 将系统消息插入到消息开头（如果还没有）
    messages = state["messages"]
    if not messages or messages[0].content != system_message.content:
        messages = [system_message] + messages
    
    # 将两个工具绑定到 LLM
    tools = [modify_code_tool, simulate_protocol_tool]
    llm_with_tools = llm.bind_tools(tools)
    
    # 调用 LLM，让它决定下一步行动
    response = llm_with_tools.invoke(messages)
    
    print(f"Debug - [agent_node] LLM 响应类型: {'工具调用' if response.tool_calls else '直接回复'}")
    
    # 返回包含 LLM 响应的状态更新
    return {"messages": [response]}


def tool_node(state: CodeAgentState):
    """
    工具节点：负责执行的双手
    
    当 agent_node 决定调用工具时，这个节点会实际执行工具，
    并将结果返回给图。
    
    Args:
        state: 当前的 Agent 状态
        
    Returns:
        包含工具执行结果的状态更新
    """
    print("Debug - [tool_node] 开始执行工具...")
    
    # 获取最后一条消息（应该是包含工具调用的 AI 消息）
    last_message = state["messages"][-1]
    tool_calls = last_message.tool_calls if hasattr(last_message, 'tool_calls') else []
    
    if not tool_calls:
        print("Warning - [tool_node] 没有工具调用，返回空结果")
        return {"messages": []}
    
    # 创建工具映射
    tools_by_name = {
        "modify_code_tool": modify_code_tool,
        "simulate_protocol_tool": simulate_protocol_tool
    }
    
    tool_messages = []
    updated_code = state.get("current_code", "")
    
    # 执行所有工具调用
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_call_id = tool_call["id"]
        
        print(f"Debug - [tool_node] 执行工具: {tool_name}")
        
        try:
            if tool_name == "modify_code_tool":
                # 修改代码工具：使用当前代码作为输入
                tool_args["original_code"] = updated_code
                result = tools_by_name[tool_name].invoke(tool_args)
                updated_code = result  # 更新当前代码
                tool_messages.append(
                    ToolMessage(
                        content="The code has been modified successfully. According to the standard workflow, the next step should be to call `simulate_protocol_tool` to verify the changes.",
                        tool_call_id=tool_call_id,
                        name=tool_name
                    )
                )
            elif tool_name == "simulate_protocol_tool":
                # 模拟工具：使用当前代码作为输入
                tool_args["code_to_simulate"] = updated_code
                result = tools_by_name[tool_name].invoke(tool_args)
                tool_messages.append(
                    ToolMessage(
                        content=result,
                        tool_call_id=tool_call_id,
                        name=tool_name
                    )
                )
            else:
                # 未知工具
                tool_messages.append(
                    ToolMessage(
                        content=f"错误：未知工具 {tool_name}",
                        tool_call_id=tool_call_id,
                        name=tool_name
                    )
                )
        except Exception as e:
            print(f"Error - [tool_node] 工具执行失败 {tool_name}: {e}")
            tool_messages.append(
                ToolMessage(
                    content=f"工具执行失败: {str(e)}",
                    tool_call_id=tool_call_id,
                    name=tool_name
                )
            )
    
    print(f"Debug - [tool_node] 执行了 {len(tool_messages)} 个工具")
    
    # 返回工具消息和更新的代码
    return {
        "messages": tool_messages,
        "current_code": updated_code
    }


def should_continue(state: CodeAgentState) -> Literal["tools", "__end__"]:
    """
    条件路由函数：决定 Agent 的下一步行动
    
    检查最后一条消息是否包含工具调用，如果有则执行工具，
    否则结束对话。
    
    Args:
        state: 当前的 Agent 状态
        
    Returns:
        "tools" 如果需要执行工具，"__end__" 如果要结束对话
    """
    last_message = state["messages"][-1]
    
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        print("Debug - [should_continue] 路由到工具执行")
        return "tools"
    else:
        print("Debug - [should_continue] 路由到结束")
        return "__end__"


# 构建自主代码编辑 Agent 图
def build_code_agent_graph():
    """
    构建并编译自主代码编辑 Agent 的 LangGraph 工作流
    
    Returns:
        编译后的图对象，可以直接调用
    """
    print("Debug - [build_code_agent_graph] 开始构建 Agent 图")
    
    # 创建状态图
    workflow = StateGraph(CodeAgentState)
    
    # 添加节点
    workflow.add_node("agent", agent_node)      # Agent 思考节点
    workflow.add_node("tools", tool_node)       # 工具执行节点
    
    # 定义图的流程
    workflow.add_edge(START, "agent")           # 从开始节点到 Agent
    
    # 添加条件边：Agent 决定是调用工具还是结束
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",      # 如果需要工具，去工具节点
            "__end__": END         # 如果完成，结束流程
        }
    )
    
    # 工具执行后回到 Agent 继续思考
    workflow.add_edge("tools", "agent")
    
    # 编译图
    graph = workflow.compile()
    print("Debug - [build_code_agent_graph] Agent 图构建完成")
    
    return graph


# 初始化全局的代码编辑 Agent
code_agent_graph = build_code_agent_graph()


# ############################################################################
# # 对话式编辑功能 (保留现有功能)
# ############################################################################

def _edit_sop_with_diff(original_sop: str, user_instruction: str, hardware_context: str) -> str:
    """
    (内部函数) 使用大模型生成diff并应用它来修改SOP。
    
    参数:
        original_sop (str): 原始SOP文本。
        user_instruction (str): 用户的修改指令。
        hardware_context (str): 硬件配置，用于提供上下文。
        
    返回:
        str: 修改后的新SOP。
    """
    try:
        print(f"Debug - [edit_sop_with_diff] 开始为SOP生成diff")
        
        # 导入我们需要的模板和工具
        from backend.prompts import SOP_EDIT_DIFF_PROMPT_TEMPLATE
        from langchain_core.prompts import PromptTemplate
        from langchain.chains import LLMChain
        
        # 1. 准备调用大模型的输入
        prompt = PromptTemplate(
            input_variables=["original_sop", "user_instruction", "hardware_context"],
            template=SOP_EDIT_DIFF_PROMPT_TEMPLATE
        )
        chain = LLMChain(llm=llm, prompt=prompt)
        
        # 2. 调用大模型生成diff
        diff_output = chain.run({
            "original_sop": original_sop,
            "user_instruction": user_instruction,
            "hardware_context": hardware_context
        })
        
        print(f"Debug - [edit_sop_with_diff] LLM生成的SOP Diff内容:\n---\n{diff_output}\n---")
        
        if not diff_output or not "------- SEARCH" in diff_output:
            print("Warning - LLM did not return a valid diff. Returning original SOP.")
            raise ValueError("AI did not produce a valid modification for the SOP. Please try rephrasing your request.")

        # 3. 应用diff
        print(f"Debug - [edit_sop_with_diff] 应用diff前的SOP长度: {len(original_sop)}")
        new_sop = apply_diff(original_sop, diff_output)
        print(f"Debug - [edit_sop_with_diff] 应用diff后的SOP长度: {len(new_sop)}")
        
        print(f"Debug - [edit_sop_with_diff] SOP Diff应用成功，SOP已修改。")
        
        return new_sop

    except ValueError as ve:
        print(f"Error - [edit_sop_with_diff] 应用SOP diff时出错: {ve}")
        raise ve # 重新抛出，让调用者知道是diff应用问题
    except Exception as e:
        print(f"Error - [edit_sop_with_diff] 编辑SOP时发生未知错误: {e}")
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Debug - [edit_sop_with_diff] 完整错误堆栈:\n{error_traceback}")
        raise RuntimeError(f"An unexpected error occurred while editing the SOP: {e}")


def converse_about_sop(original_sop: str, user_instruction: str, hardware_context: str) -> Dict[str, str]:
    """
    处理关于SOP的对话，可能是编辑指令或普通聊天。
    
    返回一个字典，包含类型和内容。
    """
    print(f"Debug - [converse_about_sop] Classifying user instruction: '{user_instruction}'")
    intent = _classify_sop_intent(user_instruction)
    print(f"Debug - [converse_about_sop] Classified intent as: '{intent}'")
    
    if intent == "edit":
        try:
            modified_sop = _edit_sop_with_diff(original_sop, user_instruction, hardware_context)
            # 统一响应格式，使用 'content' 作为键
            return {"type": "edit", "content": modified_sop}
        except ValueError as e:
            # 专门处理diff应用失败的情况
            print(f"Warning - [converse_about_sop] Diff application failed: {e}")
            error_message = f"I tried to edit the SOP, but couldn't apply the changes. This can happen if the instruction is ambiguous. Please try rephrasing. (Error: {str(e)})"
            return {"type": "chat", "content": error_message}
        except Exception as e:
            # 处理其他所有未知错误
            print(f"Error - [converse_about_sop] An unexpected error occurred: {e}")
            error_message = f"I encountered an unexpected server error while trying to edit the SOP. Please try again. (Details: {str(e)})"
            return {"type": "chat", "content": error_message}
    else: # intent == "chat"
        chat_response = _chat_about_sop(original_sop, user_instruction)
        # 统一响应格式，使用 'content' 作为键
        return {"type": "chat", "content": chat_response}


def _classify_sop_intent(user_instruction: str) -> str:
    """
    (内部函数) 对用户的SOP相关指令进行意图分类。
    """
    try:
        import json
        import re
        from backend.prompts import SOP_CONVERSATION_CLASSIFIER_PROMPT_TEMPLATE
        from langchain_core.prompts import PromptTemplate
        from langchain.chains import LLMChain

        # Use specialized, faster model for intent classification
        intent_llm = ChatOpenAI(
            model_name=DEEPSEEK_INTENT_MODEL,
            openai_api_base=DEEPSEEK_BASE_URL,
            openai_api_key=DEEPSEEK_API_KEY,
            temperature=0.0,
            max_retries=1,
            request_timeout=20
        )

        prompt = PromptTemplate(
            input_variables=["user_instruction"],
            template=SOP_CONVERSATION_CLASSIFIER_PROMPT_TEMPLATE
        )
        chain = LLMChain(llm=intent_llm, prompt=prompt)
        
        response_str = chain.run({"user_instruction": user_instruction})
        
        # 增强的JSON解析
        try:
            # 1. 尝试直接解析
            response_json = json.loads(response_str)
        except json.JSONDecodeError:
            # 2. 如果失败，尝试从Markdown代码块中提取
            match = re.search(r'```json\s*(\{.*?\})\s*```', response_str, re.DOTALL)
            if not match:
                # 3. 如果还是失败，尝试在整个字符串中查找JSON对象
                match = re.search(r'(\{.*?\})', response_str, re.DOTALL)
            
            if match:
                response_json = json.loads(match.group(1))
            else:
                # 如果所有方法都失败，抛出异常，由外部catch块处理
                raise ValueError("No valid JSON found in the response.")

        intent = response_json.get("intent", "chat")
        
        if intent not in ["edit", "chat"]:
            return "chat" 
            
        return intent
    except Exception as e:
        print(f"Error during intent classification, defaulting to 'chat': {e}")
        # 降级：如果JSON解析和提取都失败，使用关键词进行判断
        edit_keywords = [
            'change', 'add', 'remove', 'replace', 'modify', 'update', 'use', 'delete', 'make', 
            '改', '增加', '添加', '删除', '替换', '修改', '更新', '使用', '设为', '换成', '变为'
        ]
        if any(keyword in user_instruction.lower() for keyword in edit_keywords):
            print("Info: JSON parsing failed, but keyword matching classified as 'edit'.")
            return "edit"
        return "chat"


def _classify_code_intent(user_instruction: str) -> str:
    """
    (Internal) Classifies the user's intent for a code-related instruction.
    """
    try:
        import json
        import re
        from backend.prompts import CODE_CONVERSATION_CLASSIFIER_PROMPT_TEMPLATE
        from langchain_core.prompts import PromptTemplate
        from langchain.chains import LLMChain

        # Use specialized, faster model for intent classification
        intent_llm = ChatOpenAI(
            model_name=DEEPSEEK_INTENT_MODEL,
            openai_api_base=DEEPSEEK_BASE_URL,
            openai_api_key=DEEPSEEK_API_KEY,
            temperature=0.0,
            max_retries=1,
            request_timeout=20
        )

        prompt = PromptTemplate(
            input_variables=["user_instruction"],
            template=CODE_CONVERSATION_CLASSIFIER_PROMPT_TEMPLATE
        )
        chain = LLMChain(llm=intent_llm, prompt=prompt)
        
        response_str = chain.run({"user_instruction": user_instruction})
        
        # Enhanced JSON parsing
        try:
            response_json = json.loads(response_str)
        except json.JSONDecodeError:
            match = re.search(r'```json\s*(\{.*?\})\s*```', response_str, re.DOTALL)
            if not match:
                match = re.search(r'(\{.*?\})', response_str, re.DOTALL)
            
            if match:
                response_json = json.loads(match.group(1))
            else:
                raise ValueError("No valid JSON found in the response.")

        intent = response_json.get("intent", "chat")
        
        return intent if intent in ["edit", "chat"] else "chat"
    except Exception as e:
        print(f"Error during code intent classification, defaulting to 'chat': {e}")
        # Fallback to keyword matching
        edit_keywords = [
            'change', 'add', 'remove', 'replace', 'modify', 'update', 'use', 'delete', 'make', 
            '改', '增加', '添加', '删除', '替换', '修改', '更新', '使用', '设为', '换成', '变为'
        ]
        if any(keyword in user_instruction.lower() for keyword in edit_keywords):
            print("Info: JSON parsing failed, but keyword matching classified as 'edit' for code.")
            return "edit"
        return "chat"

def _chat_about_code(original_code: str, user_instruction: str) -> str:
    """
    (Internal) Handles a general chat conversation about the code.
    """
    try:
        from backend.prompts import GENERAL_CODE_CHAT_PROMPT_TEMPLATE
        from langchain_core.prompts import PromptTemplate
        from langchain.chains import LLMChain

        prompt = PromptTemplate(
            input_variables=["original_code", "user_instruction"],
            template=ENG_GENERAL_CODE_CHAT_PROMPT_TEMPLATE
        )
        chain = LLMChain(llm=llm, prompt=prompt)
        
        response = chain.run({
            "original_code": original_code,
            "user_instruction": user_instruction
        })
        return response
    except Exception as e:
        print(f"Error during general code chat: {e}")
        return "Sorry, I encountered an error while trying to respond."

def converse_about_code(original_code: str, user_instruction: str) -> Dict[str, str]:
    """
    使用自主 LangGraph Agent 处理代码相关的对话
    
    这个重构后的函数用新的 Agent 替换了旧的固化逻辑，
    Agent 可以自主决定是否需要修改代码、运行模拟，或只是回答问题。
    
    Args:
        original_code: 原始代码
        user_instruction: 用户指令
        
    Returns:
        包含类型和内容的字典
    """
    print(f"Debug - [converse_about_code] Processing user instruction with autonomous agent")
    
    try:
        # Initialize Agent state
        initial_state = CodeAgentState(
            messages=[
                HumanMessage(content=f"""I have the following Opentrons protocol. Please help me with the user's request.

User Request: {user_instruction}

Current Code:
```python
{original_code}
```

Please analyze the user's request. If it requires modifying the code, use the `modify_code_tool`. If it requires validating the code, use the `simulate_protocol_tool`. If it's a general question, answer it directly. You can call multiple tools as needed to complete the task.""")
            ],
            current_code=original_code
        )
        
        # Invoke the Agent graph
        print("Debug - [converse_about_code] Starting Agent execution")
        final_state = code_agent_graph.invoke(initial_state)
        
        # 分析 Agent 的最终响应
        last_message = final_state["messages"][-1]
        final_code = final_state.get("current_code", original_code)
        
        print(f"Debug - [converse_about_code] Agent 执行完成")
        
        # 判断是否有代码修改
        if final_code != original_code:
            # 代码被修改了，返回编辑类型
            return {
                "type": "edit", 
                "content": final_code
            }
        else:
            # 没有代码修改，返回聊天类型
            if hasattr(last_message, 'content'):
                response_content = last_message.content
            else:
                response_content = "Task completed."
            
            return {
                "type": "chat",
                "content": response_content
            }
            
    except Exception as e:
        print(f"Error - [converse_about_code] Agent execution failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback to a simple reply
        error_message = f"I'm sorry, I encountered a problem while processing your request. Error details: {str(e)}\n\nPlease try rephrasing your request or ensure the code is formatted correctly."
        return {"type": "chat", "content": error_message}


def _validate_python_syntax(code: str) -> tuple[bool, str]:
    """
    快速验证Python代码语法是否正确。
    
    Args:
        code: 要检查的Python代码字符串
        
    Returns:
        (is_valid, error_message): 如果语法正确返回(True, "")，否则返回(False, 错误信息)
    """
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        error_msg = f"Python语法错误: {e.msg} (第{e.lineno}行"
        if e.offset:
            error_msg += f", 第{e.offset}列"
        error_msg += ")"
        if e.text:
            error_msg += f"\n问题行: {e.text.strip()}"
        return False, error_msg
    except Exception as e:
        return False, f"代码解析异常: {str(e)}"


# 旧的 _edit_and_validate_code_with_retries 函数已被新的 Agent 架构取代
# NOTE: Removed deprecated functions _edit_and_validate_code_with_retries and edit_code_with_diff
# These have been replaced by the new conversational code editing system using LangGraph agents

async def converse_about_code_stream(original_code: str, user_instruction: str):
    """
    Handles conversational code edits via a real-time stream.
    Yields events for agent thoughts, tool calls, and final results.
    """
    print(f"Debug - [converse_about_code_stream] Starting stream for: {user_instruction}")
    
    # Initialize Agent state
    initial_state = CodeAgentState(
        messages=[
            HumanMessage(content=f"""I have the following Opentrons protocol. Please help me with the user's request.

User Request: {user_instruction}

Current Code:
```python
{original_code}
```

Please analyze the user's request. If it requires modifying the code, use the `modify_code_tool`. If it requires validating the code, use the `simulate_protocol_tool`. If it's a general question, answer it directly. You can call multiple tools as needed to complete the task.""")
        ],
        current_code=original_code
    )
    
    current_state = initial_state
    
    try:
        async for chunk in code_agent_graph.astream(initial_state):
            for node_name, node_output in chunk.items():
                current_state.update(node_output)
                
                if node_name == "agent":
                    yield {
                        "event_type": "thought",
                        "message": "The agent is thinking about the next step..."
                    }
                    # Check if the agent is calling a tool
                    last_message = current_state["messages"][-1]
                    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                         yield {
                            "event_type": "tool_call",
                            "tool_name": last_message.tool_calls[0]['name'],
                            "message": f"Decided to call tool: `{last_message.tool_calls[0]['name']}`"
                        }

                elif node_name == "tools":
                    last_tool_message = current_state["messages"][-1]
                    yield {
                        "event_type": "tool_result",
                        "tool_name": last_tool_message.name,
                        "content": last_tool_message.content,
                        "message": f"Tool `{last_tool_message.name}` finished execution."
                    }
        
        # Final result analysis
        final_code = current_state.get("current_code", original_code)
        if final_code != original_code:
            final_content = final_code
            result_type = "edit"
        else:
            final_content = current_state["messages"][-1].content
            result_type = "chat"
            
        yield {
            "event_type": "final_result",
            "type": result_type,
            "content": final_content,
            "message": "Agent has finished the task."
        }

    except Exception as e:
        print(f"Error - [converse_about_code_stream] Stream failed: {e}")
        yield {
            "event_type": "error",
            "message": str(e)
        }