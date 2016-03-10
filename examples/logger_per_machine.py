"""
When instantiating multiple Machine, it can be useful to set different
logger per machine. This example show how to add a specific log prefix
for each machine log entry.
"""
import logging
import transitions


def make_fsm(no):
    # Similar result could be achieved with single logger
    # but using here a LoggerAdapter
    logger = logging.getLogger(__name__ + '[FSM%s] ' % no)
    logger.setLevel(logging.INFO)

    return transitions.Machine(
        states=['A', 'B', 'C'],
        initial='A',
        transitions=[
            {'trigger': 'e0', 'source': 'A', 'dest': 'B'},
            {'trigger': 'e1', 'source': 'B', 'dest': 'C'},
        ],
        specific_logger=logger
    )


logging.basicConfig()

fsm0 = make_fsm(0)
fsm1 = make_fsm(1)

fsm0.e0()
fsm1.e0()
fsm0.e1()
fsm1.e1()
