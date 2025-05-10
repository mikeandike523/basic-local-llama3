# conversation_token_counter.py

from typing import List
from llama_models.llama3.chat_format import ChatFormat
from llama_models.llama3.tokenizer import Tokenizer
from llama_models.datatypes import RawMessage

class TokenCounter:
    """
    Count tokens in a chat history and check against a model's context window.
    """

    def __init__(self, max_window: int):
        """
        :param max_window: the model's max_seq_len (e.g. 8192)
        """
        self.max_window = max_window
        self.tokenizer = Tokenizer.get_instance()
        self.formatter = ChatFormat(self.tokenizer)

    def count(self, messages: List[RawMessage]) -> int:
        """
        Return the number of tokens when encoding the given chat history.
        """
        llm_input = self.formatter.encode_dialog_prompt(messages)
        return len(llm_input.tokens)

    def fits(self, messages: List[RawMessage], gen_budget: int = 0) -> bool:
        """
        Check whether (history_tokens + gen_budget) <= max_window.
        """
        return (self.count(messages) + gen_budget) <= self.max_window

    def truncate_oldest(
        self,
        messages: List[RawMessage],
        gen_budget: int = 0,
        drop_pairs: bool = True
    ) -> List[RawMessage]:
        """
        Drop oldest messages until it fits.

        :param gen_budget: tokens you plan to generate
        :param drop_pairs: if True, remove user+assistant pairs together
        """
        msgs = messages.copy()
        while not self.fits(msgs, gen_budget) and len(msgs) > 1:
            # always keep the system prompt at index 0
            # drop either a pair (user + assistant) or a single oldest message
            if drop_pairs and len(msgs) > 2:
                # drop msgs[1] (user) and msgs[2] (assistant)
                msgs.pop(1)
                msgs.pop(1)
            else:
                msgs.pop(1)
        return msgs
