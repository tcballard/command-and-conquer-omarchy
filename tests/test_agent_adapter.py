import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('adapter', Path(__file__).resolve().parents[1] / 'agent-player/test_adapter.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class AgentAdapterTests(unittest.TestCase):
    def observation(self):
        return dict(own=[], production=[], placements={}, enemies=[], cash=0,
                    request=3, tick=100, explored=[])

    def test_no_resources_or_units_waits(self):
        self.assertEqual(adapter.choose(self.observation()), {'kind': 'wait'})

    def test_deploys_only_owned_mcv(self):
        o = self.observation()
        o['own'] = [dict(id=14, actor='mcv', cell=[18, 73], mobile=True, combat=False)]
        self.assertEqual(adapter.choose(o), dict(kind='deploy', group=[14]))

    def test_never_queues_unaffordable_power(self):
        o = self.observation()
        o['production'] = [dict(queue='Building', items=[], available=[dict(actor='powr', cost=300)])]
        o['cash'] = 299
        self.assertEqual(adapter.choose(o)['kind'], 'wait')
        o['cash'] = 300
        self.assertEqual(adapter.choose(o), dict(kind='produce', actor='powr'))

    def test_reconnection_observation_does_not_duplicate_production(self):
        o = self.observation()
        o['cash'] = 5000
        o['production'] = [dict(queue='Building', items=[dict(actor='powr', done=False)], available=[dict(actor='powr', cost=300)])]
        self.assertEqual(adapter.choose(o)['kind'], 'wait')

    def test_combat_uses_supplied_visible_target_and_owned_combat_units(self):
        o = self.observation()
        o['own'] = [dict(id=1, actor='harv', cell=[18, 73], mobile=True, combat=False),
                    dict(id=2, actor='e1', cell=[20, 73], mobile=True, combat=True)]
        o['enemies'] = [dict(id=90, cell=[21, 73], actor='e1')]
        self.assertEqual(adapter.choose(o), dict(kind='attack', group=[2], target=90))

    def test_exploration_does_not_invent_a_cell(self):
        o = self.observation()
        o['request'] = 8
        o['own'] = [dict(id=i, actor='e1', cell=[18, 73], mobile=True, combat=True) for i in range(6)]
        o['explored'] = [[20, 71], [21, 69]]
        a = adapter.choose(o)
        self.assertEqual(a['kind'], 'defend')
        self.assertIn(a['cell'], o['explored'])
