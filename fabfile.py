from __future__ import with_statement
from fabric.api import *
from fabric.contrib.files import exists, contains, append
from fabric.state import connections
import fabric.network
import sys, os, urllib, contextlib, functools, subprocess

# Make sure we're working in the same directory as fabfile.py
fabdir = os.path.dirname(env.real_fabfile)
os.chdir(fabdir)

# Username and private key file
env.user = 'usf_ubc_gnutella3'
env.password = 'eece411'
env.key_filename = os.path.join(fabdir, 'id_rsa')
env.warn_only = True

# Get host data and utilities 
sys.path.append(fabdir)
import utils, hosts

# Allow -H option on command-line to override host list
if not env.hosts:
    env.hosts = hosts.all_hosts

########### Tasks! ########

@utils.unreliable
def whoami():
    """
    Gets the username of the current logged in user 
    """
    run('whoami')


@utils.unreliable
def install_java():
    """
    Installs java on the target machine
    """
    if not exists('jre1.6.0_16'):
        run('wget http://www.ece.ubc.ca/%7Esamera/TA/411/project/jre.tar.gz 2>&1', pty=True)
        run('tar xf ~/jre.tar.gz')
        append('export PATH=/home/%s/jre1.6.0_16/bin:$PATH' % env.user, '~/.bash_profile')
    else:
        puts('Java is already installed on this node!')

@utils.unreliable
def install_fabric():
    with settings(warn_only=False):
        # Update yum and install setuptools and gcc
        sudo('yum -y makecache && yum -y install gcc python-setuptools-devel')

        # Install paramiko and fabric
        sudo('easy_install -f http://pypi.python.org/packages/source/p/paramiko/paramiko-1.7.6.zip paramiko fabric')

    # Check to see if we actually have the fab tool now
    run('fab --version')


@utils.unreliable
def check_java():
    """
    Checks the version of java installed on this machine.
    """
    run('java -version 2>&1 | head -1')


@utils.unreliable
def check_fabric():
    run('fab --version')


@utils.unreliable
def status():
    """ 
    Retrieves the status of a node, including:
    * If it's up (responds to ping)
    * Whether we can login
    * Disk space used
    * Disk space available
    * Uptime and current load
    * Whether Java has been installed

    The status is stored on the node at ~/status/status_[hostname].txt
    """
    # Ping it and return of it's down
    up = utils.ping(env.host_string, 10)
    puts('Host is ' + ('UP' if up else 'DOWN'))
    if not up:
        return False

    # Hide output while we're getting info
    with hide('running', 'stdout', 'stderr'):
        # Check if we can SSH in and run a command
        try:
            run('whoami')
        except SystemExit:
            puts('Unable to log in!')
            return False

        # Get the status info
        disk = run('df -h').split('\n')[1].split()
        uptime = run('uptime')
        java = run('java -version 2>&1 | head -1')
        python = run('python --version 2>&1')

        # Make status folder if necessary
        run('mkdir -p status')
        status_file = './status/status_%s.txt' % env.host_string

        # Empty or make status file
        run('echo -n > %s' % status_file)
        
        # Write status to file
        append('Disk space used: %s' % disk[2], status_file)
        append('Disk space free: %s' % disk[3], status_file)
        append('Uptime and load: %s' % uptime, status_file)
        append('Java: %s' % ('not installed' if java.failed else java), status_file)
        append('Python: %s' % ('not installed' if python.failed else python), status_file)
    
    # Print out status that was written
    run('cat %s' % status_file)
    return True


@utils.unreliable
def update_files():
    sys.path.append(os.path.dirname(__file__))
    from scp import SCPClient
    client = SCPClient(connections[env.host_string]._transport)
    client.put(['fabfile.py', 'utils.py', 'hosts.py', 'scp.py', 'id_rsa'])


@utils.unreliable
def install_crontab():
    """
    Installs a cron entry on the remote machine that runs the status sync script
    """
    # Create crontab file with echo
    run('echo "* * * * * /usr/bin/fab -f /home/%(user)s/fabfile.py random_sync" > crontab' % env)

    # Call crontab [file] to install
    run('crontab ./crontab')

    # Start crond and add it to /etc/rc.local
    sudo('/etc/init.d/crond restart')
    append('/etc/init.d/crond start', '/etc/rc.local', use_sudo=True)

    
def sync_status():
    """
    Fetches all statuses from a remote node and writes to local status cache
    """
    # Run status update, if not, write status file for host and return
    # TODO: make this run in it's own cron job (locally?)
    host_up = status()

    # Make local status folder if necessary
    local('mkdir -p ./status' % env)
    local('mkdir -p ./statusnew' % env)

    # Write out status if failed to contact server
    if not host_up:
        status_file = './status/status_%(host_string)s.txt' % env
        local('echo DOWN >> %s' % status_file)  
        return

    # Pull remote server's status files using scp
    from scp import SCPClient
    client = SCPClient(connections[env.host_string]._transport)
    client.get('~/status/*', './statusnew/' % env, preserve_times=True)

    # Use rsync to update older files
    local('rsync -auv ./statusnew/* ./status/' % env)

    # Write time into last_sync file
    local('date > ./status/last_sync' % env)

    # TODO: build html from statuses and save atomically?


def random_sync():
    """
    Syncs with another random node, chosen from the host list.
    """
    import random
    host = random.choice(env.hosts)
    puts('Syncing with host %s' % host)

    with settings(host_string=host):
        sync_status()

    # Don't run this for every node, just the first given
    exit()



########### End of Tasks ########



