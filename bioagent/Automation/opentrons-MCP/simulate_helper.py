#!/usr/bin/env python3
"""
Opentrons Protocol Simulation Helper
用于在 MCP 中执行协议模拟的辅助脚本
"""

import opentrons.simulate
import traceback
import tempfile
import os
import sys
import json
import argparse
from datetime import datetime


def format_runlog_entry(entry):
    """格式化单个运行日志条目"""
    try:
        payload = entry.get('payload', {})
        text = payload.get('text', '')
        
        # 提取关键信息
        instrument = str(payload.get('instrument', '')).replace('<InstrumentContext: ', '').replace('>', '')
        volume = payload.get('volume')
        location = payload.get('location')
        
        formatted = {
            'action': text,
            'instrument': instrument if instrument != 'None' else None,
            'volume': volume,
            'location': str(location) if location else None
        }
        
        return formatted
    except Exception as e:
        return {'action': str(entry), 'error': str(e)}


def simulate_protocol_from_file(protocol_path, output_format='summary'):
    """从文件路径模拟协议"""
    try:
        if not os.path.exists(protocol_path):
            return {
                'success': False,
                'error': f'Protocol file not found: {protocol_path}',
                'error_type': 'FileNotFoundError'
            }
        
        with open(protocol_path, 'r', encoding='utf-8') as protocol_file:
            runlog, _bundle = opentrons.simulate.simulate(protocol_file)
        
        return format_simulation_result(runlog, output_format, protocol_path)
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__,
            'traceback': traceback.format_exc()
        }


def simulate_protocol_from_code(protocol_code, output_format='summary'):
    """从代码字符串模拟协议"""
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(protocol_code)
            temp_file_path = f.name
        
        try:
            with open(temp_file_path, 'r', encoding='utf-8') as protocol_file:
                runlog, _bundle = opentrons.simulate.simulate(protocol_file)
            
            result = format_simulation_result(runlog, output_format, 'inline_code')
            
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_file_path)
            except:
                pass
        
        return result
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__,
            'traceback': traceback.format_exc()
        }


def format_simulation_result(runlog, output_format, source):
    """格式化模拟结果"""
    result = {
        'success': True,
        'source': source,
        'timestamp': datetime.now().isoformat(),
        'total_steps': len(runlog)
    }
    
    if output_format == 'json':
        # 返回完整的 JSON 格式
        result['runlog'] = [format_runlog_entry(entry) for entry in runlog]
        
    elif output_format == 'detailed':
        # 详细的文本格式
        steps = []
        for i, entry in enumerate(runlog, 1):
            formatted = format_runlog_entry(entry)
            step_text = f"Step {i}: {formatted['action']}"
            if formatted.get('instrument'):
                step_text += f" (Instrument: {formatted['instrument']})"
            if formatted.get('volume'):
                step_text += f" (Volume: {formatted['volume']}µL)"
            steps.append(step_text)
        
        result['steps'] = steps
        
    else:  # summary format
        # 总结格式
        actions = []
        instruments_used = set()
        total_volume = 0
        
        for entry in runlog:
            formatted = format_runlog_entry(entry)
            if formatted.get('instrument'):
                instruments_used.add(formatted['instrument'])
            if formatted.get('volume'):
                total_volume += formatted['volume']
            
            # 简化动作描述
            action = formatted['action']
            if 'Picking up tip' in action:
                actions.append('拿取吸头')
            elif 'Aspirating' in action:
                actions.append(f"吸取 {formatted.get('volume', '?')}µL")
            elif 'Dispensing' in action:
                actions.append(f"分配 {formatted.get('volume', '?')}µL")
            elif 'Dropping tip' in action:
                actions.append('丢弃吸头')
            else:
                actions.append(action)
        
        result['summary'] = {
            'total_steps': len(runlog),
            'instruments_used': list(instruments_used),
            'total_volume_handled': total_volume,
            'key_actions': actions
        }
    
    return result


def main():
    parser = argparse.ArgumentParser(description='Opentrons Protocol Simulator')
    parser.add_argument('--file', help='Protocol file path')
    parser.add_argument('--code', help='Protocol code as string')
    parser.add_argument('--format', choices=['summary', 'detailed', 'json'], 
                       default='summary', help='Output format')
    
    args = parser.parse_args()
    
    if args.file:
        result = simulate_protocol_from_file(args.file, args.format)
    elif args.code:
        result = simulate_protocol_from_code(args.code, args.format)
    else:
        result = {
            'success': False,
            'error': 'Either --file or --code must be provided',
            'error_type': 'ArgumentError'
        }
    
    # 输出结果为 JSON
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()