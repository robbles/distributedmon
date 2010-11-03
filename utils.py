from __future__ import with_statement
from fabric.api import *
import fabric.network
import functools, subprocess, signal

# Time for a task to time out
TASK_TIMEOUT = 30
# Time for ping to time out
PING_TIMEOUT = 3

class TimeoutException(Exception):
    """ Used to signal a timeout on a task """
    pass

# Utility functions
def unreliable(func):
    """
    Wraps a task to mask connection failures with a warning
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Start timeout to break out of unresponsive task
        def timeout(*args):
            raise TimeoutException
        signal.signal(signal.SIGALRM, timeout)
        signal.alarm(TASK_TIMEOUT)

        if not ping(env.host_string, PING_TIMEOUT):
            puts('Host is down, skipping...')
            return
        try:
            result = func(*args, **kwargs)
            signal.alarm(0)
            return result
        except SystemExit:
            warn('Host %s is inaccessible!' % env.host_string)
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except BaseException, e:
            warn('Error running task on host %s: %s' % (env.host_string, e))

    return wrapper

def ping(host, timeout):
    """ 
    Returns True if a host is up (responds to ping within timeout seconds) 
    """
    result = subprocess.call(['ping', '-c1', '-W', str(timeout), host], stdout=subprocess.PIPE)
    return result == 0


# Patch fabric's password prompting
def throw_up(*args):
    puts('Host is asking for different password, failing...')
    raise SystemExit
fabric.network.original_prompt = fabric.network.prompt_for_password
fabric.network.prompt_for_password = throw_up
        
