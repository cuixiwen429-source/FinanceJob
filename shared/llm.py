"""FinanceJob LLM 客户端 — DeepSeek API 封装

统一 AI 调用接口，支持 JSON 结构化输出、重试和降级。
"""

import json
import os
from typing import Optional

from openai import OpenAI


class LLMClient:
    """DeepSeek / OpenAI-compatible API 客户端"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", os.getenv("OPENAI_API_KEY", ""))
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
        self.model = model or os.getenv("LLM_MODEL", "deepseek-chat")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=120.0,
        )

    def chat(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> str:
        """发送对话请求，返回文本响应"""
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.extend(messages)

        kwargs = dict(
            model=self.model,
            messages=msgs,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    def chat_json(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        temperature: float = 0.1,
    ) -> dict:
        """发送对话请求，返回解析后的 JSON"""
        text = self.chat(messages, system=system, temperature=temperature, json_mode=True)
        # 尝试提取 JSON 块
        text = text.strip()
        if text.startswith("```json"):
            text = text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif text.startswith("```"):
            text = text.split("```", 1)[1].split("```", 1)[0].strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw": text, "error": "JSON parse failed"}

    def simple_prompt(
        self,
        prompt: str,
        system: str = "You are a helpful assistant for a finance job seeker in China.",
        temperature: float = 0.3,
    ) -> str:
        """简单的单轮对话"""
        return self.chat(
            [{"role": "user", "content": prompt}],
            system=system,
            temperature=temperature,
        )


# 全局单例
_llm_instance: Optional[LLMClient] = None


def get_llm() -> LLMClient:
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LLMClient()
    return _llm_instance
