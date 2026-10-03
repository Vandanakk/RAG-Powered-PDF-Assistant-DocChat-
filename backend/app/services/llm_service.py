from typing import Optional
from google import genai
from google.genai import errors
from app.config import settings

class LLMService:
    def __init__(self, api_key: Optional[str] = None, model_name: str = settings.GEMINI_MODEL):
        self._explicit_api_key = api_key
        self.model_name = model_name
        self._client = None
        self._cached_key = None

    @property
    def api_key(self) -> str:
        key = self._explicit_api_key or settings.GEMINI_API_KEY
        return (key or "").strip().strip("\"'")

    def _get_client(self) -> genai.Client:
        current_key = self.api_key
        if not current_key or current_key in ("your_gemini_api_key", "your_gemini_api_key_here"):
            raise ValueError(
                "Gemini API key is not configured. Please set a valid GEMINI_API_KEY in your .env file."
            )

        if self._client is None or self._cached_key != current_key:
            self._client = genai.Client(api_key=current_key)
            self._cached_key = current_key

        return self._client


    def generate_grounded_answer(
        self,
        question: str,
        context: str,
        history: Optional[list] = None,
    ) -> str:
        """
        Generate answer using ONLY the provided document context with the strict grounded prompt.
        Prevents hallucination and stops Gemini from answering from general knowledge.
        Provides conceptual synthesis for explanation questions rather than indexing/listing.
        """
        client = self._get_client()

        history_block = ""
        if history:
            turn_lines = []
            for h in history[-6:]:
                role = getattr(h, "role", None) or (h.get("role") if isinstance(h, dict) else "user")
                text = getattr(h, "text", None) or (h.get("text") if isinstance(h, dict) else "")
                role_label = "User" if role == "user" else "Assistant"
                if text and str(text).strip():
                    turn_lines.append(f"{role_label}: {str(text).strip()}")
            if turn_lines:
                history_block = "RECENT CONVERSATION HISTORY:\n" + "\n".join(turn_lines) + "\n\n"

        prompt = f"""You are answering questions about the uploaded document.

When the user asks to explain a topic, do not merely list section titles or summarize the table of contents. Synthesize the actual information contained in the retrieved passages into a clear conceptual explanation.

If the retrieved passages contain headings plus detailed paragraphs, use the detailed paragraphs to explain what each component does, how the components connect, and why they are used.

For explanation, architecture, or methodology questions, structure the answer conceptually where information is present in the context:
- What is the overall approach and objective?
- What data and biological inputs are used?
- How is the graph constructed and what relation types are used?
- What is the baseline?
- What is the proposed improvement or architecture?
- How does patient conditioning work?
- How does knowledge-guided attention work?
- How does message passing work?
- How is severity predicted?
- What is the auxiliary objective (if mentioned)?

Strict Grounding Rules:
1. Answer using ONLY the provided document context below.
2. Do not fabricate details or invent information that isn't present in the document.
3. If the document does not provide enough detail to explain something, say so instead of inventing an explanation.
4. If the answer cannot be found in the provided context, say:
'I couldn't find the answer in the uploaded document.'

{history_block}DOCUMENT CONTEXT:
{context}

QUESTION:
{question}"""

        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
            if response and response.text:
                return response.text.strip()
            return "I couldn't find the answer in the uploaded document."
        except errors.ClientError as e:
            raise RuntimeError(f"Gemini API Client Error: {e.message if hasattr(e, 'message') else str(e)}")
        except errors.APIError as e:
            raise RuntimeError(f"Gemini API Error ({getattr(e, 'code', 'error')}): {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Failed to generate response from Gemini: {str(e)}")


_llm_service = None

def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
