from pathlib import Path
from pydantic import BaseModel
from ._ocr_google_gemini_multimodal import ImageProcessResult, TextBlock
from moeflow_companion.utils import read_image_dim
import datetime
from moeflow_companion.data import (
    MoeflowProjectMeta,
    MoeflowTextBlock,
    MoeflowProject,
    MoeflowFile,
)


def export_moeflow_project(
    image_files: list[Path],
    process_result: list[ImageProcessResult],
    project_name: str | None,
    dest_dir: Path,
) -> Path:
    if not project_name:
        project_name = image_files[0].name.rsplit(".", 1)[0]
    meta = MoeflowProjectMeta(
        name=project_name,
        intro=f"processed by moeflow companion {datetime.datetime.now().isoformat()}",
    )
    proj = MoeflowProject(
        meta=meta,
        files=_convert_files(image_files, process_result),
    )
    dest = dest_dir / f"{project_name}.zip"
    dest.parent.mkdir(parents=True, exist_ok=True)

    return proj.to_zip(dest)


class FileProcessResult(BaseModel):
    local_path: Path
    image_w: int
    image_h: int
    text_blocks: list[TextBlock]

    @staticmethod
    def from_image_process_result(
        img_path: Path, result: ImageProcessResult
    ) -> "FileProcessResult":
        image_w, image_h = read_image_dim(img_path)
        return FileProcessResult(
            local_path=img_path,
            image_w=image_w,
            image_h=image_h,
            text_blocks=[
                TextBlock(
                    source=block.source,
                    translated=block.translated,
                    left=(block.left) / 1000.0 * image_w,
                    top=(block.top) / 1000.0 * image_h,
                    right=(block.right) / 1000.0 * image_w,
                    bottom=(block.top) / 1000.0 * image_h,
                )
                for block in result.text_blocks
            ]
        )


def _convert_files(
    image_files: list[Path],
    process_result: list[ImageProcessResult],
) -> list[MoeflowFile]:
    files: list[MoeflowFile] = []
    for image_file, result in zip(image_files, process_result):
        image_w, image_h = read_image_dim(image_file)

        files.append(
            MoeflowFile(
                local_path=image_file,
                image_w=image_w,
                image_h=image_h,
                text_blocks=[
                    MoeflowTextBlock(
                        source=block.source,
                        translated=block.translated,
                        # gemini gives coordinates in scaled 1000x1000 image
                        # and moeflow expects normalized [0, 1] coordinates
                        # ref: https://cloud.google.com/gen-ai/docs/gemini/ocr#ocr-parameters
                        center_x=(block.left + block.right) / 2.0 / 1000.0 * image_w,
                        center_y=(block.top + block.bottom) / 2.0 / 1000.0 * image_h,
                        normalized_center_x=(block.left + block.right) / 2.0 / 1000.0,
                        normalized_center_y=(block.top + block.bottom) / 2.0 / 1000.0,
                    )
                    for block in result.text_blocks
                ],
            )
        )
    return files
