import asyncio
import json
import mimetypes
import os
from pathlib import Path
from typing import Any, List, Literal, Union, Tuple, Optional, AsyncIterator

import aiofiles
import yaml
from telegram import InputMedia, InputMediaDocument
from yaml import YAMLError

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.constants import YAML_CONFIG_PATH
from aimods_bot.src.helpers.constants.media import MEDIA_GROUP_TYPES
from aimods_bot.src.helpers.constants.models import MediaItem
from aimods_bot.src.helpers.loggers import logger

SEM = asyncio.Semaphore(2)

log = logger.getChild("file_utils")


async def get_file(file):
    try:
        iter(file)
    except TypeError:
        return file.get_file()
    else:
        return await get_file(file[-1])


async def get_data_from_json(key: Optional[str] = None, file_path: str = "aimods_bot/misc/data.json") -> Any:
    """
    Extract a field from the specified JSON file.

    Args:
        key: Key to search for in the JSON (None returns entire content).
        file_path: Path to the file (default: aimods_bot/misc/data.json).

    Returns:
        The value associated with the requested key, or entire content if key is None.

    Raises:
        FileNotFoundError: If the file does not exist.
        KeyError: If the key is missing.
        json.JSONDecodeError: If the file is not valid JSON.
        ValueError: If path traversal is detected.
    """
    file_path = _validate_path(file_path)

    try:
        async with aiofiles.open(file_path, encoding="utf-8") as fp:
            content_str = await fp.read()
            content = json.loads(content_str)
    except FileNotFoundError:
        raise
    except json.JSONDecodeError:
        raise

    if key is None:
        return content

    if key not in content:
        raise KeyError(f"Key '{key}' missing in '{file_path}'")

    return content[key]


async def set_data_in_json(
        key: Union[str, List[str]],
        value: Any,
        file_path: str = "aimods_bot/misc/data.json"
) -> bool:
    """
    Set a value in a JSON file.

    Args:
        key: String key or list of keys for nested access.
        value: Value to set.
        file_path: Path to the JSON file.

    Returns:
        True if successful, False otherwise.

    Raises:
        ValueError: If path traversal is detected.
    """
    file_path = _validate_path(file_path)

    try:
        c = await get_data_from_json(None, file_path)
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        log.error(f"Cannot read JSON file: {e}")
        return False

    if isinstance(key, str):
        c[key] = value
    else:  # isinstance(key, list)
        c_ref = c
        for el in key[:-1]:
            if el not in c_ref:
                log.error(f"Key path {key} not found in {file_path}.")
                return False
            c_ref = c_ref[el]

        last_key = key[-1]
        c_ref[last_key] = value

    try:
        async with aiofiles.open(file_path, "w", encoding="utf-8") as fp:
            await fp.write(json.dumps(c, indent=4))
        log.info(f"JSON file updated successfully: {file_path}")
        return True
    except (OSError, IOError) as e:
        log.error(f"Error writing JSON file ({file_path}): {e}")
        return False


def get_file_type(file: Union[str, InputMedia]) -> Literal["document", "photo", "audio", "video", "gif"]:
    """
    Determine the file type based on MIME type or InputMedia type.

    Args:
        file: File path (str) or InputMedia object.

    Returns:
        File type as a string literal.
    """
    if isinstance(file, InputMedia):
        t = file.type.lower() if file.type.lower() in ("photo", "audio", "video", "gif") else "document"
        return t

    mime, _ = mimetypes.guess_type(file)

    if mime is None:
        return "document"

    if mime.startswith("image/"):
        return "gif" if mime == "image/gif" else "photo"
    elif mime.startswith("video/"):
        return "video"
    elif mime.startswith("audio/"):
        return "audio"
    else:
        return "document"


async def normalize_files(
        items: List[MediaItem]
) -> List[Tuple[Literal["document", "photo", "audio", "video", "gif"], InputMedia]]:
    """
    Create InputMedia instances from a list of MediaItems.

    Args:
        items: List of MediaItem objects to normalize.

    Returns:
        List of tuples containing (file_type, InputMedia).
    """
    output = []

    for el in items:
        if isinstance(el.item, InputMedia):
            if el.as_doc:
                output.append(("document", InputMediaDocument(el.item.media)))
            else:
                output.append((el.type, el.item))
        else:  # el.item is a string path
            try:
                validated_path = _validate_path(el.item)
                if not os.path.exists(validated_path):
                    log.error(f"Directory or file not found: {validated_path}")
                    continue

                async with aiofiles.open(validated_path, "rb") as fp:
                    file_content = await fp.read()

                if el.as_doc:
                    output.append((el.type, InputMediaDocument(file_content)))
                else:
                    output.append((el.type, MEDIA_GROUP_TYPES[el.type](file_content)))
            except (OSError, IOError) as e:
                log.error(f"Error reading file {el.item}: {e}")
                continue
            except ValueError as e:
                log.error(f"Invalid path {el.item}: {e}")
                continue

    return output


async def make_temp_file(content: Any, filename: str) -> Optional[Path]:
    """
    Create a temporary file with the given content.

    Args:
        content: Content to write (currently supports list).
        filename: Name of the file to create.

    Returns:
        Path object if successful, None otherwise.
    """
    if isinstance(content, list):
        try:
            output_path = Path(f"./{filename}.txt")
            async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
                for s in content:
                    await f.write(str(s) + "\n")
            return output_path
        except (FileNotFoundError, PermissionError, OSError) as e:
            log.error(f"Error writing file {filename}: {e}")
            return None

    log.warning(f"Unsupported content type for make_temp_file: {type(content)}")
    return None


async def create_latex_file(path: str, chunks: AsyncIterator[str]) -> Path:
    """
    Create a LaTeX file from an async iterator of chunks.

    Args:
        path: Path where to create the file.
        chunks: Async iterator of string chunks.

    Returns:
        Path object of the created file.

    Raises:
        OSError: If file creation fails.
        ValueError: If path traversal is detected.
    """
    validated_path = _validate_path(path)
    p = Path(validated_path)

    async with aiofiles.open(p, "w", encoding="utf-8") as f:
        async for chunk in chunks:
            await f.write(chunk)
    return p


def tex_escape(s: str) -> str:
    """
    Escape special LaTeX characters in a string.

    Args:
        s: String to escape.

    Returns:
        Escaped string safe for LaTeX.
    """
    _LATEX_ESC = {
        "\\": r"\textbackslash{}",
        "{": r"\{", "}": r"\}",
        "#": r"\#", "$": r"\$", "%": r"\%",
        "&": r"\&", "_": r"\_", "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(_LATEX_ESC.get(ch, ch) for ch in s)


async def convert_latex_to_pdf(tex_path: Union[str, Path], timeout: int = 60) -> Path:
    """
    Convert a LaTeX file to PDF using lualatex.

    Args:
        tex_path: Path to the .tex file.
        timeout: Maximum time in seconds for compilation.

    Returns:
        Path object of the generated PDF.

    Raises:
        RuntimeError: If compilation fails or times out.
        ValueError: If path traversal is detected.
    """
    validated_path = _validate_path(str(tex_path))
    tex_path = Path(validated_path).resolve()
    pdf_path = tex_path.with_suffix(".pdf")

    if not _is_safe_filename(tex_path.name):
        raise ValueError(f"Unsafe filename detected: {tex_path.name}")

    cmd = [
        "lualatex",
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
        tex_path.name,
    ]

    async with SEM:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(tex_path.parent),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise RuntimeError(f"LuaLaTeX compilation timeout after {timeout}s")

        if proc.returncode != 0:
            error_msg = f"Compilation failed:\nSTDOUT:\n{stdout.decode()}\nSTDERR:\n{stderr.decode()}"
            raise RuntimeError(error_msg)

    if not pdf_path.exists():
        raise RuntimeError(f"PDF file was not created: {pdf_path}")

    return pdf_path


async def delete_os_file(path: Union[str, Path]) -> bool:
    """
    Delete a file from the filesystem.

    Args:
        path: Path to the file to delete.

    Returns:
        True if successful, False otherwise.
    """
    try:
        validated_path = _validate_path(str(path))
        file_path = Path(validated_path)

        if file_path.exists():
            file_path.unlink()
            log.info(f"File deleted: {file_path}")
            return True
        else:
            log.warning(f"File not found: {file_path}")
            return False
    except PermissionError:
        log.error(f"Permission denied when deleting {path}")
        return False
    except OSError as e:
        log.error(f"Error deleting file {path}: {e}")
        return False
    except ValueError as e:
        log.error(f"Invalid path {path}: {e}")
        return False


async def save_yaml_configuration(context: CustomContext) -> bool:
    """
    Save YAML configuration from context to file.

    Args:
        context: CustomContext containing the configuration.

    Returns:
        True if successful, False otherwise.
    """
    yaml_configuration = context.pydb.configuration

    try:
        validated_path = _validate_path(YAML_CONFIG_PATH)
        async with aiofiles.open(validated_path, "w", encoding="utf-8") as f:
            yaml_content = yaml.safe_dump(
                yaml_configuration.model_dump(),
                sort_keys=False,
                allow_unicode=True
            )
            await f.write(yaml_content)
        log.info(f"YAML configuration updated successfully: {validated_path}")
        return True
    except YAMLError as e:
        log.error(f"Unable to save YAML configuration: {e}")
        return False
    except (OSError, IOError) as e:
        log.error(f"Error writing YAML file: {e}")
        return False
    except ValueError as e:
        log.error(f"Invalid configuration path: {e}")
        return False


def _validate_path(path: str) -> str:
    """
    Validate a file path to prevent path traversal attacks.

    Args:
        path: Path to validate.

    Returns:
        Validated path string.

    Raises:
        ValueError: If path contains suspicious patterns.
    """
    if not path:
        raise ValueError("Path cannot be empty")

    normalized = os.path.normpath(path)

    if ".." in normalized or normalized.startswith("/"):
        # Basic Check - Allow absolute paths only if they're within expected directories
        allowed_prefixes = ("aimods_bot/", "./", ".")
        if not any(normalized.startswith(prefix) for prefix in allowed_prefixes):
            raise ValueError(f"Potential path traversal detected: {path}")

    return normalized


def _is_safe_filename(filename: str) -> bool:
    """
    Check if a filename is safe to use in shell commands.

    Args:
        filename: Filename to check.

    Returns:
        True if safe, False otherwise.
    """
    import re
    return bool(re.match(r'^[\w\-. ]+$', filename))
