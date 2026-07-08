"""OpenAI streaming interceptor"""

from collections.abc import AsyncGenerator

from openai import AsyncOpenAI

from .base import BaseStreamInterceptor, SafetyResult, TokenChunk, TokenStatus


class OpenAIStreamInterceptor(BaseStreamInterceptor):
    def __init__(self, api_key: str, model: str = "gpt-4"):
        super().__init__()
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def intercept_stream(
        self, prompt: str, model: str | None = None, **kwargs
    ) -> AsyncGenerator[TokenChunk, None]:
        # Reset state for new stream
        self.reset_state()
        model = model or self.model

        try:
            stream = await self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
                **kwargs
            )

            token_index = 0

            async for chunk in stream:
                if self.is_blocked:
                    break

                # Handle regular content
                if chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    safety_result = await self.process_token(token)

                    token_chunk = TokenChunk(
                        content=token,
                        index=token_index,
                        status=safety_result.status,
                        status_reason=safety_result.reason,
                    )

                    if safety_result.status == TokenStatus.BLOCKED:
                        self.is_blocked = True
                        token_chunk.content = f"[BLOCKED: {safety_result.reason}]"
                        yield token_chunk
                        break

                    yield token_chunk
                    token_index += 1

                # Handle tool calls
                if chunk.choices[0].delta.tool_calls:
                    tool_call = chunk.choices[0].delta.tool_calls[0]
                    tool_name = tool_call.function.name if tool_call.function else None
                    tool_args = tool_call.function.arguments if tool_call.function else ""

                    if tool_args:
                        safety_result = await self.process_token(tool_args)

                        token_chunk = TokenChunk(
                            content=tool_args,
                            index=token_index,
                            is_tool_call=True,
                            tool_name=tool_name,
                            tool_args=tool_args,
                            status=safety_result.status,
                            status_reason=safety_result.reason,
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
                status_reason=str(e),
            )

    async def _safety_check(self) -> SafetyResult:
        partial_text = self._build_partial_command()

        dangerous = self._detect_dangerous_patterns(partial_text)
        if dangerous:
            return SafetyResult(
                status=TokenStatus.BLOCKED,
                reason=f"Dangerous pattern detected: {dangerous}",
                blocked_at_index=self.total_tokens,
                partial_match=dangerous,
                confidence=0.95,
            )

        suspicious = self._detect_suspicious_patterns(partial_text)
        if suspicious:
            return SafetyResult(
                status=TokenStatus.SUSPICIOUS,
                reason=f"Suspicious pattern: {suspicious}",
                confidence=0.6,
            )

        return SafetyResult(status=TokenStatus.SAFE)