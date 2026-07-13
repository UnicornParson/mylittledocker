# FsExt-MCP-Server (Python)
## Overview
A full-featured secure MCP server for local file system operations, with built-in image processing, OCR and media tools. Fully compliant with the official Model Context Protocol specification, offering standardized request/response schemas, large-file streaming I/O, multi-transport remote deployment, and comprehensive text search & replace functionality for LLM agent integration.

### Core Features
- **Full File & Directory Management**: Support file creation, deletion, copy, move, metadata query, existence check; full directory tree recursion copy and move with overwrite safety controls.
- **Streaming File Read/Write**: Integrate full text reading, segmented line-based text reading, chunked binary reading, text/binary overwriting and appending writing, optimized to avoid loading entire large files into memory.
- **Powerful Search & Replace**: Support directory-wide recursive file content search, single/multi-file contextual matching with configurable pre/post matching lines, regular expression matching, case-insensitive search, and in-place text replacement with match count statistics.
- **Image Processing Tools**: Built-in high-performance image toolkit powered by Pillow, including resize (aspect ratio lock + canvas padding support), crop, and arbitrary-angle clockwise rotation.
- **Native Tesseract OCR Recognition**: Reliable text extraction from images dependent on local Tesseract binary installation. No WASM fallback; an empty binary path argument will not trigger alternative JS-based OCR engines. Multi-language tessdata resource support with configurable binary and data paths.
- **Strict Input Validation & Unified Response Format**: Every tool enables strict `additionalProperties: false` schema validation to block unexpected input fields. All operations share a universal success/error wrapping structure for consistent client parsing.
- **Multi-Transport Support**: Compatible with official standard MCP transports: `stdio` (local desktop client integration), `sse` (legacy lightweight remote stream), and Streamable HTTP (modern bidirectional remote streaming transport).
- **Workspace Security Isolation**: Provide `--lock-root` directory restriction capability. All file/directory operations are strictly confined to the specified root workspace to prevent unauthorized cross-directory path escape attacks.

## Quick Start: Run directly with uvx (No pre-installation required)
`uvx` automatically pulls the published PyPI package and launches an isolated runtime environment, eliminating manual dependency installation or virtual environment setup.

### 1. Basic uvx startup commands
#### Short command (recommended)
```bash
# Default stdio mode, unrestricted full filesystem access
uvx fsext-mcp-server

# Lock all operations to a dedicated workspace (production security recommended)
uvx fsext-mcp-server --lock-root /your/workspace
```

#### Full complete command
```bash
# Stdio mode with workspace isolation
uvx fsext-mcp-server --transport stdio --lock-root /your/workspace

# Remote SSE streaming service
uvx fsext-mcp-server --transport sse --host 0.0.0.0 --port 8000 --lock-root /your/workspace

# Modern Streamable HTTP remote service
uvx fsext-mcp-server --transport http --host 0.0.0.0 --port 8000 --lock-root /your/workspace
```

### 2. Integrate FsExt tools with LLM frameworks
No pre-deployment on host machines required; `uvx` dynamically instantiates the server when an MCP client establishes a connection.

#### Client config example (Claude Desktop / Cursor MCP json)
```json
{
  "mcpServers": {
    "fsext": {
      "command": "uvx",
      "args": [
        "fsext-mcp-server",
        "--lock-root",
        "/your/workspace"
      ],
      "env": {"PYTHONUTF8": "1"}
    }
  }
}
```

#### LangChain / LangGraph core integration snippet
Session lifecycle limitations exist within official `langchain-mcp-adapters`; complete stable long-connection logic requires extra adapter customization. Below is the standard minimal connection template:
```python
# Core config: Connect to FsExt MCP via uvx stdio transport
server_config = {
    "fsext": {
        "transport": "stdio",
        "command": "uvx",
        "args": ["fsext-mcp-server", "--lock-root", r"/your/workspace"],
        "env": {"PYTHONUTF8": "1"}
    }
}

# Load all exposed filesystem MCP tools
client = MultiServerMCPClient(server_config)
async with client.session("fsext") as session:
    mcp_tools = await load_mcp_tools(session)

# Bind loaded MCP tools to LLM instance for agent workflows
llm = ChatOpenAI(base_url="your-local-llm-api").bind_tools(mcp_tools)
```

## Traditional installation & launch via pip
### Install published PyPI package
```bash
pip install fsext-mcp-server
```

### Launch commands after pip installation
```bash
# Default stdio local mode
fsext-mcp-server-py
fsext-mcp-server

# Short alias
fsext-py
fsext

# Secure workspace locked mode
fsext --lock-root /your/workspace

# Remote SSE streaming server
fsext --transport sse --port 8000
```

### Local source repository development setup
It is recommended to use `uv` for fast, deterministic environment deployment:
```bash
# Clone official source repository
git clone https://github.com/kurtzhi/fsext-mcp-server-python
cd fsext-mcp-server-python

# Install full runtime + dev dependencies
uv sync
```

### Core Runtime Dependencies Description
- **chardet**: Automatic text file encoding detection
- **Pillow**: Core image processing backend for resize, crop, rotate pipelines
- **python-magic**: Accurate cross-platform file MIME type identification
- **fastmcp**: Official Python MCP server framework
- **uvicorn / starlette**: HTTP/SSE transport server runtime
- **pydantic**: Strict schema validation for all tool input parameters
- **tesseract**: Native bindings for local Tesseract OCR binary

## Startup Usage
The server supports three official MCP transport modes and flexible workspace root isolation configuration via CLI flags.

### Startup Parameter Reference Table
| Parameter | Default Value | Description |
| --- | --- | --- |
| `--transport` | stdio | MCP transport type: `stdio` / `sse` / `http` |
| `--host` | 127.0.0.1 | Network bind address (ignored under stdio transport) |
| `--port` | 8000 | Service bind port (ignored under stdio transport) |
| `--lock-root` | None | Restrict all filesystem operations to this root directory; full unrestricted access if omitted |

### Common Production Startup Commands
#### 1. Default Local Stdio Mode (for Claude Desktop / Cursor AI Clients)
```bash
uv run -m fsext
```

#### 2. Stdio Mode with Mandatory Workspace Lock (Secure Local Agent Use)
```bash
uv run -m fsext --lock-root /your/workspace/path
```

#### 3. Remote SSE Transport Mode
```bash
uv run -m fsext --transport sse --host 0.0.0.0 --port 8000
```
##### Access Endpoints
1. SSE long-lived stream subscription channel (server event push):
   `http://<host>:<port>/sse`
2. Client JSON-RPC request submission channel:
   `http://<host>:<port>/messages`

##### MCP Inspector Connection Config
- Transport type: SSE
- Connection address input: `http://127.0.0.1:8000/sse`

#### 4. Standard Streamable HTTP Remote Transport (Modern Bidirectional)
```bash
uv run -m fsext --transport http --host 0.0.0.0 --port 8000
```
##### Unified Bidirectional Access Endpoint
Single shared entry point for both client requests and server streaming:
`http://<host>:<port>/mcp`

##### MCP Inspector Connection Config
- Transport type: Streamable HTTP
- Connection address input: `http://127.0.0.1:8000/mcp`

#### 5. SSE vs Streamable HTTP Transport Feature Comparison
| Feature | SSE Dual-Endpoint Transport | Streamable HTTP Single-Endpoint Transport |
| --- | --- | --- |
| Endpoint Architecture | Two separate endpoints: GET stream subscription + POST message sender | Single unified URL handles all bidirectional traffic |
| Communication Pattern | Unidirectional server-to-client event push only | Full bidirectional request/stream hybrid capability |
| Connection Reliability | Frequent session loss, complex cross-endpoint state management | Automatic session recovery, optimized for high concurrent remote connections |
| Official Specification Status | Legacy compatible implementation, not recommended for new deployments | Current official MCP standard for remote network integrations |

## Unified Global Response Specification
All MCP tools share an identical top-level wrapping JSON structure for both successful execution and runtime failure states. Every tool’s business payload is nested within the `info` sub-object under the root `res` field.

### Core Structure Definition
```json
{
  "res": {
    "success": boolean,
    "info": object
  }
}
```
- `success`: Global operation status flag
    - `true`: Tool logic executed without exceptions; `info` contains tool-specific return data
    - `false`: Operation failed (workspace escape block, missing file, IO error, invalid input schema, permission denied, etc.)
- Dual behavior of `info` field:
    1. Success mode (`success: true`): Custom structured business payload unique to each tool
    2. Failure mode (`success: false`): Fixed standardized error object with machine-readable error code and human-readable explanation
       ```json
       "info": {
         "code": "ERROR_CODE_IDENTIFIER",
         "message": "Detailed human-readable failure description"
       }
       ```

### Full Example Responses
#### 1. Successful Response Sample (fs_list_directory)
```json
{
  "res": {
    "success": true,
    "info": {
      "paths": [
        "/tmp/tests/test_util.py",
        "/tmp/tests/__init__.py",
        "/tmp/tests/img/cochem_castle.jpg"
      ]
    }
  }
}
```

#### 2. Failure Response Sample (Workspace Path Escape Restriction)
```json
{
  "res": {
    "success": false,
    "info": {
      "code": "WORKSPACE_ESCAPE_FORBIDDEN",
      "message": "Access restricted: Path `/tmp/test2` is outside allowed workspace `/tmp/tests`"
    }
  }
}
```

All tools enforce workspace root isolation and fully follow the standardized input/output schema definitions listed below.

# Complete MCP Tools Reference
All tool input schemas enable `additionalProperties: false` strict validation to reject unrecognized parameters and prevent malicious path injection vectors.

## 1. Directory Operation Tools
### fs_list_directory
**Description**: Scan target directory recursively or shallowly, return filtered absolute filesystem path list with file-type and extension filtering controls.
**Parameters**:
- `source_dir` (string, required): Root directory path for scanning
- `recursive` (boolean, required): Enable full recursive traversal of all subdirectories
- `only_files` (boolean, required): Filter output to return only regular files, exclude directories
- `file_extension` (string, optional, default=""): Filter results to files matching the specified suffix extension
  **Success Response Payload**:
```json
{
  "res": {
    "success": true,
    "info": {
      "paths": ["/absolute/path/file1.txt", "/absolute/path/file2.py"]
    }
  }
}
```

### fs_copy_directory
**Description**: Recursively copy an entire directory tree, with configurable overwrite behavior for pre-existing target directories.
**Parameters**:
- `source_dir` (string, required): Source directory tree path
- `copy_dest_dir` (string, required): Target output directory path
- `overwrite` (boolean, optional, default=false): Clear and overwrite existing destination directory contents
  **Success Response Payload**:
```json
{
  "res": {
    "success": true,
    "info": {}
  }
}
```

### fs_move_directory
**Description**: Atomically move an entire directory tree to a new target path. Fails immediately if destination exists unless overwrite is explicitly enabled to avoid accidental data loss.
**Parameters**:
- `source_dir` (string, required): Source directory path
- `dest_dir` (string, required): Target directory path
- `overwrite` (boolean, optional, default=false): Allow overwriting conflicting destination directories
  **Success Response Payload**: Empty `info` object wrapper with success flag.

## 2. Single File Basic Operation Tools
### fs_create_file
**Description**: Create a new text file, automatically generate missing parent directories, support configurable text encoding and initial file content.
**Parameters**:
- `file_path` (string, required): Target absolute file path
- `content` (string, optional, default=""): Initial text content written to the new file
- `charset` (string, optional, default="utf-8"): Text encoding enum value (full charset list below)
  Supported Charset Enum Values:
  `utf-8`, `utf-16`, `latin-1`, `iso-8859-1`, `cp1252`, `Windows-1252`, `gbk`, `gb2312`, `shift_jis`, `euc_jp`, `euc_kr`
  **Success Response Payload**: Empty `info` object wrapper with success flag.

### fs_delete_file
**Description**: Permanently delete a single regular file only; rejects directory path inputs to block mass recursive deletion risks.
**Parameters**:
- `file_path` (string, required): Target regular file absolute path
  **Success Response Payload**: Empty `info` object wrapper with success flag.

### fs_copy_file
**Description**: Copy a single file while retaining original filesystem metadata, with configurable overwrite for conflicting target files.
**Parameters**:
- `source_file_path` (string, required): Source file absolute path
- `dest_file_path` (string, required): Target output file absolute path
- `overwrite` (boolean, optional, default=false): Overwrite pre-existing destination file
  **Success Response Payload**: Empty `info` object wrapper with success flag.

### fs_move_file
**Description**: Atomically move a single file to a new absolute path, with configurable overwrite behavior for conflicting destination files.
**Parameters**:
- `source_file_path` (string, required): Source file absolute path
- `dest_file_path` (string, required): Target file absolute path
- `overwrite` (boolean, optional, default=false): Allow overwriting conflicting destination files
  **Success Response Payload**: Empty `info` object wrapper with success flag.

### fs_get_file_info
**Description**: Retrieve complete metadata for files or directories, with optional SHA-256 cryptographic digest calculation for integrity verification.
**Parameters**:
- `file_path` (string, required): Target filesystem entry absolute path
- `calc_digest` (boolean, optional, default=false): Compute SHA-256 hash of file contents
  **Success Response Payload**:
```json
{
  "res": {
    "success": true,
    "info": {
      "absolute_path": "C:\\Users\\zhigu\\Documents\\My Games\\fsext-mcp-server\\pyproject.toml",
      "is_readable": true,
      "is_writable": true,
      "size": 1672,
      "is_regular_file": true,
      "is_directory": false,
      "is_symbolic_link": false,
      "creation_millis": 1782288135574.7114,
      "last_modified_millis": 1782279393020.1187,
      "last_access_millis": 1782644004556.3462,
      "sha256_digest": "59614cf5f8ecff38de37637f1d5b6f607d885bd277815786f5ce4bb2ee5b73a6"
    }
  }
}
```

### fs_is_file_exists
**Description**: Lightweight existence check for any filesystem entry (file or directory) without loading full metadata.
**Parameters**:
- `file_path` (string, required): Target absolute path to verify
  **Success Response Payload**:
```json
{
  "res": {
    "success": true,
    "info": {
      "exists": true
    }
  }
}
```

## 3. File Read & Write Tools
### fs_read_full_text
**Description**: Read the complete text content of a target file with user-specified text encoding.
**Parameters**:
- `file_path` (string, required): Target text file absolute path
- `charset` (string, optional, default="utf-8"): Text encoding enum value
  **Success Response Payload**:
```json
{
  "res": {
    "success": true,
    "info": {
      "content": "complete-text-file-content-here"
    }
  }
}
```

### fs_read_text_range
**Description**: Stream segmented text reading optimized for large files; skip leading lines and limit total read lines to avoid memory overload.
**Parameters**:
- `file_path` (string, required): Target text file absolute path
- `lines_to_skip` (integer, required, minimum=0): Number of initial lines to skip during reading
- `max_lines_to_read` (integer, required, minimum=0): Maximum total lines to extract from file
- `line_separator` (string, optional, default="\n"): Line break delimiter character
- `charset` (string, optional, default="utf-8"): Text encoding enum value
  **Success Response Payload**:
```json
{
  "res": {
    "success": true,
    "info": {
      "lines_count": 5,
      "content": "segmented-text-content-block"
    }
  }
}
```

### fs_read_binary_chunk
**Description**: Chunked streaming read for binary files; returns Base64 encoded byte payloads for safe network JSON-RPC transmission with end-of-stream marker detection.
**Parameters**:
- `file_path` (string, required): Target binary file absolute path
- `bytes_to_skip` (integer, required, minimum=0): Number of leading bytes to skip before reading chunk
- `max_bytes_to_read` (integer, required, minimum=0): Maximum byte length to read in single chunk
  **Success Response Payload**:
```json
{
  "res": {
    "success": true,
    "info": {
      "data_base64": "base64-encoded-binary-byte-data",
      "raw_bytes_length": 5,
      "end_of_stream": true
    }
  }
}
```

### fs_write_text
**Description**: Write UTF or multi-encoded text content to target file, supporting full overwrite or append-only write modes.
**Parameters**:
- `file_path` (string, required): Target output file absolute path
- `text` (string, required, minLength=1): Raw text content to persist
- `append` (boolean, optional, default=false): Append mode flag (false = overwrite entire file)
- `charset` (string, optional, default="utf-8"): Text encoding enum value
  **Success Response Payload**: Empty `info` object wrapper with success flag.

### fs_write_binary
**Description**: Decode Base64 encoded binary payload and write raw bytes to target file, supporting append mode for multi-chunk binary uploads.
**Parameters**:
- `file_path` (string, required): Target output file absolute path
- `base64_data` (string, required, minLength=1): Base64 encoded raw binary byte payload
- `append` (boolean, optional, default=false): Append binary data to end of file (false = overwrite)
  **Success Response Payload**: Empty `info` object wrapper with success flag.

## 4. Content Search & In-Place Replace Tools
### fs_search_files_by_content
**Description**: Recursively scan directory tree and return absolute paths of all files containing matching target text pattern; support regex matching, case insensitivity, and file extension filtering.
**Parameters**:
- `dir_path` (string, required): Root directory for recursive content scan
- `recursive` (boolean, required): Enable full subdirectory recursion
- `search_term` (string, required): Plain text keyword or regular expression pattern
- `is_regex` (boolean, optional, default=false): Treat search_term as regex pattern when true
- `ignore_case` (boolean, optional, default=true): Case-insensitive pattern matching
- `file_extension` (string, optional, default=""): Filter scanned files by extension suffix
- `charset` (string, optional, default="utf-8"): Text encoding enum value for file parsing

### fs_search_in_files_by_content
**Description**: Multi-directory bulk content matching, returns structured match results with configurable preceding and trailing context lines around matched content, plus global result count limiting.
**Parameters**:
- `dir_path` (string, required): Root scan directory absolute path
- `recursive` (boolean, required): Enable full recursive subdirectory traversal
- `search_term` (string, required): Search keyword or regex pattern
- `limit` (integer, required): Hard maximum limit on total returned matching entries
- `is_regex` (boolean, optional, default=false): Enable regular expression matching
- `ignore_case` (boolean, optional, default=true): Disable case-sensitive matching
- `lines_before` (integer, optional, default=0): Number of context lines preceding each matched line
- `lines_after` (integer, optional, default=0): Number of context lines following each matched line
- `file_extension` (string, optional, default=""): Filter scanned files by extension suffix
- `charset` (string, optional, default="utf-8"): Text encoding enum value for file parsing
  **Success Response Payload**:
```json
{
  "res": {
    "success": true,
    "info": {
      "results": [
        {
          "file_path": "/absolute/path/source.py",
          "start_line": 1,
          "end_line": 1,
          "text": "full-matched-line-content-with-context"
        }
      ]
    }
  }
}
```

### fs_search_in_file_by_content
**Description**: Precision single-file content search, returns structured matching segments with configurable pre/post context lines for code and document inspection workflows.
**Parameters**:
- `file_path` (string, required): Target single file absolute path
- `search_term` (string, required): Search keyword or regex pattern
- `is_regex` (boolean, optional, default=false): Enable regular expression matching logic
- `ignore_case` (boolean, optional, default=true): Case-insensitive matching toggle
- `lines_before` (integer, optional, default=0): Preceding context lines for each match
- `lines_after` (integer, optional, default=0): Subsequent context lines for each match
- `charset` (string, optional, default="utf-8"): Text encoding enum value for file parsing
  **Success Response Payload**: Structured array of line match objects identical to multi-file search output format.

### fs_file_replace
**Description**: Perform global in-place text replacement within a single target file; return total count of matched and replaced text segments after write.
**Parameters**:
- `file_path` (string, required): Target editable file absolute path
- `search_term` (string, required): Text substring to locate and replace
- `replacement` (string, required): New replacement text payload
- `line_separator` (string, optional, default="\n"): Line break delimiter for file parsing
  **Success Response Payload**:
```json
{
  "res": {
    "success": true,
    "info": {
      "count": 1
    }
  }
}
```

## 5. Image Processing Tools
### fs_image_resize
**Description**: Resize source image to specified width/height dimensions, with native support for aspect ratio preservation and canvas padding to fill exact target resolution dimensions.
**Parameters**:
- `source_path` (string, required): Source input image absolute path
- `dest_path` (string, required): Resized output image absolute path
- `width` (integer, required, exclusiveMinimum=0): Target pixel width dimension
- `height` (integer, required, exclusiveMinimum=0): Target pixel height dimension
- `keep_aspect_ratio` (boolean, optional, default=true): Lock original image aspect ratio during scaling
- `pad_to_target` (boolean, optional, default=true): Add transparent padding to fill exact target width/height when aspect ratio is locked
  **Success Response Payload**: Empty `info` object wrapper with success flag.

### fs_image_crop
**Description**: Extract a rectangular pixel region from source image and export as a standalone output image file.
**Parameters**:
- `source_path` (string, required): Source input image absolute path
- `dest_path` (string, required): Cropped output image absolute path
- `x` (integer, required, minimum=0): Left pixel coordinate of crop region origin
- `y` (integer, required, minimum=0): Top pixel coordinate of crop region origin
- `width` (integer, required, exclusiveMinimum=0): Pixel width of cropped rectangular region
- `height` (integer, required, exclusiveMinimum=0): Pixel height of cropped rectangular region
  **Success Response Payload**: Empty `info` object wrapper with success flag.

### fs_image_rotate
**Description**: Rotate source image clockwise by arbitrary floating-point degree values; automatically expand output canvas dimensions to retain full image content without clipping edges.
**Parameters**:
- `source_path` (string, required): Source input image absolute path
- `dest_path` (string, required): Rotated output image absolute path
- `degrees` (number, required): Clockwise rotation angle in degrees
  **Success Response Payload**: Empty `info` object wrapper with success flag.

## 6. OCR Text Extraction Tool
### fs_ocr_extract_text
**Description**: Extract human-readable text from raster image files via local Tesseract OCR binary installation. No WASM JavaScript fallback implementation exists; an empty `tesseract_bin_path` argument will not initialize alternative web-based OCR engines.
**Parameters**:
- `image_path` (string, required): Input image absolute path for text recognition
- `tesseract_bin_path` (string, optional, default=""): Absolute path to local Tesseract executable binary; empty value uses system PATH lookup only
- `tessdata_path` (string, optional, default=""): Absolute directory path containing Tesseract language training data files
- `lang` (string, optional, default="eng"): Language code prefix matching available tessdata training files
  **Success Response Payload**:
```json
{
  "res": {
    "success": true,
    "info": {
      "content": "full-ocr-extracted-text-from-input-image"
    }
  }
}
```

## Project Build & Development Scripts
All standardized npm-equivalent uv development scripts for source repository contributors:
```bash
# Clean compiled build artifacts and temporary output directories
uv run -m scripts.clean

# Compile source code and type validation
uv run -m scripts.build

# Watch source files for incremental development rebuilds
uv run -m scripts.dev

# Full rebuild pipeline: clean artifacts + full source compilation
uv run -m scripts.rebuild

# Launch remote SSE transport server instance
uv run -m scripts.server

# FastMCP interactive development mode
uv run -m scripts.fastmcp

# MCP Inspector debug connection launcher
uv run -m scripts.inspect

# Execute full test suite with compiled test artifacts
uv run -m scripts.test
```

## Core Runtime Dependencies
- **fastmcp**: Official Python MCP server runtime framework
- **Pillow**: Cross-platform image processing backend for resize, crop, rotate pipelines
- **tesseract**: Native Python bindings for local Tesseract OCR binary
- **chardet**: Multi-encoding text file detection
- **iconv-lite equivalent backends**: Cross-platform text encoding conversion utilities
- **cors**: CORS middleware for HTTP/SSE remote transport servers
- **minimist equivalent CLI parser**: Command line argument parsing for startup flags
- **pydantic**: Strict typed schema validation for all MCP tool input schemas
- **uvicorn / starlette**: ASGI HTTP server runtime for remote transport deployments

## License
This project is open-sourced under the **Apache License 2.0**. See the `LICENSE` file located in the project root directory for complete legal license terms and conditions.

## Third-Party Component Licenses
This project integrates multiple open-source dependency libraries including chardet, Pillow, python-magic, and Tesseract bindings. All third-party libraries retain their respective original open-source license agreements and copyright statements.

Important Note: No FFmpeg binary artifacts are bundled within this distribution. End users must comply with FFmpeg’s official licensing terms separately if media processing extensions are enabled externally.

## Repository & Issue Tracking
- GitHub Source Repository: https://github.com/kurtzhi/fsext-mcp-server-python
- Bug Reports & Feature Requests: https://github.com/kurtzhi/fsext-mcp-server-python/issues
