import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
from langchain_deepseek import ChatDeepSeek

from app.core.config import settings


class StepDocumentation:
    """步骤文档记录"""
    def __init__(self):
        self.step_number: int = 0
        self.step_name: str = ""
        self.description: str = ""
        self.tool: str = ""
        self.tool_input: str = ""
        self.step_type: str = ""
        self.result: str = ""
        self.token_usage: Dict[str, int] = {}
        self.execution_time: float = 0.0
        self.timestamp: str = ""
        self.status: str = "pending"  # pending, running, completed, failed


class TaskDocumentation:
    """任务文档记录"""
    def __init__(self, task: str):
        self.task: str = task
        self.start_time: str = datetime.now().isoformat()
        self.end_time: str = ""
        self.total_tokens: int = 0
        self.steps: List[StepDocumentation] = []
        self.final_result: str = ""
        self.status: str = "running"  # running, completed, failed


class DocumentationTool:
    """文档生成和token统计工具"""
    
    def __init__(self):
        os.environ["DEEPSEEK_API_KEY"] = settings.DEEPSEEK_API_KEY
        self.llm = ChatDeepSeek(model="deepseek-chat")
        self.current_task: Optional[TaskDocumentation] = None
    
    def start_task(self, task: str) -> TaskDocumentation:
        """开始记录任务"""
        self.current_task = TaskDocumentation(task)
        return self.current_task
    
    def add_step(self, step_data: Dict[str, Any], result: str, token_usage: Dict[str, int], execution_time: float) -> StepDocumentation:
        """添加步骤记录"""
        if self.current_task is None:
            raise ValueError("No active task")
        
        step_doc = StepDocumentation()
        step_doc.step_number = len(self.current_task.steps) + 1
        step_doc.step_name = step_data.get("step_name", "")
        step_doc.description = step_data.get("description", "")
        step_doc.tool = step_data.get("tool", "")
        step_doc.tool_input = step_data.get("tool_input", "")
        step_doc.step_type = step_data.get("step_type", "")
        step_doc.result = result
        step_doc.token_usage = token_usage
        step_doc.execution_time = execution_time
        step_doc.timestamp = datetime.now().isoformat()
        step_doc.status = "completed"
        
        self.current_task.steps.append(step_doc)
        self.current_task.total_tokens += token_usage.get("total_tokens", 0)
        
        return step_doc
    
    def complete_task(self, final_result: str) -> TaskDocumentation:
        """完成任务记录"""
        if self.current_task is None:
            raise ValueError("No active task")
        
        self.current_task.end_time = datetime.now().isoformat()
        self.current_task.final_result = final_result
        self.current_task.status = "completed"
        
        return self.current_task
    
    def generate_task_report(self, task_doc: TaskDocumentation) -> str:
        """生成任务报告"""
        try:
            report = f"""
# 任务执行报告

## 任务信息
- **任务描述**: {task_doc.task}
- **开始时间**: {task_doc.start_time}
- **结束时间**: {task_doc.end_time}
- **总Token消耗**: {task_doc.total_tokens}
- **状态**: {task_doc.status}

## 执行步骤详情

"""
            
            for step in task_doc.steps:
                report += f"""
### 步骤 {step.step_number}: {step.step_name}

**描述**: {step.description}
**工具**: {step.tool}
**输入**: {step.tool_input}
**类型**: {step.step_type}
**执行时间**: {step.execution_time:.2f}秒
**Token消耗**: {step.token_usage}
**结果**: {step.result[:500]}{"..." if len(step.result) > 500 else ""}

---
"""
            
            report += f"""
## 最终结果
{task_doc.final_result}

## 统计摘要
- 总步骤数: {len(task_doc.steps)}
- 总Token消耗: {task_doc.total_tokens}
- 平均每步Token: {task_doc.total_tokens // len(task_doc.steps) if task_doc.steps else 0}
"""
            
            return report
            
        except Exception as e:
            return f"报告生成错误: {str(e)}"
    
    def save_task_report(self, task_doc: TaskDocumentation, filename: Optional[str] = None) -> str:
        """保存任务报告到文件"""
        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"task_report_{timestamp}.md"
            
            report = self.generate_task_report(task_doc)
            
            # 确保reports目录存在
            os.makedirs("reports", exist_ok=True)
            filepath = os.path.join("reports", filename)
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(report)
            
            return f"报告已保存到: {filepath}"
            
        except Exception as e:
            return f"保存报告错误: {str(e)}"
    
    def get_token_usage_summary(self, task_doc: TaskDocumentation) -> Dict[str, Any]:
        """获取token使用统计"""
        if not task_doc.steps:
            return {"total_tokens": 0, "step_breakdown": []}
        
        step_breakdown = []
        for step in task_doc.steps:
            step_breakdown.append({
                "step": step.step_number,
                "step_name": step.step_name,
                "tool": step.tool,
                "tokens": step.token_usage.get("total_tokens", 0),
                "prompt_tokens": step.token_usage.get("prompt_tokens", 0),
                "completion_tokens": step.token_usage.get("completion_tokens", 0)
            })
        
        return {
            "total_tokens": task_doc.total_tokens,
            "step_breakdown": step_breakdown,
            "average_tokens_per_step": task_doc.total_tokens // len(task_doc.steps)
        } 