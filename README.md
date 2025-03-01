# Gradio based LLM roundtable discussion interface

Made for own amusement and productivity, but maybe it will be useful for someone else too.

Introduce some subject and let LLMs discuss it among themselves.
Selected chairman LLM will summarize the discussion in each round.
User might add some additional context to the discussion, keep conversation context and let it continue in new round.

Token usage is not high, since there is no aggressive agentic prompting in background.

At the moment some currently popular reasoning models are included.

Also there is enhanced privacy - actual conversations are stored locally in `chatbot_sessions` folder as json files.
One can load those sessions and continue the discussion later or view them in the UI.

Pop in API keys, select LLMs and enjoy!

There are however bugs and rough edges, UI needs to be simplified and made in more user-friendly way.

Also tested Claude Code Beta here to tidy up the code.

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