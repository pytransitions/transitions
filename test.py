from transitions.extensions.nesting import HierarchicalMachine as HMachine
from transitions.extensions.nesting import NestedState

class Foo(HMachine) :
    def __init__(self) :

        self.states = [NestedState(name='1'), {'name': '2'},
                       NestedState('3')]

        HMachine.__init__(self, states=self.states, initial='1')

foo = Foo()
foo.add_transition('process', '*', '2')
foo.process()
print(foo.state)
foo.add_states(['4'], parent='2')
foo.add_transition('into', '2', '2_4')
foo.into()
print(foo.state)
