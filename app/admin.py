from django.contrib import admin
from .models import SegmentAvecCompte

@admin.register(SegmentAvecCompte)
class SegmentAvecCompteAdmin(admin.ModelAdmin):
    list_display = ('member_id', 'decimal_mois', 'duree_moyenne_voyage')

