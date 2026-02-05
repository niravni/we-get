import pytest
from docopt import docopt, DocoptExit

from tget.core.tget import WG
import tget.core.tget as tget_core


@pytest.mark.parametrize(
    'argv, exp_res',
    [
        [None, {'arguments': None, 'parguments': {}, 'tget_run': 0}],
        [['--search', 'ubuntu'],  {
            'arguments': {
                '--config': [],
                '--filter': [],
                '--genre': [],
                '--get-list': 0,
                '--help': 0,
                '--json': 0,
                '--links': 0,
                '--list': 0,
                '--quality': [],
                '--results': [],
                '--search': ['ubuntu'],
                '--sfw': 0,
                '--sort-type': [],
                '--target': ['all'],
                '--version': 0
            },
            'parguments': {
                '--search': ['ubuntu'], '--target': ['all']}, 'tget_run': 1
        }],
    ]
)
def test_parse_arguments(argv, exp_res):
    wg = WG()
    if argv is None:
        with pytest.raises(DocoptExit):
            wg.parse_arguments()
        assert vars(wg) == exp_res
        with pytest.raises(DocoptExit):
            wg.parse_arguments(argv)
        assert vars(wg) == exp_res
    else:
        wg.parse_arguments(argv)
        assert vars(wg) == exp_res


@pytest.mark.parametrize(
    'argv, exp_res',
    [
        [
            [],
            {
                '--filter': [], '--genre': [], '--get-list': 0, '--help': 0, '--json': 0,
                '--links': 0, '--list': 0, '--quality': [], '--results': [], '--search': [],
                '--sort-type': [], '--target': ['all'], '--version': 0, '--config': [], '--sfw': 0}
        ],
    ],
)
def test_we_get_docopt(argv, exp_res):
    res = docopt(tget_core.__doc__, argv=argv)
    assert exp_res == res
