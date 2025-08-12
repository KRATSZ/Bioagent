from typing import Optional, List, Tuple
import langchain
from dotenv import load_dotenv
from langchain import PromptTemplate, chains
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from pydantic import ValidationError
from rmrkl import ChatZeroShotAgent, RetryAgentExecutor
from langchain.memory import ConversationBufferMemory  # 新增导入
from .prompts import FORMAT_INSTRUCTIONS, QUESTION_PROMPT, REPHRASE_TEMPLATE, SUFFIX
from .tools import make_tools


def _make_llm(model, temp, api_key, streaming: bool = False):
    llm = langchain.chat_models.ChatOpenAI(
        temperature=temp,
        model_name=model,
        request_timeout=1000,
        streaming=streaming,
        callbacks=[StreamingStdOutCallbackHandler()],
        openai_api_key=api_key,
    )
    return llm


class BioAgent:
    def __init__(
        self,
        tools=None,
        model="gpt-4-0613",
        tools_model="gpt-3.5-turbo-0613",
        temp=0.1,
        max_iterations=40,
        verbose=True,
        streaming: bool = True,
        openai_api_key: Optional[str] = None,
        api_keys: dict = {},
        local_rxn: bool = False,
    ):
        """Initialize BioAgent."""

        load_dotenv()
        try:
            self.llm = _make_llm(model, temp, openai_api_key, streaming)
        except ValidationError:
            raise ValueError("Invalid OpenAI API key")

        if tools is None:
            api_keys["OPENAI_API_KEY"] = openai_api_key
            tools_llm = _make_llm(tools_model, temp, openai_api_key, streaming)
            tools = make_tools(tools_llm, api_keys=api_keys, local_rxn=local_rxn, verbose=verbose)

            # 新增记忆组件
            self.memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True
            )

            # 修改agent_executor初始化
            self.agent_executor = RetryAgentExecutor.from_agent_and_tools(
                tools=tools,
                agent=ChatZeroShotAgent.from_llm_and_tools(
                    self.llm,
                    tools,
                    suffix=SUFFIX,
                    format_instructions=FORMAT_INSTRUCTIONS,
                    question_prompt=QUESTION_PROMPT,
                ),
                verbose=True,
                max_iterations=max_iterations,
                memory=self.memory,  # 添加记忆组件
            )

        rephrase = PromptTemplate(
            input_variables=["question", "agent_ans","chat_history"], template=REPHRASE_TEMPLATE
        )

        self.rephrase_chain = chains.LLMChain(prompt=rephrase, llm=self.llm)

    def run(self, prompt: str, history: List[Tuple[str, str]] = None) -> str:
        """支持连续对话的run方法"""
        try:
            # 处理对话历史
            if history:
                for human, ai in history:
                    self.memory.save_context({"input": human}, {"output": ai})

            # 执行agent
            outputs = self.agent_executor({"input": prompt,"chat_history":self.memory})

            # 返回当前响应
            return outputs["output"]
        except Exception as e:
            return f"Error occurred: {str(e)}"
