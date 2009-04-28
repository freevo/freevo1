"""
Freevo Version number
"""
__version__ = '1.8.4-svn'

runtime  = '0.3.1'
mmpython = '0.4.10'

try:
    import revision
    _revision = revision.__revision__
except ImportError:
    _revision = 'Unknown'

_version = __version__
if _version.endswith('-svn'):
    _version = _version.split('-svn')[0] + ' r%s' % _revision
