"""
上下文管理工具
提供上下文管理的实用工具函数
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class ContextTools:
    """上下文管理工具类"""

    @staticmethod
    def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
        """从文本中提取关键词"""
        # 简单的关键词提取（可以改进为更复杂的算法）
        words = re.findall(r"\b\w+\b", text.lower())
        word_freq = {}

        # 过滤停用词
        stop_words = {
            "的",
            "是",
            "在",
            "有",
            "和",
            "与",
            "或",
            "但",
            "而",
            "如果",
            "那么",
            "因为",
            "所以",
            "这个",
            "那个",
            "这些",
            "那些",
            "我",
            "你",
            "他",
            "她",
            "它",
            "我们",
            "你们",
            "他们",
            "她们",
            "它们",
            "a",
            "an",
            "the",
            "and",
            "or",
            "but",
            "if",
            "then",
            "because",
            "so",
            "this",
            "that",
            "these",
            "those",
            "i",
            "you",
            "he",
            "she",
            "it",
            "we",
            "they",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "can",
        }

        for word in words:
            if len(word) > 2 and word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1

        # 按频率排序并返回前N个关键词
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:max_keywords]]

    @staticmethod
    def generate_summary(text: str, max_length: int = 200) -> str:
        """生成文本摘要"""
        if len(text) <= max_length:
            return text

        # 简单的摘要生成（可以改进为更复杂的算法）
        sentences = re.split(r"[。！？.!?]", text)
        summary = ""

        for sentence in sentences:
            if len(summary + sentence) <= max_length:
                summary += sentence + "。"
            else:
                break

        return summary.strip()

    @staticmethod
    def parse_markdown_todo(content: str) -> List[Dict[str, Any]]:
        """解析Markdown格式的待办事项"""
        lines = content.split("\n")
        todos = []

        for line in lines:
            line = line.strip()
            if line.startswith("- [ ]") or line.startswith("- [x]"):
                completed = line.startswith("- [x]")
                text = line[4:].strip()
                todos.append({"text": text, "completed": completed})

        return todos

    @staticmethod
    def parse_markdown_history(content: str) -> List[Dict[str, Any]]:
        """解析Markdown格式的历史记录"""
        lines = content.split("\n")
        messages = []
        current_message = {}
        current_content = []

        for line in lines:
            if line.startswith("### ") and ":" in line:
                # 保存之前的消息
                if current_message and current_content:
                    current_message["content"] = "\n".join(current_content).strip()
                    messages.append(current_message)

                # 解析新消息
                parts = line.split(":", 2)
                if len(parts) >= 2:
                    timestamp = parts[0][4:].strip()  # 移除 '### '
                    role = parts[1].strip()
                    current_message = {"timestamp": timestamp, "role": role}
                    current_content = []
            elif line.strip() and current_message:
                current_content.append(line)

        # 添加最后一条消息
        if current_message and current_content:
            current_message["content"] = "\n".join(current_content).strip()
            messages.append(current_message)

        return messages

    @staticmethod
    def parse_markdown_resources(content: str) -> List[Dict[str, str]]:
        """解析Markdown格式的资源链接"""
        lines = content.split("\n")
        resources = []
        current_resource = {}

        for line in lines:
            line = line.strip()
            if line.startswith("## ") and not line.startswith("## 任务信息"):
                # 保存之前的资源
                if current_resource:
                    resources.append(current_resource)

                # 开始新资源
                current_resource = {"title": line[3:].strip()}
            elif line.startswith("- URL:") and current_resource:
                current_resource["url"] = line[6:].strip()
            elif line.startswith("- 描述:") and current_resource:
                current_resource["description"] = line[5:].strip()
            elif line.startswith("- 添加时间:") and current_resource:
                current_resource["added_at"] = line[6:].strip()

        # 添加最后一个资源
        if current_resource:
            resources.append(current_resource)

        return resources

    @staticmethod
    def format_chat_message(
        role: str, content: str, timestamp: Optional[datetime] = None
    ) -> str:
        """格式化聊天消息"""
        if timestamp is None:
            timestamp = datetime.utcnow()

        return f"### {timestamp}: {role}\n{content}\n"

    @staticmethod
    def format_todo_item(text: str, completed: bool = False) -> str:
        """格式化待办事项"""
        checkbox = "- [x]" if completed else "- [ ]"
        return f"{checkbox} {text}"

    @staticmethod
    def format_resource_link(
        title: str, url: str, description: str = "", added_at: Optional[datetime] = None
    ) -> str:
        """格式化资源链接"""
        if added_at is None:
            added_at = datetime.utcnow()

        formatted = f"\n## {title}\n- URL: {url}\n"
        if description:
            formatted += f"- 描述: {description}\n"
        formatted += f"- 添加时间: {added_at}\n"

        return formatted

    @staticmethod
    def format_summary_entry(
        section: str, content: str, updated_at: Optional[datetime] = None
    ) -> str:
        """格式化总结条目"""
        if updated_at is None:
            updated_at = datetime.utcnow()

        return f"\n## {section}\n{content}\n\n---\n更新时间: {updated_at}\n"

    @staticmethod
    def format_scratchpad_entry(
        content: str, timestamp: Optional[datetime] = None
    ) -> str:
        """格式化临时笔记"""
        if timestamp is None:
            timestamp = datetime.utcnow()

        return f"\n### {timestamp}: 临时笔记\n{content}\n"

    @staticmethod
    def calculate_context_size(context_data: Dict[str, Any]) -> int:
        """计算上下文大小（字符数）"""
        total_size = 0

        # 计算基本信息的长度
        for key in ["task_id", "title", "description", "status"]:
            if key in context_data:
                total_size += len(str(context_data[key]))

        # 计算文件内容的长度
        files = context_data.get("files", {})
        for file_type, file_data in files.items():
            if isinstance(file_data, dict) and "content" in file_data:
                total_size += len(file_data["content"])

        return total_size

    @staticmethod
    def compress_context(
        context_data: Dict[str, Any], max_size: int = 10000
    ) -> Dict[str, Any]:
        """压缩上下文数据"""
        current_size = ContextTools.calculate_context_size(context_data)

        if current_size <= max_size:
            return context_data

        # 压缩策略：保留基本信息，压缩文件内容
        compressed = context_data.copy()
        files = compressed.get("files", {})

        for file_type, file_data in files.items():
            if isinstance(file_data, dict) and "content" in file_data:
                content = file_data["content"]
                if len(content) > max_size // len(files):
                    # 生成摘要
                    file_data["content"] = ContextTools.generate_summary(
                        content, max_size // len(files)
                    )
                    file_data["compressed"] = True

        return compressed

    @staticmethod
    def generate_llm_summary(
        text: str, llm, max_length: int = 200, prompt_template: str = None
    ) -> str:
        """使用大模型生成摘要"""
        if prompt_template is None:
            prompt_template = (
                "请对以下内容进行压缩和摘要，保留关键信息，摘要长度不超过{max_length}字：\n"
                + "内容：{text}"
            )
        prompt = prompt_template.format(text=text, max_length=max_length)
        # 兼容 langchain deepseek_llm
        response = llm.invoke(prompt)
        if hasattr(response, "content"):
            return response.content.strip()
        return str(response)

    @staticmethod
    def compress_context_with_llm(
        context_data: Dict[str, Any], llm, max_size: int = 10000
    ) -> Dict[str, Any]:
        """使用大模型对上下文进行压缩（摘要）"""
        current_size = ContextTools.calculate_context_size(context_data)
        if current_size <= max_size:
            return context_data
        compressed = context_data.copy()
        files = compressed.get("files", {})
        for file_type, file_data in files.items():
            if isinstance(file_data, dict) and "content" in file_data:
                content = file_data["content"]
                if len(content) > max_size // max(1, len(files)):
                    # 用LLM生成摘要
                    summary = ContextTools.generate_llm_summary(
                        content, llm, max_length=max_size // max(1, len(files))
                    )
                    file_data["content"] = summary
                    file_data["compressed"] = True
        return compressed

    @staticmethod
    def merge_contexts(
        context1: Dict[str, Any], context2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """合并两个上下文"""
        merged = context1.copy()

        # 合并文件内容
        files1 = merged.get("files", {})
        files2 = context2.get("files", {})

        for file_type, file_data2 in files2.items():
            if file_type in files1:
                # 合并内容
                content1 = files1[file_type].get("content", "")
                content2 = file_data2.get("content", "")
                files1[file_type]["content"] = content1 + "\n\n" + content2
            else:
                files1[file_type] = file_data2

        merged["files"] = files1
        merged["updated_at"] = datetime.utcnow().isoformat()

        return merged

    @staticmethod
    def validate_context_structure(
        context_data: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """验证上下文结构"""
        errors = []
        required_fields = ["task_id", "title", "description", "status"]

        for field in required_fields:
            if field not in context_data:
                errors.append(f"缺少必需字段: {field}")

        if "files" in context_data:
            files = context_data["files"]
            if not isinstance(files, dict):
                errors.append("files字段必须是字典类型")
            else:
                for file_type, file_data in files.items():
                    if not isinstance(file_data, dict):
                        errors.append(f"文件 {file_type} 必须是字典类型")
                    elif "content" not in file_data:
                        errors.append(f"文件 {file_type} 缺少content字段")

        return len(errors) == 0, errors

    @staticmethod
    def create_context_backup(context_data: Dict[str, Any], backup_path: str) -> bool:
        """创建上下文备份"""
        try:
            backup_file = Path(backup_path)
            backup_file.parent.mkdir(parents=True, exist_ok=True)

            with open(backup_file, "w", encoding="utf-8") as f:
                json.dump(context_data, f, ensure_ascii=False, indent=2)

            return True
        except Exception as e:
            print(f"创建备份失败: {e}")
            return False

    @staticmethod
    def load_context_backup(backup_path: str) -> Optional[Dict[str, Any]]:
        """加载上下文备份"""
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                return None

            with open(backup_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"加载备份失败: {e}")
            return None
