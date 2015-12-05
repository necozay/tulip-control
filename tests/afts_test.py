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
	ts = transys.AFTS()
	ts.sys_actions.add('mode0')
	ts.states.add_from({'s1', 's2'})
	ts.set_progress_map({'mode0' : ('s0', 's1'), 'mode1' : ('s1', 's2')})
