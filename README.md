# transitions

A lightweight, object-oriented state machine implementation in Python.

## Status
* [![Build Status](https://travis-ci.org/tyarkoni/transitions.png?branch=master)](https://travis-ci.org/tyarkoni/transitions)
* [![Coverage Status](https://coveralls.io/repos/tyarkoni/transitions/badge.svg?branch=master&service=github)](https://coveralls.io/github/tyarkoni/transitions?branch=master)

## Installation

    pip install transitions

...or clone the repo from GitHub and then:

    python setup.py install


## Table of Contents
- [Quickstart](#quickstart)
- [Non-Quickstart](#the-non-quickstart)
    - [Basic initialization](#basic-initialization)
    - [States](#states)
        - [Callbacks](#state-callbacks)
        - [Checking state](#checking-state)
    - [Transitions](#transitions)
        - [Automatic transitions](#automatic-transitions-for-all-states)
        - [Transitioning from multiple states](#transitioning-from-multiple-states)
        - [Ordered transitions](#ordered-transitions)
        - [Conditional transitions](#conditional-transitions)
        - [Callbacks](#transition-callbacks)
    - [Passing data](#passing-data)
    - [Diagrams](#diagrams)
    - [Alternative initialization patterns](#alternative-initialization-patterns)
    - [Logging](#logging)
    - Extensions
        - [Hierarchical State Machine](#hsm)
        - [Threading](#threading)
    - [Bug reports etc.](#bug-reports)


## Quickstart

They say [a good example is worth](https://www.google.com/webhp?ie=UTF-8#q=%22a+good+example+is+worth%22&start=20) 100 pages of API documentation, a million directives, or a thousand words. 

Well, "they" probably lie...but here's an example anyway:

```python
from transitions import Machine
import random

class NarcolepticSuperhero(object):

    # Define some states. Most of the time, narcoleptic superheroes are just like
    # everyone else. Except for...
    states = ['asleep', 'hanging out', 'hungry', 'sweaty', 'saving the world']

    def __init__(self, name):
    
        # No anonymous superheroes on my watch! Every narcoleptic superhero gets 
        # a name. Any name at all. SleepyMan. SlumberGirl. You get the idea.
        self.name = name

        # What have we accomplished today?
        self.kittens_rescued = 0
        
        # Initialize the state machine
        self.machine = Machine(model=self, states=NarcolepticSuperhero.states, initial='asleep')
        
        # add some transitions. We could also define these using a static list of 
        # dictionaries, as we did with states above, and then pass the list to 
        # the Machine initializer as the transitions= argument.
        
        # At some point, every superhero must rise and shine.
        self.machine.add_transition('wake_up', 'asleep', 'hanging out')
        
        # Superheroes need to keep in shape.
        self.machine.add_transition(trigger='work_out', source='hanging out', dest='hungry')
        
        # Those calories won't replenish themselves!
        self.machine.add_transition('eat', 'hungry', 'hanging out')

        # Superheroes are always on call. ALWAYS. But they're not always 
        # dressed in work-appropriate clothing.
        self.machine.add_transition('distress_call', '*', 'saving the world', 
                         before='change_into_super_secret_costume')
        
        # When they get off work, they're all sweaty and disgusting. But before
        # they do anything else, they have to meticulously log their latest 
        # escapades. Because the legal department says so.
        self.machine.add_transition('complete_mission', 'saving the world', 'sweaty', 
                         after='update_journal')
        
        # Sweat is a disorder that can be remedied with water.
        # Unless you've had a particularly long day, in which case... bed time!
        self.machine.add_transition('clean_up', 'sweaty', 'asleep', conditions=['is_exhausted'])
        self.machine.add_transition('clean_up', 'sweaty', 'hanging out')
        
        # Our NarcolepticSuperhero can fall asleep at pretty much any time.
        self.machine.add_transition('nap', '*', 'asleep')

    def update_journal(self):
        """ Dear Diary, today I saved Mr. Whiskers. Again. """
        self.kittens_rescued += 1
        
    def is_exhausted(self):
        """ Basically a coin toss. """
        return random.random() < 0.5

    def change_into_super_secret_costume(self):
        print("Beauty, eh?")
```

There, now you've baked a state machine into `NarcolepticSuperhero`. Let's take him/her/it out for a spin...

```python
>>> batman = NarcolepticSuperhero("Batman")
>>> batman.state
'asleep'

>>> batman.wake_up()
>>> batman.state
'hanging out'

>>> batman.nap()
>>> batman.state
'asleep'

>>> batman.clean_up()
MachineError: "Can't trigger event clean_up from state asleep!"

>>> batman.wake_up()
>>> batman.work_out()
>>> batman.state
'hungry'

# Batman still hasn't done anything useful...
>>> batman.kittens_rescued
0

# We now take you live to the scene of a horrific kitten entreement...
>>> batman.distress_call()
'Beauty, eh?'
>>> batman.state
'saving the world'

# Back to the crib. 
>>> batman.complete_mission()
>>> batman.state
'sweaty'

>>> batman.clean_up()
>>> batman.state
'asleep'   # Too tired to shower!

# Another productive day, Alfred.
>>> batman.kittens_rescued
1
```

## The non-quickstart

### Basic initialization

Getting a state machine up and running is pretty simple. Let's say you have the object `lump` (an instance of class `Matter`), and you want to manage its states:

```python
class Matter(object):
    pass
    
lump = Matter()
```

You can initialize a (_minimal_) working state machine bound to `lump` like this:

```python
from transitions import Machine
machine = Machine(model=lump, states=['solid', 'liquid', 'gas', 'plasma'], initial='solid')

# Lump now has state!
lump.state
>>> 'solid'
```

I say “minimal”, because while this state machine is technically operational, it doesn't actually _do_ anything. It starts in the `'solid'` state, but won't ever move into another state, because no transitions are defined...yet!

Let's try again.

```python
# The states
states=['solid', 'liquid', 'gas', 'plasma']

# And some transitions between states. We're lazy, so we'll leave out 
# the inverse phase transitions (freezing, condensation, etc.).
transitions = [
    { 'trigger': 'melt', 'source': 'solid', 'dest': 'liquid' },
    { 'trigger': 'evaporate', 'source': 'liquid', 'dest': 'gas' },
    { 'trigger': 'sublimate', 'source': 'solid', 'dest': 'gas' },
    { 'trigger': 'ionize', 'source': 'gas', 'dest': 'plasma' }
]

# Initialize
machine = Machine(lump, states=states, transitions=transitions, initial='liquid')

# Now lump maintains state...
lump.state
>>> 'liquid'

# And that state can change...
lump.evaporate()
lump.state
>>> 'gas'
lump.ionize()
lump.state
>>> 'plasma'
```

Notice the shiny new methods attached to the `Matter` instance (`evaporate()`, `ionize()`, etc.). Each method triggers the corresponding transition. You don't have to explicitly define these methods anywhere; the name of each transition is bound to the model passed to the `Machine` initializer (in this case, `lump`).

### States

The soul of any good state machine (and of many bad ones, no doubt) is a set of states. Above, we defined the valid model states by passing a list of strings to the `Machine` initializer. But internally, states are actually represented as `State` objects. 

You can initialize and modify States in a number of ways. Specifically, you can: 

- pass a string to the `Machine` initializer giving the name(s) of the state(s), or
- directly initialize each new `State` object, or 
- pass a dictionary with initialization arguments

The following snippets illustrate several ways to achieve the same goal:

```python
# Create a list of 3 states to pass to the Machine
# initializer. We can mix types; in this case, we 
# pass one State, one string, and one dict.
states = [
    State(name='solid'),
    'liquid',
    { 'name': 'gas'}
    ]
machine = Machine(lump, states)

# This alternative example illustrates more explicit 
# addition of states and state callbacks, but the net
# result is identical to the above.
machine = Machine(lump)
solid = State('solid')
liquid = State('liquid')
gas = State('gas')
machine.add_states([solid, liquid, gas])

```

#### <a name="state-callbacks"></a>Callbacks
A `State` can also be associated with a list of `enter` and `exit` callbacks, which are called whenever the state machine enters or leaves that state. You can specify callbacks during initialization, or add them later. 

For convenience, whenever a new `State` is added to a `Machine`, the methods `on_enter_«state name»` and `on_exit_«state name»` are dynamically created.

```python
# Our old Matter class, now with  a couple of new methods we 
# can trigger when entering or exit states.
class Matter(object):
    def say_hello(self): print("hello, new state!")
    def say_goodbye(self): print("goodbye, old state!")
    
lump = Matter()

# Same states as above, but now we give StateA an exit callback
states = [
    State(name='solid', on_exit=['say_goodbye']),
    'liquid',
    { 'name': 'gas' }
    ]
    
machine = Machine(lump, states=states)
machine.add_transition('sublimate', 'solid', 'gas')
    
# Callbacks can also be added after initialization using 
# the dynamically added on_enter_ and on_exist_ methods.
lump.on_enter_StateC('say_hello')

# Test out the callbacks...
machine.set_state('solid')
lump.sublimate()
>>> 'goodbye, old state!'
>>> 'hello, new state!'
```

In addition to passing in callbacks when initializing a `State`, or adding them dynamically, it's also possible to define callbacks in the model class itself, which may increase code clarity. For example:

```python
class Matter(object):
    def say_hello(self): print("hello, new state!")
    def say_goodbye(self): print("goodbye, old state!")
    def on_enter_A(self): print("We've just entered state A!")
    
lump = Matter()
machine = Machine(lump, states=['A', 'B', 'C'])
```

Now, any time `lump` transitions to state `A`, the `on_enter_A()` method defined in the `Matter` class will fire.

#### Checking state
You can always check the current state of the model by either:

- inspecting the `.state` attribute, or
- calling `is_«state name»()`

And if you want to retrieve the actual `State` object for the current state, you can do that through the `Machine` instance's `get_state()` method.

```python
lump.state
>>> 'solid'
lump.is_gas()
>>> False
lump.is_solid()
>>> True
machine.get_state().name
>>> 'solid'
```

### Transitions
Some of the above examples already illustrate the use of transitions in passing, but here we'll explore them in more detail. 

As with states, each transition is represented internally as its own object--an instance of class `Transition`. The quickest way to initialize a set of transitions is to pass a dictionary, or list of dictionaries, to the `Machine` initializer. We already saw this above:

```python
transitions = [
    { 'trigger': 'melt', 'source': 'solid', 'dest': 'liquid' },
    { 'trigger': 'evaporate', 'source': 'liquid', 'dest': 'gas' },
    { 'trigger': 'sublimate', 'source': 'solid', 'dest': 'gas' },
    { 'trigger': 'ionize', 'source': 'gas', 'dest': 'plasma' }
]
machine = Machine(model=Matter(), states=states, transitions=transitions)
```

Defining transitions in dictionaries has the benefit of clarity, but can be cumbersome. If you're after brevity, you might choose to define transitions using lists. Just make sure that the elements in each list are in the same order as the positional arguments in the `Transition` initialization (i.e., `trigger`, `source`, `destination`, etc.). 

The following list-of-lists is functionally equivalent to the list-of-dictionaries above:

```python
transitions = [
    ['melt', 'solid', 'liquid'],
    ['evaporate', 'liquid', 'gas'],
    ['sublimate', 'solid', 'gas'],
    ['ionize', 'gas', 'plasma']
]
```

Alternatively, you can add transitions to a `Machine` after initialization:

```python
machine = Machine(model=lump, states=states, initial='solid')
machine.add_transition('melt', source='solid', dest='liquid')
```

The `trigger` argument defines the name of the new triggering method that gets attached to the base model. When this method is called, it will try to execute the transition:

```python
>>> lump.melt()
>>> lump.state
'liquid'
```

By default, calling an invalid trigger will raise an exception:

```python
>>> lump.to_gas()
>>> # This won't work because only objects in a solid state can melt
>>> lump.melt()
transitions.core.MachineError: "Can't trigger event melt from state gas!"
```

This behavior is generally desirable, since it helps alert you to problems in your code. But in some cases, you might want to silently ignore invalid triggers. You can do this by setting `ignore_invalid_triggers=True` (either on a state-by-state basis, or globally for all states):

```python
>>> # Globally suppress invalid trigger exceptions
>>> m = Machine(lump, states, initial='solid', ignore_invalid_triggers=True)
>>> # ...or suppress for only one group of states
>>> states = ['new_state1', 'new_state2']
>>> m.add_states(states, ignore_invalid_triggers=True)
>>> # ...or even just for a single state. Here, exceptions will only be suppressed when the current state is A.
>>> states = [State('A', ignore_invalid_triggers=True), 'B', 'C']
>>> m = Machine(lump, states)
```

#### Automatic transitions for all states
In addition to any transitions added explicitly, a `to_«state»()` method is created automatically whenever a state is added to a `Machine` instance. This method transitions to the target state no matter which state the machine is currently in:

```python
lump.to_liquid()
lump.state
>>> 'liquid'
lump.to_solid()
lump.state
>>> 'solid'
```

If you desire, you can disable this behavior by setting `auto_transitions=False` in the `Machine` initializer.

#### Transitioning from multiple states
A given trigger can be attached to multiple transitions, some of which can potentially begin or end in the same state. For example:

```python
machine.add_transition('transmogrify', ['solid','liquid', 'gas'], 'plasma')
machine.add_transition('transmogrify', 'plasma', 'solid')
# This next transition will never execute
machine.add_transition('transmogrify', 'plasma', 'gas')
```

In this case, calling `transmogrify()` will set the model's state to `'solid'` if it's currently `'plasma'`, and set it to `'plasma'` otherwise. (Note that only the _first_ matching transition will execute; thus, the transition defined in the last line above won't do anything.)

You can also make a trigger cause a transition from _all_ states to a particular destination by using the `'*'` wildcard:

```python
machine.add_transition('to_liquid', '*', 'liquid')
```

#### Ordered transitions
A common desire is for state transitions to follow a strict linear sequence. For instance, given states `['A', 'B', 'C']`, you might want valid transitions for `A` → `B`, `B` → `C`, and `C` → `A` (but no other pairs). 

To facilitate this behavior, Transitions provides an `add_ordered_transitions()` method in the `Machine` class:

```python
states = ['A', 'B', 'C']
 # See the "alternative initialization" section for an explanation of the 1st argument to init
machine = Machine(None, states, initial='A') 
machine.add_ordered_transitions()
machine.next_state()
print(machine.state)
>>> 'B'
# We can also define a different order of transitions
machine = Machine(None, states, initial='A') 
machine.add_ordered_transitions(['A', 'C', 'B'])
machine.next_state()
print(machine.state)
>>> 'C'
```

#### Conditional transitions
Sometimes you only want a particular transition to execute if a specific condition occurs. You can do this by passing a method, or list of methods, in the `conditions` argument:

```python
# Our Matter class, now with a bunch of methods that return booleans.
class Matter(object):
    def is_flammable(self): return False
    def is_really_hot(self): return True

machine.add_transition('heat', 'solid', 'gas', conditions='is_flammable')
machine.add_transition('heat', 'solid', 'liquid', conditions=['is_really_hot'])
```

In the above example, calling `heat()` when the model is in state `'solid'` will transition to state `'gas'` if `is_flammable` returns `True`. Otherwise, it will transition to state `'liquid'` if `is_really_hot` returns `True`.

For convenience, there's also an `'unless'` argument that behaves exactly like conditions, but inverted:

```python
machine.add_transition('heat', 'solid', 'gas', unless=['is_flammable', 'is_really_hot'])
```

In this case, the model would transition from solid to gas whenever `heat()` fires, provided that both `is_flammable()` and `is_really_hot()` return `False`.

Note that condition-checking methods will passively receive optional arguments and/or data objects passed to triggering methods. For instance, the following call:

```python
lump.heat(temp=74)
```

...would pass the `temp=74` optional kwarg to the `is_flammable()` check (possibly wrapped in an `EventData` instance). For more on this, see the [Passing data](#passing-data) section below.

#### <a name="transition-callbacks"></a>Callbacks
You can attach callbacks to transitions as well as states. Every transition has `'before'` and `'after'` attributes that contain a list of methods to call before and after the transition executes:

```python
class Matter(object):
    def make_hissing_noises(self): print("HISSSSSSSSSSSSSSSS")
    def disappear(self): print("where'd all the liquid go?")

transitions = [
    { 'trigger': 'melt', 'source': 'solid', 'dest': 'liquid', 'before': 'make_hissing_noises'},
    { 'trigger': 'evaporate', 'source': 'liquid', 'dest': 'gas', 'after': 'disappear' }
]

lump = Matter()
machine = Machine(lump, states, transitions=transitions, initial='solid')
lump.melt()
>>> "HISSSSSSSSSSSSSSSS"
lump.evaporate()
>>> "where'd all the liquid go?"
```

### Passing data
Sometimes you need to pass the callback functions registered at machine initialization some data that reflects the model's current state. Transitions allows you to do this in two different ways. 

First (the default), you can pass any positional or keyword arguments directly to the trigger methods (created when you call `add_transition()`):

```python
class Matter(object):
    def __init__(self): self.set_environment()
    def set_environment(self, temp=0, pressure=101.325):
        self.temp = temp
        self.pressure = pressure
    def print_temperature(self): print("Current temperature is %d degrees celsius." % self.temp)
    def print_pressure(self): print("Current pressure is %.2f kPa." % self.pressure)

lump = Matter()
machine = Machine(lump, ['solid', 'liquid'], initial='solid')
machine.add_transition('melt', 'solid', 'liquid', before='set_environment')

lump.melt(45)  # positional arg
lump.print_temperature()
> 'Current temperature is 45 degrees celsius.'

machine.set_state('solid')  # reset state so we can melt again
lump.melt(pressure=300.23)  # keyword args also work
lump.print_pressure()
> 'Current pressure is 300.23 kPa.'

```

You can pass any number of arguments you like to the trigger.

There is one important limitation to this approach: every callback function triggered by the state transition must be able to handle _all_ of the arguments. This may cause problems if the callbacks each expect somewhat different data. 

To get around this, Transitions supports an alternate method for sending data. If you set `send_event=True` at `Machine` initialization, all arguments to the triggers will be wrapped in an `EventData` instance and passed on to every callback. (The `EventData` object also maintains internal references to the source state, model, transition, machine, and trigger associated with the event, in case you need to access these for anything.)

```python
class Matter(object):

    def __init__(self):
        self.temp = 0
        self.pressure = 101.325

    # Note that the sole argument is now the EventData instance.
    # This object stores positional arguments passed to the trigger method in the
    # .args property, and stores keywords arguments in the .kwargs dictionary.
    def set_environment(self, event):
        self.temp = event.kwargs.get('temp', 0)
        self.pressure = event.kwargs.get('pressure', 101.325)

    def print_pressure(self): print("Current pressure is %.2f kPa." % self.pressure)

lump = Matter()
machine = Machine(lump, ['solid', 'liquid'], send_event=True, initial='solid')
machine.add_transition('melt', 'solid', 'liquid', before='set_environment')

lump.melt(temp=45, pressure=1853.68)  # keyword args
lump.print_pressure()
> 'Current pressure is 1853.68 kPa.'

```

### Diagrams

Transitions can generate basic state diagrams displaying all valid transitions between states. To use the graphing functionality, you'll need to have `pygraphviz` installed (`pip install pygraphviz`). Generating a state diagram for any machine is as simple as calling its `get_graph()` method, which returns a PyGraphviz `AGraph` instance. For example:

```python
graph = machine.get_graph()
graph.draw('my_state_diagram.png', prog='dot')
```

This produces something like this:

![state diagram example](https://cloud.githubusercontent.com/assets/19777/11530591/1a0c08a6-98f6-11e5-88a7-756585aafbbb.png)

### Alternative initialization patterns

In all of the examples so far, we've attached a new `Machine` instance to a separate model (`lump`, an instance of class `Matter`). While this separation keeps things tidy (because you don't have to monkey patch a whole bunch of new methods into the `Matter` class), it can also get annoying, since it requires you to keep track of which methods are called on the state machine, and which ones are called on the model that the state machine is bound to (e.g., `lump.on_enter_StateA()` vs. `machine.add_transition()`). 

Fortunately, Transitions is flexible, and supports two other initialization patterns. 

First, you can create a standalone state machine that doesn't require another model at all. Simply omit the model argument during initialization:

```python
machine = Machine(states=states, transitions=transitions, initial='solid')
machine.melt()
machine.state
>>> 'liquid'
```

If you initialize the machine this way, you can then attach all triggering events (like `evaporate()`, `sublimate()`, etc.) and all callback functions directly to the `Machine` instance. 

This approach has the benefit of consolidating all of the state machine functionality in one place, but can feel a little bit unnatural if you think state logic should be contained within the model itself rather than in a separate controller.

An alternative (potentially better) approach is to have the model inherit from the `Machine` class. Transitions is designed to support inheritance seamlessly. (just be sure to override class `Machine`'s `__init__` method!):

```python
class Matter(Machine):
    def say_hello(self): print("hello, new state!")
    def say_goodbye(self): print("goodbye, old state!")

    def __init__(self):
        states = ['solid', 'liquid', 'gas']
        Machine.__init__(self, states=states, initial='solid')
        self.add_transition('melt', 'solid', 'liquid')
    
lump = Matter()
lump.state
>>> 'solid'
lump.melt()
lump.state
>>> 'liquid'
```

Here you get to consolidate all state machine functionality into your existing model, which often feels more natural way than sticking all of the functionality we want in a separate standalone `Machine` instance.

### Logging

Transitions includes very rudimentary logging capabilities. A number of events -- namely, state changes, transition triggers, and conditional checks -- are logged using the standard Python `logging` module (with different log levels). This means you can easily configure logging to standard output in a script:

```python

# Set up logging
import logging
from transitions import logger
logger.setLevel(logging.INFO)  # logging.DEBUG for verbosity

# Business as usual
machine = Machine(states=states, transitions=transitions, initial='solid')
...
```

### Extension: <a name="hsm"></a>Hierarchical State Machine (HSM)

Transitions includes an extension module which allows to nest states. This allows to create contexts and to model cases where states are related to certain subtasks in the state machine. To create a nested state, either import `NestedState` from transitions or use a dictionary with initialization arguments.

```python
from transitions import HierarchicalMachine as Machine
from transitions import NestedState as State

states = ['standing', 'walking', {'name': 'caffeinated', 'children':['dithering', 'running']}]
transitions = [
  ['walk', 'standing', 'walking'],
  ['stop', 'walking', 'standing'],
  ['drink', '*', 'caffeinated'],
  ['walk', 'caffeinated_dithering', 'caffeinated_running'],
  ['relax', 'caffeinated', 'standing']
]
machine = Machine(states=states, transitions=transitions, initial='standing', ignore_invalid_triggers=True)

machine.walk() # Walking now
machine.stop() # let's stop for a moment
machine.drink() # coffee time
machine.state
>>> 'caffeinated_dithering'
machine.walk() # we have to go faster
machine.state
>>> 'caffeinated_running'
machine.stop() # can't stop moving!
machine.state
>>> 'caffeinated_running'
machine.relax() # leave nested state
machine.state # phew, what a ride
>>> 'standing'
```

Some things that have to be considered when working with nested states: State *names are concatenated*. A substate `bar` from state `foo` will be known by `foo_bar`. A substate `baz` of `bar` will be refered to as `foo_bar_baz` and so on. When entering a substate, `enter` will be called for all parent states. The same is true for exiting substates. If you transit into a state with nested states and do not specify a child, the *first declared child will be entered*. Third, a transition specified for a parent state will be resolved and *added to all substates*.

```python
states = ['A', 'B', 
  {'name': 'C', 'children':['1', '2', 
    {'name': '3', 'children': ['a', 'b', 'c']}
  ]}
]

transitions = [
    ['reset', 'C', 'A']
]

# we rely on auto transitions
machine = Machine(states=states, transitions=transitions, initial='A')

machine.to_B() # exit state A, enter state B
machine.to_C() # exit B, enter C, enter C_1
machine.to_C_3() # exit C_1, enter C_3, enter C_3_a
machine.state
>>> 'C_3_a'
machine.to_C_2() # exit C_3_a, exit C_3, enter C_2
machine.reset() # exit C_2, exit C, enter A
machine.to_C_3_a() # exit A, enter C, enter C_3, enter C_3_a
```

### Extension: Reuse of previously created HSMs

Besides semantic order, nested states are very handy if you want to specify state machines for specific tasks and plan to reuse them. Transitions offers two ways to achieve this: You can either *pass a state machine* as an argument or retrieve the machine's *blueprint*, store this as plain text somewhere and pass this to a new machine.

```python
count_states = ['1', '2', '3', 'done']
count_trans = [
    ['increase', '1', '2'],
    ['increase', '2', '3'],
    ['decrease', '3', '2'],
    ['decrease', '2', '1'],
    ['done', '3', 'done'],
    ['reset', '*', '1']
]

counter = Machine(states=count_states, transitions=count_trans, initial='1')

counter.increase() # love my counter
counter.blueprints
>>> {'states': ['1', '2', '3', 'done'], 'transitions': [{'unless': None, 'dest': '2', 'after': None, 'source': '1', 'trigger': 'increase', 'conditions': None, 'before': None}, ...]}
...
states = ['waiting', 'collecting', {'name': 'counting', children: counter}]
# states = ['waiting', 'collecting', {'name': 'counting', children: counter.blueprints}]

transitions = [
    ['collect', '*', 'collecting'],
    ['wait', '*', 'waiting'],
    ['count', 'wait', 'counting']
]

collector = Machine(states=states, transitions=transitions, initial='waiting')
collector.collect() # collecting
collector.count() # let's see what we got
collector.increase() # counting_2
collector.increase() # counting_3
collector.done() # counting_done
collector.wait() # go back to waiting
```

Sometimes you want such an embedded state collection to 'return' which means after it is done it should exit and transit to one of your states. To achieve this behaviour you can remap state transitions. In the example above we would like the counter to return if the state `done` was reached. This is done as follows:

```python
states = ['waiting', 'collecting', {'name': 'counting', children: counter, 'remap': {'done': 'waiting'}}]

... # same as above

collector.increase() # counting_3
collector.done()
collector.state
>>> 'waiting' # be aware that 'finish' will entirely be removed from the state machine
```

If a reused state machine does not have a final state, you can of course add the transitions manually. If 'counter' had no 'done' state, we could just add `['done', 'counter_3', 'A']` to achieve the same behaviour.

### <a name="threading"></a>Extension: Threadsafe(-ish) State Machine

In cases where event dispatching is done in threads, one can use either `LockedMachine` or `LockedHierarchicalMachine` where **function access** (!sic) is secured with reentrant locks. This does not save you from corrupting your machine by tinkering with member variables of your model or state machine.

```python
from transition import LockedMachine as Machine
from threading import Thread
import time

states = ['A', 'B', 'C']
machine = Machine(states=states, initial='A')

# let us assume that entering B will take some time
thread = Thread(target=self.stuff.to_B)
thread.start()
time.sleep(0.01) # thread requires some time to start
machine.to_C() # synchronized access; won't execute before thread is done
# accessing attributes directly
thread = Thread(target=self.stuff.to_B)
thread.start()
machine.new_attrib = 42 # not synchronized! will mess with execution order
```

### <a name="bug-reports"></a>I have a [bug report/issue/question]...
For bug reports and other issues, please open an issue on GitHub. 

For usage questions, post on Stack Overflow, making sure to tag your question with the `transitions` and `python` tags. 

For any other questions, solicitations, or large unrestricted monetary gifts, email [Tal Yarkoni](mailto:tyarkoni@gmail.com).
