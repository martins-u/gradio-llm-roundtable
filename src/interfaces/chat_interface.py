from datetime import datetime
from typing import Any, Dict, Generator, List, Optional, Tuple
import logging
import gradio as gr

from src.config import Config, PathConfig
from src.interfaces import LLMClientManager, SessionManager, PromptManager
from src.models import ChatMode, ChatSession, Provider
from src.utils import get_error_details

logger = logging.getLogger(__name__)

class ChatInterface:
    def __init__(self):
        PathConfig.ensure_dirs()
        self.config = Config.load_from_env()
        self.llm_manager = LLMClientManager(self.config)
        self.session_manager = SessionManager()
        self.prompt_manager = PromptManager()
        
        self.default_prompt = self.prompt_manager.load_default_prompt()
        self.initial_session = ChatSession(system=self.default_prompt if self.default_prompt else "")
        
    @staticmethod
    def _translate_to_chatbox(session: ChatSession) -> List[Tuple]:
        """Translates session history to a format suitable for the Gradio chatbox"""
        if session.mode == ChatMode.STANDARD:
            # Standard mode - pairs of user/assistant messages
            display_history = []
            for i in range(0, len(session.history), 2):
                user_text = session.history[i].content
                assistant_text = session.history[i+1].content if i+1 < len(session.history) else ""
                display_history.append((user_text, assistant_text))
            return display_history
        else:
            # Round table mode - group messages by user query
            display_history = []
            i = 0
            while i < len(session.history):
                if session.history[i].role == "user":
                    user_text = session.history[i].content
                    
                    # Collect all assistant responses until the next user message
                    all_responses = []
                    j = i + 1
                    while j < len(session.history) and session.history[j].role == "assistant":
                        if session.history[j].source:
                            all_responses.append(f"**{session.history[j].source}**: {session.history[j].content}")
                        else:
                            all_responses.append(session.history[j].content)
                        j += 1
                        
                    # Join all responses with dividers
                    if all_responses:
                        assistant_text = "\n\n---\n\n".join(all_responses)
                    else:
                        assistant_text = ""
                        
                    display_history.append((user_text, assistant_text))
                    i = j  # Jump to the next user message
                else:
                    # Skip any out-of-order messages
                    i += 1
                    
            return display_history

    def _handle_message(
        self,
        message: str,
        session: ChatSession,
        provider: str,
        model: str,
        temperature: float
    ) -> Tuple[List[Tuple[str, str]], ChatSession, str]:
        if not message.strip():
            return [], session, ""
            
        session.add_message("user", message)
        
        try:
            if session.mode == ChatMode.STANDARD:
                # Standard chat mode - single model response
                response = self.llm_manager.get_completion(
                    Provider(provider),
                    model,
                    session.history,
                    session.system,
                    temperature
                )
                session.add_message("assistant", response)
            
            else:
                # Round table mode - multiple model responses followed by chairman summary
                if not session.round_table.models:
                    return [], session, "No models configured for round table. Please add models first."
                    
                if not session.round_table.chairman_model:
                    return [], session, "No chairman model selected for round table. Please select a chairman."
                
                # Get responses from all round table participants
                round_table_responses = self.llm_manager.get_round_table_completions(
                    session.round_table.models,
                    session.history,
                    session.system,
                    temperature
                )
                
                # Add each participant's response to the session history
                for model_name, response in round_table_responses.items():
                    session.add_message("assistant", response, model_name)
                
                # Get chairman's summary
                chairman_provider, chairman_model = session.round_table.chairman_model
                chairman_response = self.llm_manager.get_chairman_summary(
                    chairman_provider,
                    chairman_model,
                    session.history,
                    session.system,
                    round_table_responses,
                    temperature
                )
                
                # Add chairman's response with special marker
                chairman_name = f"Chairman ({chairman_model})"
                session.add_message("assistant", chairman_response, chairman_name)
            
            # Auto-save after successful response
            if len(session.history) > 4:  # Only auto-save if there's meaningful content
                self._auto_save_session(session)
            
            return self._translate_to_chatbox(session), session, ""
            
        except Exception as e:
            error_msg = get_error_details(e)
            logger.error(f"Error processing message: {error_msg}")
            return [], session, error_msg

    def _update_models(self, provider: str) -> Dict[str, Any]:
        return gr.update(
            choices=self.config.models[provider],
            value=self.config.models[provider][0]
        )

    def _refresh_sessions(self) -> Dict[str, Any]:
        return gr.update(choices=self.session_manager.list_sessions())

    def _load_prompt(
        self, prompt_file: str, session: ChatSession
    ) -> Tuple[ChatSession, str]:
        try:
            if not prompt_file:
                return session, "No prompt file selected"
            prompt_content = self.prompt_manager.load_prompt(prompt_file)
            session.system = prompt_content
            return session, f"Successfully loaded prompt from {prompt_file}"
        except Exception as e:
            error_msg = get_error_details(e)
            return session, f"Error loading prompt: {error_msg}"

    def _save_session(
        self, session: ChatSession, filename: str
    ) -> Tuple[str, Dict[str, Any]]:
        try:
            if not filename.strip():
                return "Please enter a filename", gr.update()
            result = self.session_manager.save_session(session, filename)
            return result, gr.update(choices=self.session_manager.list_sessions())
        except Exception as e:
            error_msg = get_error_details(e)
            return f"Error saving session: {error_msg}", gr.update()

    def _load_session(
        self, filename: str
    ) -> Tuple[ChatSession, str, List[Tuple[str, str]], str, Dict[str, Any]]:
        try:
            if not filename:
                return ChatSession(), "No session file selected", [], ChatMode.STANDARD.value, gr.update(visible=False)
            session, message = self.session_manager.load_session(filename)
            
            # Update UI based on session mode
            chat_mode = session.mode.value
            round_table_visible = session.mode == ChatMode.ROUND_TABLE
            
            return session, message, self._translate_to_chatbox(session), chat_mode, gr.update(visible=round_table_visible)
        except Exception as e:
            error_msg = get_error_details(e)
            return ChatSession(), f"Error loading session: {error_msg}", [], ChatMode.STANDARD.value, gr.update(visible=False)

    def _clear_session(self) -> Tuple[ChatSession, List]:
        # Preserve the current system prompt when clearing
        current_system = self.initial_session.system
        return ChatSession(system=current_system), []

    def _auto_save_session(self, session: ChatSession) -> None:
        """Auto-save the current session with timestamp"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"autosave_{timestamp}.json"
            self.session_manager.save_session(session, filename)
            logger.info(f"Session auto-saved to {filename}")
        except Exception as e:
            logger.error(f"Failed to auto-save session: {str(e)}")

    def build_interface(self) -> gr.Blocks:
        with gr.Blocks() as demo:
            gr.Markdown("## Enhanced Multi-Provider Chat Interface")
            
            with gr.Row():
                chat_mode_radio = gr.Radio(
                    label="Chat Mode",
                    choices=[mode.value for mode in ChatMode],
                    value=ChatMode.STANDARD.value
                )
            
            with gr.Row():
                provider_dropdown = gr.Dropdown(
                    label="Provider",
                    choices=[p.value for p in Provider],
                    value=Provider.ANTHROPIC.value
                )
                model_dropdown = gr.Dropdown(
                    label="Model",
                    choices=self.config.models[Provider.ANTHROPIC],
                    value=self.config.models[Provider.ANTHROPIC][0]
                )
                temperature_slider = gr.Slider(
                    minimum=0, maximum=2, step=0.01, value=0.7, label="Temperature"
                )

            # Round Table Configuration Section (conditionally visible)
            with gr.Accordion("Round Table Configuration", open=False) as round_table_config:
                gr.Markdown("### Round Table Participants")
                
                with gr.Row():
                    rt_model_name = gr.Textbox(
                        label="Participant Name",
                        placeholder="Enter a name for this participant"
                    )
                    rt_provider = gr.Dropdown(
                        label="Provider",
                        choices=[p.value for p in Provider],
                        value=Provider.ANTHROPIC.value
                    )
                    rt_model = gr.Dropdown(
                        label="Model",
                        choices=self.config.models[Provider.ANTHROPIC],
                        value=self.config.models[Provider.ANTHROPIC][0]
                    )
                    add_rt_model_button = gr.Button("Add Participant")
                
                rt_models_table = gr.Dataframe(
                    headers=["Name", "Provider", "Model"],
                    row_count=0,
                    col_count=(3, "fixed"),
                    interactive=False
                )
                
                remove_rt_model_button = gr.Button("Remove Selected Participant")
                
                gr.Markdown("### Chairman Configuration")
                with gr.Row():
                    chairman_provider = gr.Dropdown(
                        label="Chairman Provider",
                        choices=[p.value for p in Provider],
                        value=Provider.ANTHROPIC.value
                    )
                    chairman_model = gr.Dropdown(
                        label="Chairman Model",
                        choices=self.config.models[Provider.ANTHROPIC],
                        value=self.config.models[Provider.ANTHROPIC][0]
                    )
                    set_chairman_button = gr.Button("Set Chairman")
                
                chairman_status = gr.Textbox(label="Chairman Status", value="No chairman selected")

            with gr.Row():
                prompt_dropdown = gr.Dropdown(
                    label="System Prompt",
                    choices=self.prompt_manager.list_prompts(),
                    value=PathConfig.DEFAULT_PROMPT_FILE if (self.prompt_manager.prompts_dir / PathConfig.DEFAULT_PROMPT_FILE).exists() else None
                )
                load_prompt_button = gr.Button("Load Selected Prompt")
                prompt_status = gr.Textbox(label="Prompt Status")

            chatbox = gr.Chatbot(label="Chat", resizeable = True)
            msg_input = gr.Textbox(
                label="Your Message",
                placeholder="Type your message here...",
                lines=1
            )

            with gr.Row():
                with gr.Column():
                    session_filename = gr.Textbox(
                        label="Session Filename",
                        placeholder="Enter filename to save session"
                    )
                    save_button = gr.Button("Save Session")
                    save_status = gr.Textbox(label="Save Status")

                with gr.Column():
                    session_dropdown = gr.Dropdown(
                        label="Load Session",
                        choices=self.session_manager.list_sessions(),
                        value=None
                    )
                    refresh_sessions_button = gr.Button("Refresh Sessions List")
                    load_button = gr.Button("Load Session")
                    load_status = gr.Textbox(label="Load Status")

            clear_button = gr.Button("Clear Chat")
            
            session_state = gr.State(self.initial_session.to_dict())
            
            # Add a status indicator
            status_indicator = gr.Textbox(
                label="Status", 
                value="Ready", 
                interactive=False
            )
            
            def handle_message_with_status(
                message: str,
                session_dict: Dict,
                provider: str,
                model: str,
                temperature: float
            ) -> Generator[Tuple[List[Tuple[str, str]], Dict, str, str], None, None]:
                
                session = ChatSession.from_dict(session_dict)
                
                if session.mode == ChatMode.STANDARD:
                    status_update = "Processing your request..."
                    yield [], session_dict, "", status_update
                    
                    result = self._handle_message(message, session, provider, model, temperature)
                    yield result[0], result[1].to_dict(), "", "Ready"
                else:
                    # For round table, provide more detailed status updates
                    status_update = "Starting round table discussion..."
                    yield [], session_dict, "", status_update
                    
                    # Instead of directly handling the message, we'll provide more detailed updates
                    session.add_message("user", message)
                    
                    try:
                        if not session.round_table.models:
                            yield [], session.to_dict(), "", "No models configured for round table"
                            return
                            
                        if not session.round_table.chairman_model:
                            yield [], session.to_dict(), "", "No chairman model selected for round table"
                            return
                        
                        # Get responses from all round table participants
                        status_update = "Collecting opinions from round table participants..."
                        yield [], session.to_dict(), "", status_update
                        
                        round_table_responses = self.llm_manager.get_round_table_completions(
                            session.round_table.models,
                            session.history,
                            session.system,
                            temperature
                        )
                        
                        # Add each participant's response to the session history
                        for model_name, response in round_table_responses.items():
                            session.add_message("assistant", response, model_name)
                            # Update the display after each model responds
                            yield self._translate_to_chatbox(session), session.to_dict(), "", f"Got response from {model_name}..."
                        
                        # Get chairman's summary
                        status_update = "Waiting for chairman's summary..."
                        yield self._translate_to_chatbox(session), session.to_dict(), "", status_update
                        
                        chairman_provider, chairman_model = session.round_table.chairman_model
                        chairman_response = self.llm_manager.get_chairman_summary(
                            chairman_provider,
                            chairman_model,
                            session.history,
                            session.system,
                            round_table_responses,
                            temperature
                        )
                        
                        # Add chairman's response with special marker
                        chairman_name = f"Chairman ({chairman_model})"
                        session.add_message("assistant", chairman_response, chairman_name)
                        
                        # Auto-save after successful response
                        if len(session.history) > 4:  # Only auto-save if there's meaningful content
                            self._auto_save_session(session)
                        
                        yield self._translate_to_chatbox(session), session.to_dict(), "", "Round table discussion complete"
                        
                    except Exception as e:
                        error_msg = get_error_details(e)
                        logger.error(f"Error in round table discussion: {error_msg}")
                        yield [], session.to_dict(), "", f"Error: {str(e)}"
            
            def load_prompt(
                prompt_file: str,
                session_dict: Dict
            ) -> Tuple[Dict, str]:
                session = ChatSession.from_dict(session_dict)
                result = self._load_prompt(prompt_file, session)
                return result[0].to_dict(), result[1]
            
            def load_session(filename: str) -> Tuple[Dict, str, List[Tuple[str, str]], str, Dict[str, Any]]:
                result = self._load_session(filename)
                return result[0].to_dict(), result[1], result[2], result[3], result[4]
            
            def clear_session() -> Tuple[Dict, List, str]:
                result = self._clear_session()
                status_message = "Chat session cleared"
                return result[0].to_dict(), result[1], status_message
            
            def save_session(
                session_dict: Dict,
                filename: str
            ) -> Tuple[str, Dict[str, Any]]:
                session = ChatSession.from_dict(session_dict)
                return self._save_session(session, filename)
            
            # Define Round Table specific functions
            def add_rt_model(
                name: str, provider: str, model: str, session_dict: Dict
            ) -> Tuple[Dict, List[List[str]], str]:
                if not name.strip():
                    return session_dict, [], "Please enter a name for the participant"
                    
                session = ChatSession.from_dict(session_dict)
                
                # Check if the name already exists
                if name in session.round_table.models:
                    return session_dict, [[n, p.value, m] for n, (p, m) in session.round_table.models.items()], f"Participant '{name}' already exists"
                
                session.round_table.add_model(name, Provider(provider), model)
                
                # Convert models to a list for the dataframe
                models_list = []
                for model_name, (prov, mod) in session.round_table.models.items():
                    models_list.append([model_name, prov.value, mod])
                
                status_message = f"Added {name} ({model}) to round table participants"
                return session.to_dict(), models_list, status_message
            
            def remove_rt_model(
                selected_data, session_dict: Dict, models_table: List[List[str]]
            ) -> Tuple[Dict, List[List[str]], str]:
                if selected_data is None or len(selected_data) == 0:
                    return session_dict, models_table, "No participant selected for removal"
                    
                session = ChatSession.from_dict(session_dict)
                removed_names = []
                
                # In newer Gradio versions, selected_data contains the actual selected rows
                for row in selected_data:
                    if len(row) >= 1:
                        model_name = row[0]
                        if model_name in session.round_table.models:
                            del session.round_table.models[model_name]
                            removed_names.append(model_name)
                
                # Rebuild the models list
                models_list = []
                for model_name, (prov, mod) in session.round_table.models.items():
                    models_list.append([model_name, prov.value, mod])
                
                status_message = f"Removed participant(s): {', '.join(removed_names)}" if removed_names else "No participants removed"
                return session.to_dict(), models_list, status_message
            
            def set_chairman(
                provider: str, model: str, session_dict: Dict
            ) -> Tuple[Dict, str, str]:
                session = ChatSession.from_dict(session_dict)
                session.round_table.set_chairman(Provider(provider), model)
                
                chairman_status = f"Chairman: {model} ({provider})"
                status_message = f"Set chairman to {model} ({provider})"
                
                return session.to_dict(), chairman_status, status_message
            
            def toggle_chat_mode(mode: str, session_dict: Dict) -> Tuple[Dict, Dict[str, Any], str, List[Tuple[str, str]]]:
                session = ChatSession.from_dict(session_dict)
                old_mode = session.mode
                new_mode = ChatMode(mode)
                
                # Clear chat history when switching modes to maintain clean separation
                if old_mode != new_mode and session.has_content():
                    # Create a new session that preserves system prompt but clears history
                    current_system = session.system
                    round_table_config = session.round_table
                    
                    # Create a new clean session with same settings but clear history
                    session = ChatSession(
                        system=current_system,
                        round_table=round_table_config,
                        mode=new_mode
                    )
                    
                    clear_history_message = f"Chat history cleared when switching to {new_mode.value} mode."
                else:
                    # Just update the mode without clearing if no history or no mode change
                    session.mode = new_mode
                    clear_history_message = ""
                
                # Toggle visibility of round table configuration
                round_table_visible = mode == ChatMode.ROUND_TABLE.value
                
                # Update status message
                if session.mode == ChatMode.ROUND_TABLE:
                    participants_count = len(session.round_table.models)
                    has_chairman = session.round_table.chairman_model is not None
                    
                    if participants_count == 0:
                        status_message = f"Switched to Round Table mode. Please add participants. {clear_history_message}"
                    elif not has_chairman:
                        status_message = f"Switched to Round Table mode with {participants_count} participants. Please set a chairman. {clear_history_message}"
                    else:
                        status_message = f"Switched to Round Table mode with {participants_count} participants and chairman. {clear_history_message}"
                else:
                    status_message = f"Switched to Standard Chat mode. {clear_history_message}"
                
                # Return empty chatbox to reflect cleared history
                chat_display = []
                
                return session.to_dict(), gr.update(visible=round_table_visible), status_message, chat_display
            
            def update_rt_provider_models(provider: str) -> Dict[str, Any]:
                return gr.update(
                    choices=self.config.models[provider],
                    value=self.config.models[provider][0]
                )
            
            # Connect all the event handlers
            msg_input.submit(
                handle_message_with_status,
                inputs=[msg_input, session_state, provider_dropdown, model_dropdown, temperature_slider],
                outputs=[chatbox, session_state, msg_input, status_indicator]
            )
            
            provider_dropdown.change(
                self._update_models,
                inputs=[provider_dropdown],
                outputs=[model_dropdown]
            )
            
            # Round table specific event handlers
            chat_mode_radio.change(
                toggle_chat_mode,
                inputs=[chat_mode_radio, session_state],
                outputs=[session_state, round_table_config, status_indicator, chatbox]
            )
            
            rt_provider.change(
                update_rt_provider_models,
                inputs=[rt_provider],
                outputs=[rt_model]
            )
            
            chairman_provider.change(
                update_rt_provider_models,
                inputs=[chairman_provider],
                outputs=[chairman_model]
            )
            
            add_rt_model_button.click(
                add_rt_model,
                inputs=[rt_model_name, rt_provider, rt_model, session_state],
                outputs=[session_state, rt_models_table, status_indicator]
            )
            
            remove_rt_model_button.click(
                remove_rt_model,
                inputs=[rt_models_table, session_state, rt_models_table],
                outputs=[session_state, rt_models_table, status_indicator]
            )
            
            set_chairman_button.click(
                set_chairman,
                inputs=[chairman_provider, chairman_model, session_state],
                outputs=[session_state, chairman_status, status_indicator]
            )
            
            save_button.click(
                save_session,
                inputs=[session_state, session_filename],
                outputs=[save_status, session_dropdown]
            )
            
            # When loading an existing round table session, show the current participants
            def update_rt_models_on_load(session_dict: Dict) -> Tuple[List[List[str]], str]:
                session = ChatSession.from_dict(session_dict)
                
                # Convert models to a list for the dataframe
                models_list = []
                for model_name, (prov, mod) in session.round_table.models.items():
                    models_list.append([model_name, prov.value, mod])
                
                # Update chairman status
                chairman_text = "No chairman selected"
                if session.round_table.chairman_model:
                    prov, model = session.round_table.chairman_model
                    chairman_text = f"Chairman: {model} ({prov.value})"
                
                return models_list, chairman_text
            
            load_button.click(
                load_session,
                inputs=[session_dropdown],
                outputs=[session_state, load_status, chatbox, chat_mode_radio, round_table_config]
            ).then(
                update_rt_models_on_load,
                inputs=[session_state],
                outputs=[rt_models_table, chairman_status]
            )
            
            refresh_sessions_button.click(
                self._refresh_sessions,
                outputs=[session_dropdown]
            )

            load_prompt_button.click(
                load_prompt,
                inputs=[prompt_dropdown, session_state],
                outputs=[session_state, prompt_status]
            )
            
            clear_button.click(
                clear_session,
                outputs=[session_state, chatbox, status_indicator]
            )

        return demo
