"""Google Gemini streaming interceptor"""
from typing import AsyncGenerator, Optional
import google.generativeai as genai
from .base import BaseStreamInterceptor, TokenChunk, SafetyResult, TokenStatus

class GoogleStreamInterceptor(BaseStreamInterceptor):
    """Streaming interceptor for Google Gemini"""
    
    def __init__(self, api_key: str, model: str = "gemini-pro"):
        super().__init__()
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.model_name = model
    
    async def intercept_stream(
        self,
        prompt: str,
        model: str = None,
        **kwargs
    ) -> AsyncGenerator[TokenChunk, None]:
        """Intercept Google Gemini streaming response"""
        
        model_name = model or self.model_name
        self.is_blocked = False
        
        try:
            # Gemini streaming
            response = await self.model.generate_content_async(
                prompt,
                stream=True,
                **kwargs
            )
            
            token_index = 0
            
            async for chunk in response:
                if self.is_blocked:
                    break
                    
                if chunk.text:
                    token = chunk.text
                    
                    safety_result = await self.process_token(token)
                    
                    token_chunk = TokenChunk(
                        content=token,
                        index=token_index,
                        status=safety_result.status,
                        status_reason=safety_result.reason
                    )
                    
                    if safety_result.status == TokenStatus.BLOCKED:
                        self.is_blocked = True
                        token_chunk.content = f"[BLOCKED: {safety_result.reason}]"
                        yield token_chunk
                        break
                    
                    yield token_chunk
                    token_index += 1
                    
        except Exception as e:
            yield TokenChunk(
                content=f"[ERROR: {str(e)}]",
                index=0,
                status=TokenStatus.BLOCKED,
                status_reason=str(e)
            )
    
    async def _safety_check(self) -> SafetyResult:
        """Safety check for Google tokens"""
        partial_text = self._build_partial_command()
        
        dangerous = self._detect_dangerous_patterns(partial_text)
        if dangerous:
            return SafetyResult(
                status=TokenStatus.BLOCKED,
                reason=f"Dangerous pattern detected: {dangerous}",
                blocked_at_index=self.total_tokens,
                partial_match=dangerous,
                confidence=0.95
            )
        
        suspicious = self._detect_suspicious_patterns(partial_text)
        if suspicious:
            return SafetyResult(
                status=TokenStatus.SUSPICIOUS,
                reason=f"Suspicious pattern: {suspicious}",
                confidence=0.6
            )
        
        return SafetyResult(status=TokenStatus.SAFE)