"""
LLM 引擎：整合 NVIDIA NIM API
用於自然語言議價與決策
"""
import os
from typing import Optional, Dict, Any, List
from loguru import logger
from openai import OpenAI

class LLMEngine:
    """
    封裝 NVIDIA NIM API 呼叫
    預設模型：qwen/qwen3.5-397b-a17b
    """
    def __init__(self, model: str = "qwen/qwen3.5-397b-a17b"):
        self.model = model
        api_key = os.getenv("NVIDIA_NIM_API_KEY")
        base_url = os.getenv("NVIDIA_NIM_ENDPOINT", "https://integrate.api.nvidia.com/v1")
        
        if not api_key:
            logger.warning("⚠️  未找到 NVIDIA_NIM_API_KEY，將使用模擬模式")
            self.client = None
        else:
            self.client = OpenAI(
                api_key=api_key,
                base_url=base_url
            )
            logger.info(f"✅ LLM 引擎已啟動：{model}")

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """
        發送對話請求並取得回應
        messages: [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
        """
        if not self.client:
            return self._mock_response(messages)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=512
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM 呼叫失敗：{e}")
            return self._mock_response(messages)

    def _mock_response(self, messages: List[Dict[str, str]]) -> str:
        """
        當 API 不可用時的模擬回應
        """
        last_msg = messages[-1]["content"] if messages else ""
        if "價格" in last_msg or "價格" in last_msg:
            return "我認為這個價格很合理，可以接受。"
        return "我同意這個提議。"

# 全域實例
llm_engine = LLMEngine()
