# <a name="transitions-module"></a> transitions

A lightweight, object-oriented state machine implementation in Python. Compatible with Python 2.7+ and 3.0+.

## Status
* [![Build Status](https://travis-ci.org/tyarkoni/transitions.png?branch=master)](https://travis-ci.org/tyarkoni/transitions)
* [![Coverage Status](https://coveralls.io/repos/tyarkoni/transitions/badge.svg?branch=master&service=github)](https://coveralls.io/github/tyarkoni/transitions?branch=master)

## Installation

    pip install transitions

... or clone the repo from GitHub and then:

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
        - [Queued transitions](#queued-transitions)
        - [Conditional transitions](#conditional-transitions)
        - [Callbacks](#transition-callbacks)
    - [Passing data](#passing-data)
    - [Alternative initialization patterns](#alternative-initialization-patterns)
    - [Logging](#logging)
    - [Extensions](#extensions)
        - [Diagrams](#diagrams)
        - [Hierarchical State Machine](#hsm)
        - [Threading](#threading)
    - [Bug reports etc.](#bug-reports)


## Quickstart

They say [a good example is worth](https://www.google.com/webhp?ie=UTF-8#q=%22a+good+example+is+worth%22&start=20) 100 pages of API documentation, a million directives, or a thousand words.

Well, "they" probably lie... but here's an example anyway:

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

        # Add some transitions. We could also define these using a static list of
        # dictionaries, as we did with states above, and then pass the list to
        # the Machine initializer as the transitions= argument.

        # At some point, every superhero must rise and shine.
        self.machine.add_transition(trigger='wake_up', source='asleep', dest='hanging out')

        # Superheroes need to keep in shape.
        self.machine.add_transition('work_out', 'hanging out', 'hungry')

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

I say “minimal”, because while this state machine is technically operational, it doesn't actually _do_ anything. It starts in the `'solid'` state, but won't ever move into another state, because no transitions are defined... yet!

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
lump.trigger('ionize')
lump.state
>>> 'plasma'
```

Notice the shiny new methods attached to the `Matter` instance (`evaporate()`, `ionize()`, etc.). Each method triggers the corresponding transition. You don't have to explicitly define these methods anywhere; the name of each transition is bound to the model passed to the `Machine` initializer (in this case, `lump`).
Additionally, there is a method called `trigger` now attached to your model.
This method lets you execute transitions by name in case dynamic triggering is required.

### <a name="states"></a>States

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

For convenience, whenever a new `State` is added to a `Machine`, the methods `on_enter_«state name»` and `on_exit_«state name»` are dynamically created on the Machine (not on the model!), which allow you to dynamically add new enter and exit callbacks later if you need them.

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
# the dynamically added on_enter_ and on_exit_ methods.
# Note that the initial call to add the callback is made
# on the Machine and not on the model.
machine.on_enter_gas('say_hello')

# Test out the callbacks...
machine.set_state('solid')
lump.sublimate()
>>> 'goodbye, old state!'
>>> 'hello, new state!'
```

Note that `on_enter_«state name»` callback will *not* fire when a Machine is first initialized. For example if you have an `on_enter_A()` callback defined, and initialize the `Machine` with `initial='A'`, `on_enter_A()` will not be fired until the next time you enter state `A`. (If you need to make sure `on_enter_A()` fires at initialization, you can simply create a dummy initial state and then explicitly call `to_A()` inside the `__init__` method.)

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
machine.get_state(lump.state).name
>>> 'solid'
```

### <a name="transitions"></a>Transitions
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

If you need to know which transitions are valid from a certain state, you can use `get_triggers`:

```
m.get_triggers('solid')
>>> ['melt', 'sublimate']
m.get_triggers('liquid')
>>> ['evaporate']
m.get_triggers('plasma')
>>> []
# you can also query several states at once 
m.get_triggers('solid', 'liquid', 'gas', 'plasma')
>>> ['melt', 'evaporate', 'sublimate', 'ionize']
```

#### <a name="automatic-transitions-for-all-states"></a>Automatic transitions for all states
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

#### <a name="transitioning-from-multiple-states"></a>Transitioning from multiple states
A given trigger can be attached to multiple transitions, some of which can potentially begin or end in the same state. For example:

```python
machine.add_transition('transmogrify', ['solid', 'liquid', 'gas'], 'plasma')
machine.add_transition('transmogrify', 'plasma', 'solid')
# This next transition will never execute
machine.add_transition('transmogrify', 'plasma', 'gas')
```

In this case, calling `transmogrify()` will set the model's state to `'solid'` if it's currently `'plasma'`, and set it to `'plasma'` otherwise. (Note that only the _first_ matching transition will execute; thus, the transition defined in the last line above won't do anything.)

You can also make a trigger cause a transition from _all_ states to a particular destination by using the `'*'` wildcard:

```python
machine.add_transition('to_liquid', '*', 'liquid')
```

Note that wildcard transitions will only apply to states that exist at the time of the add_transition() call. Calling a wildcard-based transition when the model is in a state added after the transition was defined will elicit an invalid transition message, and will not transition to the target state.

#### <a name="ordered-transitions"></a> Ordered transitions
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

#### <a name="queued-transitions"></a>Queued transitions

The default behaviour in Transitions is to process events instantly. This means events within an `on_enter` method will be processed _before_ callbacks bound to `after` are called.

```python
def go_to_C():
    global machine
    machine.to_C()

def after_advance():
    print("I am in state B now!")

def entering_C():
    print("I am in state C now!")

states = ['A', 'B', 'C']
machine = Machine(states=states)

# we want a message when state transition to B has been completed
machine.add_transition('advance', 'A', 'B', after=after_advance)

# call transition from state B to state C
machine.on_enter_B(go_to_C)

# we also want a message when entering state C
machine.on_enter_C(entering_C)
machine.advance()
>>> 'I am in state C now!'
>>> 'I am in state B now!' # what?
```

The execution order of this example is
```
prepare -> before -> on_enter_B -> on_enter_C -> after.
```
If queued processing is enabled, a transition will be finished before the next transition is triggered:

```python
machine = Machine(states=states, queued=True)
...
machine.advance()
>>> 'I am in state B now!'
>>> 'I am in state C now!' # That's better!
```

This results in
```
prepare -> before -> on_enter_B -> queue(to_C) -> after  -> on_enter_C.
```
**Important note:** when processing events in a queue, the trigger call will _always_ return `True`, since there is no way to determine at queuing time whether a transition involving queued calls will ultimately complete successfully. This is true even when only a single event is processed.

```python
machine.add_transition('jump', 'A', 'C', conditions='will_fail')
...
# queued=False
machine.jump()
>>> False
# queued=True
machine.jump()
>>> True
```

#### <a name="conditional-transitions"></a>Conditional transitions
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
# equivalent to lump.trigger('heat', temp=74)
```

... would pass the `temp=74` optional kwarg to the `is_flammable()` check (possibly wrapped in an `EventData` instance). For more on this, see the [Passing data](#passing-data) section below.

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

There is also a `'prepare'` callback that is executed as soon as a transition starts, before any `'conditions'` are checked or other callbacks are executed.

```python
class Matter(object):
    heat = False
    attempts = 0
    def count_attempts(self): self.attempts += 1
    def is_really_hot(self): return self.heat
    def heat_up(self): self.heat = random.random() < 0.25
    def stats(self): print('It took you %i attempts to melt the lump!' %self.attempts)

states=['solid', 'liquid', 'gas', 'plasma']

transitions = [
    { 'trigger': 'melt', 'source': 'solid', 'dest': 'liquid', 'prepare': ['heat_up', 'count_attempts'], 'conditions': 'is_really_hot', 'after': 'stats'},
]

lump = Matter()
machine = Machine(lump, states, transitions=transitions, initial='solid')
lump.melt()
lump.melt()
lump.melt()
lump.melt()
>>> "It took you 4 attempts to melt the lump!"
```

Note that `prepare` will not be called unless the current state is a valid source for the named transition.

In summary, callbacks on transitions are executed in the following order:

* `'prepare'` (executed as soon as the transition starts)
* `'conditions'` / `'unless'` (conditions *may* fail and halt the transition)
* `'before'` (executed while the model is still in the source state)
* `'after'` (executed while the model is in the destination state)

Default actions meant to be executed before or after *every* transition can be passed to `Machine` during initialization with
`before_state_change` and `after_state_change` respectively:

```python
class Matter(object):
    def make_hissing_noises(self): print("HISSSSSSSSSSSSSSSS")
    def disappear(self): print("where'd all the liquid go?")

states=['solid', 'liquid', 'gas', 'plasma']

lump = Matter()
m = Machine(lump, states, before_state_change='make_hissing_noises', after_state_change='disappear')
lump.to_gas()
>>> "HISSSSSSSSSSSSSSSS"
>>> "where'd all the liquid go?"
```

### <a name="passing-data"></a>Passing data
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

lump.melt(45)  # positional arg; 
# equivalent to lump.trigger('melt', 45)
lump.print_temperature()
>>> 'Current temperature is 45 degrees celsius.'

machine.set_state('solid')  # reset state so we can melt again
lump.melt(pressure=300.23)  # keyword args also work
lump.print_pressure()
>>> 'Current pressure is 300.23 kPa.'

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
>>> 'Current pressure is 1853.68 kPa.'

```

### <a name="alternative-initialization-patterns"></a>Alternative initialization patterns

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

Transitions includes very rudimentary logging capabilities. A number of events--namely, state changes, transition triggers, and conditional checks--are logged as INFO-level events using the standard Python `logging` module. This means you can easily configure logging to standard output in a script:

```python

# Set up logging
import logging
from transitions import logger
logger.setLevel(logging.INFO)

# Business as usual
machine = Machine(states=states, transitions=transitions, initial='solid')
...
```

### <a name="extensions"></a> Extensions

Even though the core of transitions is kept lightweight, there are a variety of MixIns to extend its functionality. Currently supported are:

- **Diagrams** to visualize the current state of a machine
- **Hierarchical State Machines** for nesting and reuse
- **Threadsafe Locks** for parallel execution

There are two mechanisms to retrieve a state machine instance with the desired features enabled. The first approach makes use of the convenience `factory` with the three parameters `graph`, `nested` and `locked` set to `True` if the certain feature is required:

```python
from transitions.extensions import MachineFactory

# create a machine with mixins
diagram_cls = MachineFactory.get_predefined(graph=True)
nested_locked_cls = MachineFactory.get_predefined(nested=True, locked=True)

# create instances from these classes
# instances can be used like simple machines
machine1 = diagram_cls(model, state, transitions...)
machine2 = nested_locked_cls(model, state, transitions)
```

This approach targets experimental use since in this case the underlying classes do not have to be known. However, classes can also be directly imported from `transitions.extensions`. The naming scheme is as follows:

|                                | Diagrams | Nested | Locked |
| -----------------------------: | :------: | :----: | :----: |
| Machine                        | ✘        | ✘      | ✘      |
| GraphMachine                   | ✓        | ✘      | ✘      |
| HierarchicalMachine            | ✘        | ✓      | ✘      |
| LockedMachine                  | ✘        | ✘      | ✓      |
| HierarchicalGraphMachine       | ✓        | ✓      | ✘      |
| LockedGraphMachine             | ✓        | ✘      | ✓      |
| LockedHierarchicalMachine      | ✘        | ✓      | ✓      |
| LockedHierarchicalGraphMachine | ✓        | ✓      | ✓      |

To use a full featured state machine, one could write:

```python
from transitions.extensions import LockedHierarchicalGraphMachine as Machine

#enable ALL the features!
machine = Machine(model, states, transitions)
```

#### <a name="diagrams"></a> Diagrams

Additional Keywords:
* `title` (optional): Sets the title of the generated image
* `show_conditions` (default False): Shows conditions at transition edges
* `show_auto_transitions` (default False): Shows auto transitions in graph

Transitions can generate basic state diagrams displaying all valid transitions between states. To use the graphing functionality, you'll need to have `pygraphviz` installed (`pip install pygraphviz`). With `GraphMachine` enabled, a PyGraphviz `AGraph` object is generated during machine initialization and is constantly updated when the machine state changes:

```python
from transitions.extensions import GraphMachine as Machine
m = Model()
machine = Machine(model=m, ...)
# in cases where auto transitions should be visible
# Machine(model=m, show_auto_transitions=True, ...)

# draw the whole graph ...
m.get_graph().draw('my_state_diagram.png', prog='dot')
# ... or just the region of interest
# (previous state, active state and all reachable states)
m.get_graph(show_roi=True).draw('my_state_diagram.png', prog='dot')
```

This produces something like this:

![state diagram example](https://cloud.githubusercontent.com/assets/19777/11530591/1a0c08a6-98f6-11e5-88a7-756585aafbbb.png)

Also, have a look at our [example](./examples) IPython/Jupyter notebooks for a more detailed example.

### <a name="hsm"></a>Hierarchical State Machine (HSM)

Transitions includes an extension module which allows to nest states. This allows to create contexts and to model cases where states are related to certain subtasks in the state machine. To create a nested state, either import `NestedState` from transitions or use a dictionary with the initialization arguments `name` and `children`. Optionally, `initial` can be used to define a sub state to transit to, when the nested state
 is entered.

```python
from transitions.extensions import HierarchicalMachine as Machine

states = ['standing', 'walking', {'name': 'caffeinated', 'children':['dithering', 'running']}]
transitions = [
  ['walk', 'standing', 'walking'],
  ['stop', 'walking', 'standing'],
  ['drink', '*', 'caffeinated'],
  ['walk', ['caffeinated', 'caffeinated_dithering'], 'caffeinated_running'],
  ['relax', 'caffeinated', 'standing']
]

machine = Machine(states=states, transitions=transitions, initial='standing', ignore_invalid_triggers=True)

machine.walk() # Walking now
machine.stop() # let's stop for a moment
machine.drink() # coffee time
machine.state
>>> 'caffeinated'
machine.walk() # we have to go faster
machine.state
>>> 'caffeinated_running'
machine.stop() # can't stop moving!
machine.state
>>> 'caffeinated_running'
machine.relax() # leave nested state
machine.state # phew, what a ride
>>> 'standing'
# machine.on_enter_caffeinated_running('callback_method')
```

A configuration making use of  `initial` could look like this:

```python
# ...
states = ['standing', 'walking', {'name': 'caffeinated', 'initial': 'dithering' 'children':['dithering', 'running']}]
transitions = [
  ['walk', 'standing', 'walking'],
  ['stop', 'walking', 'standing'],
  # this transition will end in 'caffeinated_dithering'...
  ['drink', '*', 'caffeinated'], 
  # ... that is why we do not need do specify 'caffeinated' here anymore
  ['walk', 'caffeinated_dithering', 'caffeinated_running'], 
  ['relax', 'caffeinated', 'standing']
]
# ...
```

Some things that have to be considered when working with nested states: State *names are concatenated* with `NestedState.separator`. Currently the separator is set to underscore ('_') and therefore behaves similar to the basic machine. This means a substate `bar` from state `foo` will be known by `foo_bar`. A substate `baz` of `bar` will be referred to as `foo_bar_baz` and so on. When entering a substate, `enter` will be called for all parent states. The same is true for exiting substates. Third, nested states can overwrite transition behaviour of their parents. If a transition is not known to the current state it will be delegated to its parent.

In some cases underscore as a separator is not sufficient. For instance if state names consists of more than one word and a concatenated naming such as `state_A_name_state_C` would be confusing. Setting the separator to something else than underscore changes some of the behaviour (auto_transition and setting callbacks). You can even use unicode characters if you use python 3:

```python
from transitions.extensions.nesting import NestedState
NestedState.separator = '↦'
states = ['A', 'B',
  {'name': 'C', 'children':['1', '2',
    {'name': '3', 'children': ['a', 'b', 'c']}
  ]}
]

transitions = [
    ['reset', 'C', 'A'],
    ['reset', 'C↦2', 'C']  # overwriting parent reset
]

# we rely on auto transitions
machine = Machine(states=states, transitions=transitions, initial='A')
machine.to_B()  # exit state A, enter state B
machine.to_C()  # exit B, enter C
machine.to_C.s3.a()  # enter C↦a; enter C↦3↦a;
machine.state,
>>> 'C↦3↦a'
machine.to('C↦s2')  # not interactive; exit C↦3↦a, exit C↦3, enter C↦2
machine.reset()  # exit C↦2; reset C has been overwritten by C↦3
machine.state
>>> 'C'
machine.reset()  # exit C, enter A
machine.state
>>> 'A'
# s.on_enter('C↦3↦a', 'callback_method')
```

Instead of `to_C_3_a()` auto transition is called as `to_C.s3.a()`. If your substate starts with a digit, transitions adds a prefix 's' ('3' becomes 's3') to the auto transition `FunctionWrapper` to comply with the attribute naming scheme of python.
If interactive completion is not required, `to('C↦3↦a')` can be called directly. Additionally, `on_enter/exit_<<state name>>` is replaced with `on_enter/exit(state_name, callback)`.

To check whether the current state is a substate of a specific state `is_state` supports the keyword `allow_substates`:

```python
machine.state
>>> 'C.2.a'
machine.is_C() # checks for specific states
>>> False
machine.is_C(allow_substates=True)
>>> True
```

#### Reuse of previously created HSMs

Besides semantic order, nested states are very handy if you want to specify state machines for specific tasks and plan to reuse them. Be aware that this will *embed* the passed machine's states. This means if your states had been altered *before*, this change will be persistent.

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
states = ['waiting', 'collecting', {'name': 'counting', 'children': counter}]
# states = ['waiting', 'collecting', {'name': 'counting', children: counter}]

transitions = [
    ['collect', '*', 'collecting'],
    ['wait', '*', 'waiting'],
    ['count', 'wait', 'counting_1']
]

collector = Machine(states=states, transitions=transitions, initial='waiting')
collector.collect()  # collecting
collector.count()  # let's see what we got
collector.increase()  # counting_2
collector.increase()  # counting_3
collector.done()  # collector.state == counting_done
collector.wait()  # collector.state == waiting
```

Sometimes you want such an embedded state collection to 'return' which means after it is done it should exit and transit to one of your states. To achieve this behaviour you can remap state transitions. In the example above we would like the counter to return if the state `done` was reached. This is done as follows:

```python
states = ['waiting', 'collecting', {'name': 'counting', 'children': counter, 'remap': {'done': 'waiting'}}]

... # same as above

collector.increase() # counting_3
collector.done()
collector.state
>>> 'waiting' # be aware that 'counting_done' will be removed from the state machine
```

If a reused state machine does not have a final state, you can of course add the transitions manually. If 'counter' had no 'done' state, we could just add `['done', 'counter_3', 'waiting']` to achieve the same behaviour.

#### <a name="threading"></a> Threadsafe(-ish) State Machine

In cases where event dispatching is done in threads, one can use either `LockedMachine` or `LockedHierarchicalMachine` where **function access** (!sic) is secured with reentrant locks. This does not save you from corrupting your machine by tinkering with member variables of your model or state machine.

```python
from transitions.extensions import LockedMachine as Machine
from threading import Thread
import time

states = ['A', 'B', 'C']
machine = Machine(states=states, initial='A')

# let us assume that entering B will take some time
thread = Thread(target=machine.to_B)
thread.start()
time.sleep(0.01) # thread requires some time to start
machine.to_C() # synchronized access; won't execute before thread is done
# accessing attributes directly
thread = Thread(target=machine.to_B)
thread.start()
machine.new_attrib = 42 # not synchronized! will mess with execution order
```

### <a name="bug-reports"></a>I have a [bug report/issue/question]...
For bug reports and other issues, please open an issue on GitHub.

For usage questions, post on Stack Overflow, making sure to tag your question with the `transitions` and `python` tags.

For any other questions, solicitations, or large unrestricted monetary gifts, email [Tal Yarkoni](mailto:tyarkoni@gmail.com).
