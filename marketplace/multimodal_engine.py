"""
多模態 AI 引擎
支持圖像識別、OCR、視覺問答等任務
"""
import os
from typing import Optional, Dict, Any
from loguru import logger
from openai import OpenAI  # 兼容 NVIDIA NIM 或 OpenAI

class MultimodalEngine:
    """
    多模態處理引擎
    支持：圖像識別、OCR、視覺問答
    """
    def __init__(self, model: str = "qwen/qwen-vl-max"):
        self.model = model
        api_key = os.getenv("NVIDIA_NIM_API_KEY") or os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("NVIDIA_NIM_ENDPOINT", "https://integrate.api.nvidia.com/v1")
        
        if not api_key:
            logger.warning("⚠️  未檢測到 API Key，多模態功能將使用模擬模式")
            self.client = None
        else:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
            logger.info(f"✅ 多模態引擎已啟動：{model}")

    def analyze_image(self, image_url: str, prompt: str = "請描述這張圖片") -> str:
        """
        分析圖片並返回文字描述
        :param image_url: 圖片 URL
        :param prompt: 提示詞
        """
        if not self.client:
            return self._mock_response(prompt)
        
        try:
            # 構建多模態請求
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_url}}
                        ]
                    }
                ],
                max_tokens=512
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"多模態分析失敗：{e}")
            return f"分析失敗：{str(e)}"

    def _mock_response(self, prompt: str) -> str:
        """模擬回應（用於測試）"""
        return f"[模擬模式] 已收到圖片並理解您的問題：{prompt}"

# 全域實例
multimodal_engine = MultimodalEngine()
