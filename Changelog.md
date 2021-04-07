# Changelog

## 0.8.8 (April 2021)

Release 0.8.8 is a minor release and contains a bugfix and several new or improved features:

- Bugfix #526: `AsyncMachine` does not remove models when `remove_models` is called (thanks @Plazas87)
- Feature #517: Introduce `try/except` for finalize callbacks in `Machine` and `HierachicalMachine`. Thus, errors occurring in finalize callbacks will be suppressed and only the original error will be raised.
- Feature #520: Show references in graphs and markup. Introduce `MarkupMachine.format_references` to tweak reference formatting (thanks @StephenCarboni)
- Feature #485: Introduce `Machine.on_exception` to handle raised exceptions in callbacks (thanks @thedrow)
- Feature #527: `Machine.get_triggers` now supports `State` and `Enum` as arguments (thanks @luup2k)
- Feature #506: `NestedState` and `HierachicalMachine.add_states` now accept (lists of) states and enums as `initial` parameter

## 0.8.7 (February 2021)

Release 0.8.7 is a minor release and contains a bugfix, a feature and adjustments to internal processes:

- State configuration dictionaries passed to `HierarchicalMachine` can also use `states` as a keyword to define substates. If `children` and `states` are present, only `children` will be considered.
- Feature #500: `HierarchicalMachine` with custom separator now adds `is_state` partials for nested states (e.g. `is_C.s3.a()`) to models (thanks @alterscape)
- Bugfix #512: Use `model_attribute` consistently in `AsyncMachine` (thanks @thedrow)
- Testing now treats most warnings as errors (thanks @thedrow)
- As a consequence, `pygraphviz.Agraph` in `diagrams_pygraphviz` are now copied by `transitions` since `AGraph.copy` as of version `1.6` does not close temporary files appropriately
- `HierarchicalMachine` now checks whether `state_cls`, `event_cls` and `transition_cls` have been subclassed from nested base classes (e.g. `NestedState`) to prevent hard to debug inheritance errors

## 0.8.6 (December 2020)

Release 0.8.6 is a minor release and contains bugfixes and new features:

- `HierarchicalMachine.add_states` will raise a `ValueError` when an `Enum` name contains the currently used `NestedState.separator`.
- Bugfix #486: Reset `NestedState._scope` when enter/exit callbacks raise an exception (thanks @m986883511)
- Bugfix #488: Let `HierarchicalMachine._get_trigger` which is bound to `model.trigger` raise a `MachineError` for invalid events and `AttributeError` for unknown events (thanks @hsharrison)
- Introduced `HierarchicalMachine.has_trigger` to determine whether an event is valid for an HSM
- Feature #490: `AsyncMachine` features an event queue dictionary for individual models when `queued='model'` (thanks @jekel)
- Feature #490: `Machine.remove_model` will now also remove model events from the event queue when `queued=True`
- Feature #491: `Machine.get_transitions` and its HSM counterpart now accept `Enum` and `State` for `source` and `dest` (thanks @thedrow)

## 0.8.5 (November 2020)

Release 0.8.5 is a minor release and contains bugfixes:

- `AsyncMachine.switch_model_context` is expected to be `async` now for easier integration of async code during model switch.
- Bugfix #478: Initializing a machine with `GraphSupport` threw an exception when initial was set to a nested or parallel state (thanks @nickvazztau)

## 0.8.4 (October 2020)

Release 0.8.4 is a minor release and contains bugfixes as well as new features:

- Bugfix #477: Model callbacks were not added to a LockedHierarchicalMachine when the machine itself served as a model (thanks @oliver-goetz)
- Bugfix #475: Clear collection of tasks to prevent memory leak when initializing many models (thanks @h-nakai)
- Feature #474: Added static `AsyncMachine.protected_tasks` list which can be used to prevent `transitions` to cancel certain tasks.
- Feature: Constructor of `HierarchicalMachine` now accepts substates ('A_1_c') and parallel states (['A', 'B']) as `initial` parameter

## 0.8.3 (September 2020)

Release 0.8.3 is a minor release and contains several bugfixes mostly related to `HierarchicalStateMachine`:

- Feature #473: Assign `is_<model_attribute>_<state_name>` instead of `is_<state_name>` when `model_attribute != "state"` to enable multiple versions of such convenience functions. A warning will be raised when `is_<state_name>` is used. (thanks @artofhuman)
- Similarly, auto transitions (`to_<state_name>`) will be assigned as `to_<model_attribute>_<state_name>`. `to_<state_name>` will work as before but raise a warning until version 0.9.0.
- Bugfix: `allow_substates` did not consider enum states
- Feature: Nested enums can now be passed in a dict as `children` with `initial` parameter
- Bugfix #449: get_triggers/get_transitions did not return nested triggers correctly (thanks @alexandretanem)
- Feature #452: Improve handling of label attributes in custom diagram states and `TransitionGraphSupport` (thanks @badiku)
- Bugfix #456: Prevent parents from overriding (falsy) results of their children's events (thanks @alexandretanem)
- Bugfix #458: Entering the same state caused key errors when transition was defined on a parent (thanks @matlom)
- Bugfix #459: Do not remove current timeout runner in AsyncTimeout to prevent accidental overrides (thanks @rgov)
- Rewording of `State.enter/exit` debug message emitted when callbacks have been processed.
- Bugfix #370: Fix order of `before_state_change/before` and `after/after_state_change` in `AsyncMachine` (thanks @tzoiker and @vishes-shell)
- Bugfix #470: `Graph.get_graph()` did not consider `enum` states when `show_roi=True` (thanks @termim)

## 0.8.2 (June 2020)

Release 0.8.2 is a minor release and contains several bugfixes and improvements:

- Bugfix #438: Improved testing without any optional `graphviz` package
- Bugfix: `_check_event_result` failed when model was in parallel state
- Bugfix #440: Only allow explicit `dest=None` in `Machine.add_transition` (not just falsy) for internal transitions (thanks @Pathfinder216)
- Bugfix #419: Fix state creation of nested enums (thanks @thedrow)
- Bugfix #428: HierarchicalGraphMachine did not find/apply styling for parallel states (thanks @xiaohuihui1024)
- Bugfix: `Model.trigger` now considers the machine's and current state's `ignore_invalid_triggers` attribute and can be called with non-existing events (thanks @potens1)
- Bugfix: Child states may not have been exited when the executed transition had been defined on a parent (thanks @thedrow)
- Feature #429: Introduced `transitions.extensions.asyncio.AsyncTimeout` as a state decorator to avoid threads used in `transitions.extensions.state.Timeout` (thanks @potens1)
- Feature #444: `transitions` can now be tested online at mybinder.org
- PR #418: Use sets instead of lists to cache already covered transitions in nested state machines (thanks @thedrow)
- PR #422: Improve handling of unresolved attributes for easier inheritance (thanks @thedrow)
- PR #445: Refactored AsyncMachine to enable trio/anyio override

## 0.8.1 (April 2020)

Release 0.8.1 is a minor release of HSM improvements and bugfixes in the diagram and async extension:

- Feature: Introduced experimental `HierarchicalAsync(Graph)Machine`
- Feature #405: Support for nested Enums in `HierarchicalMachine` (thanks @thedrow)
- Bugfix #400: Fix style initialization when initial state is an `Enum` (thanks @kbinpgh)
- Bugfix #403: AsyncMachine.dispatch now returns a boolean as expected (thanks @thedrow)
- Bugfix #413: Improve diagram output for `HierarchicalMachine` (thanks @xiaohuihui1024)
- Increased coverage (thanks @thedrow)
- Introduced `xdist` for parallel testing with `pytest` (thanks @thedrow)

## 0.8.0 (March 2020)

Release 0.8.0 is a major release and introduces asyncio support for Python 3.7+, parallel state support and some bugfixes:

- Feature: `HierarchicalMachine` has been rewritten to support parallel states. Please have a look at the ReadMe.md to check what has changed.
  - The previous version can be found in `transitions.extensions.nesting_legacy` for now
- Feature: Introduced `AsyncMachine` (see discussion #259); note that async HSMs are not yet supported
- Feature #390: String callbacks can now point to properties and attributes (thanks @jsenecal)
- Bugfix: Auto transitions are added multiple times when add_states is called more than once
- Bugfix: Convert state.\_name from `Enum` into strings in `MarkupMachine` when necessary
- Bugfix #392: Allow `Machine.add_ordered_transitions` to be called without the initial state (thanks @mkaranki and @facundofc)
- `GraphMachine` now attempts to fall back to `graphviz` when importing `pygraphviz` fails
- Not implemented/tested so far (contributions are welcome!):
  - Proper Graphviz support of parallel states
  - AsyncHierachicalMachine

## 0.7.2 (January 2020)

Release 0.7.2 is a minor release and contains bugfixes and a new feature:

- Bugfix #386: Fix transitions for enums with str behavior (thanks @artofhuman)
- Bugfix #378: Don't mask away KeyError when executing a transition (thanks @facundofc)
- Feature #387: Add support for dynamic model state attribute (thanks @v1k45)

## 0.7.1 (September 2019)

Release 0.7.1 is a minor release and contains several documentation improvements and a new feature:

- Feature #334: Added Enum (Python 3.4+: `enum` Python 2.7: `enum34`) support (thanks @artofhuman and @justinttl)
- Replaced test framework `nosetests` with `pytest` (thanks @artofhuman)
- Extended `add_ordered_transitions` documentation in `Readme.md`
- Collected code snippets from earlier discussions in `examples/Frequently asked questions.ipynb`
- Improved stripping of `long_description` in `setup.py` (thanks @artofhuman)

## 0.7.0 (August 2019)

Release 0.7.0 is a major release with fundamental changes to the diagram extension. It also introduces an intermediate `MarkupMachine` which can be used to transfer and (re-)initialize machine configurations.

- Feature #263: `MarkupMachine` can be used to retrieve a Machine's dictionary representation
  - `GraphMachine` uses this representation for Graphs now and does not rely on `Machine` attributes any longer
- Feature: The default value of `State.ignore_invalid_triggers` changed to `None`. If it is not explicitly set, the `Machine`'s value is used instead.
- Feature #325: transitions now supports `pygraphviz` and `graphviz` for the creation of diagrams. Currently, `GraphMachine` will check for `pygraphviz` first and fall back to `graphviz`. To use `graphviz` directly pass `use_pygraphiv=False` to the constructor of `GraphMachine`
- Diagram style has been overhauled. Have a look at `GraphMachine`'s attributes `machine_attributes` and `style_attributes` to adjust it to your needs.
- Feature #305: Timeouts and other features are now marked in the graphs
- Bugfix #343: `get_graph` was not assigned to models added during machine runtime

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
- Narrowed warnings filter to prevent output cluttering by other 3rd party modules (thanks to @ksandeep)
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
- Added automatic to\_{state}() methods
- Added ability to easily add ordered transitions
