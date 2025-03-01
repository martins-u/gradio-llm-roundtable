from typing import Dict, List, Tuple
import time
import logging
import requests

import anthropic
from openai import OpenAI

from src.config import Config
from src.models import Message, Provider
from src.utils import APIError, get_error_details

logger = logging.getLogger(__name__)

class LLMClientManager:
    def __init__(self, config: Config):
        self.config = config
        self.anthropic_client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        self.openai_client = OpenAI(api_key=config.openai_api_key)
    
    def get_completion(
        self,
        provider: Provider,
        model: str,
        messages: List[Message],
        system_prompt: str,
        temperature: float
    ) -> str:
        max_retries = 3
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                if provider == Provider.ANTHROPIC:
                    return self._anthropic_completion(model, messages, system_prompt, temperature)
                elif provider == Provider.OPENROUTER:
                    return self._openrouter_completion(model, messages, system_prompt, temperature)
                elif provider == Provider.OPENAI:
                    return self._openai_completion(model, messages, system_prompt, temperature)
                raise ValueError(f"Unknown provider: {provider}")
            except Exception as e:
                last_error = e
                retry_count += 1
                logger.warning(f"Attempt {retry_count} failed: {str(e)}. Retrying...")
                time.sleep(1)
        
        error_msg = get_error_details(last_error)
        logger.error(f"Error getting completion from {provider} after {max_retries} attempts: {error_msg}")
        raise APIError(message=f"Failed after {max_retries} attempts: {error_msg}")
    
    def get_round_table_completions(
        self,
        model_configs: Dict[str, Tuple[Provider, str]],
        messages: List[Message],
        system_prompt: str,
        temperature: float
    ) -> Dict[str, str]:
        results = {}
        errors = []
        
        round_table_system_prompt = system_prompt + "\n\nYou are participating in a round table discussion with other AI models. " \
                               "Provide your perspective on the user's query."
        
        for model_name, (provider, model) in model_configs.items():
            try:
                response = self.get_completion(provider, model, messages, round_table_system_prompt, temperature)
                results[model_name] = response
            except Exception as e:
                error_msg = get_error_details(e)
                logger.error(f"Error getting completion from {model_name}: {error_msg}")
                errors.append(f"{model_name}: {str(e)}")
        
        if not results and errors:
            raise APIError(message=f"All round table models failed: {'; '.join(errors)}")
            
        return results
    
    def get_chairman_summary(
        self,
        provider: Provider,
        model: str,
        messages: List[Message],
        system_prompt: str,
        round_table_responses: Dict[str, str],
        temperature: float
    ) -> str:
        chairman_system_prompt = system_prompt + "\n\nYou are the chairman of a round table discussion. " \
                           "Review the perspectives from other AI models and provide a comprehensive summary that " \
                           "highlights key insights, areas of agreement and disagreement, and your own judgment on the matter."
        
        context_message = "Here are the responses from the round table participants:\n\n"
        for model_name, response in round_table_responses.items():
            context_message += f"=== {model_name} ===\n{response}\n\n"
            
        context_message += "Please synthesize these perspectives and provide your final summary as the chairman."
        
        chairman_messages = []
        
        for msg in messages:
            if msg.role == "user":
                chairman_messages.append(msg)
        
        chairman_messages.append(Message(role="user", content=context_message))
        
        return self.get_completion(provider, model, chairman_messages, chairman_system_prompt, temperature)

    def _anthropic_completion(
        self, model: str, messages: List[Message], system_prompt: str, temperature: float
    ) -> str:
        if model == "claude-3-7-sonnet-20250219":
            self.config.max_tokens = 64000
        try:
            anthropic_messages = []
            
            for msg in messages:
                role = "assistant" if msg.role == "assistant" else "user"
                anthropic_messages.append({"role": role, "content": msg.content})

            response = None
            stream = None
            text_content = []
            text_deltas = False

            if model == "claude-3-7-sonnet-20250219":
                text_deltas = True
                try:
                    stream = self.anthropic_client.messages.create(
                        model=model,
                        system=system_prompt,
                        max_tokens=64000,
                        thinking={
                            "type": "enabled",
                            "budget_tokens": 54000
                        },
                        messages=anthropic_messages,
                        stream=True
                    )
                    for event in stream:
                        if event.type == "content_block_delta" and hasattr(event, 'delta') and hasattr(event.delta, 'text'):
                            text_content.append(event.delta.text)
                except Exception as stream_error:
                    logger.error(f"Streaming error: {str(stream_error)}")
                    text_deltas = False
                    response = self.anthropic_client.messages.create(
                        model=model,
                        system=system_prompt,
                        max_tokens=self.config.max_tokens,
                        temperature=temperature,
                        messages=anthropic_messages
                    )
            else:
                response = self.anthropic_client.messages.create(
                    model=model,
                    system=system_prompt,
                    max_tokens=self.config.max_tokens,
                    temperature=temperature,
                    messages=anthropic_messages
                )
            
            if len(text_content) == 0 and response is not None:
                for content in response.content:
                    if hasattr(content, 'text'):
                        text_content.append(content.text)

            if not text_deltas:
                return "\n".join(text_content)
            else:
                return "".join(text_content)
            
        except Exception as e:
            raise APIError(
                message=str(e),
                response=getattr(e, 'response', None),
                body=getattr(e, 'body', str(e))
            )

    def _openrouter_completion(
        self, model: str, messages: List[Message], system_prompt: str, temperature: float
    ) -> str:
        try:
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.config.openrouter_api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": model,
                "messages": [{"role": "system", "content": system_prompt}] + 
                           [m.model_dump() for m in messages],
                "temperature": temperature
            }
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json().get("choices", [{}])[0].get("message", {}).get("content", "<No data returned>")
        except Exception as e:
            raise APIError(message=str(e))

    def _openai_completion(
        self, model: str, messages: List[Message], system_prompt: str, temperature: float
    ) -> str:
        try:
            if model in ["o1-preview", "gpt-4.5-preview"]:
                completion = self.openai_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": system_prompt}] +
                            [m.model_dump() for m in messages],
                    store=False
                )
            else:
                completion = self.openai_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": system_prompt}] +
                            [m.model_dump() for m in messages],
                    temperature=temperature,
                    store=False
                )
            return completion.choices[0].message.content or ""
        except Exception as e:
            raise APIError(message=str(e))