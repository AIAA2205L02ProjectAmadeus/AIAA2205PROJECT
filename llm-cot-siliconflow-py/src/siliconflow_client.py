import os
import requests
from dotenv import load_dotenv

class SiliconflowClient:
    """
    用于与 Siliconflow API 交互的客户端。
    """
    def __init__(self, model_name: str):
        load_dotenv()
        self.api_key = os.getenv("SILICONFLOW_API_KEY")
        if not self.api_key:
            raise ValueError("未找到 SILICONFLOW_API_KEY。请在 .env 文件中设置。")
        
        self.api_url = "https://api.siliconflow.cn/v1/chat/completions"
        self.model_name = model_name

    def generate(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.7) -> str:
        """
        调用 Siliconflow API 生成文本。

        :param prompt: 发送给模型的提示。
        :param max_tokens: 生成内容的最大长度。
        :param temperature: 控制生成文本的随机性。
        :return: 模型生成的文本内容。
        """
        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {self.api_key}",
            "content-type": "application/json"
        }
        
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=120)
            response.raise_for_status()  # 如果响应状态码不是 2xx，则抛出异常
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            return content.strip()

        except requests.exceptions.RequestException as e:
            print(f"调用 API 时发生错误: {e}")
            return f"API_ERROR: {e}"
        except (KeyError, IndexError) as e:
            print(f"解析 API 响应时发生错误: {e}")
            print(f"原始响应: {response.text}")
            return f"RESPONSE_PARSE_ERROR: {e}"