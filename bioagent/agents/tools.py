from langchain import agents
from langchain.base_language import BaseLanguageModel
from bioagent.tools import *
from langchain.memory import ConversationBufferMemory
from bioagent.agents.mcp_tools import load_mcp_tools
from bioagent.tools.biomni_wrappers import make_biomni_wrapped_tools
import os

def make_tools(llm: BaseLanguageModel, api_keys: dict = {}, local_rxn: bool=False, verbose=True):


    # 创建共享内存
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=False)
    chemspace_api_key = api_keys.get("CHEMSPACE_API_KEY") or os.getenv(
        "CHEMSPACE_API_KEY"
    )
    all_tools = agents.load_tools([])
    all_tools += [
        KnowledgeGraphSearch(llm=llm),
        SMILESToBiosyntheticPathway(),
        AddReactantsToBionavi(memory),
        SMILESToPredictedSynthesisInfo(llm=llm,memory=memory),
        GenomeCollectorTool(),
        GenomeQueryTool()
    ]

    # Load MCP tools if config exists
    mcp_cfg = api_keys.get("MCP_CONFIG") or os.getenv("MCP_CONFIG") or "./mcp_config.yaml"
    try:
        if os.path.exists(mcp_cfg):
            mcp_tools = load_mcp_tools(mcp_cfg)
            if mcp_tools:
                all_tools += mcp_tools
    except Exception:
        pass

    # Wrap selected Biomni tools
    try:
        biomni_tools = make_biomni_wrapped_tools(
            whitelist_modules=["database", "literature", "biochemistry", "genetics"]
        )
        if biomni_tools:
            all_tools += biomni_tools
    except Exception:
        pass

    return all_tools
