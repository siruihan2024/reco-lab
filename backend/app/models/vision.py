# app/models/vision.py
"""
Vision Language Model Client
使用 Qwen3-VL 进行图片理解
"""
import base64
from typing import Optional
import httpx
from app.config import VL_API_URL, VL_MODEL, OPENAI_API_KEY


class VisionClient:
    """视觉语言模型客户端"""
    
    def __init__(self, base_url: str = VL_API_URL, model: str = VL_MODEL, api_key: str = OPENAI_API_KEY):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
    
    async def understand_image(
        self, 
        image_data: bytes, 
        prompt: Optional[str] = None,
        max_tokens: int = 512
    ) -> str:
        """
        理解图片内容
        
        Args:
            image_data: 图片二进制数据
            prompt: 自定义提示词（可选）
            max_tokens: 最大生成 token 数
            
        Returns:
            理解结果文本
        """
        # 编码图片为 base64
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        image_url = f"data:image/jpeg;base64,{image_base64}"
        
        # 默认提示词：提取商品关键信息
        if not prompt:
            prompt = """请识别图片中的商品，提取以下信息（用简短的关键词）：
1. 商品类别（如：服装、电子产品、食品等）
2. 商品名称或描述（如：T恤、智能手表、零食）
3. 明显特征（如：颜色、材质、品牌、用途）

只返回关键词，用空格分隔，不要解释。例如：运动鞋 Nike 黑色 跑步"""
        
        # 构造消息
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url}
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
        
        # 调用 VL 模型
        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.3  # 低温度保证稳定性
        }
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return content.strip()
        except Exception as e:
            raise Exception(f"Vision model failed: {str(e)}")
    
    async def extract_query(self, image_data: bytes) -> str:
        """
        从图片中提取商品查询关键词
        
        Args:
            image_data: 图片二进制数据
            
        Returns:
            查询关键词字符串
        """
        prompt = """分析图片中的商品，用1-3个最关键的词描述它，适合用于搜索。

示例：
- 泳衣 → 泳衣
- 红色连衣裙 → 连衣裙 红色
- Nike运动鞋 → 运动鞋
- 智能手表 → 智能手表
- 防晒霜 → 防晒霜

只返回关键词，用空格分隔，不要其他内容："""
        
        result = await self.understand_image(image_data, prompt=prompt, max_tokens=50)
        return result.strip()