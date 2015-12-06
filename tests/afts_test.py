#!/usr/bin/env python
"""Tests for Augmented FTS synthesis."""

from tulip import spec, synth, transys
from nose.tools import raises

import logging
logging.basicConfig(level=logging.ERROR)
logging.getLogger('ltl_parser_log').setLevel(logging.WARNING)

class AFTS_test:

	def setUp(self):
		env_sws = transys.AFTS()
		env_sws.owner = 'env'

		env_sws.sys_actions.add('mode0')
		env_sws.sys_actions.add('mode1')

		env_sws.atomic_propositions.add_from(['loop','exit'])

		env_sws.states.add('s0', ap={'loop'})
		env_sws.states.add('s1', ap={'loop'})
		env_sws.states.add('s2', ap={'loop'})
		env_sws.states.add('s3', ap={'loop'})
		env_sws.states.add('s4', ap={'exit'})

		env_sws.states.initial.add('s0')

		env_sws.transitions.add('s0', 's1', sys_actions='mode0')
		env_sws.transitions.add('s1', 's2', sys_actions='mode0')
		env_sws.transitions.add('s2', 's3', sys_actions='mode0')
		env_sws.transitions.add('s3', 's0', sys_actions='mode0')
		env_sws.transitions.add('s3', 's4', sys_actions='mode0')
		env_sws.transitions.add('s4', 's3', sys_actions='mode0')

		env_sws.transitions.add('s0', 's0', sys_actions='mode1')
		env_sws.transitions.add('s1', 's1', sys_actions='mode1')
		env_sws.transitions.add('s2', 's2', sys_actions='mode1')
		env_sws.transitions.add('s3', 's3', sys_actions='mode1')
		env_sws.transitions.add('s4', 's4', sys_actions='mode1')

		self.env_sws = env_sws

	def tearDown(self):
		self.env_sws = None

	def test_with_pg(self):
		self.env_sws.set_progress_map({'mode0' : ('s0', 's1', 's2', 's3'),
									   'mode1' : ('s0',)
									  })
		# self.env_sws.set_progress_map({'mode0' : ('s0', 's1', 's2', 's3')})
		# eventually reach s4
		sys_prog = {'exit'}
		specs = spec.GRSpec(set(), set(), set(), set(),
                    set(), set(), set(), sys_prog)
		ctrl = synth.synthesize('gr1c', specs, env=self.env_sws, ignore_env_init=True)
		assert ctrl != None

	def test_without_pg(self):
		self.env_sws.set_progress_map({'mode0' : ('s0', 's1', 's2'),
									   'mode1' : ('s0',)
									 })

		# self.env_sws.set_progress_map({'mode0' : ('s0', 's1', 's2')})

		# eventually reach s4
		sys_prog = {'exit'}
		specs = spec.GRSpec(set(), set(), set(), set(),
                    set(), set(), set(), sys_prog)
		ctrl = synth.synthesize('gr1c', specs, env=self.env_sws, ignore_env_init=True)
		assert ctrl != None

@raises(Exception)
def test_wrongmode():
	"""Add progress group with action that is not in AFTS"""
	ts = transys.AFTS()
	ts.sys_actions.add('mode0')
	ts.states.add_from({'s1', 's2'})
	ts.set_progress_map({'mode0' : ('s0', 's1'), 'mode1' : ('s1', 's2')})

def test_nopg():
	"""PG for one mode but not the other"""
	ts = transys.AFTS()
	ts.owner = 'env'
	ts.sys_actions.add('mode0')
	ts.sys_actions.add('mode1')

	ts.states.add_from({'s0', 's1', 's2'})

	ts.transitions.add('s0', 's1', sys_actions='mode0')
	ts.transitions.add('s1', 's0', sys_actions='mode0')
	ts.transitions.add('s1', 's2', sys_actions='mode0')
	ts.transitions.add('s2', 's2', sys_actions='mode0')

	ts.set_progress_map({'mode0' : ('s0', 's1')})

	specs = spec.GRSpec(set(), set(), set(), set(),
                    set(), set(), set(), {'eloc = "s1"', 'eloc = "s2"'})
	ctrl = synth.synthesize('gr1c', specs, env=ts, ignore_env_init=True)
	assert ctrl != None

def test_singleton():
	"""AFTS with one mode and one state"""
	ts = transys.AFTS()
	ts.owner = 'env'
	ts.sys_actions.add('mode0')
	ts.states.add('s0')
	ts.transitions.add('s0', 's0', sys_actions='mode0')
	specs = spec.GRSpec(set(), set(), set(), set(),
                    set(), set(), set(), set())
	ctrl = synth.synthesize('gr1c', specs, env=ts, ignore_env_init=True)
	assert ctrl != None

def test_multi_pg():
	"""Multiple progress groups for same mode"""
	ts = transys.AFTS()
	ts.owner = 'env'
	ts.sys_actions.add('mode0')
	ts.sys_actions.add('mode1')

	ts.atomic_propositions.add_from(['goal'])

	ts.states.add('s0')
	ts.states.add('s1', ap = {'goal'})
	ts.states.add('s2')

	ts.transitions.add('s0', 's0', sys_actions='mode0')
	ts.transitions.add('s0', 's1', sys_actions='mode0')
	ts.transitions.add('s2', 's1', sys_actions='mode0')
	ts.transitions.add('s2', 's2', sys_actions='mode0')

	ts.transitions.add('s1', 's2', sys_actions='mode1')
	ts.transitions.add('s1', 's0', sys_actions='mode1')

	ts.set_progress_map({'mode0' : [set(['s0']), set(['s1'])] })

	specs = spec.GRSpec(set(), set(), set(), set(),
                    set(), set(), set(), 'goal')

	ctrl = synth.synthesize('gr1c', specs, env=ts, ignore_env_init=True)
	assert ctrl != None

def test_env_act():
	"""Progress group with environment actions"""
	ts = transys.AFTS()
	ts.owner = 'env'
	ts.sys_actions.add('sys_m0')
	ts.sys_actions.add('sys_m1')
	ts.env_actions.add('env_m0')
	ts.env_actions.add('env_m1')

	ts.states.add('s0')
	ts.states.add('s1')

	ts.transitions.add('s0', 's1', sys_actions='sys_m0', env_actions = 'env_m0')
	ts.transitions.add('s0', 's1', sys_actions='sys_m0', env_actions = 'env_m1')
	ts.transitions.add('s0', 's1', sys_actions='sys_m1', env_actions = 'env_m0')
	ts.transitions.add('s0', 's1', sys_actions='sys_m1', env_actions = 'env_m1')
	ts.transitions.add('s1', 's1', sys_actions='sys_m0', env_actions = 'env_m1')
	ts.transitions.add('s1', 's1', sys_actions='sys_m1', env_actions = 'env_m0')
	ts.transitions.add('s1', 's1', sys_actions='sys_m1', env_actions = 'env_m1')
	ts.transitions.add('s1', 's0', sys_actions='sys_m0', env_actions = 'env_m0')

	ts.set_progress_map({('env_m0', 'sys_m0') : ( 's1', ) })

	specs = spec.GRSpec(set(), set(), set(), set(),
                    set(), set(), set(), 'eloc = "s0"')

	ctrl = synth.synthesize('gr1c', specs, env=ts, ignore_env_init=True)
	assert ctrl != None


