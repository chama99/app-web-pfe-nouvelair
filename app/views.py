from django.http import HttpResponse
from django.shortcuts import render, redirect
import pandas as pd
from django.contrib.auth.views import LoginView
from .models import SegmentAvecCompte
from datetime import datetime
from sklearn.preprocessing import MultiLabelBinarizer
import os
from django.conf import settings
from django.core.files.storage import default_storage
from django.contrib import messages  # ✅ pour messages success et error

class CustomLoginView(LoginView):
    template_name = 'login.html'


def process_avec_compte(df_avec_compte):
    df_sales = df_avec_compte[df_avec_compte['ACTION'] == 'Sales'].copy()
    df_sales['SCH_DEP_DT'] = pd.to_datetime(df_sales['SCH_DEP_DT'], errors='coerce')
    df_sales['SCH_ARR_DT'] = pd.to_datetime(df_sales['SCH_ARR_DT'], errors='coerce')
    df_sales['MOIS'] = df_sales['SCH_DEP_DT'].dt.month

    grouped = df_sales.groupby("MEMBER_ID")
    df_features = pd.DataFrame()
    df_features["MOIS_VOYAGES"] = grouped["MOIS"].agg(lambda x: sorted(x.dropna().unique().tolist()))
    df_features = df_features.reset_index()

    mlb = MultiLabelBinarizer(classes=range(1, 13))
    vecteurs = mlb.fit_transform(df_features['MOIS_VOYAGES'])
    df_vecteurs = pd.DataFrame(vecteurs, columns=[f'mois_{i}' for i in range(1, 13)])
    df_mois = pd.concat([df_features[['MEMBER_ID']], df_vecteurs], axis=1)
    df_mois['binary_mois'] = df_mois[[f'mois_{i}' for i in range(1, 13)]].apply(lambda row: ''.join(row.astype(str)), axis=1)
    df_mois['decimal_mois'] = df_mois['binary_mois'].apply(lambda x: int(x, 2))
    df_mois = df_mois[['MEMBER_ID', 'decimal_mois']].copy()

    df_t = df_sales[df_sales['IS_ROUND_TRIP'] == 'T']
    df_grouped = df_t[['MEMBER_ID', 'TKT_NO', 'SCH_DEP_DT', 'SCH_ARR_DT']].dropna()
    df_voyage_duree = df_grouped.groupby(['MEMBER_ID', 'TKT_NO']).agg(
        date_depart_min=('SCH_DEP_DT', 'min'),
        date_arrivee_max=('SCH_ARR_DT', 'max')
    ).reset_index()
    df_voyage_duree['duree_voyage_jours'] = (df_voyage_duree['date_arrivee_max'] - df_voyage_duree['date_depart_min']).dt.days

    df_f = df_sales[df_sales['IS_ROUND_TRIP'] == 'F'].sort_values(by=['MEMBER_ID', 'SCH_DEP_DT'])
    paired_trips = []
    for member_id, group in df_f.groupby('MEMBER_ID'):
        group = group.reset_index(drop=True)
        used_indices = set()
        for i, row in group.iterrows():
            if i in used_indices:
                continue
            dep_port, arr_port, dep_date = row['DEP_PORT'], row['ARR_PORT'], row['SCH_DEP_DT']
            tkt_no = row['TKT_NO']
            possible_returns = group[
                (group['DEP_PORT'] == arr_port) &
                (group['ARR_PORT'] == dep_port) &
                (group['SCH_DEP_DT'] > dep_date) &
                ((group['SCH_DEP_DT'] - dep_date).dt.days <= 60)
            ]
            possible_returns = possible_returns[~possible_returns.index.isin(used_indices)]
            if not possible_returns.empty:
                retour_row = possible_returns.iloc[0]
                used_indices.update([i, retour_row.name])
                paired_trips.append({
                    'MEMBER_ID': member_id,
                    'TKT_NO': tkt_no,
                    'duree_voyage_jours': (retour_row['SCH_DEP_DT'] - dep_date).days
                })
    df_paired = pd.DataFrame(paired_trips)

    colonnes = ['MEMBER_ID', 'TKT_NO', 'duree_voyage_jours']
    df_voyage_duree = df_voyage_duree[colonnes] if not df_voyage_duree.empty else pd.DataFrame(columns=colonnes)
    df_paired = df_paired if not df_paired.empty else pd.DataFrame(columns=colonnes)
    df_combined = pd.concat([df_voyage_duree, df_paired], ignore_index=True)

    df_duree = df_combined.groupby('MEMBER_ID').agg(
        duree_moyenne_voyage=('duree_voyage_jours', 'mean')
    ).reset_index()

    df_merged = df_mois.merge(df_duree, on='MEMBER_ID', how='left')
    return df_merged


def upload_csv_view(request):
    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'segmenter_avec_compte':
            file_path = os.path.join(settings.MEDIA_ROOT, 'transactions.csv')
            if not os.path.exists(file_path):
                messages.error(request, "❌ Aucun fichier global trouvé.")
                return redirect('upload_csv')

            df = pd.read_csv(file_path)
            df_avec_compte = df[df['MEMBER_ID'].notna()].copy()
            df_features = process_avec_compte(df_avec_compte)

            SegmentAvecCompte.objects.all().delete()
            for _, row in df_features.iterrows():
                SegmentAvecCompte.objects.create(
                    member_id=row['MEMBER_ID'],
                    decimal_mois=row['decimal_mois'],
                    duree_moyenne_voyage=row['duree_moyenne_voyage']
                )

            messages.success(request, f"✅ {len(df_features)} voyageurs avec compte segmentés et enregistrés.")
            return redirect('upload_csv')

        elif 'csv_file' in request.FILES:
            csv_file = request.FILES['csv_file']
            file_path = os.path.join(settings.MEDIA_ROOT, 'transactions.csv')
            with default_storage.open(file_path, 'wb+') as destination:
                for chunk in csv_file.chunks():
                    destination.write(chunk)

            messages.success(request, "✅ Fichier enregistré avec succès.")
            return redirect('upload_csv')

    return render(request, 'upload.html')
