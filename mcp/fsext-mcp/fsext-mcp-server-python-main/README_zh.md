# FsExt-MCP-Server (Python) 
## 概述
一套功能完整、安全可控的 Model Context Protocol（MCP）本地文件系统服务，内置图像处理、光学文字识别（OCR）多媒体工具，完全遵循官方 MCP 标准规范。支持标准化请求/响应校验、大文件流式读写、多传输协议远程部署，专为 LLM AI 智能体集成打造。

### 核心特性
- **完整文件与目录管理**：支持文件创建、删除、复制、移动、元数据查询、存在性校验；支持完整目录树递归复制与移动，内置覆写安全控制。
- **流式文件读写**：支持全文读取、按行分段读取、二进制分块读取，同时提供文本/二进制覆写与追加写入逻辑，全程避免大文件一次性载入内存。
- **强大检索与替换**：支持目录全局递归内容检索、单/多文件带上下文匹配、正则匹配、大小写忽略，支持文件内原地文本替换并返回替换统计数量。
- **图像处理工具集**：基于 Pillow 高性能图像引擎，提供图片缩放（固定宽高比+画布填充）、矩形裁切、任意角度顺时针旋转能力。
- **原生 Tesseract OCR 文字识别**：依赖本地 Tesseract 程序完成图片文字提取，无 WASM JS 降级方案；二进制路径留空时不会切换网页版 OCR。支持自定义程序路径、语言数据包路径与多语种识别。
- **严格入参校验 + 统一返回格式**：全部工具开启 `additionalProperties: false` 严格参数校验，拦截非法入参；所有操作共用一套标准化成功/错误返回结构，客户端解析逻辑统一。
- **多标准 MCP 传输协议**：原生支持三种官方传输方式：`stdio`（本地桌面客户端）、`SSE`（传统远程流式）、Streamable HTTP（现代双向长连接远程协议）。
- **工作目录安全隔离**：提供 `--lock-root` 根目录锁定参数，所有文件操作严格限制在指定工作区内，杜绝跨目录路径逃逸风险。

## 快速启动：uvx 免安装运行
`uvx` 自动拉取 PyPI 正式包并创建隔离运行环境，无需手动配置虚拟环境、安装依赖。

### 1. uvx 基础启动命令
#### 最简推荐命令
```bash
# 默认 stdio 模式，无目录限制，完整访问本地文件
uvx fsext-mcp-server

# 锁定操作目录（生产环境安全推荐）
uvx fsext-mcp-server --lock-root /你的工作目录
```

#### 完整参数启动示例
```bash
# Stdio 本地模式 + 工作目录锁定
uvx fsext-mcp-server --transport stdio --lock-root /你的工作目录

# 远程 SSE 流式服务
uvx fsext-mcp-server --transport sse --host 0.0.0.0 --port 8000 --lock-root /你的工作目录

# 现代 Streamable HTTP 双向远程服务
uvx fsext-mcp-server --transport http --host 0.0.0.0 --port 8000 --lock-root /你的工作目录
```

### 2. LLM 框架接入工具
无需提前部署到宿主机，MCP 客户端建立连接时 uvx 会自动拉起服务。

#### 客户端配置示例（Claude Desktop / Cursor MCP 配置 json）
```json
{
  "mcpServers": {
    "fsext": {
      "command": "uvx",
      "args": [
        "fsext-mcp-server",
        "--lock-root",
        "/你的工作目录"
      ],
      "env": {"PYTHONUTF8": "1"}
    }
  }
}
```

#### LangChain / LangGraph 核心接入代码
官方 `langchain-mcp-adapters` 存在会话生命周期兼容问题，完整稳定长连接逻辑需要额外适配，以下为标准基础调用模板：
```python
# 核心配置：通过 uvx stdio 连接 FsExt MCP 服务
server_config = {
    "fsext": {
        "transport": "stdio",
        "command": "uvx",
        "args": ["fsext-mcp-server", "--lock-root", r"/你的工作目录"],
        "env": {"PYTHONUTF8": "1"}
    }
}

# 加载全部文件操作 MCP 工具
client = MultiServerMCPClient(server_config)
async with client.session("fsext") as session:
    mcp_tools = await load_mcp_tools(session)

# 工具绑定 LLM，构建对话工作流
llm = ChatOpenAI(base_url="本地大模型接口地址").bind_tools(mcp_tools)
```

## 传统 pip 安装与启动
### 安装 PyPI 发布包
```bash
pip install fsext-mcp-server
```

### pip 安装后启动命令
```bash
# 默认本地 stdio 模式
fsext-mcp-server
# 简写别名
fsext

# 锁定工作目录启动
fsext --lock-root /你的工作目录

# 远程 SSE 服务
fsext --transport sse --port 8000
```

### 源码仓库本地开发部署
推荐使用 uv 实现极速、确定化环境配置：
```bash
# 克隆官方源码仓库
git clone https://github.com/kurtzhi/fsext-mcp-server-python
cd fsext-mcp-server-python

# 安装运行与开发全套依赖
uv sync
```

### 核心运行依赖说明
- **chardet**：自动检测文件文本编码
- **Pillow**：图像处理核心库，提供缩放、裁切、旋转能力
- **python-magic**：精准识别文件 MIME 类型
- **fastmcp**：官方 Python MCP 服务运行框架
- **uvicorn / starlette**：HTTP/SSE 传输服务运行时
- **pydantic**：全部工具入参强类型校验
- **tesseract**：本地 Tesseract OCR 程序绑定

## 启动参数说明
服务支持三种 MCP 传输模式，搭配灵活的工作目录锁定配置。

### 启动参数对照表
| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--transport` | stdio | MCP 传输类型：`stdio`/`sse`/`http` |
| `--host` | 127.0.0.1 | 服务绑定地址（stdio 模式下失效） |
| `--port` | 8000 | 服务绑定端口（stdio 模式下失效） |
| `--lock-root` | 无 | 将全部文件操作限制在该根目录；不填则无访问限制 |

### 常用启动命令
#### 1. 默认本地 Stdio 模式（适配 Claude Desktop / Cursor）
```bash
uv run -m fsext
```

#### 2. Stdio 模式 + 工作目录锁定（安全本地使用）
```bash
uv run -m fsext --lock-root /你的工作目录路径
```

#### 3. 远程 SSE 传输模式
```bash
uv run -m fsext --transport sse --host 0.0.0.0 --port 8000
```
##### 访问端点
1. SSE 长连接订阅通道（接收服务端推送消息）
   `http://<host>:<port>/sse`
2. 客户端请求发送通道（调用工具、发送初始化请求）
   `http://<host>:<port>/messages`

##### MCP Inspector 客户端配置
- 传输类型：SSE
- 连接地址填写：`http://127.0.0.1:8000/sse`

#### 4. 官方标准 Streamable HTTP 双向远程传输
```bash
uv run -m fsext --transport http --host 0.0.0.0 --port 8000
```
##### 统一访问端点
单入口兼顾双向收发，无分离 /sse、/messages 路由：
`http://<host>:<port>/mcp`

##### MCP Inspector 客户端配置
- 传输类型：Streamable HTTP
- 连接地址填写：`http://127.0.0.1:8000/mcp`

#### 5. SSE 与 Streamable HTTP 传输核心差异对比
| 特性 | SSE（双端点传输） | Streamable HTTP（现代标准） |
| --- | --- | --- |
| 端点架构 | 双接口：POST 发请求 + GET 接收服务流 | 单一接口：同一 URL 同时处理 POST 请求与 GET 长流 |
| 通信方式 | 单向：仅服务端推送，客户端无法复用同一条流回传数据 | 可选双向：支持普通 HTTP 响应，也可同连接开启 SSE 实时推送 |
| 连接稳定性 | 两端口状态同步复杂，极易断连丢失会话 | 自动会话恢复，高并发场景稳定性更强，维护成本更低 |
| 标准现状 | 传统兼容方案，新项目不推荐 | 分布式远程客户端对接官方最新标准 |

## 全局统一返回规范
所有 MCP 工具无论执行成功或异常，共用一套顶层包装结构，工具业务数据统一存放于 `res` 下的 `info` 字段。

### 结构定义
```json
{
  "res": {
    "success": boolean,
    "info": object
  }
}
```
- `success`：全局执行标识
    - `true`：工具正常执行，`info` 携带各工具专属业务返回数据
    - `false`：执行失败（工作目录越权、文件不存在、IO 错误、参数非法等）
- `info` 双模式：
    1. 成功模式（`success: true`）：当前工具自定义业务对象
    2. 失败模式（`success: false`）：固定错误结构，包含错误码与可读描述
       ```json
       "info": {
         "code": "错误编码",
         "message": "详细错误描述"
       }
       ```

### 完整返回示例
#### 1. 成功示例（fs_list_directory 目录扫描）
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

#### 2. 失败示例（访问超出锁定工作目录）
```json
{
  "res": {
    "success": false,
    "info": {
      "code": "WORKSPACE_ESCAPE_FORBIDDEN",
      "message": "访问受限：路径 `/tmp/test2` 不在允许的工作目录 `/tmp/tests` 范围内"
    }
  }
}
```

全部工具均支持工作目录路径拦截，并严格遵循标准化入参、返回规范。

# 完整 MCP 工具参考文档
## 1. 目录操作工具
### fs_list_directory
**功能说明**：扫描指定目录，递归/仅文件/后缀过滤，返回绝对路径列表。
**入参**：
- `source_dir` (字符串，必填)：待扫描目录路径
- `recursive` (布尔，必填)：是否递归扫描子目录
- `only_files` (布尔，必填)：是否仅返回文件，排除文件夹
- `file_extension` (字符串，选填，默认空)：按后缀筛选文件
  **成功返回**：
```json
{
  "res": {
    "success": true,
    "info": {
      "paths": ["/绝对路径/file1.txt", "/绝对路径/file2.py"]
    }
  }
}
```

### fs_copy_directory
**功能说明**：递归完整复制整个目录树，支持覆写已存在目标文件夹。
**入参**：
- `source_dir` (字符串，必填)：源目录路径
- `copy_dest_dir` (字符串，必填)：目标目录路径
- `overwrite` (布尔，选填，默认false)：是否清空并覆写目标目录
  **成功返回**：
```json
{
  "res": {
    "success": true,
    "info": {}
  }
}
```

### fs_move_directory
**功能说明**：移动完整目录树，目标路径存在时直接报错，防止误覆盖。
**入参**：
- `source_dir` (字符串，必填)：源目录路径
- `dest_dir` (字符串，必填)：目标目录路径
- `overwrite` (布尔，选填，默认false)：允许覆盖冲突目录
  **成功返回**：空 info 对象，仅标记成功

## 2. 文件基础操作工具
### fs_create_file
**功能说明**：创建文件，自动补全不存在的父目录，支持初始化内容与多编码。
**入参**：
- `file_path` (字符串，必填)：目标文件路径
- `content` (字符串，选填，默认空)：初始文本内容
- `charset` (字符串，选填，默认utf-8)：文本编码枚举，可选值：
  `utf-8`, `utf-16`, `latin-1`, `iso-8859-1`, `cp1252`, `Windows-1252`, `gbk`, `gb2312`, `shift_jis`, `euc_jp`, `euc_kr`
  **成功返回**：空 info 对象

### fs_delete_file
**功能说明**：仅删除单个普通文件，禁止传入目录路径，防止批量误删。
**入参**：
- `file_path` (字符串，必填)：待删除文件路径
  **成功返回**：空 info 对象

### fs_copy_file
**功能说明**：复制单个文件，保留原文件元数据，支持覆写开关。
**入参**：
- `source_file_path` (字符串，必填)：源文件路径
- `dest_file_path` (字符串，必填)：目标文件路径
- `overwrite` (布尔，选填，默认false)：覆盖已存在文件
  **成功返回**：空 info 对象

### fs_move_file
**功能说明**：移动单个文件，自定义冲突覆写行为。
**入参**：
- `source_file_path` (字符串，必填)：源文件路径
- `dest_file_path` (字符串，必填)：目标文件路径
- `overwrite` (布尔，选填，默认false)：覆盖冲突文件
  **成功返回**：空 info 对象

### fs_get_file_info
**功能说明**：获取文件/文件夹完整元数据，可选计算 SHA256 哈希摘要。
**入参**：
- `file_path` (字符串，必填)：目标路径
- `calc_digest` (布尔，选填，默认false)：是否计算文件哈希
  **成功返回**：
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
**功能说明**：轻量校验文件/文件夹是否存在。
**入参**：
- `file_path` (字符串，必填)：目标路径
  **成功返回**：
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

## 3. 文件读写工具
### fs_read_full_text
**功能说明**：一次性读取完整文本文件内容，支持多编码。
**入参**：
- `file_path` (字符串，必填)：文件路径
- `charset` (字符串，选填，默认utf-8)：文本编码
  **成功返回**：
```json
{
  "res": {
    "success": true,
    "info": {
      "content": "完整文本内容"
    }
  }
}
```

### fs_read_text_range
**功能说明**：大文件分段读取文本，支持跳过开头行数、限制读取总行数。
**入参**：
- `file_path` (字符串，必填)：文件路径
- `lines_to_skip` (整数，必填，≥0)：跳过前置行数
- `max_lines_to_read` (整数，必填，≥0)：最大读取行数
- `line_separator` (字符串，选填，默认`\n`)：换行分隔符
- `charset` (字符串，选填，默认utf-8)：文本编码
  **成功返回**：
```json
{
  "res": {
    "success": true,
    "info": {
      "lines_count": 5,
      "content": "分段读取文本"
    }
  }
}
```

### fs_read_binary_chunk
**功能说明**：二进制文件分块读取，返回 Base64 编码字节流，附带流结束标记。
**入参**：
- `file_path` (字符串，必填)：文件路径
- `bytes_to_skip` (整数，必填，≥0)：跳过前置字节
- `max_bytes_to_read` (整数，必填，≥0)：单次最大读取字节数
  **成功返回**：
```json
{
  "res": {
    "success": true,
    "info": {
      "data_base64": "base64二进制数据",
      "raw_bytes_length": 5,
      "end_of_stream": true
    }
  }
}
```

### fs_write_text
**功能说明**：写入文本内容，支持覆写或追加模式。
**入参**：
- `file_path` (字符串，必填)：目标文件路径
- `text` (字符串，必填，长度≥1)：待写入文本
- `append` (布尔，选填，默认false)：开启追加写入
- `charset` (字符串，选填，默认utf-8)：文本编码
  **成功返回**：空 info 对象

### fs_write_binary
**功能说明**：解码 Base64 二进制数据写入文件，支持追加。
**入参**：
- `file_path` (字符串，必填)：目标文件路径
- `base64_data` (字符串，必填，长度≥1)：base64 编码二进制数据
- `append` (布尔，选填，默认false)：开启追加写入
  **成功返回**：空 info 对象

## 4. 检索与替换工具
### fs_search_files_by_content
**功能说明**：遍历目录，返回包含目标文本的全部文件路径；支持正则、大小写忽略、后缀过滤。
**入参**：
- `dir_path` (字符串，必填)：扫描根目录
- `recursive` (布尔，必填)：是否递归扫描
- `search_term` (字符串，必填)：检索关键词/正则表达式
- `is_regex` (布尔，选填，默认false)：启用正则匹配
- `ignore_case` (布尔，选填，默认true)：忽略大小写
- `file_extension` (字符串，选填，默认空)：文件后缀过滤
- `charset` (字符串，选填，默认utf-8)：文件编码

### fs_search_in_files_by_content
**功能说明**：多文件批量内容匹配，返回带前后上下文的结构化匹配结果，可限制最大匹配条数。
**入参**：
- `dir_path` (字符串，必填)：扫描根目录
- `recursive` (布尔，必填)：是否递归扫描
- `search_term` (字符串，必填)：检索关键词/正则
- `limit` (整数，必填)：最大匹配结果条数
- `is_regex` (布尔，选填，默认false)：正则开关
- `ignore_case` (布尔，选填，默认true)：忽略大小写
- `lines_before` (整数，选填，默认0)：匹配行前置上下文行数
- `lines_after` (整数，选填，默认0)：匹配行后置上下文行数
- `file_extension` (字符串，选填，默认空)：后缀过滤
- `charset` (字符串，选填，默认utf-8)：文件编码
  **成功返回**：
```json
{
  "res": {
    "success": true,
    "info": {
      "results": [
        {
          "file_path": "/test/file.ts",
          "start_line": 1,
          "end_line": 1,
          "text": "匹配行完整内容"
        }
      ]
    }
  }
}
```

### fs_search_in_file_by_content
**功能说明**：单文件精准检索，返回带上下文的匹配行。
**入参**：同多文件检索，仅路径改为单个文件
**成功返回**：与多文件检索 result 数组结构一致

### fs_file_replace
**功能说明**：文件内原地文本全局替换，返回成功替换次数。
**入参**：
- `file_path` (字符串，必填)：目标文件路径
- `search_term` (字符串，必填)：待替换文本
- `replacement` (字符串，必填)：替换新文本
- `line_separator` (字符串，选填，默认`\n`)：换行分隔符
  **成功返回**：
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

## 5. 图像处理工具
### fs_image_resize
**功能说明**：图片缩放至指定尺寸，支持锁定原图比例、填充画布至目标宽高。
**入参**：
- `source_path` (字符串，必填)：原图路径
- `dest_path` (字符串，必填)：输出图片路径
- `width` (整数，必填，>0)：目标宽度
- `height` (整数，必填，>0)：目标高度
- `keep_aspect_ratio` (布尔，选填，默认true)：锁定原图宽高比
- `pad_to_target` (布尔，选填，默认true)：不足尺寸自动填充画布
  **成功返回**：空 info 对象

### fs_image_crop
**功能说明**：从原图裁切指定矩形区域，导出新图片。
**入参**：
- `source_path` (字符串，必填)：原图路径
- `dest_path` (字符串，必填)：裁切输出路径
- `x` (整数，必填，≥0)：裁切起始X坐标
- `y` (整数，必填，≥0)：裁切起始Y坐标
- `width` (整数，必填，>0)：裁切区域宽度
- `height` (整数，必填，>0)：裁切区域高度
  **成功返回**：空 info 对象

### fs_image_rotate
**功能说明**：图片顺时针旋转任意角度，自动扩展画布完整保留图像内容。
**入参**：
- `source_path` (字符串，必填)：原图路径
- `dest_path` (字符串，必填)：旋转输出路径
- `degrees` (数字，必填)：顺时针旋转角度
  **成功返回**：空 info 对象

## 6. OCR 文字提取工具
### fs_ocr_extract_text
**功能说明**：调用本地 Tesseract 程序识别图片文字，无 WASM 网页兜底方案；`tesseract_bin_path` 留空仅从系统环境变量查找程序。
**入参**：
- `image_path` (字符串，必填)：待识别图片路径
- `tesseract_bin_path` (字符串，选填，默认空)：本地 tesseract 可执行文件路径
- `tessdata_path` (字符串，选填，默认空)：语言数据包目录路径
- `lang` (字符串，选填，默认eng)：识别语言前缀，匹配 tessdata 文件
  **成功返回**：
```json
{
  "res": {
    "success": true,
    "info": {
      "content": "图片识别出的全部文字"
    }
  }
}
```

# 项目构建与开发脚本
源码仓库统一开发命令（uv 工具）
```bash
# 清理编译产物
uv run -m scripts.clean

# 完整编译源码
uv run -m scripts.build

# 开发热更新监听模式
uv run -m scripts.dev

# 完整重建：清理 + 编译
uv run -m scripts.rebuild

# 启动 SSE 远程服务
uv run -m scripts.server

# FastMCP 开发调试模式
uv run -m scripts.fastmcp

# MCP Inspector 调试连接
uv run -m scripts.inspect

# 编译并执行全套测试用例
uv run -m scripts.test
```

# 核心运行依赖
- **fastmcp**：Python 官方 MCP 服务运行框架
- **Pillow**：图像缩放、裁切、旋转处理引擎
- **tesseract**：本地 Tesseract OCR 程序绑定
- **chardet**：文件编码自动检测
- **字符编码转换库**：多编码读写支持
- **cors**：远程 HTTP/SSE 跨域中间件
- **命令行解析工具**：启动参数解析
- **pydantic**：全部工具入参强校验
- **uvicorn / starlette**：ASGI HTTP 远程传输服务

# 开源许可证
本项目基于 **Apache License 2.0** 开源，完整许可条款见项目根目录 `LICENSE` 文件。

# 第三方依赖许可说明
项目依赖 chardet、Pillow、python-magic、tesseract 等开源库，各第三方组件遵循自身原始开源协议与版权声明。
备注：项目不内置 FFmpeg 二进制程序，如需拓展媒体功能，请单独遵循 FFmpeg 官方许可条款。

# 项目仓库与问题反馈
- GitHub 源码仓库：https://github.com/kurtzhi/fsext-mcp-server-python
- Bug 反馈与功能需求：https://github.com/kurtzhi/fsext-mcp-server-python/issues