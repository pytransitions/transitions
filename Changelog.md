# Changelog

## 0.6.9 (October 2018)

Release 0.6.9 is a minor release and contains two bugfixes:

- Bugfix #314: Do not override already defined model functions with convenience functions (thanks @Arkanayan)
- Bugfix #316: `state.Error` did not call parent's `enter` method (thanks @potens1)

## 0.6.8 (May, 2018)

Release 0.6.8 is a minor release and contains a critical bugfix:

- Bugfix #301: Reading `Readme.md` in `setup.py` causes a `UnicodeDecodeError` in non-UTF8-locale environments (thanks @jodal)

## 0.6.7 (May, 2018)

Release 0.6.7 is identical to 0.6.6. A release had been necessary due to #294 related to PyPI.

## 0.6.6 (May, 2018)

Release 0.6.6 is a minor release and contains several bugfixes and new features:

- Bugfix: `HierarchicalMachine` now considers the initial state of `NestedState` instances/names passed to `initial`.
- Bugfix: `HierarchicalMachine` used to ignore children when `NestedStates` were added to the machine.
- Bugfix #300: Fixed missing brackets in `TimeoutState` (thanks @Synss)
- Feature #289: Introduced `Machine.resolve_callable(func, event_data)` to enable customization of callback definitions (thanks @ollamh and @paulbovbel)
- Feature #299: Added support for internal transitions with `dest=None` (thanks @maueki)
- Feature: Added `Machine.dispatch` to trigger events on all models assigned to `Machine`

## 0.6.5 (April, 2018)

Release 0.6.5 is a minor release and contains a new feature and a bugfix:

- Feature #287: Embedding `HierarchicalMachine` will now reuse the machine's `initial` state. Passing `initial: False` overrides this (thanks @mrjogo).
- Bugfix #292: Models using `GraphMashine` were not picklable in the past due to `graph` property. Graphs for each model are now stored in `GraphMachine.model_graphs` (thanks @ansumanm).

## 0.6.4 (January, 2018)

Release 0.6.4 is a minor release and contains a new feature and two bug fixes related to `HierachicalMachine`:

- Bugfix #274: `initial` has not been passed to super in `HierachicalMachine.add_model` (thanks to @illes).
- Feature #275: `HierarchicalMachine.add_states` now supports keyword `parent` to be a `NestedState` or a string.
- Bugfix #278: `NestedState` has not been exited correctly during reflexive triggering (thanks to @hrsmanian).

## 0.6.3 (November, 2017)

Release 0.6.3 is a minor release and contains a new feature and two bug fixes:

- Bugfix #268: `Machine.add_ordered_transitions` changed states' order if `initial` is not the first or last state (thanks to @janekbaraniewski).
- Bugfix #265: Renamed `HierarchicalMachine.to` to `to_state` to prevent warnings when HSM is used as a model.
- Feature #266: Introduce `Machine.get_transitions` to get a list of transitions for alteration (thanks to @Synss).

## 0.6.2 (November, 2017)

Release 0.6.2 is a minor release and contains new features and bug fixes but also several internal changes:

- Documentation: Add docstring to every public method
- Bugfix #257: Readme example variable had been capitalized (thanks to @fedesismo)
- Add `appveyor.yml` for Windows testing; However, Windows testing is disabled due to #258
- Bugfix #262: Timeout threads prevented program from execution when main thread ended (thanks to @tkuester)
- `prep_ordered_arg` is now protected in `core`
- Convert `logger` instances to `_LOGGER` to comply with protected module constant naming standards
- `traverse` is now protected in `HierarchicalMachine`
- Remove abstract class `Diagram` since it did not add functionality to `diagrams`
- Specify several overrides of `add_state` or `add_transition` to keep the base class parameters instead of `*args` and `**kwargs`
- Change several `if len(x) > 0:` checks to `if x:` as suggested by the static code analysis to make use of falsy empty lists/strings.

## 0.6.1 (September, 2017)

Release 0.6.1 is a minor release and contains new features as well as bug fixes:

- Feature #245: Callback definitions ('before', 'on_enter', ...) have been moved to classes `Transition` and `State`
- Bugfix #253: `Machine.remove_transitions` converted `defaultdict` into dict (thanks @Synss)
- Bugfix #248: `HierarchicalStateMachine`'s copy procedure used to cause issues with function callbacks and object references (thanks @Grey-Bit)
- Renamed `Machine.id` to `Machine.name` to be consistent with the constructor parameter `name`
- Add `Machine.add_transitions` for adding multiple transitions at once (thanks @Synss)

## 0.6.0 (August, 2017)

Release 0.6.0 is a major release and introduces new state features and bug fixes:

- `add_state_features` convenience decorator supports creation of custom states
- `Tags` makes states taggable
- `Error` checks for error states (not accepted states that cannot be left); subclass of `Tags`
- `Volatile` enables scoped/temporary state objects to handle context parameters
- Removed `add_self` from `Machine` constructor 
- `pygraphviz` is now optional; use `pip install transitions[diagrams]` to install it
- Narrowed warnings filter to prevent output cluttering by other 3rd party  modules (thanks to @ksandeep)
- Reword HSM exception when wrong state object had been passedn (thanks to @Blindfreddy)
- Improved handling of partials during graph generation (thanks to @Synss)
- Introduced check to allow explicit passing of callback functions which match the `on_enter_<state>` scheme (thanks to @termim)
- Bug #243: on_enter/exit callbacks defined in dictionaries had not been assigned correctly in HSMs (thanks to @Blindfreddy)
- Introduced workaround for Python 3 versions older than 3.4 to support dill version 0.2.7 and higher (thanks to @mmckerns)
- Improved manifest (#242) to comply with distribution standards (thanks to @jodal)

## 0.5.3 (May, 2017)

Release 0.5.3 is a minor release and contains several bug fixes:

- Bug #214: `LockedMachine` as a model prevented correct addition of `on_enter/exit_<state>` (thanks to @kr2)
- Bug #217: Filtering rules for auto transitions in graphs falsely filtered certain transitions (thanks to @KarolOlko)
- Bug #218: Uninitialized `EventData.transition` caused `AttributeError` in `EventData.__repr__` (thanks to @kunalbhagawati)
- Bug #215: State instances passed to `initial` parameter of `Machine` constructor had not been processed properly (thanks @mathiasimmer)

## 0.5.2 (April, 2017)

Release 0.5.2 is a minor release and contains a bug fix:
- Bug #213: prevent `LICENSE` to be installed to root of installation path

## 0.5.1 (April, 2017)

Release 0.5.1 is a minor release and contains new features and bug fixes:
- Added reflexive transitions (thanks to @janLo)
- Wildcards for reflexive (`wildcard_same`) and all (`wildcard_all`) destinations are `Machine` class variables now which can be altered if necessary.
- Add LICENSE to packaged distribution (thanks to @bachp)
- Bug #211: `prepare` and `finalized` had not been called for HierarchicalMachines (thanks to @booware) 

## 0.5.0 (March, 2017)
Release 0.5.0 is a major release:
- CHANGED API: `MachineError` is now limited to internal error and has been replaced by `AttributeError` and `ValueError` where applicable (thanks to @ankostis)
- CHANGED API: Phasing out `add_self`; `model=None` will add NO model starting from next major release; use `model='self'` instead.
- Introduced deprecation warnings for upcoming changes concerning `Machine` keywords `model` and `add_self`
- Introduced `Machine.remove_transition` (thanks to @PaleNeutron)
- Introduced `Machine._create_state` for easier subclassing of states
- `LockedMachine` now supports custom context managers for each model (thanks to @paulbovbel)
- `Machine.before/after_state_change` can now be altered dynamically (thanks to @peendebak)
- `Machine.add_ordered_transitions` now supports `prepare`, `conditons`, `unless`, `before` and `after` (thanks to @aforren1)
- New `prepare_event` and `finalize_event` keywords to handle transitions globally (thanks to @ankostis)
- New `show_auto_transitions` keyword for `GraphMachine.__init__` (default `False`); if enabled, show auto transitions in graph
- New `show_roi` keyword for `GraphMachine._get_graph` (default `False`); if `True`, show only reachable states in retrieved graph
- Test suite now skips contextual tests (e.g. pygraphviz) if dependencies cannot be found (thanks to @ankostis)
- Improved string representation of several classes (thanks to @ankostis)
- Improved `LockedMachine` performance by removing recursive locking
- Improved graph layout for nested graphs
- `transitions.extensions.nesting.AGraph` has been split up into `Graph` and `NestedGraph` for easier maintenance
- Fixed bug related to pickling `RLock` in nesting
- Fixed order of callback execution (thanks to @ankostis)
- Fixed representation of condition names in graphs (thanks to @cemoody)

## 0.4.3 (December, 2016)
Release 0.4.3 is a minor release and contains bug fixes and several new features:
- Support dynamic model addition via `Machine.add_model` (thanks to @paulbovbel)
- Allow user to explicitly pass a lock instance or context manager to LockedMachine (thanks to @paulbovbel)
- Fixed issue related to parsing of HSMs (thanks to @steval and @user2154065 from SO)
- When `State` is passed to `Machine.add_transition`, it will check if the state (and not just the name) is known to the machine

## 0.4.2 (October, 2016)
Release 0.4.2 contains several new features and bugfixes:
- Machines can work with multiple models now (thanks to @gemerden)
- New `initial` keyword for nested states to automatically enter a child
- New `Machine.trigger` method to trigger events by name (thanks to @IwanLD)
- Bug fixes related to remapping in nested (thanks to @imbaczek)
- Log messages in `Transition.execute` and `Machine.__init__` have been reassigned to DEBUG log level (thanks to @ankostis)
- New `Machine.get_triggers` method to return all valid transitions from (a) certain state(s) (thanks to @limdauto and @guilhermecgs)

## 0.4.1 (July, 2016)
Release 0.4.1 is a minor release containing bug fixes, minor API changes, and community feedback:
- `async` is renamed to `queued` since it describes the mechanism better
- HierarchicalStateMachine.is_state now provides `allow_substates` as an optional argument(thanks to @jonathanunderwood)
- Machine can now be used in scenarios where multiple inheritance is required (thanks to @jonathanunderwood)
- Adds support for tox (thanks to @medecau and @aisbaa)
- Bug fixes:
    - Problems with conditions shown multiple times in graphs
    - Bug which omitted transitions with same source and destination in diagrams (thanks to @aisbaa)
    - Conditions passed incorrectly when HSMs are used as a nested state
    - Class nesting issue that prevented pickling with dill
    - Two bugs in HierarchicalStateMachine (thanks to @ajax2leet)
    - Avoided recursion error when naming a transition 'process' (thanks to @dceresuela)


- Minor PEP8 fixes (thanks to @medecau)

## 0.4.0 (April, 2016)
Release 0.4 is a major release that includes several new features:
- New `async` Machine keyword allows queueing of transitions (thanks to @khigia)
- New `name` Machine keyword customizes transitions logger output for easier debugging of multiple running instances
- New `prepare` Transition keyword for callbacks before any 'conditions' are checked (thanks to @TheMysteriousX)
- New `show_conditions` GraphSupport keyword adds condition checks to dot graph edges (thanks to @khigia)
- Nesting now supports custom (unicode) substate separators
- Nesting no longer requires a leaf state (e.g. to_C() does not enter C_1 automatically)
- Factory for convenient extension mixins
- Numerous minor improvements and bug fixes

## 0.3.1 (January 3, 2016)
Mostly a bug fix release. Changes include:
- Fixes graphing bug introduced in 0.3.0 (thanks to @wtgee)
- Fixes bug in dynamic addition of before/after callbacks (though this is a currently undocumented feature)
- Adds coveralls support and badge
- Adds a few tests to achieve near-100% coverage

## 0.3.0 (January 2, 2016)
Release 0.3 includes a number of new features (nesting, multithreading, and graphing) as well as bug fixes and minor improvements:
- Support for nested states (thanks to @aleneum)
- Basic multithreading support for function access (thanks to @aleneum)
- Basic graphing support via graphviz (thanks to @svdgraaf)
- Stylistic edits, minor fixes, and improvements to README
- Expanded and refactored tests
- Minor bug fixes

## 0.2.9 (November 10, 2015)
- Enabled pickling in Python 3.4 (and in < 3.4 with the dill module)
- Added reference to generating Transition in EventData objects
- Fixed minor bugs

## 0.2.8 (August, 6, 2015)
- README improvements, added TOC, and typo fixes
- Condition checks now receive optional data
- Removed invasive basicConfig() call introduced with logging in 0.2.6

## 0.2.7 (July 27, 2015)
- Fixed import bug that prevented dependency installation at setup

## 0.2.6 (July 26, 2015)
- Added rudimentary logging for key transition and state change events
- Added generic before/after callbacks that apply to all state changes
- Ensured string type compatibility across Python 2 and 3

## 0.2.5 (May 4, 2015)
- Added ability to suppress invalid trigger calls
- Shorthand definition of transitions via lists

## 0.2.4 (March 11, 2015)
- Automatic detection of predefined state callbacks
- Fixed bug in automatic transition creation
- Added Changelog

## 0.2.3 (January 14, 2015)
- Added travis-ci support
- Cleaned up and PEP8fied code
- Added 'unless' argument to transitions that mirrors 'conditions'

## 0.2.2 (December 28, 2014)
- Python 2/3 compatibility
- Added automatic to_{state}() methods
- Added ability to easily add ordered transitions
