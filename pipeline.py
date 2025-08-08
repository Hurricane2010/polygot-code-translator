from dotenv import load_dotenv
import os
from langchain import PromptTemplate, LLMChain
from langchain.llms import OpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from services.lint_service import LintService
from chunk_code import chunk_code
from services.execution_service import ExecutionService
import concurrent.futures

load_dotenv()

PROMPT_TEMPLATES = {
    'r': """
# Convert the following Python code to R, ignore prompts with no code

{source_chunk}

# R translation:
""",
    'java': """
// Convert the following Python code to Java, ignore prompts with no code

{source_chunk}

// Java translation:
""",
    'pyspark': """
# Convert the following Python code to Pyspark, ignore prompts with no code

{source_chunk}

# Pyspark translation:
""",
}

class PolyglotPipeline:
    """Pipeline for translating Python code to other languages."""
    def __init__(self, target_lang: str, chunk_size: int = 2000, chunk_overlap: int = 200):
        self.target = target_lang
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in environment variables.")
        self.llm = OpenAI(temperature=0, openai_api_key=api_key)
        template_str = PROMPT_TEMPLATES.get(target_lang)
        if not template_str:
            raise ValueError(f"Unsupported target language: {target_lang}")
        self.prompt = PromptTemplate(template=template_str, input_variables=["source_chunk"])
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def wrap_java_code(self, code: str) -> str:
        indented = "\n".join("        " + line if line.strip() != "" else "" for line in code.splitlines())
        wrapped = (
            "public class TranslatedProgram {\n"
            "    public static void main(String[] args) {\n"
            f"{indented}\n"
            "    }\n"
            "}\n"
        )
        return wrapped

    def run(self, source: str) -> tuple[str, list[dict]]:
        chunks = chunk_code(source)

        def translate_chunk(chunk):
            if not chunk.strip():
                return {"code": "", "exec": None}
            try:
                translated = self.chain.run({
                    "source_chunk": chunk
                }).strip()

                linted = LintService.validate_and_fix(translated, self.target)

                if self.target == "java":
                    linted = self.wrap_java_code(linted)

                exec_result = ExecutionService.execute_code(linted, self.target)
                return {"code": linted, "exec": exec_result}
            except Exception as e:
                return {
                    "code": f"# Failed to translate chunk:\n# {e}\n\n{chunk}",
                    "exec": {"success": False, "output": "", "error": str(e)}
                }

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(translate_chunk, chunks))

        full_code = "\n\n".join(r["code"] for r in results)
        return full_code, [r["exec"] for r in results]


class PythonVersionPipeline:
    """Pipeline for upgrading/downgrading Python code to a target version."""
    def __init__(self, target_version: str):
        self.target_version = target_version
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in environment variables.")
        self.llm = OpenAI(temperature=0, openai_api_key=api_key)
        self.prompt = PromptTemplate(
            template=f"""
# You are a Python version migration assistant.
# Convert the given Python code to be fully compatible with Python {target_version}.
# Update syntax, libraries, and semantics as needed, or downgrade features.
# Maintain equivalent functionality.

{{source_chunk}}

# Updated Python {target_version} code:
""",
            input_variables=["source_chunk"]
        )
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)

    def run(self, source: str) -> tuple[str, list[dict]]:
        chunks = chunk_code(source)
        results = []

        for chunk in chunks:
            if not chunk.strip():
                results.append({"code": "", "exec": None})
                continue
            try:
                updated_code = self.chain.run({"source_chunk": chunk}).strip()
                linted = LintService.validate_and_fix(updated_code, "python")
                exec_result = ExecutionService.execute_code(linted, "python")
                results.append({"code": linted, "exec": exec_result})
            except Exception as e:
                results.append({
                    "code": f"# Failed to update chunk:\n# {e}\n\n{chunk}",
                    "exec": {"success": False, "output": "", "error": str(e)}
                })

        full_code = "\n\n".join(r["code"] for r in results)
        return full_code, [r["exec"] for r in results]


class AIOverviewAgent:
    """Generates a developer-facing report on potential issues and tweaks."""
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set.")
        self.llm = OpenAI(temperature=0, openai_api_key=api_key)

    def generate_report(self, original_code: str, new_code: str) -> str:
        prompt = f"""
You are a senior software engineer. Compare the original code and the modified code.
List:
- Potential issues
- Manual tweaks developers might need
- Compatibility concerns
- Refactoring suggestions

Original code:
{original_code}

Modified code:
{new_code}

Provide your analysis:
"""
        return self.llm(prompt)
