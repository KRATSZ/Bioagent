#!/usr/bin/env python3
"""专门测试ChemMCP的脚本"""

import subprocess
import sys
import os

def test_chemmcp_installation():
    """测试ChemMCP是否已安装"""
    try:
        result = subprocess.run([sys.executable, "-m", "chemmcp", "--help"], 
                              capture_output=True, text=True, timeout=10)
        print(f"ChemMCP --help 退出码: {result.returncode}")
        if result.stdout:
            print(f"标准输出:\n{result.stdout[:500]}")
        if result.stderr:
            print(f"错误输出:\n{result.stderr[:500]}")
        return result.returncode == 0
    except FileNotFoundError:
        print("❌ ChemMCP 模块未找到")
        return False
    except subprocess.TimeoutExpired:
        print("❌ ChemMCP 调用超时")
        return False
    except Exception as e:
        print(f"❌ ChemMCP 测试异常: {e}")
        return False

def test_chemmcp_module_direct():
    """直接测试chemmcp模块导入"""
    try:
        import chemmcp
        print(f"✅ ChemMCP 模块导入成功, 版本: {getattr(chemmcp, '__version__', 'unknown')}")
        return True
    except ImportError as e:
        print(f"❌ ChemMCP 模块导入失败: {e}")
        return False

def check_required_packages():
    """检查ChemMCP所需的包"""
    required_packages = ["uv", "docker", "rdkit"]
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == "uv":
                result = subprocess.run(["uv", "--version"], capture_output=True, text=True, timeout=5)
                if result.returncode != 0:
                    missing_packages.append(package)
            elif package == "docker":
                result = subprocess.run(["docker", "--version"], capture_output=True, text=True, timeout=5)
                if result.returncode != 0:
                    missing_packages.append(package)
            else:
                __import__(package)
        except (ImportError, FileNotFoundError, subprocess.TimeoutExpired):
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ 缺少依赖包: {missing_packages}")
    else:
        print("✅ 所有必需包已安装")
    
    return len(missing_packages) == 0

if __name__ == "__main__":
    print("🧪 测试ChemMCP状态")
    print("=" * 40)
    
    # 测试直接导入
    module_ok = test_chemmcp_module_direct()
    
    # 测试命令行
    cmd_ok = test_chemmcp_installation()
    
    # 检查依赖
    deps_ok = check_required_packages()
    
    print("\n📊 ChemMCP状态总结:")
    print(f"模块导入: {'✅' if module_ok else '❌'}")
    print(f"命令行调用: {'✅' if cmd_ok else '❌'}")
    print(f"依赖包: {'✅' if deps_ok else '❌'}")
    
    if not (module_ok or cmd_ok):
        print("\n💡 建议:")
        print("1. 安装ChemMCP: pip install git+https://github.com/OSU-NLP-Group/ChemMCP.git")
        print("2. 或者暂时禁用ChemMCP: 在mcp_config.yaml中设置 enabled: false")

