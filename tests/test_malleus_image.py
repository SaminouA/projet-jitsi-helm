"""Exercise image entrypoint arguments with a fake Maven; no Docker/network."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

class MalleusImage(unittest.TestCase):
    def test_video_only_meeting_parameters_and_offline_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            mvn = Path(directory, 'mvn')
            mvn.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
            mvn.chmod(0o755)
            env = dict(os.environ, PATH=directory+':'+os.environ['PATH'],
                       GRID_URL='http://load-selenium:4444/wd/hub', PARTICIPANTS='2', DURATION='90')
            result = subprocess.run(['sh', 'tests/load/docker/run-malleus-container.sh', 'test'],
                                    env=env, capture_output=True, text=True, check=True)
            args = result.stdout.splitlines()
            for expected in ['-o', '-Dorg.jitsi.malleus.participants=2',
                             '-Dorg.jitsi.malleus.duration=90', '-Dorg.jitsi.malleus.conferences=1',
                             '-Dorg.jitsi.malleus.audio_senders=0', '-Dorg.jitsi.malleus.enable_p2p=false']:
                self.assertIn(expected, args)
            self.assertTrue(any('config.startWithAudioMuted=true' in arg for arg in args))

    def test_publication_requires_execution_and_only_manual_trigger(self):
        w=yaml.safe_load(Path('.github/workflows/build-malleus.yml').read_text())
        self.assertEqual(w.get('on', w.get(True)), {'workflow_dispatch': None})
        steps=w['jobs']['malleus']['steps']
        execution=next(s for s in steps if s.get('id')=='execution')
        self.assertIn('--network=none', execution['run'])
        self.assertIn('--self-test', execution['run'])
        self.assertIn('--maven-self-test', execution['run'])
        publication=next(s for s in steps if s.get('name')=='Publish only after successful execution')
        self.assertEqual(publication['if'], "success() && steps.execution.outcome == 'success'")
