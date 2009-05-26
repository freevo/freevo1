"""
Freevo Version number
"""
__version__ = '1.9.0'

runtime  = '0.3.1'
mmpython = '0.4.10'

try:
    import revision
    _revision = revision.__revision__
except ImportError:
    try:
        import src.revision as revision
        _revision = revision.__revision__
    except ImportError:
        _revision = 'Unknown'

_version = __version__
if _version.endswith('-svn'):
    version = _version.split('-svn')[0] + ' r%s' % _revision
else:
    version = _version
