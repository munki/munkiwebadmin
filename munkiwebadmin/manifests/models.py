#from django.db import models
# we're not using a database for out manifests, so no need to import models
import os
import plistlib
import subprocess
from catalogs.models import Catalog

from django.conf import settings

USERNAME_KEY = settings.MANIFEST_USERNAME_KEY
APPNAME = settings.APPNAME
REPO_DIR = settings.MUNKI_REPO_DIR
try:
    GIT = settings.GIT_PATH
except:
    GIT = None
    

def is_git_repo(directory_path):
    if GIT is None:
        return False
    try:
        os.chdir(directory_path)
    except OSError:
        # directory doesn't exist or we don't have rights
        return False
    cmd = [GIT, 'status']
    retcode = subprocess.call(cmd, shell=False, bufsize=-1,
                              stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE)
    return (retcode == 0)


def git_add_and_commit(filepath, committer, action='modified'):
    if GIT and os.path.exists(filepath):
        (directory, item) = os.path.split(filepath)
        os.chdir(directory)
        cmd = [GIT, 'add', item]
        proc = subprocess.Popen(cmd, shell=False, bufsize=-1,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE)
        (output, error) = proc.communicate()
        if proc.returncode:
            print >> sys.stderr, "Could not add %s to git index:" % filepath
            print >> sys.stderr, error
            return -1
            
        manifests_path = os.path.join(REPO_DIR, 'manifests/')
        if filepath.startswith(manifests_path):
            itempath = filepath[len(manifests_path):]
        else:
            itempath = filepath
            
        # set up GIT author info
        author_name = (committer.first_name +  
                       ' ' + committer.last_name)
        if author_name == ' ':
            author_name = committer.username
        author_email = (committer.email or 
                                   '%s@munkiweb' % committer.username)
        author_info = '%s <%s>' % (author_name, author_email)
        commit_msg = ('%s %s manifest \'%s\' via %s' 
                      % (author_name, action, itempath, APPNAME))
        cmd = [GIT, 'commit', '-m', commit_msg, '--author', author_info]
        proc = subprocess.Popen(cmd, shell=False, bufsize=-1,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE)
        (output, error) = proc.communicate()
        if proc.returncode:
            print "Git commit of changes to %s failed" % filepath
            print error
            return -1
    return 0


def trimVersionString(version_string):
    ### from munkilib.updatecheck
    """Trims all lone trailing zeros in the version string after major/minor.

    Examples:
      10.0.0.0 -> 10.0
      10.0.0.1 -> 10.0.0.1
      10.0.0-abc1 -> 10.0.0-abc1
      10.0.0-abc1.0 -> 10.0.0-abc1
    """
    if version_string == None or version_string == '':
        return ''
    version_parts = version_string.split('.')
    # strip off all trailing 0's in the version, while over 2 parts.
    while len(version_parts) > 2 and version_parts[-1] == '0':
        del(version_parts[-1])
    return '.'.join(version_parts)


class Manifest(object):
    @classmethod
    def list(cls):
        '''Returns a list of available manifests'''
        manifests_path = os.path.join(REPO_DIR, 'manifests')
        manifests = []
        skipdirs = ['.svn', '.git']
        for dirpath, dirnames, filenames in os.walk(manifests_path):
            for skipdir in skipdirs:
                if skipdir in dirnames:
                    dirnames.remove(skipdir)
            subdir = dirpath[len(manifests_path):]
            for name in filenames:
                if name.startswith('.'):
                    # don't process these
                    continue
                manifests.append(os.path.join(subdir, name).lstrip('/'))
        return manifests
    
    
    @classmethod
    def new(cls):
        '''Returns an empty manifest object'''
        manifest = {}
        for section in ['catalogs', 'included_manifests', 'managed_installs',
                        'managed_uninstalls', 'managed_updates',
                        'optional_installs']:
            manifest[section] = []
        return manifest
    
    
    @classmethod
    def read(cls, manifest_name):
        '''Gets the contents of a manifest'''
        manifest_path = os.path.join(
            REPO_DIR, 'manifests', manifest_name.replace(':', '/'))
        if os.path.exists(manifest_path):
            try:
                return plistlib.readPlist(manifest_path)
            except Exception, errmsg:
                return {}
        else:
            return {}
            
            
    @classmethod
    def write(cls, manifest_name, manifest, committer):
        '''Writes a changed manifest to disk'''
        # muck about with the username
        if '_user_name' in manifest:
            user_list = manifest['_user_name']
            if user_list:
                manifest[USERNAME_KEY] = user_list[0]
            del manifest['_user_name']
        manifest_path = os.path.join(
            REPO_DIR, 'manifests', manifest_name.replace(':', '/'))
        #try:
        #    prev_manifest = plistlib.readPlist(manifest_path)
        #except Exception:
        #    pass
        try:
            plistlib.writePlist(manifest, manifest_path)
            git_add_and_commit(manifest_path, committer)
        except Exception, errmsg:
            pass
            # need to deal with errors
            
    
    @classmethod
    def getValidInstallItems(cls, manifest_name):
        '''Returns a list of valid install item names for the
        given manifest, taking into account the current list
        of catalogs'''
        manifest = cls.read(manifest_name)
        if manifest:
            catalog_list = manifest.get('catalogs', [])
            install_items = set()
            for catalog in catalog_list:
                catalog_items = Catalog.detail(catalog)
                if catalog_items:
                    catalog_item_names = list(set(
                        [item['name'] for item in catalog_items]))
                    install_items.update(catalog_item_names)
                    catalog_item_names_with_versions = list(set(
                        [item['name'] + '-' + 
                        trimVersionString(item['version'])
                        for item in catalog_items]))
                    install_items.update(catalog_item_names_with_versions)
            return list(install_items)
        return []


    @classmethod
    def getSuggestedInstallItems(cls, manifest_name):
        '''Returns a list of suggested install item names for the
        given manifest, taking into account the current list
        of catalogs, and filtering out updates and versions.'''
        install_items = []
        manifest = cls.read(manifest_name)
        if manifest:
            catalog_list = manifest.get('catalogs', [])
            for catalog in catalog_list:
                catalog_items = Catalog.detail(catalog)
                install_items = list(set(
                    [item['name'] for item in catalog_items
                    if not item.get('update_for')]))
        return install_items
                
            
    @classmethod
    def findUserForManifest(cls, manifest_name):
        '''returns a username for a given manifest name'''
        if USERNAME_KEY:
            return cls.read(manifest_name).get(USERNAME_KEY, '')
    