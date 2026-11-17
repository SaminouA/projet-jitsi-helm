"""A real failed media command must fail the workflow step."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

class MediaPublicationGate(unittest.TestCase):
    def test_failed_media_command_fails_step(self):
        workflow = yaml.safe_load(Path('.github/workflows/build-selenium.yml').read_text())
        step = next(s for s in workflow['jobs']['selenium']['steps']
                    if s.get('name') == 'Test real synthetic camera and microphone')
        with tempfile.TemporaryDirectory() as directory:
            for command, code in [('docker', 0), ('python3', 17)]:
                p = Path(directory, command)
                p.write_text('#!/bin/sh\nexit ' + str(code) + '\n')
                p.chmod(0o755)
            env = dict(os.environ, PATH=directory+':'+os.environ['PATH'],
                       RUNNER_TEMP=directory, IMAGE='test-only')
            result = subprocess.run(['bash', '-e', '-c', step['run']], env=env,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 17)

class SyntheticMediaConfiguration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import importlib.util
        spec = importlib.util.spec_from_file_location('selenium_media_test', 'scripts/test-selenium-media.py')
        cls.media = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.media)

    def test_missing_synthetic_switch_is_rejected(self):
        self.media.validate_flags(list(self.media.REQUIRED_FLAGS))
        for flag in self.media.REQUIRED_FLAGS:
            with self.subTest(flag=flag), self.assertRaises(RuntimeError):
                self.media.validate_flags([x for x in self.media.REQUIRED_FLAGS if x != flag])

    def test_session_or_tracks_without_real_signal_are_rejected(self):
        good = dict(ok=True, videoTracks=1, audioTracks=1, width=640, height=360,
                    decodedFrames=30, audioRms=0.05)
        self.media.validate_media(good)
        for key in ['videoTracks', 'audioTracks', 'width', 'height', 'decodedFrames', 'audioRms']:
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                self.media.validate_media(dict(good, **{key: 0}))
        with self.assertRaisesRegex(RuntimeError, 'audio-capture:NotFoundError'):
            self.media.validate_media(dict(ok=False, category='audio-capture:NotFoundError'))

    def test_wrapper_forwards_synthetic_flags_and_configured_paths(self):
        import json
        import re
        dockerfile = Path('tests/load/docker/Dockerfile.selenium').read_text()
        fragment = re.search(r"printf '%s\\n' '([^']+)' > /opt/selenium/browser_binary_location", dockerfile)
        self.assertIsNotNone(fragment)
        binary = json.loads('{' + fragment.group(1) + '}')['goog:chromeOptions']['binary']
        self.assertEqual(binary, '/opt/jitsi/chrome-wrapper')
        with tempfile.TemporaryDirectory() as directory:
            stub = Path(directory, 'chrome')
            stub.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
            stub.chmod(0o755)
            wrapper = Path(directory, 'wrapper')
            wrapper.write_text(Path('tests/load/docker/chrome-wrapper.sh').read_text()
                               .replace('/usr/bin/google-chrome', str(stub)))
            result = subprocess.run(['sh', str(wrapper), '--headless=new'],
                                    check=True, capture_output=True, text=True)
            self.media.validate_flags(result.stdout.splitlines())
            self.assertIn('--headless=new', result.stdout.splitlines())
        self.assertIn('chmod 0644 /usr/share/jitsi-meet-torture/resources/*', dockerfile)

    def test_publication_requires_success_and_no_automatic_trigger(self):
        workflow = yaml.safe_load(Path('.github/workflows/build-selenium.yml').read_text())
        # PyYAML YAML1.1 interprets the GitHub key 'on' as True.
        self.assertEqual(workflow.get('on', workflow.get(True)), {'workflow_dispatch': None})
        steps = workflow['jobs']['selenium']['steps']
        media = next(s for s in steps if s.get('id') == 'media')
        publication = next(s for s in steps if s.get('name') == 'Publish only after media test success')
        self.assertEqual(media['shell'], 'bash')
        self.assertIn('set -euo pipefail', media['run'])
        self.assertEqual(publication['if'], "success() && steps.media.outcome == 'success'")
        self.assertNotIn('continue-on-error', media)
