"""Seuils de securite du generateur, sans acces reseau ou cluster."""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('malleus_light', ROOT / 'scripts/run-malleus-light.py')
load = importlib.util.module_from_spec(spec)
spec.loader.exec_module(load)


class LoadSafetyTests(unittest.TestCase):
    def setUp(self):
        self.base = {'nodes': ['node 100m 5% 2300Mi 38%'], 'generator_disk_free_mib': 700,
                     'pods': {'web': {'ready': True, 'restarts': 0}}}

    def test_healthy_baseline(self):
        self.assertTrue(load.healthy(self.base, self.base))

    def test_cpu_memory_and_disk_thresholds(self):
        for line in ['node 1600m 80% 2300Mi 38%', 'node 100m 5% 4900Mi 80%']:
            sample = copy.deepcopy(self.base); sample['nodes'] = [line]
            self.assertFalse(load.healthy(sample, self.base))
        sample = copy.deepcopy(self.base); sample['generator_disk_free_mib'] = 299
        self.assertFalse(load.healthy(sample, self.base))

    def test_restart_unready_or_replaced_pod_stops(self):
        for field, value in [('ready', False), ('restarts', 1)]:
            sample = copy.deepcopy(self.base); sample['pods']['web'][field] = value
            self.assertFalse(load.healthy(sample, self.base))
        sample = copy.deepcopy(self.base); sample['pods']['other'] = sample['pods'].pop('web')
        self.assertFalse(load.healthy(sample, self.base))
