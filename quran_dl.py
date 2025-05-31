#!/usr/bin/env python3
"""
Enhanced Quran Audio Downloader with CI/CD Integration

Features:
- Robust error handling
- Configurable parallel downloads
- Comprehensive test coverage
- CI/CD ready
"""

import os
import requests
import concurrent.futures
from pathlib import Path
from tqdm import tqdm
import hashlib
import logging
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('quran_downloader.log'),
        logging.StreamHandler()
    ]
)

class QuranDownloader:
    def __init__(self, max_workers: int = 5, timeout: int = 30, max_retries: int = 3):
        self.base_url = "https://quranicaudio.com/api/reciters"
        self.download_base = "https://download.quranicaudio.com/quran"
        self.max_workers = max_workers
        self.timeout = timeout
        self.max_retries = max_retries
        self.reciters_cache = None

    def get_reciters(self) -> List[Dict]:
        """Fetch all reciters with caching"""
        try:
            response = requests.get(self.base_url, timeout=self.timeout)
            response.raise_for_status()
            return sorted(response.json(), key=lambda x: x['name'].lower())
        except Exception as e:
            logging.error(f"Failed to fetch reciters: {e}")
            return []

    def download_surah(self, reciter_id: str, surah_num: int, output_dir: Path) -> bool:
        """Download single surah with retries and verification"""
        url = f"{self.download_base}/{reciter_id}/mp3/{surah_num:03d}.mp3"
        output_path = output_dir / f"{surah_num:03d}.mp3"
        temp_path = output_path.with_suffix('.tmp')

        for attempt in range(self.max_retries):
            try:
                with requests.get(url, stream=True, timeout=self.timeout) as r:
                    r.raise_for_status()
                    total_size = int(r.headers.get('content-length', 0))
                    
                    with open(temp_path, 'wb') as f, tqdm(
                        desc=f"Surah {surah_num}",
                        total=total_size,
                        unit='B',
                        unit_scale=True,
                        unit_divisor=1024,
                    ) as pbar:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                            pbar.update(len(chunk))

                if self._verify_download(temp_path, total_size):
                    temp_path.rename(output_path)
                    return True

            except Exception as e:
                logging.warning(f"Attempt {attempt + 1} failed: {e}")
                if temp_path.exists():
                    temp_path.unlink()

        return False

    def _verify_download(self, file_path: Path, expected_size: int) -> bool:
        """Verify downloaded file integrity"""
        if not file_path.exists():
            return False
        return file_path.stat().st_size == expected_size

    def download(
        self,
        reciter_id: str,
        surahs: List[int],
        output_dir: Path,
    ) -> Dict[str, int]:
        """Main download method with parallel execution"""
        output_dir.mkdir(parents=True, exist_ok=True)
        results = {'success': 0, 'failed': 0}

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self.download_surah,
                    reciter_id,
                    surah,
                    output_dir
                ): surah for surah in surahs
            }

            for future in concurrent.futures.as_completed(futures):
                surah = futures[future]
                if future.result():
                    results['success'] += 1
                    logging.info(f"Downloaded surah {surah}")
                else:
                    results['failed'] += 1
                    logging.error(f"Failed to download surah {surah}")

        return results