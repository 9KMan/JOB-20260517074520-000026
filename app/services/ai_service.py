from typing import List, Dict, Any, Optional, Tuple
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.schema import HumanMessage, SystemMessage
from app.core.config import get_settings

settings = get_settings()


class AIService:
    def __init__(self):
        self.openai_model = ChatOpenAI(
            api_key=settings.openai_api_key,
            model="gpt-4-turbo",
            temperature=0.7,
        )
        self.claude_model = ChatAnthropic(
            api_key=settings.anthropic_api_key,
            model="claude-3-5-sonnet-20241022",
            temperature=0.7,
        )
        self.model_mapping = {
            "gpt-4-turbo": self.openai_model,
            "claude-3-5-sonnet": self.claude_model,
            "gemini-1.5-pro": self.openai_model,
        }

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> Tuple[str, int, int]:
        chat_messages = []
        
        if system_prompt:
            chat_messages.append(SystemMessage(content=system_prompt))
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                chat_messages.append(HumanMessage(content=content))
            else:
                chat_messages.append(HumanMessage(content=content))
        
        llm = self.model_mapping.get(model, self.openai_model)
        llm.temperature = temperature
        
        response = await llm.ainvoke(chat_messages)
        response_content = response.content if hasattr(response, 'content') else str(response)
        
        input_tokens = sum(len(str(m)) // 4 for m in chat_messages)
        output_tokens = len(str(response_content)) // 4
        
        return response_content, input_tokens, output_tokens

    async def chat_with_rag(
        self,
        messages: List[Dict[str, str]],
        model: str,
        context_chunks: List[str],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> Tuple[str, int, int]:
        context = "\n\n".join([f"Context: {chunk}" for chunk in context_chunks])
        
        rag_system_prompt = f"""You are an AI assistant with access to a knowledge base. 
Use the following context to answer questions accurately. If the context doesn't contain 
the answer, say so.

{context}

{system_prompt or ''}"""
        
        return await self.chat(messages, model, rag_system_prompt, temperature)


ai_service = AIService()