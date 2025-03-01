#!/usr/bin/env python3

import logging
from src.config import Config
from src.interfaces.chat_interface import ChatInterface

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    # Try to load environment variables from .env file
    try:
        from dotenv import load_dotenv
        load_dotenv()
        logger.info("Loaded environment variables from .env file")
    except ImportError:
        logger.warning("python-dotenv not installed. Using environment variables directly.")
    
    interface = ChatInterface()
    
    # Validate config before starting
    if not Config.validate_config(interface.config):
        logger.error("Missing required API keys. Please check your environment variables or .env file.")
        print("\nError: Missing API keys. Please create a .env file with your API keys or set them as environment variables.")
        print("See .env.template for required keys.\n")
        return
    
    interface.build_interface().launch()

if __name__ == "__main__":
    main()