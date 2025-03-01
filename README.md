# AI Chatbot

A modern chat interface for multiple LLM providers including Anthropic, OpenAI, and OpenRouter. Includes support for round-table discussions with multiple models.

## Features

- Support for multiple AI providers:
  - Anthropic (Claude)
  - OpenAI (GPT models)
  - OpenRouter (various models)
- Standard chat mode with single model responses
- Round-table discussion mode with multiple models
- Save and load chat sessions
- Custom system prompts
- Temperature control
- Auto-save functionality

## Project Structure

```
ai-chatbot/
├── main.py                # Main entry point
├── src/                   # Source code directory
│   ├── config/            # Configuration modules
│   │   ├── app_config.py  # Application configuration
│   │   └── path_config.py # File path configuration
│   ├── interfaces/        # Interface components
│   │   ├── chat_interface.py   # Gradio UI interface
│   │   ├── llm_client.py       # LLM client manager
│   │   └── session_manager.py  # Session and prompt management
│   ├── models/            # Data models
│   │   ├── messages.py    # Message model
│   │   ├── providers.py   # Enum definitions for providers
│   │   └── session.py     # Chat session models
│   └── utils/             # Utility functions
│       └── errors.py      # Error handling utilities
├── chatbot_sessions/      # Saved chat sessions
└── chatbot_prompts/       # Custom system prompts
```

## Setup

1. Create a `.env` file with your API keys:
```
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key
OPENROUTER_API_KEY=your_openrouter_key
```

2. Install dependencies:
```bash
pip install anthropic openai gradio requests python-dotenv
```

3. Run the application:
```bash
python main.py
```

## Round Table Feature

The round table feature allows multiple AI models to discuss a topic together:

1. Switch to "Round Table" mode
2. Add participants from different providers
3. Set a chairman to summarize the discussion
4. Ask your question and watch the models collaborate