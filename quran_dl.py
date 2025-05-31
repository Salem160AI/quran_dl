#!/usr/bin/env python3
"""
quran_dl.py - Quran Audio Downloader

An enhanced Python script to download Quran recitations from quranicaudio.com with:
- Structured folder output
- Download verification with checksums
- Parallel downloads with progress feedback
- Resume capability for interrupted downloads
- Configuration presets
- Multiple selection options
"""

import argparse
import requests
import os
import re
import json
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin
import time
import configparser
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from tqdm import tqdm

class QuranDownloader:
    def __init__(self, max_workers: int = 5, timeout: int = 30, max_retries: int = 3):
        """
        Initialize the Quran downloader
        
        Args:
            max_workers: Number of parallel downloads
            timeout: Request timeout in seconds
            max_retries: Maximum download attempts per file
        """
        self.base_url = "https://quranicaudio.com"
        self.download_base = "https://download.quranicaudio.com/quran"
        self.max_workers = max_workers
        self.timeout = timeout
        self.max_retries = max_retries
        self.reciters_cache = None
        self.reciters_cache_time = 0
        self.cache_expiry = 3600  # 1 hour cache
        self.config_file = "quran_dl_config.ini"
        self.config = configparser.ConfigParser()
        self._load_config()

    def _load_config(self):
        """Load or initialize configuration"""
        self.config['DEFAULT'] = {
            'output_dir': 'quran_downloads',
            'max_workers': '5',
            'max_retries': '3',
            'timeout': '30'
        }
        
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)

    def _save_config(self):
        """Save current configuration to file"""
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

    def get_reciters(self, force_refresh: bool = False) -> List[Dict]:
        """Fetch all reciters from Quranicaudio.com API with caching"""
        current_time = time.time()
        
        if not force_refresh and self.reciters_cache and (current_time - self.reciters_cache_time) < self.cache_expiry:
            return self.reciters_cache
            
        try:
            response = requests.get(
                urljoin(self.base_url, "/api/reciters"),
                timeout=self.timeout
            )
            response.raise_for_status()
            reciters = sorted(response.json(), key=lambda x: x['name'].lower())
            self.reciters_cache = reciters
            self.reciters_cache_time = current_time
            return reciters
        except Exception as e:
            print(f"Failed to fetch reciters: {e}")
            return []

    def display_reciters(self, reciters: List[Dict]):
        """Display reciters in alphabetical order"""
        print("\nAvailable Reciters (Alphabetical Order):")
        print("-" * 60)
        for i, reciter in enumerate(reciters, 1):
            print(f"{i:3}. {reciter['name']} ({reciter['language']})")
        print("-" * 60)

    def parse_surah_selection(self, selection: str) -> List[int]:
        """
        Parse surah selection string into list of surah numbers
        
        Args:
            selection: Selection string (e.g., "1", "1,2,3", "1-5")
            
        Returns:
            List of surah numbers
        """
        if selection.lower() == 'all':
            return list(range(1, 115))
            
        # Handle ranges (e.g., 1-5)
        if '-' in selection:
            try:
                start, end = map(int, selection.split('-'))
                if 1 <= start <= end <= 114:
                    return list(range(start, end + 1))
                raise ValueError("Range must be between 1 and 114")
            except ValueError as e:
                raise ValueError(f"Invalid range format: {e}")
        
        # Handle comma-separated list
        if ',' in selection:
            try:
                surahs = list({int(s.strip()) for s in selection.split(',') if s.strip()})
                if all(1 <= s <= 114 for s in surahs):
                    return sorted(surahs)
                raise ValueError("All numbers must be between 1 and 114")
            except ValueError as e:
                raise ValueError(f"Invalid list format: {e}")
        
        # Handle single surah
        try:
            surah = int(selection)
            if 1 <= surah <= 114:
                return [surah]
            raise ValueError("Surah number must be between 1 and 114")
        except ValueError as e:
            raise ValueError(f"Invalid surah number: {e}")

    def _get_file_hash(self, filepath: str) -> str:
        """Calculate MD5 hash of a file"""
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _verify_download(self, local_path: str, original_size: int, remote_hash: str = None) -> bool:
        """Verify downloaded file integrity"""
        if not os.path.exists(local_path):
            return False
        
        if os.path.getsize(local_path) != original_size:
            return False
            
        if remote_hash:
            return self._get_file_hash(local_path) == remote_hash
            
        return True

    def _get_remote_file_info(self, url: str) -> Tuple[int, str]:
        """Get remote file size and hash if available"""
        try:
            # First try HEAD request for size
            head_resp = requests.head(url, timeout=self.timeout)
            head_resp.raise_for_status()
            original_size = int(head_resp.headers.get('content-length', 0))
            
            # Try to get hash if available (some servers provide this)
            remote_hash = head_resp.headers.get('content-md5', None)
            
            return original_size, remote_hash
        except Exception:
            # Fallback to GET request if HEAD fails
            try:
                response = requests.get(url, stream=True, timeout=self.timeout)
                response.raise_for_status()
                original_size = int(response.headers.get('content-length', 0))
                remote_hash = response.headers.get('content-md5', None)
                return original_size, remote_hash
            except Exception as e:
                raise Exception(f"Failed to get file info: {str(e)}")

    def _download_with_progress(self, url: str, filepath: str, expected_size: int) -> bool:
        """Download file with progress bar"""
        try:
            # Check for existing partial download
            temp_path = filepath + ".tmp"
            resume_byte_pos = 0
            if os.path.exists(temp_path):
                resume_byte_pos = os.path.getsize(temp_path)
            
            headers = {}
            if resume_byte_pos:
                headers['Range'] = f'bytes={resume_byte_pos}-'
            
            response = requests.get(url, stream=True, timeout=self.timeout, headers=headers)
            response.raise_for_status()
            
            # Adjust expected size for resumed download
            total_size = expected_size
            if resume_byte_pos:
                total_size += resume_byte_pos
            
            mode = 'ab' if resume_byte_pos else 'wb'
            with open(temp_path, mode) as f, tqdm(
                unit='B', unit_scale=True,
                unit_divisor=1024, miniters=1,
                desc=f"Surah {os.path.basename(filepath)}",
                total=total_size,
                initial=resume_byte_pos
            ) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:  # filter out keep-alive new chunks
                        f.write(chunk)
                        pbar.update(len(chunk))
            
            return True
        except Exception as e:
            if os.path.exists(temp_path):
                # Only delete if download failed completely (not for resume)
                if not resume_byte_pos:
                    os.remove(temp_path)
            raise e

    def _download_surah(self, reciter: Dict, surah: int, output_dir: str = "quran_downloads") -> Dict:
        """
        Download a single surah with verification
        
        Args:
            reciter: Reciter dictionary
            surah: Surah number (1-114)
            output_dir: Base output directory
            
        Returns:
            Dictionary with download results
        """
        result = {
            'surah': surah,
            'success': False,
            'path': None,
            'error': None,
            'attempts': 0
        }
        
        reciter_id = reciter['id']
        path_segment = "_mp3" if reciter_id in ['alafasy', 'abdulbasitmurattal', 'misharyrashidalfasy'] else "mp3"
        
        # Create proper folder structure
        safe_reciter_name = re.sub(r'[\\/*?:"<>|]', "", reciter['name'])
        download_dir = os.path.join(output_dir, safe_reciter_name)
        os.makedirs(download_dir, exist_ok=True)
        
        surah_num = f"{surah:03d}"
        filename = f"{surah_num}.mp3"
        filepath = os.path.join(download_dir, filename)
        url = f"{self.download_base}/{reciter_id}/{path_segment}/{surah_num}.mp3"
        
        # Check if file already exists and is valid
        if os.path.exists(filepath):
            try:
                original_size, remote_hash = self._get_remote_file_info(url)
                if self._verify_download(filepath, original_size, remote_hash):
                    result.update({
                        'success': True,
                        'path': filepath,
                        'size': original_size,
                        'message': 'Already downloaded and verified'
                    })
                    return result
            except Exception:
                pass  # Proceed with download if verification fails
        
        # Get original file info
        try:
            original_size, remote_hash = self._get_remote_file_info(url)
            if original_size == 0:
                result['error'] = "Invalid file size (0 bytes)"
                return result
        except Exception as e:
            result['error'] = str(e)
            return result
        
        # Download with retries
        for attempt in range(1, self.max_retries + 1):
            result['attempts'] = attempt
            try:
                temp_path = filepath + ".tmp"
                
                if self._download_with_progress(url, filepath, original_size):
                    if self._verify_download(temp_path, original_size, remote_hash):
                        os.replace(temp_path, filepath)
                        result.update({
                            'success': True,
                            'path': filepath,
                            'size': original_size
                        })
                        return result
                    
                    os.remove(temp_path)
                    time.sleep(1)  # Wait before retry
                
            except Exception as e:
                result['error'] = str(e)
                time.sleep(1)
        
        return result

    def download(
        self,
        reciter_name: Optional[str] = None,
        surah_selection: Optional[str] = None,
        output_dir: str = None,
        interactive: bool = False,
        save_preset: Optional[str] = None,
        load_preset: Optional[str] = None
    ) -> Dict:
        """
        Main download method
        
        Args:
            reciter_name: Name of reciter to download (None for interactive)
            surah_selection: Surah selection string (None for interactive)
            output_dir: Output directory (None uses default)
            interactive: Whether to use interactive mode
            save_preset: Name to save current settings as preset
            load_preset: Name of preset to load
            
        Returns:
            Dictionary with download summary
        """
        summary = {
            'reciter': None,
            'total': 0,
            'success': 0,
            'failed': 0,
            'time_elapsed': 0,
            'output_dir': output_dir or self.config['DEFAULT']['output_dir'],
            'errors': []
        }
        
        # Handle presets
        if load_preset:
            if load_preset in self.config:
                reciter_name = self.config[load_preset].get('reciter', None)
                surah_selection = self.config[load_preset].get('surah_selection', None)
                output_dir = self.config[load_preset].get('output_dir', None)
                print(f"Loaded preset: {load_preset}")
            else:
                print(f"Preset '{load_preset}' not found")
        
        start_time = time.time()
        
        # Get reciters list
        reciters = self.get_reciters()
        if not reciters:
            summary['error'] = "No reciters found"
            return summary
        
        # Select reciter
        selected_reciter = None
        if reciter_name:
            for r in reciters:
                if r['name'].lower() == reciter_name.lower():
                    selected_reciter = r
                    break
            if not selected_reciter:
                raise ValueError(f"Reciter '{reciter_name}' not found")
        elif interactive:
            self.display_reciters(reciters)
            while True:
                try:
                    reciter_choice = int(input("\nEnter the number of the reciter you want: "))
                    if 1 <= reciter_choice <= len(reciters):
                        selected_reciter = reciters[reciter_choice - 1]
                        break
                    print(f"Please enter a number between 1 and {len(reciters)}")
                except ValueError:
                    print("Please enter a valid number.")
        else:
            raise ValueError("Either reciter_name or interactive must be specified")
        
        summary['reciter'] = selected_reciter['name']
        
        # Get surah selection
        surahs_to_download = []
        if surah_selection:
            try:
                surahs_to_download = self.parse_surah_selection(surah_selection)
            except ValueError as e:
                raise ValueError(f"Invalid surah selection: {e}")
        elif interactive:
            print("\nDownload Options:")
            print("1. Single Surah")
            print("2. Multiple Surahs (comma-separated)")
            print("3. Range of Surahs (e.g., 1-5)")
            print("4. All 114 Surahs")
            
            while True:
                choice = input("\nEnter your choice (1-4): ").strip()
                if choice in ['1', '2', '3', '4']:
                    break
                print("Invalid input. Please enter 1-4.")
            
            if choice == '1':
                while True:
                    try:
                        surah = int(input("\nEnter Surah number (1-114): "))
                        if 1 <= surah <= 114:
                            surahs_to_download = [surah]
                            break
                        print("Please enter a number between 1 and 114.")
                    except ValueError:
                        print("Please enter a valid number.")
            elif choice == '2':
                while True:
                    input_str = input("\nEnter Surah numbers (comma-separated, e.g., 1,2,3): ").strip()
                    try:
                        surahs = list({int(s.strip()) for s in input_str.split(',') if s.strip()})
                        if all(1 <= s <= 114 for s in surahs):
                            surahs_to_download = sorted(surahs)
                            break
                        print("All numbers must be between 1 and 114.")
                    except ValueError:
                        print("Please enter valid numbers separated by commas.")
            elif choice == '3':
                while True:
                    input_str = input("\nEnter Surah range (e.g., 1-5): ").strip()
                    try:
                        start, end = map(int, input_str.split('-'))
                        if 1 <= start <= end <= 114:
                            surahs_to_download = list(range(start, end + 1))
                            break
                        print("Range must be between 1 and 114.")
                    except ValueError:
                        print("Please enter a valid range (e.g., 1-5).")
            else:
                surahs_to_download = list(range(1, 115))
        
        summary['total'] = len(surahs_to_download)
        
        # Save preset if requested
        if save_preset:
            self.config[save_preset] = {
                'reciter': selected_reciter['name'],
                'surah_selection': ','.join(map(str, surahs_to_download)) if len(surahs_to_download) < 114 else 'all',
                'output_dir': summary['output_dir']
            }
            self._save_config()
            print(f"Settings saved as preset: {save_preset}")
        
        # Display summary
        if interactive:
            print("\n" + "=" * 60)
            print("Download Summary:".center(60))
            print(f"Reciter: {selected_reciter['name']}")
            print(f"Total Surahs: {len(surahs_to_download)}")
            
            if len(surahs_to_download) <= 20:
                print("Surahs:", ', '.join(map(str, surahs_to_download)))
            else:
                print(f"Surahs: {surahs_to_download[0]}-{surahs_to_download[-1]}")
            
            print(f"Folder Structure: {summary['output_dir']}/{re.sub(r'[\\/*?:"<>|]', '', selected_reciter['name'])}/")
            print("=" * 60)
            
            confirm = input("\nProceed with download? (y/n): ").lower()
            if confirm != 'y':
                print("Download cancelled.")
                return summary
        
        # Download with thread pool
        if interactive:
            print("\nStarting downloads...\n")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._download_surah, selected_reciter, surah, summary['output_dir']): surah
                for surah in surahs_to_download
            }
            
            for future in as_completed(futures):
                surah = futures[future]
                try:
                    result = future.result()
                    if result['success']:
                        summary['success'] += 1
                        if interactive:
                            print(f"\nSurah {surah} - Downloaded to {result['path']}")
                    else:
                        summary['failed'] += 1
                        error_msg = f"Surah {surah} - {result['error'] or 'Unknown error'}"
                        summary['errors'].append(error_msg)
                        if interactive:
                            print(f"\n{error_msg}")
                except Exception as e:
                    summary['failed'] += 1
                    error_msg = f"Surah {surah} - Error: {str(e)}"
                    summary['errors'].append(error_msg)
                    if interactive:
                        print(f"\n{error_msg}")
        
        summary['time_elapsed'] = time.time() - start_time
        
        if interactive:
            print("\n" + "=" * 60)
            print("Download Summary:".center(60))
            print(f"Successfully downloaded: {summary['success']}/{summary['total']}")
            print(f"Time elapsed: {summary['time_elapsed']:.1f} seconds")
            print(f"Files saved in: {summary['output_dir']}/{re.sub(r'[\\/*?:"<>|]', '', selected_reciter['name'])}/")
            print("=" * 60)
        
        return summary

def main():
    parser = argparse.ArgumentParser(
        description="Download Quran audio files from quranicaudio.com",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '-r', '--reciter',
        help="Name of reciter to download (use 'list' to show available reciters)"
    )
    parser.add_argument(
        '-s', '--surah',
        help="Surah selection (number, comma-separated list, or range, e.g., '1', '1,2,3', '1-5', or 'all')"
    )
    parser.add_argument(
        '-o', '--output',
        help="Output directory (default: 'quran_downloads')"
    )
    parser.add_argument(
        '-j', '--workers',
        type=int,
        help="Number of parallel downloads (default: 5)"
    )
    parser.add_argument(
        '-i', '--interactive',
        action='store_true',
        help="Use interactive mode"
    )
    parser.add_argument(
        '--save-preset',
        help="Save current settings as a named preset"
    )
    parser.add_argument(
        '--load-preset',
        help="Load settings from a named preset"
    )
    parser.add_argument(
        '--max-retries',
        type=int,
        help="Maximum download attempts per file (default: 3)"
    )
    parser.add_argument(
        '--timeout',
        type=int,
        help="Request timeout in seconds (default: 30)"
    )
    
    args = parser.parse_args()
    
    # Initialize downloader with config values or defaults
    downloader = QuranDownloader(
        max_workers=args.workers or int(QuranDownloader().config['DEFAULT']['max_workers']),
        timeout=args.timeout or int(QuranDownloader().config['DEFAULT']['timeout']),
        max_retries=args.max_retries or int(QuranDownloader().config['DEFAULT']['max_retries'])
    )
    
    if args.reciter == 'list':
        reciters = downloader.get_reciters()
        downloader.display_reciters(reciters)
        return
    
    if args.interactive or not args.reciter or not args.surah:
        result = downloader.download(
            interactive=True,
            save_preset=args.save_preset
        )
    else:
        result = downloader.download(
            reciter_name=args.reciter,
            surah_selection=args.surah,
            output_dir=args.output,
            save_preset=args.save_preset,
            load_preset=args.load_preset
        )
        
        if result.get('error'):
            print(f"Error: {result['error']}")
        else:
            print("\nDownload Summary:")
            print(f"Reciter: {result['reciter']}")
            print(f"Successfully downloaded: {result['success']}/{result['total']}")
            print(f"Time elapsed: {result['time_elapsed']:.1f} seconds")
            print(f"Output directory: {result['output_dir']}")

if __name__ == "__main__":
    main()