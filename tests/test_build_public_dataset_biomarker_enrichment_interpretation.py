import json
from pathlib import Path
import pandas as pd
from core.data.build_public_dataset_biomarker_enrichment_interpretation import run

def test_gdc_star_header_recovery_with_preamble(tmp_path):
    downloads=tmp_path/'downloads'; downloads.mkdir()
    star=downloads/'sample.rna_seq.augmented_star_gene_counts.tsv'
    star.write_text('#metadata line\n#another line\ngene_id\tgene_name\tgene_type\tunstranded\nENSG00000148773.12\tMKI67\tprotein_coding\t10\nENSG00000091831.20\tESR1\tprotein_coding\t20\nENSG00000141510.18\tTP53\tprotein_coding\t30\n', encoding='utf-8')
    fi=tmp_path/'fi.tsv'; pd.DataFrame({'feature':['ENSG00000148773.12','ENSG00000091831.20','ENSG00000141510.18'], 'importance':[.5,.3,.2]}).to_csv(fi, sep='\t', index=False)
    out=tmp_path/'out'; primary=tmp_path/'gene_annotation.tsv'
    cfg={'version':'v0.4.0-a42-fix3','bundle_name':'test','project':'OpenMultiOmics-Cancer-Atlas','upstream_version':'v0.4.0-a41','upstream_commit':'ff9bcd6','inputs':{'feature_importance':str(fi),'kmeans_clusters':str(tmp_path/'missing.tsv'),'model_input_matrix_candidates':[],'primary_annotation_output':str(primary),'annotation_source_roots':[str(downloads)],'gene_annotation_candidates':[str(primary)],'clinical_metadata_candidates':[]},'outputs':{'interpretation_dir':str(out),'recovered_gene_annotation':str(out/'recovered.tsv'),'annotation_recovery_diagnostics':str(out/'recovery_diag.tsv'),'annotation_resolution_diagnostics':str(out/'resolution_diag.tsv'),'resolved_feature_importance':str(out/'resolved.tsv'),'unresolved_features':str(out/'unresolved.tsv'),'gene_set_enrichment':str(out/'enrich.tsv'),'gene_set_enrichment_png':str(out/'enrich.png'),'cluster_feature_signal':str(out/'cluster.tsv'),'clinical_bridge_status':str(out/'clinical.tsv'),'interpretation_report':str(out/'report.md'),'summary_json':str(out/'summary.json')},'parameters':{'top_n_features':3,'top_n_report_features':3,'cluster_top_n_features':2,'figure_dpi':80,'minimum_resolved_fraction_for_biomarker_review':0.25,'minimum_gene_sets_with_matches_for_biomarker_review':1,'star_header_scan_lines':20}}
    p=tmp_path/'cfg.json'; p.write_text(json.dumps(cfg), encoding='utf-8')
    s=run(p)
    assert s['annotation_recovery']['recovered_annotation_rows']==3
    assert s['feature_importance']['resolved_top_n']==3
    assert s['gene_set_enrichment']['gene_sets_with_matches']>=1
    assert s['ready_for_biomarker_review'] is True
    diag=pd.read_csv(out/'recovery_diag.tsv', sep='\t')
    assert int(diag.loc[0,'header_row_detected']) == 2
