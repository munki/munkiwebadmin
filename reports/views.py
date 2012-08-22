from django.http import HttpResponse, HttpRequest, HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.core.context_processors import csrf
from django.views.decorators.csrf import csrf_exempt
from django.core.urlresolvers import reverse
from django.http import Http404
from django.contrib.auth.decorators import login_required

from models import Machine, MunkiReport


import base64
import bz2
import plistlib
import re
from datetime import datetime


@csrf_exempt
def submit(request, submission_type):
    if request.method != 'POST':
        raise Http404
    
    submit = request.POST
    mac = submit.get('mac')
    client = None
    if mac:
        try:
            machine = Machine.objects.get(mac=mac)
        except Machine.DoesNotExist:
            machine = Machine(mac=mac)
    if machine:
        try:
            report = MunkiReport.objects.get(machine=machine)
        except MunkiReport.DoesNotExist:
            report = MunkiReport(machine=machine)
    
    if machine and report:
        machine.hostname = submit.get('name', '<NO NAME>')
        machine.remote_ip = request.META['REMOTE_ADDR']
        machine.last_munki_update = datetime.now()
        if 'username' in submit:
            machine.username = submit.get('username')
        if 'location' in submit:
            machine.location = submit.get('location')
        
        report.runtype = submit.get('runtype')
        report.timestamp = datetime.now()
        
        if submission_type == 'postflight':
            report.runstate = u"done"
            if 'base64bz2report' in submit:
                report.update_report(submit.get('base64bz2report'))
            report.save()
            # extract machine data from the report
            report_data = report.get_report()
            if 'MachineInfo' in report_data:
                machine.os_version = report_data['MachineInfo'].get('os_vers')
                machine.cpu_arch = report_data['MachineInfo'].get('arch')
            machine.available_disk_space = \
                report_data.get('AvailableDiskSpace') or 0
            hwinfo = {}
            if 'SystemProfile' in report_data.get('MachineInfo', []):
                for profile in report_data['MachineInfo']['SystemProfile']:
                    if profile['_dataType'] == 'SPHardwareDataType':
                        hwinfo = profile._items[0]
                        break
            if hwinfo:
                machine.machine_model = hwinfo.get('machine_model')
                machine.cpu_type = hwinfo.get('cpu_type')
                machine.cpu_speed = hwinfo.get('current_processor_speed')
                machine.ram = hwinfo.get('physical_memory')
                machine.serial_number = hwinfo.get('serial_number')
            
            machine.save()
            return HttpResponse("Postflight report submmitted for %s.\n" 
                                 % submit.get('name'))
        
        if submission_type == 'preflight':
            report.runstate = u"in progress"
            report.activity = report.encode(
                {"Updating": "preflight"})
            report.save()
            machine.save()
            return HttpResponse(
                "Preflight report submmitted for %s.\n" %
                 submit.get('name'))
    
        if submission_type == 'report_broken_client':
            report.runstate = u"broken client"
            report.report = None
            report.errors = 1
            report.warnings = 0
            report.save()
            machine.save()
            return HttpResponse(
                "Broken client report submmitted for %s.\n" %
                 submit.get('name'))
    
    return HttpResponse("No report submitted.\n")


@login_required
def index(request):
    
    all_reports = MunkiReport.objects.all()
    
    return render_to_response('reports/index.html', 
        {'reports': all_reports,
         'user': request.user,
         'page': 'reports'})


@login_required
def overview(request, order_by=None, reverse=None):
    
    error_reports = \
        MunkiReport.objects.filter(errors__gt=0).order_by('-timestamp')
    warning_reports = \
        MunkiReport.objects.filter(warnings__gt=0).order_by('-timestamp')
    activity_reports = \
        MunkiReport.objects.filter(
            activity__isnull=False).order_by('-timestamp')
    total_reports_count = MunkiReport.objects.count()
                
    # need to preprocess activity data for the template
    activity_report_data = []
    for report in activity_reports:
        report_data = {}
        report_data['machine'] = report.machine
        #report_data['report'] = report.get_report()
        report_data['runtype'] = report.runtype
        report_data['console_user'] = report.console_user
        report_data['timestamp'] = report.timestamp
        activity = report.get_activity()
        if 'Updating' in activity:
            report_data['updating'] = activity['Updating']
        install_items = len(activity.get('ItemsToInstall',[]))
        install_results = len(activity.get('InstallResults',[]))
        removal_items = len(activity.get('ItemsToRemove',[]))
        removal_results = len(activity.get('RemovalResults',[]))
        apple_updates = len(activity.get('AppleUpdates',[]))
        report_data['pending_installs'] = max(
            (install_items + apple_updates) - install_results, 0)
        report_data['pending_removals'] = removal_items - removal_results
        report_data['install_results'] = install_results
        report_data['removal_results'] = removal_results
        activity_report_data.append(report_data)
    
    return render_to_response('reports/overview.html',
        {'error_reports': error_reports,
         'warning_reports': warning_reports,
         'activity_reports': activity_report_data,
         'total_reports_count': total_reports_count,
         'user': request.user,
         'page': 'overview'})


@login_required
def detail(request, mac):
    machine = None
    if mac:
        try:
            machine = Machine.objects.get(mac=mac)
        except Machine.DoesNotExist:
            raise Http404
    else:
        raise Http404
    
    report_plist = {}
    if machine:
        try:
            report = MunkiReport.objects.get(machine=machine)
            report_plist = report.get_report()
        except MunkiReport.DoesNotExist:
            pass
            
    # handle items that were installed during the most recent run
    install_results = {}
    for result in report_plist.get('InstallResults', []):
        nameAndVers = result['name'] + '-' + result['version']
        if result['status'] == 0:
            install_results[nameAndVers] = "installed"
        else:
            install_results[nameAndVers] = 'error'
    
    if install_results:         
        for item in report_plist.get('ItemsToInstall', []):
            name = item.get('display_name', item['name'])
            nameAndVers = ('%s-%s' 
                % (name, item['version_to_install']))
            item['install_result'] = install_results.get(
                nameAndVers, 'pending')
                
        for item in report_plist.get('ManagedInstalls', []):
            if 'version_to_install' in item:
                name = item.get('display_name', item['name'])
                nameAndVers = ('%s-%s' 
                    % (name, item['version_to_install']))
                if install_results.get(nameAndVers) == 'installed':
                    item['installed'] = True
                    
    # handle items that were removed during the most recent run
    # this is crappy. We should fix it in Munki.
    removal_results = {}
    for result in report_plist.get('RemovalResults', []):
        m = re.search('^Removal of (.+): (.+)$', result)
        if m:
            try:
                if m.group(2) == 'SUCCESSFUL':
                    removal_results[m.group(1)] = 'removed'
                else:
                    removal_results[m.group(1)] = m.group(2)
            except IndexError:
                pass
    
    if removal_results:
        for item in report_plist.get('ItemsToRemove', []):
            name = item.get('display_name', item['name'])
            item['install_result'] = removal_results.get(
                name, 'pending')
            if item['install_result'] == 'removed':
                if not 'RemovedItems' in report_plist:
                    report_plist['RemovedItems'] = [item['name']]
                elif not name in report_plist['RemovedItems']:
                    report_plist['RemovedItems'].append(item['name'])
                
    if 'managed_uninstalls_list' in report_plist:
        report_plist['managed_uninstalls_list'].sort()
        
    return render_to_response('reports/detail.html',
                              {'machine': machine,
                               'report': report_plist,
                               'user': request.user,
                               'page': 'reports'})


def raw(request, mac):
    machine = None
    if mac:
        try:
            machine = Machine.objects.get(mac=mac)
        except Machine.DoesNotExist:
            raise Http404
    else:
        raise Http404
    
    report_plist = {}
    if machine:
        try:
            report = MunkiReport.objects.get(machine=machine)
            report_plist = report.decode(report.report)
        except MunkiReport.DoesNotExist:
            pass
    
    return HttpResponse(plistlib.writePlistToString(report_plist),
        mimetype='text/plain')


def lookup_ip(request):
    return HttpResponse(request.META['REMOTE_ADDR'], mimetype='text/plain')
    