from pathlib import Path
import gradio as gr

from moeflow_companion.llm_clients.gemini_bare import GcpGeminiBare
from moeflow_companion.multimodal_workflow import (
    process_images,
    FileProcessResult,
)
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

with gr.Blocks() as multimodal_api_block:
    gr.Markdown("# multimodal workflow as API")
    file_input = gr.File(
        label="upload file",
        file_count="multiple",
        type="filepath",
    )

    target_language_input = gr.Text(
        label="target language",
        value="",
    )

    model_input = gr.Radio(
        choices=(
            GcpGeminiBare.gemini25_flash_lite,
            GcpGeminiBare.gemini25_flash,
            GcpGeminiBare.gemini25_pro,
        ),
        label="LLM",
        value=GcpGeminiBare.gemini25_flash,
    )
    run_button = gr.Button("run")

    ocr_output = gr.JSON(
        label="process result",
    )

    @run_button.click(
        inputs=[
            file_input,
            model_input,
            target_language_input,
        ],
        outputs=[ocr_output],
    )
    async def multimodal_llm_translate_file_api(
        gradio_temp_files: list[str],
        model: str,
        target_language: str,
    ) -> tuple[dict]:
        processed = await process_images(
            image_files=[Path(f) for f in gradio_temp_files],
            target_lang=target_language,
            model=model,
        )
        res_obj = {
            "files": [
                FileProcessResult.from_image_process_result(
                    img_path=Path(f), result=p
                ).model_dump(mode="json")
                for f, p in zip(gradio_temp_files, processed)
            ]
        }

        return (res_obj,)
