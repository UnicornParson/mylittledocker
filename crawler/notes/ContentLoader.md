import feedparser
from datetime import datetime
import requests
from email.utils import parsedate_to_datetime
from argon2.low_level import hash_secret_raw, Type
import base64
import time
import sys
import os
import subprocess
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright
import cloudscraper
import tempfile
import asyncio
from enum import Enum
import re
import html
from tabulate import tabulate
from dataclasses import dataclass, fields, asdict
from typing import List, Optional, Dict, Any
import logging
from .content_type import *
from .net_config import NetConfig
try:
    # for webdriver_manager >= 3.8.0
    from webdriver_manager.core.os_manager import ChromeType
except ImportError:
    # old webdriver_manager
    from webdriver_manager.core.utils import ChromeType


class ContentLoaderEnv:
    def __init__(self):
        self.logger = logging.getLogger("net.ContentLoaderEnv")

    def install_chromium_conda(self) -> bool:
        self.logger.info("try to install chromium")
        try:
            if 'ipykernel' in sys.modules: # run in Jupyter
                get_ipython().system('conda install -c conda-forge chromium-browser -y')
                get_ipython().system('conda install -c conda-forge chromedriver -y')
            else:
                subprocess.run(['conda', 'install', '-c', 'conda-forge', 'chromium-browser', '-y'], check=True)
                subprocess.run(['conda', 'install', '-c', 'conda-forge', 'chromedriver', '-y'], check=True)
            self.logger.info("chromium has been installed")
            return True
        except Exception as e:
            self.logger.warning(f"installation failed: {e}")
            return False

    def get_chromium_path(self):
        conda_prefix = os.environ.get('CONDA_PREFIX', '')
        paths = [
            os.path.join(conda_prefix, 'bin', 'chromium'),
            os.path.join(conda_prefix, 'bin', 'chromium-browser'),
            os.path.join(conda_prefix, 'Library', 'bin', 'chromium.exe'),
        ]

        for path in paths:
            if os.path.exists(path):
                return path
        return None

    def install_playwright_deps_local():
        logger = logging.getLogger("net.ContentLoaderEnv")
        logger.info("Installing local dependencies for Playwright...")
        try:
            # Create directory for dependencies
            home_dir = os.path.expanduser("~")
            deps_dir = os.path.join(home_dir, "playwright-deps")
            os.makedirs(deps_dir, exist_ok=True)

            # Install necessary packages in local directory
            deps = [
                "libatk1.0-0", "libatk-bridge2.0-0", "libxcomposite1",
                "libxdamage1", "libatspi2.0-0", "libnss3", "libnspr4",
                "libdrm2", "libxkbcommon0", "libgbm1", "libasound2"
            ]

            for dep in deps:
                # Download package
                download_cmd = f"apt-get download {dep}"
                subprocess.run(download_cmd, shell=True, check=True, cwd=deps_dir)

                # Find downloaded file
                deb_file = next((f for f in os.listdir(deps_dir) if f.endswith(".deb") and dep in f), None)
                if not deb_file:
                    logger.warning(f"Could not find .deb file for {dep}")
                    continue

                # Extract package
                deb_path = os.path.join(deps_dir, deb_file)
                extract_cmd = f"dpkg-deb -x {deb_path} {deps_dir}"
                subprocess.run(extract_cmd, shell=True, check=True)

                # Remove .deb file after extraction
                os.remove(deb_path)

            # Set environment variables
            lib_path = os.path.join(deps_dir, "usr", "lib", "x86_64-linux-gnu")
            os.environ["LD_LIBRARY_PATH"] = f"{lib_path}:{os.environ.get('LD_LIBRARY_PATH', '')}"
            logger.info(f"LD_LIBRARY_PATH set: {os.environ['LD_LIBRARY_PATH']}")

            return True
        except Exception as e:
            logger.error(f"Error installing dependencies: {e}")
            return False

class ContentLoader:
    def __init__(self):
        self.logger = logging.getLogger("net.ContentLoader")

    def try_scraper(self, url) -> str:
        scraper = cloudscraper.create_scraper()
        return scraper.get(url).text

    def get_content_raw(self, url: str) -> str:
        return self.try_scraper(url)

    async def get_content_with_anubis(self, url: str, timeout: int = 60) -> tuple[ContentType, str]:
        """
        Gets page content after passing Anubis verification
        :param url: URL to load
        :param timeout: maximum wait time in seconds
        :return: tuple[ContentType, str] - content type and content
        """
        logger = logging.getLogger("net.ContentLoader")
        p = await async_playwright().start()
        # Launch Chromium in headless mode
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()

        # Navigate to the page
        logger.info(f"Loading URL: {url}")
        await page.goto(url, wait_until="domcontentloaded")

        try:
            # Wait for Anubis elements to appear
            initial_content = await page.content()
            initial_content = html.unescape(initial_content)
            c_type = detect_content_type(initial_content)
            if c_type == ContentType.HTML_ATOM:
                x = extract_xml(initial_content)
                c = detect_content_type(x)
                if c != ContentType.RAW_ATOM:
                    raise ValueError(f"cannot extract atom from [[ {initial_content[:256]} ]] is not an atom [[ {x[:256]} ]] detected as {c.name}")
                return ContentType.RAW_ATOM, x
            elif c_type != ContentType.ANUBIS:
                return c_type, initial_content


            logger.info("Waiting for Anubis verification...")
            await page.wait_for_selector("text=Making sure you're not a bot!", timeout=timeout*1000)

            # Wait for progress bar completion
            try:
                progress_bar = page.locator("#progress")
                logger.info("Waiting for progress bar completion...")

                # Monitor progress bar changes
                start_time = time.time()
                while time.time() - start_time < timeout:
                    class_list = await progress_bar.get_attribute("class") or ""
                    if "hidden" in class_list or "invisible" in class_list:
                        logger.info("Progress bar hidden!")
                        break
                    await asyncio.sleep(0.5)
                else:
                    logger.warning("Progress bar timeout")
            except:
                logger.info("Progress bar not found, using fallback wait")
                await page.wait_for_timeout(15000)  # 15 seconds

            # Additional wait for script execution
            await page.wait_for_load_state("networkidle")

            # Check result
            if  await page.query_selector("text=Making sure you're not a bot!"):
                logger.error("Anubis verification failed!")
                return ContentType.INVALID, None

            logger.info("Anubis verification passed!")
            content = await page.content()
            content = html.unescape(content)
            return detect_content_type(content), content

        except Exception as e:
            logger.error(f"Error: {str(e)}")
            await page.screenshot(path="anubis_error.png")
            logger.info("Screenshot saved as anubis_error.png")
            return ContentType.INVALID, None
        finally:
            await browser.close()

    async def fetch(self, url: str, timeout: int = 60) -> tuple[ContentType, str]:
        content = self.get_content_raw(url)
        c_type = detect_content_type(content)
        if c_type == ContentType.ANUBIS:
            # If detected as ANUBIS, use get_content_with_anubis
            c_type, content = await self.get_content_with_anubis(url, timeout=timeout)
        return c_type, content


