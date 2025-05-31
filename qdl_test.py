#!/usr/bin/env python3
"""
Comprehensive Test Suite for Quran Downloader
"""

import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from quran_dl import QuranDownloader
import tempfile
import shutil

class TestQuranDownloader(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.downloader = QuranDownloader(max_workers=2, timeout=5, max_retries=1)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('requests.get')
    def test_get_reciters(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {'id': 'test1', 'name': 'Reciter 1'},
            {'id': 'test2', 'name': 'Reciter 2'}
        ]
        mock_get.return_value = mock_response

        reciters = self.downloader.get_reciters()
        self.assertEqual(len(reciters), 2)
        self.assertEqual(reciters[0]['name'], 'Reciter 1')

    @patch('requests.get')
    def test_download_surah_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b'test' * 1024]
        mock_response.headers = {'content-length': '4096'}
        mock_get.return_value = mock_response

        result = self.downloader.download_surah(
            reciter_id='test1',
            surah_num=1,
            output_dir=self.temp_dir
        )
        self.assertTrue(result)
        self.assertTrue((self.temp_dir / '001.mp3').exists())

    @patch('requests.get')
    def test_download_surah_failure(self, mock_get):
        mock_get.side_effect = Exception("Network error")
        result = self.downloader.download_surah(
            reciter_id='test1',
            surah_num=1,
            output_dir=self.temp_dir
        )
        self.assertFalse(result)

    @patch('quran_dl.QuranDownloader.download_surah')
    def test_parallel_downloads(self, mock_download):
        mock_download.return_value = True
        results = self.downloader.download(
            reciter_id='test1',
            surahs=[1, 2, 3],
            output_dir=self.temp_dir
        )
        self.assertEqual(results['success'], 3)
        self.assertEqual(results['failed'], 0)

if __name__ == '__main__':
    unittest.main()