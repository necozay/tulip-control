# Copyright (c) 2013-2014 by California Institute of Technology
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 
# 3. Neither the name of the California Institute of Technology nor
#    the names of its contributors may be used to endorse or promote
#    products derived from this software without specific prior
#    written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL CALTECH
# OR THE CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
# OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
"""
Transition System Module
"""
import logging
from collections import Iterable
from pprint import pformat
import copy
import warnings

from .labeled_graphs import LabeledDiGraph, str2singleton
from .labeled_graphs import prepend_with
from .mathset import PowerSet, MathSet

_hl = 40 *'-'

logger = logging.getLogger(__name__)

class KripkeStructure(LabeledDiGraph):
    """Directed graph with vertex labeling and initial vertices.
    """
    def __init__(self):
        ap_labels = PowerSet()
        node_label_types = [
            {'name':'ap',
             'values':ap_labels,
             'setter':ap_labels.math_set,
             'default':set()}
        ]
        
        super(KripkeStructure, self).__init__(node_label_types)
        
        self.atomic_propositions = self.ap
        
        # dot formatting
        self._state_dot_label_format = {
            'ap':'',
           'type?label':'',
           'separator':'\n'
        }
        
        self.dot_node_shape = {'normal':'rectangle'}

    def __str__(self):
        s = (
            'Kripke Structure: ' + self.name + '\n' +
            _hl + '\n' +
            'Atomic Propositions (APs):\n\t' +
            pformat(self.atomic_propositions, indent=3) + 2*'\n' +
            'States labeled with sets of APs:\n' +
            _dumps_states(self) + 2*'\n' +
            'Initial States:\n' +
            pformat(self.states.initial, indent=3) + 2*'\n' +
            'Actions:\n\t' + str(self.actions) + 2*'\n' +
            'Transitions:\n' +
            pformat(self.transitions(), indent=3) +
            '\n' + _hl + '\n'
        )
        return s

class FiniteTransitionSystem(LabeledDiGraph):
    """Finite Transition System modeling a closed system.
    
    Implements Def. 2.1, p.20 U{[BK08]
    <http://tulip-control.sourceforge.net/doc/bibliography.html#bk08>}:
        - states (instance of L{States}) = S
        - states.initial = S_0 \subseteq S
        - atomic_propositions = AP
        - actions = Act
        - transitions (instance of L{Transitions})::
              the transition relation ->
                = edge set + edge labeling function
                (labels \in actions)
        Unlabeled edges are defined using:
            - sys.transitions.add
            - sys.transitions.add_from
            - sys.transitions.add_adj
        and accessed using:
            - sys.transitions.find
        - the state labeling function::
                L: S-> 2^AP
        can be defined using:
            - sys.states.add
            - sys.states.add_from
        and accessed using methods:
            - sys.states(data=True)
            - sys.states.find
    
    The state labels are subsets of atomic_propositions, so \in 2^AP.
    The transition labels are actions.
    
    sys.actions_must: select constraint on actions. Options:
        
        - 'mutex': at most 1 action True each time
        - 'xor': exactly 1 action True each time
        - 'none': no constraint on action values
    
    The xor constraint can prevent the environment from
    blocking the system by setting all its actions to False.
    
    The action are taken when traversing an edge.
    Each edge is annotated by a single action.
    If an edge (s1, s2) can be taken on two transitions,
    then 2 copies of that same edge are stored.
    Each copy is annotated using a different action,
    the actions must belong to the same action set.
    That action set is defined as a ser instance.
    This description is a (closed) L{FTS}.
    
    The system and environment actions associated with an edge
    of a reactive system. To store these, 2 sub-labels are used
    and their sets are encapsulated within the same L{(open) FTS
    <OpenFiniteTransitionSystem>}.
    
    Example
    =======
    In the following C{None} represents the empty set, subset of AP.
    First create an empty transition system and add some states to it:
    
    >>> from tulip import transys as trs
    >>> ts = trs.FiniteTransitionSystem()
    >>> ts.states.add('s0')
    >>> ts.states.add_from(['s1', 's3', 'end', 5] )
    
    Set an initial state, which must already be in states:
    
    >>> ts.states.initial.add('s0')
    
    There can be more than one possible initial states:
    
    >>> ts.states.initial.add_from(['s0', 's3'] )
    
    To label the states, we need at least one atomic proposition,
    here 'p':
    
    >>> ts.atomic_propositions |= ['p', None]
    >>> ts.states.add('s0', ap={'p'})
    >>> ts.states.add_from([('s1', {'ap':{'p'} }),
                            ('s3', {'ap':{} } )])
    
    If a state has already been added, its label of atomic
    propositions can be defined directly:
    
    >>> ts.states['s0']['ap'] = {'p'}
    
    Having added states, we can also add some labeled transitions:
    
    >>> ts.actions |= ['think', 'write']
    >>> ts.transitions.add('s0', 's1', actions='think')
    >>> ts.transitions.add('s1', 5, actions='write')
    
    Note that an unlabeled transition:
    
    >>> ts.transitions.add('s0', 's3')
    
    is considered as different from a labeled one and to avoid
    unintended duplication, after adding an unlabeled transition,
    any attempt to add a labeled transition between the same states
    will raise an exception, unless the unlabeled transition is
    removed before adding the labeled transition.
    
    Using L{tuple2fts} offers a more convenient constructor
    for transition systems.
    
    The user can still invoke NetworkX functions to set custom node
    and edge labels, in addition to the above ones.
    For example:
    
    >>> ts.states.add('s0')
    >>> ts.node['s0']['my_cost'] = 5
    
    The difference is that atomic proposition and action labels
    are checked to make sure they are elements of the system's
    AP and Action sets.
    
    It is not advisable to use NetworkX C{add_node} and C{add_edge}
    directly, because that can result in an inconsistent system,
    since it skips all checks performed by transys.
    
    dot Export
    ==========
    Format transition labels using _transition_dot_label_format
    which is a dict with values:
        - 'actions' (=name of transitions attribute):
            type before separator
        - 'type?label': separator between label type and value
        - 'separator': between labels for different sets of actions
            (e.g. sys, env). Not used for closed FTS,
            because it has single set of actions.
    
    Note
    ====
    The attributes atomic_propositions and aps are equal.
    When you want to produce readable code, use atomic_propositions.
    Otherwise, aps offers shorthand access to the APs.
    
    See Also
    ========
    L{OpenFTS}, L{tuple2fts}, L{line_labeled_with}, L{cycle_labeled_with}
    """
    def __init__(self):
        """Initialize Finite Transition System.
        
        For arguments, see L{LabeledDiGraph}
        """
        ap_labels = PowerSet()
        node_label_types = [
            {'name':'ap',
             'values':ap_labels,
             'setter':ap_labels.math_set,
             'default':set()}
        ]
        edge_label_types = [
            {'name':'actions',
             'values':MathSet(),
             'setter':True}
        ]
        
        super(FiniteTransitionSystem, self).__init__(
            node_label_types, edge_label_types
        )
        
        self.atomic_propositions = self.ap
        self.aps = self.atomic_propositions # shortcut
        self.actions_must = 'xor'
        
        # dot formatting
        self._state_dot_label_format = {
            'ap':'',
           'type?label':'',
           'separator':'\n'
        }
        self._transition_dot_label_format = {
            'actions':'',
            'type?label':'',
            'separator':'\n'
        }
        self._transition_dot_mask = dict()
        self.dot_node_shape = {'normal':'rectangle'}
        self.default_export_fname = 'fts'

    def __str__(self):
        s = (
            _hl + '\nFinite Transition System (closed) : ' +
            self.name + '\n' + _hl + '\n' +
            'Atomic Propositions:\n\t' +
            pformat(self.atomic_propositions, indent=3) + 2*'\n' +
            'States and State Labels (\in 2^AP):\n' +
            _dumps_states(self) + 2*'\n' +
            'Initial States:\n' +
            pformat(self.states.initial, indent=3) + 2*'\n' +
            'Actions:\n\t' +str(self.actions) + 2*'\n' +
            'Transitions & Labels:\n' +
            pformat(self.transitions(data=True), indent=3) +
            '\n' + _hl + '\n'
        )
        return s
    
    def _save(self, path, fileformat):
        """Export options available only for FTS systems.
        
        Provides: pml (Promela)
        
        See Also
        ========
        L{save}, L{plot}
        """
        if fileformat not in {'promela', 'Promela', 'pml'}:
            return False
        
        from .export import graph2promela
        s = graph2promela.fts2promela(self, self.name)
        
        # dump to file
        f = open(path, 'w')
        f.write(s)
        f.close()
        return True

class FTS(FiniteTransitionSystem):
    """Alias to L{FiniteTransitionSystem}.
    """    
    def __init__(self, *args, **kwargs):
        FiniteTransitionSystem.__init__(self, *args, **kwargs)

class OpenFiniteTransitionSystem(LabeledDiGraph):
    """Open Finite Transition System modeling an open system.
    
    Analogous to L{FTS}, but for open systems comprised of
    the system and its environment.
    
    Please refer to L{FiniteTransitionSystem} for usage details.
    
    The only significant difference is in transition labeling.
    For closed systems, each transition is labeled with a system action.
    So each transition label comprises of a single sublabel,
    the system action.
    
    For open systems, each transition is labeled with 2 sublabels:
        - The first sublabel is a system action,
        - the second an environment action.
    
    Constraints on actions can be defined
    similarly to L{FTS} actions by setting the fields:
    
        - ofts.env_actions_must
        - ofts.sys_actions_must
    
    The default constraint is 'xor'.
    For more details see L{FTS}.
    
    See Also
    ========
    L{FiniteTransitionSystem}
    """
    def __init__(self, env_actions=None, sys_actions=None):
        """Initialize Open Finite Transition System.

        @param env_actions: environment (uncontrolled) actions,
            defined as C{edge_label_types} in L{LabeledDiGraph.__init__}

        @param sys_actions: system (controlled) actions, defined as
            C{edge_label_types} in L{LabeledDiGraph.__init__}
        """
        if env_actions is None:
            env_actions = [
                {'name':'env_actions',
                 'values':MathSet(),
                 'setter':True}
            ]
        
        if sys_actions is None:
            sys_actions = [
                {'name':'sys_actions',
                 'values':MathSet(),
                 'setter':True}
            ]
        
        ap_labels = PowerSet()
        action_types = env_actions + sys_actions
        
        node_label_types = [
            {'name':'ap',
             'values':ap_labels,
             'setter':ap_labels.math_set,
             'default':set()}
        ]
        edge_label_types = action_types
        
        LabeledDiGraph.__init__(self, node_label_types, edge_label_types)
        
        # make them available also via an "actions" dicts
        # name, codomain, *rest = x
        actions = {x['name']:x['values'] for x in edge_label_types}
        
        if 'actions' in actions:
            msg = '"actions" cannot be used as an action type name,\n'
            msg += 'because if an attribute for this action type'
            msg += 'is requested,\n then it will conflict with '
            msg += 'the dict storing all action types.'
            raise ValueError(msg)
                
        self.actions = actions
        self.atomic_propositions = self.ap
        self.aps = self.atomic_propositions
        
        # action constraint used in synth.synthesize
        self.env_actions_must = 'xor'
        self.sys_actions_must = 'xor'
        
        # dot formatting
        self._state_dot_label_format = {
            'ap':'',
           'type?label':'',
           'separator':'\n'
        }
        self._transition_dot_label_format = {
            'sys_actions':'sys',
            'env_actions':'env',
            'type?label':':',
            'separator':'\n'
        }
        
        self._transition_dot_mask = dict()
        self.dot_node_shape = {'normal':'box'}
        self.default_export_fname = 'ofts'
    
    def __str__(self):
        s = (
            _hl +'\nFinite Transition System (open) : ' +
            self.name + '\n' + _hl + '\n' +
            'Atomic Propositions:\n' +
            pformat(self.atomic_propositions, indent=3) + 2*'\n' +
            'States & State Labels (\in 2^AP):\n' +
            _dumps_states(self) + 2*'\n' +
            'Initial States:\n' +
            pformat(self.states.initial, indent=3) + 2*'\n'
        )
        
        for action_type, codomain in self.actions.iteritems():
            if 'sys' in action_type:
                s += 'System Action Type: ' + str(action_type) +\
                     ', with possible values: ' + str(codomain) + '\n'
                s += pformat(codomain, indent=3) +2*'\n'
            elif 'env' in action_type:
                s += 'Environment Action Type: ' + str(action_type) +\
                     ', with possible values:\n\t' + str(codomain) + '\n'
                s += pformat(codomain, indent=3) +2*'\n'
            else:
                s += 'Action type controlled by neither env nor sys\n' +\
                     ' (will cause you errors later)' +\
                     ', with possible values:\n\t'
                s += pformat(codomain, indent=3) +2*'\n'
        
        s += (
            'Transitions & Labeling w/ Sys, Env Actions:\n' +
            pformat(self.transitions(data=True), indent=3) +
            '\n' + _hl + '\n'
        )
        
        return s

def tuple2fts(S, S0, AP, L, Act, trans, name='fts',
              prepend_str=None):
    """Create a Finite Transition System from a tuple of fields.

    Hint
    ====
    To remember the arg order:

    1) it starts with states (S0 requires S before it is defined)

    2) continues with the pair (AP, L), because states are more
    fundamental than transitions
    (transitions require states to be defined)
    and because the state labeling L requires AP to be defined.

    3) ends with the pair (Act, trans), because transitions in trans
    require actions in Act to be defined.

    See Also
    ========
    L{tuple2ba}

    @param S: set of states
    @type S: iterable of hashables
    
    @param S0: set of initial states, must be \\subset S
    @type S0: iterable of elements from S
    
    @param AP: set of Atomic Propositions for state labeling:
            L: S-> 2^AP
    @type AP: iterable of hashables
    
    @param L: state labeling definition
    @type L: iterable of (state, AP_label) pairs:
        [(state0, {'p'} ), ...]
        | None, to skip state labeling.
    
    @param Act: set of Actions for edge labeling:
            R: E-> Act
    @type Act: iterable of hashables
    
    @param trans: transition relation
    @type trans: list of triples: [(from_state, to_state, act), ...]
        where act \\in Act
    
    @param name: used for file export
    @type name: str
    """
    def pair_labels_with_states(states, state_labeling):
        if state_labeling is None:
            return
        
        if not isinstance(state_labeling, Iterable):
            raise TypeError('State labeling function: L->2^AP must be '
                            'defined using an Iterable.')
        
        state_label_pairs = True
        
        # cannot be caught by try below
        if isinstance(state_labeling[0], str):
            state_label_pairs = False
        
        if state_labeling[0] is None:
            state_label_pairs = False
        
        try:
            (state, ap_label) = state_labeling[0]
        except:
            state_label_pairs = False
        
        if state_label_pairs:
            return state_labeling
        
        logger.debug('State labeling L not tuples (state, ap_label),\n'
                   'zipping with states S...\n')
        state_labeling = zip(states, state_labeling)
        return state_labeling
    
    # args
    if not isinstance(S, Iterable):
        raise TypeError('States S must be iterable, even for single state.')
    
    # convention
    if not isinstance(S0, Iterable) or isinstance(S0, str):
        S0 = [S0]
    
    # comprehensive names
    states = S
    initial_states = S0
    ap = AP
    state_labeling = pair_labels_with_states(states, L)
    actions = Act
    transitions = trans
    
    # prepending states with given str
    if prepend_str:
        logger.debug('Given string:\n\t' +str(prepend_str) +'\n' +
               'will be prepended to all states.')
    states = prepend_with(states, prepend_str)
    initial_states = prepend_with(initial_states, prepend_str)
    
    ts = FTS(name=name)
    
    ts.states.add_from(states)
    ts.states.initial |= initial_states
    
    ts.atomic_propositions |= ap
    
    # note: verbosity before actions below
    # to avoid screening by possible error caused by action
    
    # state labeling assigned ?
    if state_labeling is not None:
        for (state, ap_label) in state_labeling:
            if ap_label is None:
                ap_label = set()
            
            ap_label = str2singleton(ap_label)
            state = prepend_str + str(state)
            
            logger.debug('Labeling state:\n\t' +str(state) +'\n' +
                  'with label:\n\t' +str(ap_label) +'\n')
            ts.states[state]['ap'] = ap_label
    
    # any transition labeling ?
    if actions is None:
        for (from_state, to_state) in transitions:
            (from_state, to_state) = prepend_with([from_state, to_state],
                                                  prepend_str)
            logger.debug('Added unlabeled edge:\n\t' +str(from_state) +
                   '--->' +str(to_state) +'\n')
            ts.transitions.add(from_state, to_state)
    else:
        ts.actions |= actions
        for (from_state, to_state, act) in transitions:
            (from_state, to_state) = prepend_with([from_state, to_state],
                                                  prepend_str)
            logger.debug('Added labeled edge (=transition):\n\t' +
                   str(from_state) +'---[' +str(act) +']--->' +
                   str(to_state) +'\n')
            ts.transitions.add(from_state, to_state, actions=act)
    
    return ts

def line_labeled_with(L, m=0):
    """Return linear FTS with given labeling.
    
    The resulting system will be a terminating sequence::
        s0-> s1-> ... -> sN
    where: N = C{len(L) -1}.
    
    See Also
    ========
    L{cycle_labeled_with}
    
    @param L: state labeling
    @type L: iterable of state labels, e.g.,::
            [{'p', '!p', 'q',...]
    Single strings are identified with singleton Atomic Propositions,
    so [..., 'p',...] and [...,{'p'},...] are equivalent.
    
    @param m: starting index
    @type m: int
    
    @return: L{FTS} with:
        - states ['s0', ..., 'sN'], where N = len(L) -1
        - state labels defined by L, so s0 is labeled with L[0], etc.
        - transitions forming a sequence:
            - s_{i} ---> s_{i+1}, for: 0 <= i < N
    """
    n = len(L)
    S = range(m, m+n)
    S0 = [] # user will define them
    AP = {True}
    for ap_subset in L:
        # skip empty label ?
        if ap_subset is None:
            continue
        AP |= set(ap_subset)
    Act = None
    from_states = range(m, m+n-1)
    to_states = range(m+1, m+n)
    trans = zip(from_states, to_states)
    
    ts = tuple2fts(S, S0, AP, L, Act, trans, prepend_str='s')
    return ts

def cycle_labeled_with(L):
    """Return cycle FTS with given labeling.
    
    The resulting system will be a cycle::
        s0-> s1-> ... -> sN -> s0
    where: N = C{len(L) -1}.
    
    See Also
    ========
    L{line_labeled_with}
    
    @param L: state labeling
    @type L: iterable of state labels, e.g., [{'p', 'q'}, ...]
        Single strings are identified with singleton Atomic Propositions,
        so [..., 'p',...] and [...,{'p'},...] are equivalent.
    
    @return: L{FTS} with:
        - states ['s0', ..., 'sN'], where N = len(L) -1
        - state labels defined by L, so s0 is labeled with L[0], etc.
        - transitions forming a cycle:
            - s_{i} ---> s_{i+1}, for: 0 <= i < N
            - s_N ---> s_0
    """
    ts = line_labeled_with(L)
    last_state = 's' +str(len(L)-1)
    ts.transitions.add(last_state, 's0')
    
    #trans += [(n-1, 0)] # close cycle
    return ts

def add_initial_states(ts, ap_labels):
    """Make initial any state of ts labeled with any label in ap_labels.
    
    For example if isinstance(ofts, OpenFTS):
    
    >>> from tulip.transys.transys import add_initial_states
    >>> initial_labels = [{'home'}]
    >>> add_initial_states(ofts, initial_labels)
    
    @type ts: L{transys.FiniteTransitionSystem},
        L{transys.OpenFiniteTransitionSystem}
    
    @param ap_labels: labels, each comprised of atomic propositions
    @type ap_labels: iterable of sets of elements from
        ts.atomic_propositions
    """
    for label in ap_labels:
        new_init_states = ts.states.find(ap='label')
        ts.states.initial |= new_init_states

def _dumps_states(g):
    """Dump string of transition system states.
    
    @type g: L{FTS} or L{OpenFTS}
    """
    s = ''
    for state in g:
        s += '\t State: ' + str(state)
        s += ', AP: ' + str(g.states[state]['ap']) + '\n'
        
        # more labels than only AP ?
        if len(g.states[state]) == 1:
            continue
        
        s += ', '.join([
            str(k) + ': ' + str(v)
            for k,v in g.states[state]
            if k is not 'ap'
        ])
    return s

class GameGraph(LabeledDiGraph):
    """Store a game graph.
    
    When adding states, you have to say
    which player controls the outgoing transitions.
    Use C{networkx} state labels for that:
    
    >>> g = GameGraph()
    >>> g.states.add('s0', player=0)
    
    See also
    ========
    L{automata.ParityGame}
    
    Reference
    =========
    Chatterjee K.; Henzinger T.A.; Jobstmann B.
        Environment Assumptions for Synthesis
        CONCUR'08, LNCS 5201, pp. 147-161, 2008
    """
    def __init__(self, node_label_types, edge_label_types):
        node_label_types += [
            {
                'name':'player',
                'values':{0, 1},
                'default':0
            }
        ]
        
        super(GameGraph, self).__init__(node_label_types,
                                        edge_label_types)
        
    def player_states(self, n):
        """Return states controlled by player C{n}.
        
        'controlled' means that player C{n}
        gets to decide the successor state.
        
        @param n: player index (id number)
        @type n: 0 or 1
        
        @return: set of states
        @rtype: C{set}
        """
        return {x for x in self if self.node[x]['player'] == n}
    
    def edge_controlled_by(self, e):
        """Return the index of the player controlling edge C{e}.
        
        @type e: 2-tuple of nodes C{(n1, n2)}
        
        @rtype: integer 0 or 1
        """
        from_state = e[0]
        return self.node[from_state]['player']

def LabeledGameGraph(GameGraph):
    """Game graph with labeled states.
    
    Its contraction is a Kripke structure.
    Given a Kripke structure and a partition of propositions,
    then the corresponding labeled game graph
    can be obtained by graph expansion.
    
    Reference
    =========
    Chatterjee K.; Henzinger T.A.; Piterman N.
        Strategy Logic
        UCB/EECS-2007-78
    """
    def __init__(self):
        ap_labels = PowerSet()
        node_label_types = [
            {'name':'ap',
             'values':ap_labels,
             'setter':ap_labels.math_set,
             'default':set()}
        ]
        
        super(LabeledGameGraph, self).__init__(node_label_types)
        
        self.atomic_propositions = self.ap
        
        # dot formatting
        self._state_dot_label_format = {
            'ap':'',
           'type?label':'',
           'separator':'\n'
        }
        
        self.dot_node_shape = {'normal':'rectangle'}
