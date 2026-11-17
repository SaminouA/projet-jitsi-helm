"""Video : pas de faux positif audio, garde RAM et packaging passif."""
import copy
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import wave
import yaml

ROOT = Path(__file__).resolve().parents[1]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

runner = load('video_runner', 'scripts/run-malleus-light.py')
media = load('synthetic_media', 'scripts/generate-synthetic-media.py')


class VideoSafetyTests(unittest.TestCase):
    def sample(self, n=2):
        return {'browsers': [{'joined': True, 'connection': 'connected', 'tracks': [{'type': 'video', 'muted': False}],
                  'bitrate': {'video': {'upload': 10, 'download': 20}}} for _ in range(n)],
                'jvb-0': {'local_active_endpoints': n, 'bit_rate_upload': 40, 'bit_rate_download': 20}}

    def test_video_requires_all_clients_and_jvb_forwarding(self):
        for n in [2, 3]: self.assertTrue(runner.video_verified(self.sample(n), n))
        sample = self.sample(); sample['browsers'].pop()
        self.assertFalse(runner.video_verified(sample, 2))
        sample = self.sample(); sample['jvb-0']['bit_rate_upload'] = 0
        self.assertFalse(runner.video_verified(sample, 2))

    def test_audio_only_or_muted_video_never_validates_video(self):
        for field, value in [('type', 'audio'), ('muted', True)]:
            sample = self.sample(); sample['browsers'][0]['tracks'][0][field] = value
            self.assertFalse(runner.video_verified(sample, 2))
        sample = self.sample(); sample['browsers'][0]['bitrate']['video']['download'] = 0
        self.assertFalse(runner.video_verified(sample, 2))

    def test_video_disk_memory_and_tmpfs_guards(self):
        base = {'nodes': ['node 100m 5% 2300Mi 38%'], 'pods': {'web': {'ready': True, 'restarts': 0}},
                'generator_disk_free_mib': 700, 'generator_mem_available_mib': 4000, 'generator_tmpfs_free_mib': 3000}
        with patch.object(runner, 'VIDEO_MODE', True):
            self.assertTrue(runner.healthy(base, base))
            for key, value in [('generator_disk_free_mib', 499), ('generator_mem_available_mib', 1023), ('generator_tmpfs_free_mib', 511)]:
                sample = copy.deepcopy(base); sample[key] = value
                self.assertFalse(runner.healthy(sample, base))

    def test_generated_camera_is_y4m_and_wav_and_never_overwrites(self):
        with tempfile.TemporaryDirectory(dir='/dev/shm') as tmp:
            video, audio = media.generate(Path(tmp))
            with video.open('rb') as stream:
                self.assertIn(b'W1280 H720 F30:1', stream.readline())
                self.assertEqual(stream.read(6), b'FRAME\n')
            with wave.open(str(audio)) as stream:
                self.assertEqual((stream.getnchannels(), stream.getsampwidth(), stream.getframerate()), (1, 2, 48000))
            size = video.stat().st_size
            with self.assertRaises(SystemExit): media.generate(Path(tmp))
            self.assertEqual(video.stat().st_size, size)

    def test_ten_participants_rejected_before_any_network(self):
        proc = subprocess.run(['python3', '-B', str(ROOT / 'scripts/run-malleus-light.py'), '--video', '--participants', '10'],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        proc = subprocess.run(['sh', str(ROOT / 'tests/load/docker/run-malleus-container.sh'), 'test'],
                              capture_output=True, text=True, env={'PARTICIPANTS': '10'})
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('Maximum 3', proc.stderr)

    def test_job_suspended_without_cluster_credentials(self):
        job = yaml.safe_load((ROOT / 'tests/load/docker/job-malleus.yaml').read_text())
        self.assertTrue(job['spec']['suspend']); self.assertEqual(job['spec']['backoffLimit'], 0)
        self.assertFalse(job['spec']['template']['spec']['automountServiceAccountToken'])
        for name in ['Dockerfile.selenium', 'Dockerfile.malleus']:
            self.assertIn('@sha256:', (ROOT / 'tests/load/docker' / name).read_text())
