import subprocess
import tempfile
import os

class LintService:
    @staticmethod
    def validate_and_fix(code_str: str, target_lang: str) -> str:
        suffix_map = {'r': '.R', 'java': '.java', 'python': '.py'}
        formatter_cmd = {
            'r': ['Rscript', '-e', f"styler::style_file('{'{file}'}')"],
            'java': ['google-java-format', '-i'],
            'python': ['black']
        }
        suffix = suffix_map.get(target_lang, '.txt')
        cmd = formatter_cmd.get(target_lang)
        tf = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tf.write(code_str.encode('utf-8'))
        tf.close()
        formatted = code_str
        if cmd:
            try:
                full_cmd = cmd + ([tf.name] if target_lang == 'java' else [tf.name])
                subprocess.run(full_cmd, check=True)
                with open(tf.name) as f:
                    formatted = f.read()
            except Exception:
                formatted = code_str
        os.unlink(tf.name)
        return formatted