import json
from app.intent import parse_intent

def test_run_process_minimal():
    intent = parse_intent("运行进程 Alpha variables: a=1;b=true iterations: 3 append: false delay: 5 workunit: wu-1 试运行")
    assert intent.action == "run_process"
    assert intent.dry_run is True
    assert intent.process_name == "Alpha"
    assert intent.variables == {"a": 1, "b": True}
    assert intent.iterations == 3
    assert intent.append is False
    assert intent.minimum_delay == 5
    assert intent.workunit_name == "wu-1"

def test_simple_actions():
    intent = parse_intent("status")
    assert intent.action == "status"
    
    intent = parse_intent("启动")
    assert intent.action == "start"
    
    intent = parse_intent("停止")
    assert intent.action == "stop"
    
    intent = parse_intent("设备")
    assert intent.action == "devices"

def test_process_with_variables():
    intent = parse_intent("run process TestProc variables: x=10;y=hello")
    assert intent.action == "run_process"
    assert intent.process_name == "TestProc"
    assert intent.variables == {"x": 10, "y": "hello"}
    assert intent.dry_run is False