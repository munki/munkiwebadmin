from django.contrib import admin
from reports.models import Machine, MunkiReport

class MachineAdmin(admin.ModelAdmin):
    list_display = ('hostname', 'mac', 'username', 'last_munki_update',
                    'last_inventory_update')
    
class MunkiReportAdmin(admin.ModelAdmin):
    list_display = ('hostname', 'mac', 'timestamp', 'errors', 'warnings')
    
admin.site.register(Machine, MachineAdmin)
admin.site.register(MunkiReport, MunkiReportAdmin)