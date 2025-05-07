from django.db import models

class SegmentAvecCompte(models.Model):
    member_id = models.CharField(max_length=30)
    decimal_mois = models.IntegerField()
    duree_moyenne_voyage = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"Membre {self.member_id} - Cluster Features"
