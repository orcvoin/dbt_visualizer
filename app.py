from fastapi import FastAPI, UploadFile, File, Form, HTTPException
import shutil
import os
import subprocess
import logging
import uuid
import traceback

app = FastAPI()

# Логирование в stdout
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

OUTPUT_DIR = "/output"
TMP_DIR = "/tmp"
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.post("/process/")
async def process_manifest(
    manifest: UploadFile = File(...),
    out_name: str = Form("raw_graph.xml")
):
    request_id = str(uuid.uuid4())[:8]
    # input_path = os.path.join(TMP_DIR, f"{request_id}_{manifest.filename}")
    input_path = os.path.join(TMP_DIR, f"{manifest.filename}")
    # output_path = os.path.join(OUTPUT_DIR, f"{request_id}_{out_name}")
    output_path = os.path.join(OUTPUT_DIR, f"{out_name}")

    try:
        # Сохраняем входящий файл
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(manifest.file, buffer)
        logging.info(f"[{request_id}] Получен файл: {input_path}")

        # Запуск обработки
        cmd = ["python3", "generate_scheme.py", "--path", input_path, "--name", output_path]
        logging.info(f"[{request_id}] Запуск команды: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        # Лог stdout/stderr
        logging.info(f"[{request_id}] stdout: {result.stdout}")
        logging.info(f"[{request_id}] stderr: {result.stderr}")

        if result.returncode != 0:
            logging.error(f"[{request_id}] Ошибка генерации, code={result.returncode}")
            raise HTTPException(
                status_code=500,
                detail={
                    "request_id": request_id,
                    "error": "Обработка завершилась ошибкой",
                    "stderr": result.stderr,
                }
            )

        # Проверяем, что файл создан
        if not os.path.exists(output_path):
            logging.error(f"[{request_id}] Файл результата не найден: {output_path}")
            raise HTTPException(
                status_code=500,
                detail={
                    "request_id": request_id,
                    "error": "Файл результата не создан",
                }
            )

        logging.info(f"[{request_id}] Успешно обработано. Результат: {output_path}")

        return {
            "request_id": request_id,
            "status": "success",
            "input_file": input_path,
            "output_file": output_path,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    except Exception as e:
        tb = traceback.format_exc()
        logging.error(f"[{request_id}] Exception: {str(e)}\n{tb}")
        raise HTTPException(
            status_code=500,
            detail={
                "request_id": request_id,
                "error": str(e),
                "traceback": tb,
            }
        )

@app.get("/health")
async def health():
    return {"status": "ok"}
