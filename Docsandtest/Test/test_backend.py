#!/usr/bin/env python3
"""后端功能详细测试脚本

测试范围：
1. MCP工具加载和发现
2. Biomni工具封装
3. 逆合成工具
4. 基础LangChain功能
5. 前端集成测试
"""

import os
import json
import traceback
from datetime import datetime
from typing import Dict, List, Any

def setup_env():
    """设置测试环境"""
    os.environ["OPENAI_API_BASE"] = "https://api.ai190.com/v1"
    os.environ["OPENAI_API_KEY"] = "sk-Fbf6T3Gd8o3srcifmRyfUa3PfKmtbNuYgNzind0j92h2sV3n"
    os.environ["MCP_CONFIG"] = os.path.join(os.getcwd(), "mcp_config.yaml")

def test_imports():
    """测试基础导入"""
    test_results = {}
    
    try:
        from bioagent.agents import BioAgent
        test_results["bioagent_import"] = {"status": "success", "error": None}
    except Exception as e:
        test_results["bioagent_import"] = {"status": "failed", "error": str(e)}
    
    try:
        from bioagent.agents.mcp_tools import load_mcp_tools
        test_results["mcp_tools_import"] = {"status": "success", "error": None}
    except Exception as e:
        test_results["mcp_tools_import"] = {"status": "failed", "error": str(e)}
    
    try:
        from bioagent.tools.biomni_wrappers import make_biomni_wrapped_tools
        test_results["biomni_wrappers_import"] = {"status": "success", "error": None}
    except Exception as e:
        test_results["biomni_wrappers_import"] = {"status": "failed", "error": str(e)}
    
    return test_results

def test_mcp_tools():
    """测试MCP工具加载"""
    test_results = {}
    
    try:
        from bioagent.agents.mcp_tools import load_mcp_tools
        mcp_tools = load_mcp_tools()
        test_results["mcp_tools_load"] = {
            "status": "success", 
            "count": len(mcp_tools),
            "tools": [tool.name for tool in mcp_tools],
            "error": None
        }
    except Exception as e:
        test_results["mcp_tools_load"] = {
            "status": "failed", 
            "error": str(e),
            "traceback": traceback.format_exc()
        }
    
    return test_results

def test_biomni_tools():
    """测试Biomni工具封装"""
    test_results = {}
    
    try:
        from bioagent.tools.biomni_wrappers import make_biomni_wrapped_tools
        biomni_tools = make_biomni_wrapped_tools()
        test_results["biomni_tools_load"] = {
            "status": "success", 
            "count": len(biomni_tools),
            "tools": [tool.name for tool in biomni_tools[:10]],  # 只显示前10个
            "error": None
        }
    except Exception as e:
        test_results["biomni_tools_load"] = {
            "status": "failed", 
            "error": str(e),
            "traceback": traceback.format_exc()
        }
    
    return test_results

def test_bioagent_creation():
    """测试BioAgent创建"""
    test_results = {}
    
    try:
        from bioagent.agents import BioAgent
        api_keys = {
            "OPENAI_API_KEY": "sk-Fbf6T3Gd8o3srcifmRyfUa3PfKmtbNuYgNzind0j92h2sV3n",
            "MCP_CONFIG": os.path.join(os.getcwd(), "mcp_config.yaml")
        }
        agent = BioAgent(
            model="gemini-2.5-pro", 
            tools_model="gemini-2.5-pro", 
            openai_api_key="sk-Fbf6T3Gd8o3srcifmRyfUa3PfKmtbNuYgNzind0j92h2sV3n", 
            api_keys=api_keys
        )
        
        # 获取工具列表
        tools = agent.agent_executor.tools
        tool_names = [tool.name for tool in tools]
        
        test_results["bioagent_creation"] = {
            "status": "success", 
            "tool_count": len(tools),
            "tools": tool_names,
            "error": None
        }
    except Exception as e:
        test_results["bioagent_creation"] = {
            "status": "failed", 
            "error": str(e),
            "traceback": traceback.format_exc()
        }
    
    return test_results

def test_specific_tools():
    """测试特定工具功能"""
    test_results = {}
    
    # 测试逆合成工具
    try:
        from bioagent.tools.PathPrediction import SMILESToPredictedSynthesisInfo
        synthesis_tool = SMILESToPredictedSynthesisInfo()
        test_results["synthesis_tool"] = {
            "status": "success",
            "name": synthesis_tool.name,
            "description": synthesis_tool.description,
            "error": None
        }
    except Exception as e:
        test_results["synthesis_tool"] = {
            "status": "failed", 
            "error": str(e)
        }
    
    # 测试基因组工具
    try:
        from bioagent.tools.Genome import GenomeCollectorTool, GenomeQueryTool
        genome_collector = GenomeCollectorTool()
        genome_query = GenomeQueryTool()
        test_results["genome_tools"] = {
            "status": "success",
            "tools": [
                {"name": genome_collector.name, "desc": genome_collector.description},
                {"name": genome_query.name, "desc": genome_query.description}
            ],
            "error": None
        }
    except Exception as e:
        test_results["genome_tools"] = {
            "status": "failed", 
            "error": str(e)
        }
    
    return test_results

def test_config_files():
    """测试配置文件"""
    test_results = {}
    
    # 测试MCP配置
    try:
        import yaml
        with open("mcp_config.yaml", "r", encoding="utf-8") as f:
            mcp_config = yaml.safe_load(f)
        
        test_results["mcp_config"] = {
            "status": "success",
            "servers": list(mcp_config.get("mcp_servers", {}).keys()),
            "enabled_servers": [
                name for name, config in mcp_config.get("mcp_servers", {}).items() 
                if config.get("enabled", True)
            ],
            "error": None
        }
    except Exception as e:
        test_results["mcp_config"] = {
            "status": "failed", 
            "error": str(e)
        }
    
    return test_results

def run_all_tests():
    """运行所有测试"""
    print("🧪 开始BioAgent后端功能测试")
    print("=" * 50)
    
    # 设置环境
    setup_env()
    
    all_results = {}
    
    # 运行各项测试
    tests = [
        ("基础导入测试", test_imports),
        ("MCP工具测试", test_mcp_tools),
        ("Biomni工具测试", test_biomni_tools),
        ("BioAgent创建测试", test_bioagent_creation),
        ("特定工具测试", test_specific_tools),
        ("配置文件测试", test_config_files),
    ]
    
    for test_name, test_func in tests:
        print(f"\n🔍 运行 {test_name}...")
        try:
            results = test_func()
            all_results[test_name] = results
            
            # 打印简要结果
            for key, result in results.items():
                status = "✅" if result["status"] == "success" else "❌"
                print(f"  {status} {key}: {result['status']}")
                if result["status"] == "failed":
                    print(f"    错误: {result['error']}")
        except Exception as e:
            all_results[test_name] = {"error": str(e), "traceback": traceback.format_exc()}
            print(f"  ❌ 测试失败: {e}")
    
    # 生成详细报告
    generate_test_report(all_results)
    
    return all_results

def generate_test_report(results: Dict[str, Any]):
    """生成详细测试报告"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"test_report_{timestamp}.json"
    
    # 生成报告数据
    report = {
        "timestamp": timestamp,
        "summary": {},
        "detailed_results": results
    }
    
    # 统计总结
    total_tests = 0
    passed_tests = 0
    
    for test_category, test_results in results.items():
        if isinstance(test_results, dict):
            for test_name, test_result in test_results.items():
                if isinstance(test_result, dict) and "status" in test_result:
                    total_tests += 1
                    if test_result["status"] == "success":
                        passed_tests += 1
    
    report["summary"] = {
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": total_tests - passed_tests,
        "success_rate": f"{(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "0%"
    }
    
    # 保存报告
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n📊 测试报告已保存到: {report_file}")
    print(f"总测试数: {total_tests}, 通过: {passed_tests}, 失败: {total_tests - passed_tests}")
    print(f"成功率: {report['summary']['success_rate']}")

if __name__ == "__main__":
    run_all_tests()

