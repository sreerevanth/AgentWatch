"""Anthropic Claude streaming interceptor"""
from typing import AsyncGenerator, Optional
import anthropic
from .base import BaseStreamInterceptor, TokenChunk, SafetyResult, TokenStatus

class AnthropicStreamInterceptor(BaseStreamInterceptor):
    """Streaming interceptor for Anthropic Claude"""
    
    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229"):
        super().__init__()
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model
    
    async def intercept_stream(
        self,
        prompt: str,
        model: str = None,
        **kwargs
    ) -> AsyncGenerator[TokenChunk, None]:
        """Intercept Anthropic streaming response"""
        
        model = model or self.model
        self.is_blocked = False
        
        try:
            async with self.client.messages.stream(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            ) as stream:
                token_index = 0
                
                async for event in stream:
                    if self.is_blocked:
                        break
                        
                    if event.type == "content_block_delta":
                        if hasattr(event.delta, 'text') and event.delta.text:
                            token = event.delta.text
                            
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
        """Safety check for Anthropic tokens"""
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