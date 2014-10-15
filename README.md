# transitions

A lightweight, object-oriented state machine implementation in Python.

## Installation

    pip install transitions

...or clone the repo from GitHub and then:

    python setup.py install

## Quickstart

They say [a good example is worth](https://www.google.com/webhp?sourceid=chrome-instant&ion=1&espv=2&ie=UTF-8#q=%22a+good+example+is+worth%22&start=20) 100 pages of API documentation, a million directives, or a thousand words. Well, "they" probably lie... but here's an example anyway:

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
        self.machine.add_transition(name='work_out', source='hanging out', dest='hungry')
        
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
        print "Beauty, eh?"
```

There, now we've baked a state machine into our NarcolepticSuperhero. Let's take him/her/it out for a spin...

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
More documentation will follow soon. In the meantime, please direct any questions to [Tal Yarkoni](mailto:tyarkoni@gmail.com).

