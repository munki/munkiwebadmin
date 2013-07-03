#from django.db import models
# we're not using a database for out manifests, so no need to import models
import os
import subprocess
import plistlib
from catalogs.models import Catalog
from django.conf import settings

USERNAME_KEY = settings.MANIFEST_USERNAME_KEY
APPNAME = settings.APPNAME
REPO_DIR = settings.MUNKI_REPO_DIR
try:
    GIT = settings.GIT_PATH
except:
    GIT = None

class MunkiGit:
    """A simple interface for some common interactions with the git binary"""
    cmd = GIT
    args = []
    results = {}

    @staticmethod
    def __chdirToMatchPath(aPath):
        """Changes the current working directory to the same parent directory as
        the file specified in aPath. Example:
        "/Users/Shared/munki_repo/manifests/CoolManifest" would change
        directories to "/Users/Shared/munki_repo/manifests" """
        os.chdir(os.path.dirname(aPath))

    def runGit(self, customArgs=None):
        """Executes the git command with the current set of arguments and
        returns a dictionary with the keys 'output', 'error', and
        'returncode'. You can optionally pass an array into customArgs to
        override the self.args value without overwriting them."""
        customArgs = self.args if customArgs == None else customArgs
        proc = subprocess.Popen([self.cmd] + customArgs,
                                shell=False,
                                bufsize=-1,
                                stdin = subprocess.PIPE,
                                stdout = subprocess.PIPE,
                                stderr = subprocess.PIPE)
        (output, error) = proc.communicate()
        self.results = {"output": output, 
                       "error": error, "returncode": proc.returncode}
        return self.results

    def pathIsRepo(self, aPath):
        """Returns True if the path is in a Git repo, false otherwise."""
        self.__chdirToMatchPath(aPath)
        self.runGit(['status', aPath])
        return self.results['returncode'] == 0

    def commitFileAtPathForCommitter(self, aPath, committer):
        """Commits the file at 'aPath'. This method will also automatically
        generate the commit log appropriate for the status of aPath where status
        would be 'modified', 'new file', or 'deleted'"""
        self.__chdirToMatchPath(aPath)
        # get the author information
        author_name = committer.first_name + ' ' + committer.last_name
        author_name = author_name if author_name != ' ' else committer.username
        author_email = (committer.email or 
                        "%s@munkiwebadmin" % committer.username)
        author_info = '%s <%s>' % (author_name, author_email)

        # get the status of the file at aPath
        statusResults = self.runGit(['status', aPath])
        statusOutput = statusResults['output']
        if statusOutput.find("new file:") != -1:
            action = 'created'
        elif statusOutput.find("modified:") != -1:
            action = 'modified'
        elif statusOutput.find("deleted:") != -1:
            action = 'deleted'
        else:
            action = 'did something with'

        # determine the path relative to REPO_DIR for the file at aPath
        manifests_path = os.path.join(REPO_DIR, 'manifests')
        itempath = aPath
        if aPath.startswith(manifests_path):
            itempath = aPath[len(manifests_path):]

        # generate the log message
        log_msg = ('%s %s manifest \'%s\' via %s'
                  % (author_name, action, itempath, APPNAME))
        self.runGit(['commit', '-m', log_msg, '--author', author_info])
        if self.results['returncode'] != 0:
            print "Failed to commit changes to %s" % aPath
            print self.results['error']
            return -1
        return 0

    def addFileAtPathForCommitter(self, aPath, aCommitter):
        """Commits a file to the Git repo."""
        self.__chdirToMatchPath(aPath)
        self.runGit(['add', aPath])
        if self.results['returncode'] == 0:
            self.commitFileAtPathForCommitter(aPath, aCommitter)

    def deleteFileAtPathForCommitter(self, aPath, aCommitter):
        """Deletes a file from the filesystem and Git repo."""
        self.__chdirToMatchPath(aPath)
        self.runGit(['rm', aPath])
        if self.results['returncode'] == 0:
            self.commitFileAtPathForCommitter(aPath, aCommitter)


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
    @staticmethod
    def __pathForManifestNamed(aManifestName):
        '''Returns the path to a manifest given the manifest's name'''
        return os.path.join(
            REPO_DIR, 'manifests', aManifestName.replace(':', '/'))

    @classmethod
    def list(cls):
        '''Returns a list of available manifests'''
        manifests_path = os.path.join(REPO_DIR, 'manifests')
        manifests = []
        skipdirs = ['.svn', '.git', '.AppleDouble']
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
        manifest_path = cls.__pathForManifestNamed(manifest_name)
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
        manifest_path = cls.__pathForManifestNamed(manifest_name)
        #try:
        #    prev_manifest = plistlib.readPlist(manifest_path)
        #except Exception:
        #    pass
        try:
            plistlib.writePlist(manifest, manifest_path)
            if GIT:
                git = MunkiGit()
                git.addFileAtPathForCommitter(manifest_path, committer)
        except Exception, errmsg:
            pass
            # need to deal with errors

    @classmethod
    def delete(cls, manifest_name, committer):
        '''Deletes a manifest from the disk'''
        manifest_path = cls.__pathForManifestNamed(manifest_name)
        if not os.path.exists(manifest_path):
            print "Unable to find manifest to delete '%s'" % manifest_path
            return -1

        if not GIT:
            os.remove(manifest_path)
        else:
            git = MunkiGit()
            git.deleteFileAtPathForCommitter(manifest_path, committer)

    @classmethod
    def getInstallItemNames(cls, manifest_name):
        '''Returns a dictionary containing types of install items
        valid for the current manifest'''
        suggested_set = set()
        update_set = set()
        versioned_set = set()
        manifest = cls.read(manifest_name)
        if manifest:
            catalog_list = manifest.get('catalogs', ['all'])
            for catalog in catalog_list:
                catalog_items = Catalog.detail(catalog)
                if catalog_items:
                    suggested_names = list(set(
                        [item['name'] for item in catalog_items
                         if not item.get('update_for')]))
                    suggested_set.update(suggested_names)
                    update_names = list(set(
                        [item['name'] for item in catalog_items
                         if item.get('update_for')]))
                    update_set.update(update_names)
                    item_names_with_versions = list(set(
                        [item['name'] + '-' + 
                        trimVersionString(item['version'])
                        for item in catalog_items]))
                    versioned_set.update(item_names_with_versions)
        return {'suggested': list(suggested_set),
                'updates': list(update_set),
                'with_version': list(versioned_set)}

    @classmethod
    def findUserForManifest(cls, manifest_name):
        '''returns a username for a given manifest name'''
        if USERNAME_KEY:
            return cls.read(manifest_name).get(USERNAME_KEY, '')
