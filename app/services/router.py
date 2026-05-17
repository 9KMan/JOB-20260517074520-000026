from enum import Enum
from typing import List, Dict, Optional
import re


class TaskCategory(str, Enum):
    CODE = "code"
    ANALYSIS = "analysis"
    SUMMARIZATION = "summarization"
    QA = "qa"
    CREATIVE = "creative"
    GENERAL = "general"


class Model(str, Enum):
    CLAUDE = "claude-3-5-sonnet"
    GPT4 = "gpt-4-turbo"
    GEMINI = "gemini-1.5-pro"


MODEL_COSTS = {
    Model.CLAUDE.value: {"input": 3, "output": 15},
    Model.GPT4.value: {"input": 10, "output": 30},
    Model.GEMINI.value: {"input": 1.25, "output": 5},
}


CODE_KEYWORDS = [
    "function", "def ", "class ", "import ", "export ", "const ", "let ", "var ",
    "return ", "if ", "else", "for ", "while ", "switch ", "case ", "try ",
    "except", "catch", "throw", "async ", "await", "=>", "->", "::",
    "{", "}", "(", ")", "[", "]", ";", "=", "+", "-", "*", "/", "%",
    "code", "debug", "compile", "runtime", "error", "syntax", "api",
    "function", "method", "variable", "loop", "array", "object", "string",
]

ANALYSIS_KEYWORDS = [
    "analyze", "analysis", "compare", "evaluate", "assess", "review",
    "research", "study", "examine", "investigate", "consider", "determine",
    "findings", "insights", "recommend", "conclusion", "data", "metrics",
]

SUMMARIZATION_KEYWORDS = [
    "summarize", "summary", "brief", "overview", "tldr", "recap",
    "condense", "shorten", "abridge", "outline", "key points", "highlights",
]

QA_KEYWORDS = [
    "what", "why", "how", "when", "where", "who", "which", "question",
    "answer", "explain", "describe", "define", "tell me", "information",
    "fact", "true", "false", "yes", "no", "maybe",
]

CREATIVE_KEYWORDS = [
    "create", "write", "story", " poem", "song", "creative", "imagine",
    "design", " brainstorm", "invent", "generate", "new", "original",
]


class RequestClassifier:
    def __init__(self):
        self.categories = {
            TaskCategory.CODE: CODE_KEYWORDS,
            TaskCategory.ANALYSIS: ANALYSIS_KEYWORDS,
            TaskCategory.SUMMARIZATION: SUMMARIZATION_KEYWORDS,
            TaskCategory.QA: QA_KEYWORDS,
            TaskCategory.CREATIVE: CREATIVE_KEYWORDS,
        }

    def classify(self, text: str) -> TaskCategory:
        text_lower = text.lower()
        scores: Dict[TaskCategory, int] = {}

        for category, keywords in self.categories.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            scores[category] = score

        max_category = max(scores.items(), key=lambda x: x[1])[0]
        return max_category if scores[max_category] > 0 else TaskCategory.GENERAL


class AIRouter:
    def __init__(self):
        self.classifier = RequestClassifier()
        self.model_preferences = {
            TaskCategory.CODE: [Model.CLAUDE, Model.GPT4],
            TaskCategory.ANALYSIS: [Model.CLAUDE, Model.GPT4],
            TaskCategory.SUMMARIZATION: [Model.GPT4, Model.GEMINI],
            TaskCategory.QA: [Model.GPT4, Model.GEMINI],
            TaskCategory.CREATIVE: [Model.CLAUDE, Model.GPT4],
            TaskCategory.GENERAL: [Model.GPT4, Model.GEMINI],
        }

    def select_model(self, text: str, preferences: Optional[List[str]] = None) -> str:
        category = self.classifier.classify(text)
        available_models = self.model_preferences.get(category, [Model.GPT4])

        if preferences:
            for pref in preferences:
                if pref in [m.value for m in available_models]:
                    return pref

        return available_models[0].value

    def get_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        costs = MODEL_COSTS.get(model, {"input": 0, "output": 0})
        input_cost = (input_tokens / 1_000_000) * costs["input"]
        output_cost = (output_tokens / 1_000_000) * costs["output"]
        return round(input_cost + output_cost, 4)


router = AIRouter()