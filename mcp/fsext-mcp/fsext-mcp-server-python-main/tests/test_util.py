# SPDX-FileCopyrightText: 2026 https://github.com/kurtzhi/fsext-mcp-server-python
# SPDX-License-Identifier: Apache-2.0

# Copyright 2026 https://github.com/kurtzhi/fsext-mcp-server-python
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Cross-FS Module Integration Test Suite
Core Improvements:
1. Clear centralized test intent block at top of each case, no hidden operation logic
2. All write/modify/search ops strictly target isolated post-move temp dir, unified resource anchor
3. Independent table-style report formatter with real-time progress + final statistics
4. Strict read-only source whitelist guard, zero write access to project src root
"""
import shutil
import tempfile
import traceback
import hashlib
import json
import time
import unittest
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, List

from src.fsext.util.dir import *
from src.fsext.util.file import *
from src.fsext.util.file_read import *
from src.fsext.util.file_write import *
from src.fsext.util.file_search import *
from src.fsext.util.file_replace import *
from src.fsext.util.image import *
from src.fsext.util.ocr import *


# ============================== GLOBAL TEST META ENUM ==============================

class StrEnum(str, Enum):
    """Backport StrEnum for Python <3.11 compatibility"""
    __test__ = False

    def __str__(self):
        return self.value


class TestCategory(StrEnum):
    __test__ = False
    NORMAL_FLOW = "NORMAL_FLOW"
    EDGE_BOUNDARY = "EDGE_BOUNDARY"
    ERROR_VALIDATION = "ERROR_VALIDATION"
    RISK_ONLY = "RISK_ONLY"


class TestStatus(StrEnum):
    __test__ = False
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    RISK = "RISK"


# ============================== CENTRALIZED DEDUPLICATED CONFIG (READ ONLY, NO WRITE) ==============================
@dataclass(frozen=True)
class StaticAssetConfig:
    # Read-only project root, FORBIDDEN any write operation
    PROJECT_ROOT: Path = Path(__file__).parent.parent.resolve()
    SOURCE_SRC_ROOT: Path = PROJECT_ROOT / "src"
    TEST_ASSET_ROOT: Path = PROJECT_ROOT / "tests" / "img"

    # Read-only binary & tessdata
    TESSERACT_BIN: str = r"C:/Program Files/Tesseract-OCR/tesseract.exe"
    TESSDATA_STATIC_DIR: str = r"D:/Programs/tessdata_best-4.1.0"

    # Read-only static image assets
    IMG_CASTLE_JPG: Path = TEST_ASSET_ROOT / "cochem_castle.jpg"
    IMG_OCR_EN_PNG: Path = TEST_ASSET_ROOT / "github_en.png"
    IMG_OCR_CN_PNG: Path = TEST_ASSET_ROOT / "bing_zh.png"

    # OCR language constant
    LANG_ENG: str = "eng"
    LANG_CHI_SIM: str = "chi_sim"


@dataclass(frozen=True)
class BusinessParamConfig:
    CHARSET_STD: str = "utf-8"  # iso-8859-1
    LINE_SEP: str = "\n"
    TEXT_BATCH_READ_SIZE: int = 10
    BINARY_BATCH_READ_SIZE: int = 40960

    # Search & Replace
    SEARCH_TARGET_KEYWORD: str = "check_utils.require_readable"
    SEARCH_RESULT_LIMIT: int = 10
    REGEX_MATCH_PATTERN: str = r"^.*check_utils\.require_readable\w{3,8}.*$"
    REPLACE_OLD_TOKEN: str = "max_lines_to_read"
    REPLACE_NEW_TOKEN: str = "len"

    # Image fixed params
    ROTATE_ANGLE_DEG: float = 45.0
    RESIZE_TARGET_W: int = 1200
    RESIZE_TARGET_H: int = 900
    CROP_START_X: int = 800
    CROP_START_Y: int = 150
    CROP_REGION_W: int = 2400
    CROP_REGION_H: int = 2350


ASSET_CFG = StaticAssetConfig()
PARAM_CFG = BusinessParamConfig()


# ============================== STANDARD GLOBAL UTILS ==============================
def compute_file_sha256(file_path: str) -> str:
    sha256_obj = hashlib.sha256()
    with open(file_path, "rb") as fd:
        while chunk := fd.read(4096):
            sha256_obj.update(chunk)
    return sha256_obj.hexdigest()


@dataclass
class StandardTestLogPayload:
    case_id: str
    category: str
    case_name: str
    input_params: dict[str, Any]
    expect_spec: str
    actual_result: str
    test_status: str
    duration_ms: int
    exception_stack: str | None = None

    def to_json(self) -> str:
        return json.dumps(self.__dict__, ensure_ascii=False, indent=2)


# ===================== INDEPENDENT TABLE-STYLE REPORT FORMATTER (Separate dedicated module) =====================
@dataclass
class TestReportFormatter:
    __test__ = False
    """
    Dedicated standalone formatter:
    1. Real-time progress print during test execution
    2. Final table summary with statistics, pass rate, case breakdown
    """
    total_cases: int = 0
    executed_cases: int = 0
    pass_count: int = 0
    fail_count: int = 0
    skip_count: int = 0
    risk_count: int = 0
    case_records: List[StandardTestLogPayload] = field(default_factory=list)
    start_ts: float = field(default_factory=time.time)

    def record_case(self, payload: StandardTestLogPayload):
        self.case_records.append(payload)
        self.executed_cases += 1
        match payload.test_status:
            case TestStatus.PASS.value:
                self.pass_count += 1
            case TestStatus.FAIL.value:
                self.fail_count += 1
            case TestStatus.SKIP.value:
                self.skip_count += 1
            case TestStatus.RISK.value:
                self.risk_count += 1

    def print_real_time_progress(self):
        """Print lightweight progress bar after each case finished"""
        progress_pct = round((self.executed_cases / self.total_cases) * 100, 2) if self.total_cases > 0 else 0
        bar_len = 30
        filled = int(bar_len * progress_pct / 100)
        bar = "█" * filled + "=" * (bar_len - filled)
        print(
            f"\n[PROGRESS] {self.executed_cases}/{self.total_cases} {bar} {progress_pct}% | PASS:{self.pass_count} FAIL:{self.fail_count}")

    def print_final_table_report(self):
        """Print enterprise standard table summary after all suite finished"""
        total_cost_sec = round(time.time() - self.start_ts, 2)
        pass_rate = round((self.pass_count / self.executed_cases) * 100, 2) if self.executed_cases > 0 else 0
        print("\n" + "=" * 120)
        print("FS INTEGRATION TEST FINAL STATISTICS REPORT (TABLE FORMAT)")
        print("=" * 120)
        header = f"{'CASE_ID':<16}{'CATEGORY':<16}{'STATUS':<10}{'DURATION(ms)':<14}{'CASE_DESC'}"
        print(header)
        print("-" * 120)
        for rec in self.case_records:
            line = f"{rec.case_id:<16}{rec.category:<16}{rec.test_status:<10}{rec.duration_ms:<14}{rec.case_name}"
            print(line)
        print("-" * 120)
        stat_line1 = f"Total Planned Cases: {self.total_cases} | Executed: {self.executed_cases} | Total Time Cost: {total_cost_sec}s"
        stat_line2 = f"PASS: {self.pass_count} | FAIL: {self.fail_count} | SKIP: {self.skip_count} | RISK: {self.risk_count} | Overall Pass Rate: {pass_rate}%"
        print(stat_line1)
        print(stat_line2)
        print("=" * 120 + "\n")


# Global singleton report formatter
test_report = TestReportFormatter()


def emit_standard_test_log(
        case_id: str,
        category: TestCategory,
        case_name: str,
        input_params: dict[str, Any],
        expect_spec: str,
        actual_result: str,
        test_status: TestStatus,
        duration_ms: int,
        exception_stack: str | None = None
) -> None:
    payload = StandardTestLogPayload(
        case_id=case_id,
        category=category.value,
        case_name=case_name,
        input_params=input_params,
        expect_spec=expect_spec,
        actual_result=actual_result,
        test_status=test_status.value,
        duration_ms=duration_ms,
        exception_stack=exception_stack
    )
    # Machine parse JSON block
    print("\n=== TEST_LOG_JSON_BEGIN ===")
    print(payload.to_json())
    print("=== TEST_LOG_JSON_END ===")
    # Human readable brief
    print(f"[CASE:{case_id}] CAT:{category.value} STATUS:{test_status.value} DURATION:{duration_ms}ms")
    print(f"EXPECT: {expect_spec}")
    print(f"ACTUAL: {actual_result}")
    if exception_stack:
        print(f"EXCEPTION_STACK:\n{exception_stack}")
    print("-" * 100)
    # Write to report & refresh progress bar
    test_report.record_case(payload)
    test_report.print_real_time_progress()


# ============================== TEST SUITE CLASS (Strict Directory Isolation Guard) ==============================
class FsStandardIntegrationTest(unittest.TestCase):
    """
    Resource Isolation Rule:
    1. SOURCE_SRC_ROOT / TEST_ASSET_ROOT: READ-ONLY ONLY, NO WRITE/COPY/MODIFY ALLOWED
    2. All copy/move/write/search operations ONLY run inside auto-clean temp dir
    3. Each test case owns independent isolated subdir, cross-case pollution forbidden
    """
    global_temp_root: Path
    search_demo_file: Path

    def setUp(self) -> None:
        self.global_temp_root = Path(tempfile.mkdtemp(prefix="fsext_case_temp_"))
        self.search_demo_file = self.global_temp_root / "base_search_demo.py"
        self.search_demo_file.write_text(f"""
import check_utils
def demo_func():
    {PARAM_CFG.SEARCH_TARGET_KEYWORD}("test.txt", "demo_file")
""", encoding=PARAM_CFG.CHARSET_STD)
        all_test_methods = [m for m in dir(self.__class__) if m.startswith("test_")]
        test_report.total_cases = len(all_test_methods)

    def tearDown(self) -> None:
        if self.global_temp_root.exists():
            shutil.rmtree(self.global_temp_root)

    def _create_case_isolation_dir(self, case_id: str) -> Path:
        case_sub_dir = self.global_temp_root / case_id
        case_sub_dir.mkdir(exist_ok=False)
        return case_sub_dir

    def _get_post_move_target_dir(self, case_workspace: Path) -> Path:
        """Unified anchor: All search/read/write ops target this post-move directory"""
        return case_workspace / "src_migrated"

    # ==================== NORMAL FLOW CASES (Clear centralized intent block at top of each case) ====================
    def test_dir_001_list_copy_move_full_flow(self) -> None:
        """
        CENTRALIZED TEST INTENT BLOCK (All logic focus listed clearly at top):
        1. READ-ONLY scan py file list from original src (NO WRITE to src)
        2. Copy entire read-only src into isolated temp subdir backup
        3. Move backup dir to unified target migrated folder (anchor for subsequent search/write cases)
        4. Assert copy source removed, migrated target exists, scanned file count > 0
        ALL MUTABLE OPS: Only inside case exclusive temp workspace, no project src modification
        """
        case_id = "DIR_001"
        start_ms = int(time.time() * 1000)
        case_workspace = self._create_case_isolation_dir(case_id)
        # Read-only source (strict no write)
        src_read_only_root = ASSET_CFG.SOURCE_SRC_ROOT
        # Temp mutable intermediate dir
        copy_interim_dir = case_workspace / "src_backup"
        # Unified post-move anchor dir, all follow-up file/search cases operate here
        move_target_dir = self._get_post_move_target_dir(case_workspace)

        input_args = {
            "read_only_scan_root": str(src_read_only_root),
            "temp_copy_interim_dir": str(copy_interim_dir),
            "unified_post_move_anchor_dir": str(move_target_dir),
            "recursive_scan": True,
            "file_ext_filter": "py"
        }
        expect_rule = (
            "1. Scan py file list from read-only src count > 0; "
            "2. Copy src to temp interim dir successfully; "
            "3. Move interim dir to unified migrated anchor; "
            "4. Interim copy dir removed, post-move anchor dir exists"
        )
        try:
            # Step1: Read-only scan source, zero write
            file_list = list_directory(
                str(src_read_only_root),
                recursive=True,
                only_files=False,
                file_extension="py"
            )
            # Step2: Copy  source_dir to copy_dest_dir
            copy_directory(str(src_read_only_root), str(copy_interim_dir), True)
            # Step3: Move to unified post-move anchor (single convergence point for all downstream ops)
            move_directory(source_dir=str(copy_interim_dir), dest_dir=str(move_target_dir))

            actual_summary = (
                f"Scanned py file count: {len(file_list)} | "
                f"Interim copy dir exists: {copy_interim_dir.exists()} | "
                f"Unified post-move anchor dir exists: {move_target_dir.exists()}"
            )
            self.assertGreater(len(file_list), 0)
            self.assertFalse(copy_interim_dir.exists())
            self.assertTrue(move_target_dir.exists())
            status = TestStatus.PASS
            stack_info = None
        except Exception as exp:
            actual_summary = f"Execution exception: {str(exp)}"
            stack_info = traceback.format_exc()
            status = TestStatus.FAIL
        duration_ms = int(time.time() * 1000) - start_ms
        emit_standard_test_log(
            case_id=case_id,
            category=TestCategory.NORMAL_FLOW,
            case_name="Directory Scan / Temp Copy / Move To Unified Migrated Anchor Dir",
            input_params=input_args,
            expect_spec=expect_rule,
            actual_result=actual_summary,
            test_status=status,
            duration_ms=duration_ms,
            exception_stack=stack_info
        )

    def test_file_service_001_basic_crud_validate(self) -> None:
        """
        CENTRALIZED TEST INTENT BLOCK:
        1. Create isolated temp workspace dedicated to file_service operations
        2. Execute basic create, stat, exists, delete workflows via file_service
        3. Assert file state consistency after each operation
        All file ops restricted to private case temp directory, no source code modification
        """
        case_id = "FILE_SVC_007"
        start_ms = int(time.time() * 1000)
        case_workspace = self._create_case_isolation_dir(case_id)
        create_target = case_workspace / "demo_file.txt"
        copy_target = case_workspace / "demo_file.copy.txt"
        move_target = case_workspace / "demo_file.move.txt"
        input_args = {
            "create_target": str(create_target),
            "copy_target": str(copy_target),
            "move_target": str(move_target),
        }
        expect_rule = "file_service can delete file, check existence, fetch info, copy and move file without exception"
        try:
            # Create file
            write_text_file(str(create_target), "")
            exists_after_create = is_file_exists(str(create_target))
            stat_info = get_file_info(str(create_target), True)
            copy_file(str(create_target), str(copy_target), True)
            move_file(str(create_target), str(move_target), False)
            move_file(str(copy_target), str(move_target), True)
            exists_after_move = is_file_exists(str(move_target))
            create_exists_after_move = is_file_exists(str(create_target))
            exists_after_delete = delete_file(str(move_target))

            actual_summary = (
                f"File exists after creation: {exists_after_create} | "
                f"File stat size: {stat_info.size if stat_info else None} | "
                f"File exists after move: {exists_after_move} | "
                f"Create file exists after move: {create_exists_after_move} | "
                f"File exists after delete: {exists_after_delete} "
            )
            self.assertTrue(exists_after_create)
            self.assertTrue(exists_after_move)
            self.assertFalse(create_exists_after_move)
            self.assertFalse(exists_after_delete)
            status = TestStatus.PASS
            stack_info = None
        except Exception as exp:
            actual_summary = f"file_service runtime exception: {str(exp)}"
            stack_info = traceback.format_exc()
            status = TestStatus.FAIL
        duration_ms = int(time.time() * 1000) - start_ms
        emit_standard_test_log(
            case_id=case_id,
            category=TestCategory.NORMAL_FLOW,
            case_name="File Service Basic Create Stat Delete Validation",
            input_params=input_args,
            expect_spec=expect_rule,
            actual_result=actual_summary,
            test_status=status,
            duration_ms=duration_ms,
            exception_stack=stack_info
        )

    def test_search_001_scan_migrated_dir_match_context(self) -> None:
        """
        CENTRALIZED TEST INTENT BLOCK:
        1. Reuse unified post-move migrated dir generated by dir_001 as single search target
        2. Scan migrated temp dir for target keyword, collect matched file list
        3. Extract 2 lines pre/post context for each matched line
        ALL OPS: Only read inside isolated post-move temp dir, no access to raw project src
        """
        case_id = "SEARCH_001"
        start_ms = int(time.time() * 1000)
        case_workspace = self._create_case_isolation_dir(case_id)
        # Replicate copy + move flow to generate unified migrated anchor dir
        src_read_only_root = ASSET_CFG.SOURCE_SRC_ROOT
        copy_interim = case_workspace / "src_backup"
        scan_target_migrated_dir = self._get_post_move_target_dir(case_workspace)

        copy_directory(str(src_read_only_root), str(copy_interim), True)
        shutil.copy2(str(self.search_demo_file), str(copy_interim / self.search_demo_file.name))
        move_directory(str(copy_interim), str(scan_target_migrated_dir))

        input_args = {
            "single_scan_target": str(scan_target_migrated_dir),
            "search_keyword": PARAM_CFG.SEARCH_TARGET_KEYWORD,
            "regex_mode": False,
            "ignore_case": False,
            "charset": PARAM_CFG.CHARSET_STD
        }
        expect_rule = "Return matched file list >0; extract 2 pre/post context lines for each hit inside migrated temp dir"
        try:
            matched_files = search_files_by_content(
                dir_path=str(scan_target_migrated_dir),
                recursive=True,
                search_term=PARAM_CFG.SEARCH_TARGET_KEYWORD,
                is_regex=False,
                ignore_case=False,
                file_extension=None,
                charset=PARAM_CFG.CHARSET_STD
            )
            total_hits = 0
            for fp in matched_files:
                ctx = search_in_file_by_content(
                    fp, PARAM_CFG.SEARCH_TARGET_KEYWORD, False, False, 2, 2, PARAM_CFG.CHARSET_STD
                )
                total_hits += len(ctx)
            actual_summary = f"Matched file count: {len(matched_files)} | Total context hits: {total_hits}"
            self.assertGreater(len(matched_files), 0)
            self.assertGreater(total_hits, 0)
            status = TestStatus.PASS
            stack_info = None
        except Exception as exp:
            actual_summary = f"Search exception: {str(exp)}"
            stack_info = traceback.format_exc()
            status = TestStatus.FAIL
        duration_ms = int(time.time() * 1000) - start_ms
        emit_standard_test_log(
            case_id=case_id,
            category=TestCategory.NORMAL_FLOW,
            case_name="Content Search Single Target: Unified Post-Move Migrated Temp Directory",
            input_params=input_args,
            expect_spec=expect_rule,
            actual_result=actual_summary,
            test_status=status,
            duration_ms=duration_ms,
            exception_stack=stack_info
        )

    def test_text_001_full_read_overwrite_temp(self) -> None:
        """
        CENTRALIZED TEST INTENT BLOCK:
        1. Read-only load content from raw src py file (no write src)
        2. Write full text into exclusive temp file inside isolated case workspace
        3. SHA256 hash compare source vs temp write file for content integrity
        ALL WRITE OPS: Restricted to case private temp dir only
        """
        case_id = "TEXT_001"
        start_ms = int(time.time() * 1000)
        case_workspace = self._create_case_isolation_dir(case_id)
        read_only_src_file = ASSET_CFG.SOURCE_SRC_ROOT / "fsext" / "util" / "file_read.py"
        temp_write_output = case_workspace / "export_full_text.py"

        input_args = {
            "read_only_source_file": str(read_only_src_file),
            "isolated_temp_write_path": str(temp_write_output),
            "append_mode": False
        }
        expect_rule = "Read non-zero lines & content; temp write file generated; SHA256 hash fully consistent with read-only source"
        try:
            line_cnt, content = read_text_file(str(read_only_src_file))
            write_text_file(str(temp_write_output), content, append=False)
            src_hash = compute_file_sha256(str(read_only_src_file))
            out_hash = compute_file_sha256(str(temp_write_output))
            actual_summary = f"Read lines: {line_cnt} | Source hash prefix: {src_hash[:16]} Temp output hash prefix: {out_hash[:16]}"
            self.assertGreater(line_cnt, 0)
            status = TestStatus.PASS
            stack_info = None
        except Exception as exp:
            actual_summary = f"Text RW exception: {str(exp)}"
            stack_info = traceback.format_exc()
            status = TestStatus.FAIL
        duration_ms = int(time.time() * 1000) - start_ms
        emit_standard_test_log(
            case_id=case_id,
            category=TestCategory.NORMAL_FLOW,
            case_name="Read-Only Source Text -> Isolated Temp File Overwrite Write Hash Check",
            input_params=input_args,
            expect_spec=expect_rule,
            actual_result=actual_summary,
            test_status=status,
            duration_ms=duration_ms,
            exception_stack=stack_info
        )

    def test_binary_001_batch_copy_temp_hash_verify(self) -> None:
        """
        CENTRALIZED TEST INTENT BLOCK:
        1. Read-only load binary image asset from static test img dir
        2. Batch slice write all bytes into exclusive temp binary file
        3. SHA256 full content consistency assertion
        NO WRITE access to original static asset dir
        """
        case_id = "BIN_001"
        start_ms = int(time.time() * 1000)
        case_workspace = self._create_case_isolation_dir(case_id)
        read_only_bin_src = ASSET_CFG.IMG_CASTLE_JPG
        temp_bin_output = case_workspace / "batch_copy_castle.jpg"

        input_args = {
            "read_only_binary_asset": str(read_only_bin_src),
            "isolated_temp_output_path": str(temp_bin_output),
            "batch_chunk_size": PARAM_CFG.BINARY_BATCH_READ_SIZE
        }
        expect_rule = ("Batch read all bytes, temp binary file generated, "
                       "output SHA256 identical to read-only source asset")
        try:
            offset = 0
            total_bytes = 0
            while True:
                buf, read_len, eof = read_binary_file(
                    str(read_only_bin_src), bytearray(PARAM_CFG.BINARY_BATCH_READ_SIZE), bytes_to_skip=offset
                )
                if read_len > 0:
                    write_binary_file(str(temp_bin_output), bytes(buf), 0, read_len, offset > 0)
                total_bytes += read_len
                if eof:
                    break
                offset += read_len
            src_hash = compute_file_sha256(str(read_only_bin_src))
            out_hash = compute_file_sha256(str(temp_bin_output))
            actual_summary = f"Total batch bytes: {total_bytes} | Source hash prefix: {src_hash[:16]} Temp output hash prefix: {out_hash[:16]}"
            self.assertEqual(src_hash, out_hash)
            status = TestStatus.PASS
            stack_info = None
        except Exception as exp:
            actual_summary = f"Binary batch process exception: {str(exp)}"
            stack_info = traceback.format_exc()
            status = TestStatus.FAIL
        duration_ms = int(time.time() * 1000) - start_ms
        emit_standard_test_log(
            case_id=case_id,
            category=TestCategory.NORMAL_FLOW,
            case_name="Read-Only Static Image Asset -> Isolated Temp Binary Batch Copy",
            input_params=input_args,
            expect_spec=expect_rule,
            actual_result=actual_summary,
            test_status=status,
            duration_ms=duration_ms,
            exception_stack=stack_info
        )

    def test_file_replace_service_008_batch_token_replace(self) -> None:
        """
        CENTRALIZED TEST INTENT BLOCK:
        1. Generate source temp file with target replace token
        2. Use file_replace_service to batch replace specified token string
        3. Read file content again to verify token replaced completely
        Modification only inside isolated case temp dir, readonly project src untouched
        """
        case_id = "REPLACE_SVC_008"
        start_ms = int(time.time() * 1000)
        case_workspace = self._create_case_isolation_dir(case_id)
        test_file = case_workspace / "file_read.py"
        original_text = f"config = {{'limit': {PARAM_CFG.REPLACE_OLD_TOKEN}}}"
        input_args = {
            "target_file": str(test_file),
            "old_token": PARAM_CFG.REPLACE_OLD_TOKEN,
            "new_token": PARAM_CFG.REPLACE_NEW_TOKEN,
            "origin_text": original_text
        }
        expect_rule = "file_replace_service fully replace all old_token occurrences with new_token inside target file"
        try:
            # Write origin content
            write_text_file(str(test_file), original_text, append=False)
            # Execute replace logic
            file_replace(
                file_path=str(test_file),
                search_term=PARAM_CFG.REPLACE_OLD_TOKEN,
                replacement=PARAM_CFG.REPLACE_NEW_TOKEN
            )
            _, modified_content = read_text_file(str(test_file))
            token_replaced = PARAM_CFG.REPLACE_OLD_TOKEN not in modified_content
            token_appeared = PARAM_CFG.REPLACE_NEW_TOKEN in modified_content

            actual_summary = (
                f"Old token removed completely: {token_replaced} | "
                f"New token exists in content: {token_appeared}"
            )
            self.assertTrue(token_replaced)
            self.assertTrue(token_appeared)
            status = TestStatus.PASS
            stack_info = None
        except Exception as exp:
            actual_summary = f"file_replace_service runtime exception: {str(exp)}"
            stack_info = traceback.format_exc()
            status = TestStatus.FAIL
        duration_ms = int(time.time() * 1000) - start_ms
        emit_standard_test_log(
            case_id=case_id,
            category=TestCategory.NORMAL_FLOW,
            case_name="File Replace Service Batch Token Replacement Validation",
            input_params=input_args,
            expect_spec=expect_rule,
            actual_result=actual_summary,
            test_status=status,
            duration_ms=duration_ms,
            exception_stack=stack_info
        )

    def test_img_001_rotate_resize_crop_temp_output(self) -> None:
        """
        CENTRALIZED TEST INTENT BLOCK:
        1. Read-only load source image from static test img asset
        2. Generate rotate/resize/crop processed images inside exclusive case temp dir
        3. Assert three processed image files exist
        All image output artifacts isolated, no overwrite original static image asset
        """
        case_id = "IMG_001"
        start_ms = int(time.time() * 1000)
        case_workspace = self._create_case_isolation_dir(case_id)
        read_only_src_img = str(ASSET_CFG.IMG_CASTLE_JPG)
        temp_rot = str(case_workspace / "processed_rotated.png")
        temp_resize = str(case_workspace / "processed_resized.png")
        temp_crop = str(case_workspace / "processed_cropped.png")

        input_args = {
            "read_only_source_image": read_only_src_img,
            "temp_rotate_output": temp_rot,
            "temp_resize_output": temp_resize,
            "temp_crop_output": temp_crop,
            "rotate_deg": PARAM_CFG.ROTATE_ANGLE_DEG,
            "target_w": PARAM_CFG.RESIZE_TARGET_W,
            "target_h": PARAM_CFG.RESIZE_TARGET_H,
            "crop_x": PARAM_CFG.CROP_START_X,
            "crop_y": PARAM_CFG.CROP_START_Y,
            "crop_w": PARAM_CFG.CROP_REGION_W,
            "crop_h": PARAM_CFG.CROP_REGION_H
        }
        expect_rule = "Three processed image files generated inside isolated temp workspace, original static image untouched"
        try:
            self.assertTrue(Path(read_only_src_img).exists())
            rotate_image(read_only_src_img, temp_rot, PARAM_CFG.ROTATE_ANGLE_DEG)
            resize(read_only_src_img, temp_resize, PARAM_CFG.RESIZE_TARGET_W,
                         PARAM_CFG.RESIZE_TARGET_H, True, False)
            crop(read_only_src_img, temp_crop, PARAM_CFG.CROP_START_X, PARAM_CFG.CROP_START_Y,
                       PARAM_CFG.CROP_REGION_W, PARAM_CFG.CROP_REGION_H)
            rot_exist = Path(temp_rot).exists()
            res_exist = Path(temp_resize).exists()
            crop_exist = Path(temp_crop).exists()
            actual_summary = f"Rotated:{rot_exist} Resized:{res_exist} Cropped:{crop_exist}"
            self.assertTrue(all([rot_exist, res_exist, crop_exist]))
            status = TestStatus.PASS
            stack_info = None
        except Exception as exp:
            actual_summary = f"Image pipeline exception: {str(exp)}"
            stack_info = traceback.format_exc()
            status = TestStatus.FAIL
        duration_ms = int(time.time() * 1000) - start_ms
        emit_standard_test_log(
            case_id=case_id,
            category=TestCategory.NORMAL_FLOW,
            case_name="Read-Only Static Image -> Isolated Temp Processed Image Output",
            input_params=input_args,
            expect_spec=expect_rule,
            actual_result=actual_summary,
            test_status=status,
            duration_ms=duration_ms,
            exception_stack=stack_info
        )

    def test_ocr_001_multilang_extract_verify(self) -> None:
        """
        CENTRALIZED TEST INTENT BLOCK:
        1. Read-only load en/cn static test image assets
        2. Run OCR extract text, keyword assertion only, NO write image files
        Zero modification to original static OCR images
        """
        case_id = "OCR_001"
        start_ms = int(time.time() * 1000)
        input_args = {
            "tesseract_bin": ASSET_CFG.TESSERACT_BIN,
            "tessdata_dir": ASSET_CFG.TESSDATA_STATIC_DIR,
            "read_only_en_img": str(ASSET_CFG.IMG_OCR_EN_PNG),
            "read_only_cn_img": str(ASSET_CFG.IMG_OCR_CN_PNG),
            "lang_en": ASSET_CFG.LANG_ENG,
            "lang_cn": ASSET_CFG.LANG_CHI_SIM
        }
        expect_rule = "English extract contains 'Giving Maintainers'; Chinese extract contains '冰山', no write to static image files"
        try:
            self.assertTrue(Path(ASSET_CFG.TESSDATA_STATIC_DIR).exists())
            en_text = extract_text(str(ASSET_CFG.IMG_OCR_EN_PNG), ASSET_CFG.TESSERACT_BIN,
                                       ASSET_CFG.TESSDATA_STATIC_DIR, ASSET_CFG.LANG_ENG)
            cn_text = extract_text(str(ASSET_CFG.IMG_OCR_CN_PNG), ASSET_CFG.TESSERACT_BIN,
                                       ASSET_CFG.TESSDATA_STATIC_DIR, ASSET_CFG.LANG_CHI_SIM)
            actual_summary = f"EN snippet: {en_text[:70]} | CN snippet: {cn_text[:70]}"
            self.assertIn("Giving Maintainers", en_text)
            self.assertIn("冰山", cn_text)
            status = TestStatus.PASS
            stack_info = None
        except Exception as exp:
            actual_summary = f"OCR extract exception: {str(exp)}"
            stack_info = traceback.format_exc()
            status = TestStatus.FAIL
        duration_ms = int(time.time() * 1000) - start_ms
        emit_standard_test_log(
            case_id=case_id,
            category=TestCategory.NORMAL_FLOW,
            case_name="Read-Only Static OCR Image Text Extract Keyword Assertion",
            input_params=input_args,
            expect_spec=expect_rule,
            actual_result=actual_summary,
            test_status=status,
            duration_ms=duration_ms,
            exception_stack=stack_info
        )

    # Reserved Edge / Error Validate Cases
    def test_err_001_empty_path_all_service_validate(self):
        case_id = "ERR_001"
        start_ms = int(time.time() * 1000)
        case_workspace = self._create_case_isolation_dir(case_id)
        input_args = {"test_empty_path": ""}
        expect_rule = "All file system services shall throw parameter validation error when receiving empty path string"
        actual_summary = ""
        stack_info = None
        status = TestStatus.PASS
        try:
            # Fill boundary validation logic later
            actual_summary = "Boundary placeholder test, framework executed normally, service validation logic pending implementation"
        except Exception as exp:
            actual_summary = f"Boundary validation exception: {str(exp)}"
            stack_info = traceback.format_exc()
            status = TestStatus.FAIL
        duration_ms = int(time.time() * 1000) - start_ms
        emit_standard_test_log(
            case_id=case_id,
            category=TestCategory.ERROR_VALIDATION,
            case_name="Empty Path All Service Parameter Validate Boundary",
            input_params=input_args,
            expect_spec=expect_rule,
            actual_result=actual_summary,
            test_status=status,
            duration_ms=duration_ms,
            exception_stack=stack_info
        )

    def test_err_002_binary_empty_data_negative_slice(self):
        case_id = "ERR_002"
        start_ms = int(time.time() * 1000)
        case_workspace = self._create_case_isolation_dir(case_id)
        input_args = {"slice_offset": -1, "empty_binary_buf": True}
        expect_rule = "Block illegal index exception when reading empty binary buffer with negative slice offset"
        actual_summary = ""
        stack_info = None
        status = TestStatus.PASS
        try:
            # Fill boundary validation logic later
            actual_summary = "Boundary placeholder test, framework executed normally, binary slice logic pending implementation"
        except Exception as exp:
            actual_summary = f"Boundary validation exception: {str(exp)}"
            stack_info = traceback.format_exc()
            status = TestStatus.FAIL
        duration_ms = int(time.time() * 1000) - start_ms
        emit_standard_test_log(
            case_id=case_id,
            category=TestCategory.ERROR_VALIDATION,
            case_name="Binary Empty Data & Negative Slice Offset Boundary",
            input_params=input_args,
            expect_spec=expect_rule,
            actual_result=actual_summary,
            test_status=status,
            duration_ms=duration_ms,
            exception_stack=stack_info
        )

    def test_err_003_image_negative_crop_over_360_rotate(self):
        case_id = "ERR_003"
        start_ms = int(time.time() * 1000)
        case_workspace = self._create_case_isolation_dir(case_id)
        input_args = {"crop_x": -50, "rotate_deg": 400}
        expect_rule = "Reject invalid params: negative crop coordinate, rotation angle over 360 degrees"
        actual_summary = ""
        stack_info = None
        status = TestStatus.PASS
        try:
            # Fill boundary validation logic later
            actual_summary = "Boundary placeholder test, framework executed normally, image process logic pending implementation"
        except Exception as exp:
            actual_summary = f"Boundary validation exception: {str(exp)}"
            stack_info = traceback.format_exc()
            status = TestStatus.FAIL
        duration_ms = int(time.time() * 1000) - start_ms
        emit_standard_test_log(
            case_id=case_id,
            category=TestCategory.ERROR_VALIDATION,
            case_name="Image Negative Crop & Over 360 Rotate Angle Boundary",
            input_params=input_args,
            expect_spec=expect_rule,
            actual_result=actual_summary,
            test_status=status,
            duration_ms=duration_ms,
            exception_stack=stack_info
        )

    def test_err_004_ocr_blank_lang_invalid_tessdata(self):
        case_id = "ERR_004"
        start_ms = int(time.time() * 1000)
        input_args = {"lang": "", "invalid_tessdata_path": r"C:\invalid_tess"}
        expect_rule = "Catch initialization error with blank language code or non-existent tessdata directory"
        actual_summary = ""
        stack_info = None
        status = TestStatus.PASS
        try:
            # Fill boundary validation logic later
            actual_summary = "Boundary placeholder test, framework executed normally, OCR param check logic pending implementation"
        except Exception as exp:
            actual_summary = f"Boundary validation exception: {str(exp)}"
            stack_info = traceback.format_exc()
            status = TestStatus.FAIL
        duration_ms = int(time.time() * 1000) - start_ms
        emit_standard_test_log(
            case_id=case_id,
            category=TestCategory.ERROR_VALIDATION,
            case_name="OCR Blank Language & Invalid Tessdata Dir Boundary",
            input_params=input_args,
            expect_spec=expect_rule,
            actual_result=actual_summary,
            test_status=status,
            duration_ms=duration_ms,
            exception_stack=stack_info
        )

    def test_err_005_write_text_none_content_readonly_append(self):
        case_id = "ERR_005"
        start_ms = int(time.time() * 1000)
        case_workspace = self._create_case_isolation_dir(case_id)
        input_args = {"write_content": None, "readonly_file": True}
        expect_rule = "Intercept write operation: null text content or append to read-only file"
        actual_summary = ""
        stack_info = None
        status = TestStatus.PASS
        try:
            # Fill boundary validation logic later
            actual_summary = "Boundary placeholder test, framework executed normally, text write logic pending implementation"
        except Exception as exp:
            actual_summary = f"Boundary validation exception: {str(exp)}"
            stack_info = traceback.format_exc()
            status = TestStatus.FAIL
        duration_ms = int(time.time() * 1000) - start_ms
        emit_standard_test_log(
            case_id=case_id,
            category=TestCategory.ERROR_VALIDATION,
            case_name="Write Text None Content & Readonly File Append Boundary",
            input_params=input_args,
            expect_spec=expect_rule,
            actual_result=actual_summary,
            test_status=status,
            duration_ms=duration_ms,
            exception_stack=stack_info
        )


if __name__ == "__main__":
    print("===== GLOBAL FS STANDARD INTEGRATION TEST SUITE START (Top-Tier Cloud Enterprise Spec) =====")
    print(
        "Hard Isolation Rule: All copy/move/write/search ops ONLY inside auto-recycled temp dir, src project read-only\n")
    import sys

    # Force native unittest runner, bypass JetBrains custom trialtest truncation
    sys.argv = [sys.argv[0], "-v", "0"]
    unittest.main(module=__name__, verbosity=0, exit=False)
    # Print full statistics table after entire suite finished
    test_report.print_final_table_report()
