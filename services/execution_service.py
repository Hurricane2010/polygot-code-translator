import subprocess
import tempfile
import os
import shutil

class ExecutionService:
    @staticmethod
    def execute_code(code_str: str, target_lang: str) -> dict:
        suffix_map = {'r': '.R', 'java': '.java', 'python': '.py'}
        suffix = suffix_map.get(target_lang, '.txt')

        result = {"success": False, "output": "", "error": ""}

        if target_lang == "java":
            # Create temp directory for java file + class file
            with tempfile.TemporaryDirectory() as temp_dir:
                java_filename = "TranslatedProgram.java"
                java_filepath = os.path.join(temp_dir, java_filename)
                with open(java_filepath, "w", encoding="utf-8") as f:
                    f.write(code_str)

                try:
                    # Compile java file
                    compile_proc = subprocess.run(
                        ["javac", java_filepath],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if compile_proc.returncode != 0:
                        result["error"] = compile_proc.stderr.strip() or compile_proc.stdout.strip()
                        result["success"] = False
                        return result

                    # Run java class TranslatedProgram
                    run_proc = subprocess.run(
                        ["java", "-cp", temp_dir, "TranslatedProgram"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    result["success"] = run_proc.returncode == 0
                    result["output"] = run_proc.stdout.strip()
                    result["error"] = run_proc.stderr.strip()

                except subprocess.TimeoutExpired:
                    result["error"] = "Execution timed out."
                    result["success"] = False
                except Exception as e:
                    result["error"] = str(e)
                    result["success"] = False

                return result

        else:
            # For other languages: save to temp file and run as before
            tf = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tf.write(code_str.encode('utf-8'))
            tf.close()

            try:
                if target_lang == "python" or target_lang == "pyspark":
                    proc = subprocess.run(
                        ["python", tf.name],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    result["success"] = proc.returncode == 0
                    result["output"] = proc.stdout.strip()
                    result["error"] = proc.stderr.strip()

                elif target_lang == "r":
                    proc = subprocess.run(
                        ["Rscript", tf.name],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    result["success"] = proc.returncode == 0
                    result["output"] = proc.stdout.strip()
                    result["error"] = proc.stderr.strip()

                else:
                    result["error"] = f"Unsupported language for execution: {target_lang}"

            except subprocess.TimeoutExpired:
                result["error"] = "Execution timed out."
                result["success"] = False
            except Exception as e:
                result["error"] = str(e)
                result["success"] = False
            finally:
                try:
                    os.unlink(tf.name)
                except Exception:
                    pass

            return result
