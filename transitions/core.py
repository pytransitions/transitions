from functools import partial
from collections import defaultdict

def listify(obj):
    return obj if isinstance(obj, list) or obj is None else [obj]


class State(object):

    def __init__(self, name, on_enter=None, on_exit=None):
        self.name = name
        self.on_enter = listify(on_enter) if on_enter else []
        self.on_exit = listify(on_exit) if on_exit else []

    def enter(self, event):
        for oe in self.on_enter: getattr(event.model, oe)()

    def exit(self, event):
        for oe in self.on_exit: getattr(event.model, oe)()

    def add_listener(self, listener, func, *args, **kwargs):
        event_list = getattr(self, 'on_' + listener)
        event_list.append(func)


class Transition(object):

    def __init__(self, source, dest, conditions=None, before=None, after=None):
        self.source = source
        self.dest = dest
        before, after, conditions = (listify(x) for x in [before, after, conditions])
        self.before = [] if before is None else before
        self.after = [] if after is None else after
        self.conditions = [] if conditions is None else conditions

    def execute(self, event):
        machine = event.machine
        for c in self.conditions:
            if not getattr(event.model, c)(): return False

        for trigger in self.before: getattr(event.model, trigger)()
        machine.get_state(self.source).exit(event)
        machine.set_state(self.dest)
        event.update()
        machine.get_state(self.dest).enter(event)
        for trigger in self.after: getattr(event.model, trigger)()
        return True


class Event(object):

    def __init__(self, state, trigger, machine, model, *args, **kwargs):
        self.state = state
        self.trigger = trigger
        self.machine = machine
        self.model = model
        self.args = args
        for k, v in kwargs.items():
            setattr(self, k, v)

    def update(self):
        self.state = self.machine.current_state


class Trigger(object):

    def __init__(self, name, machine):
        self.name = name
        self.machine = machine
        self.transitions = defaultdict(list)

    def add_transition(self, transition):
        source = transition.source
        self.transitions[transition.source].append(transition)

    def trigger(self, *args, **kwargs):
        """ Serially execute all transitions that match the current state, 
        halting as soon as one successfully completes. """
        state_name = self.machine.current_state.name
        if state_name not in self.transitions:
            raise MachineError("Can't trigger event %s from state %s!" % (self.name, state_name))
        event = Event(self.machine.current_state, self, self.machine, self.machine.model, *args, **kwargs)
        for t in self.transitions[state_name]:
            if t.execute(event): return True
        return False


class Machine(object):

    def __init__(self, model=None, states=None, initial=None, transitions=None, send_event=False):
        self.model = self if model is None else model 
        self.states = {}
        self.triggers = {}
        self.current_state = None
        self.send_event = send_event
        
        if states is not None:
            states = listify(states)
            for s in states:
                if isinstance(s, basestring):
                    s = State(s)
                self.states[s.name] = s
                setattr(self.model, 'is_%s' % s.name, partial(self.is_state, s.name))

        self.set_state(initial)

        if transitions is not None:
            for t in transitions: self.add_transition(**t)

    def is_state(self, state):
        return self.current_state.name == state
        
    def get_state(self, state):
        if state not in self.states:
            raise ValueError("State '%s' is not a registered state." % state)
        return self.states[state]

    def set_state(self, state, save=True):
        if isinstance(state, basestring):
            state = self.get_state(state)
        self.current_state = state
        self.model.state = self.current_state.name
    
    def add_transition(self, name, source, dest, conditions=None, before=None, after=None, *args, **kwargs):
        if name not in self.triggers:
            self.triggers[name] = Trigger(name, self)
            setattr(self.model, name, self.triggers[name].trigger)

        if isinstance(source, basestring):
            source = self.states.keys() if source == '*' else [source]

        for s in source:
            t = Transition(s, dest, conditions, before, after)
            self.triggers[name].add_transition(t)

    def __getattr__(self, name):
        terms = name.split('_')
        if terms[0] in ['before', 'after']:
            name = '_'.join(terms[1:])
            if name not in self.triggers:
                raise MachineError('Trigger "%s" is not registered.' % name)
            return getattr(self.triggers[name], 'add_' + terms[0])
            
        elif name.startswith('on_enter') or name.startswith('on_exit'):
            state = self.get_state('_'.join(terms[2:]))
            return partial(state.add_listener, terms[1])


class MachineError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)



